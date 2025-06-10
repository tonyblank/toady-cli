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
        else:
            # In normal mode, show a user-friendly message
            handle_error(e, show_traceback=False)


if __name__ == "__main__":
    main()
