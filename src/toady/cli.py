"""Main CLI interface for Toady."""

import click

from toady import __version__
from toady.commands.fetch import fetch
from toady.commands.reply import reply
from toady.commands.resolve import resolve
from toady.commands.schema import schema
from toady.error_handling import handle_error
from toady.exceptions import ToadyError


@click.group()
@click.version_option(version=__version__, prog_name="toady")
@click.option(
    "--debug",
    is_flag=True,
    help="Show detailed error information for debugging",
    envvar="TOADY_DEBUG",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Toady - GitHub PR review management tool.

    Efficiently manage GitHub pull request code reviews from the command line.
    Integrates with GitHub CLI (gh) to fetch, reply to, and resolve review threads.

    \b
    Prerequisites:
      • GitHub CLI (gh) must be installed and authenticated
      • Run 'gh auth login' if not already authenticated
      • Ensure you have access to the target repository

    \b
    Core workflow:
      1. Fetch review threads: toady fetch
      2. Reply to comments: toady reply --id <thread_id> --body "Fixed!"
      3. Resolve threads: toady resolve --thread-id <thread_id>

    \b
    Agent-friendly usage:
      • All commands output JSON by default for easy parsing
      • Use --format pretty for human-readable output
      • Thread and comment IDs are consistently formatted
      • Error responses include structured error codes

    \b
    Common patterns:
    \b
      Interactive workflow:
        toady fetch                              # Auto-detect PR
        toady reply --id <id> --body "Response"
        toady resolve --thread-id <id>
    \b
      Automated workflow:
        toady fetch | jq '.[] | .thread_id'
        toady reply --id <id> --body "Automated response"
        toady resolve --all --pr 123 --yes
    \b
    Troubleshooting:
    \b
      Authentication issues:
        • Run: gh auth login
        • Verify: gh auth status
        • Ensure repo scope: gh auth login --scopes repo
    \b
      Common errors:
        • "authentication_required": GitHub CLI not logged in
        • "pr_not_found": PR doesn't exist or no repository access
        • "rate_limit_exceeded": Too many API calls, wait and retry
        • "thread_not_found": Invalid thread ID or thread was deleted
    \b
      Debug mode:
        • Set TOADY_DEBUG=1 or use --debug flag for detailed error info
        • Use --format pretty for human-readable output during testing
    \b
      ID issues:
        • Always use thread IDs from 'toady fetch' output
        • Use 'toady reply --help-ids' for complete ID documentation
        • Thread IDs (PRRT_, PRT_, RT_) are more reliable than comment IDs
    \b
      Rate limiting:
        • Use --limit option to reduce API calls
        • Add delays between operations in scripts
        • Check limits: gh api rate_limit

    For detailed command help: toady <command> --help
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


# Register commands
cli.add_command(fetch)
cli.add_command(reply)
cli.add_command(resolve)
cli.add_command(schema)


def main() -> None:
    """Entry point for the CLI."""
    try:
        cli()
    except ToadyError as e:
        # Handle known toady errors with user-friendly messages
        import os

        debug = os.environ.get("TOADY_DEBUG", "").lower() in ("1", "true", "yes")
        handle_error(e, show_traceback=debug)
    except Exception as e:
        # Handle unexpected errors
        import os

        debug = os.environ.get("TOADY_DEBUG", "").lower() in ("1", "true", "yes")
        if debug:
            # In debug mode, show the full traceback
            raise
        # In normal mode, show a user-friendly message
        handle_error(e, show_traceback=False)


if __name__ == "__main__":
    main()
