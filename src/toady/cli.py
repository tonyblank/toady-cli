"""Main CLI interface for Toady."""

import click

from toady import __version__


@click.group()
@click.version_option(version=__version__, prog_name="toady")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Toady - GitHub PR review management tool.

    Efficiently manage GitHub pull request code reviews from the command line.
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--pr",
    "pr_number",
    required=True,
    type=int,
    help="Pull request number to fetch review threads from",
    metavar="NUMBER",
)
@click.option(
    "--pretty",
    is_flag=True,
    help="Output in human-readable format instead of JSON",
)
@click.option(
    "--resolved",
    is_flag=True,
    help="Include resolved threads in addition to unresolved ones",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of threads to fetch (default: 100)",
    metavar="COUNT",
)
@click.pass_context
def fetch(
    ctx: click.Context, pr_number: int, pretty: bool, resolved: bool, limit: int
) -> None:
    """Fetch review threads from a GitHub pull request.

    By default, only unresolved review threads are fetched. Use --resolved
    to include resolved threads as well.

    Examples:

        toady fetch --pr 123

        toady fetch --pr 123 --pretty

        toady fetch --pr 123 --resolved --limit 50
    """
    # Validate PR number
    if pr_number <= 0:
        raise click.BadParameter("PR number must be positive", param_hint="--pr")

    # Validate limit
    if limit <= 0:
        raise click.BadParameter("Limit must be positive", param_hint="--limit")
    if limit > 1000:
        raise click.BadParameter("Limit cannot exceed 1000", param_hint="--limit")

    # Show what we're fetching
    thread_type = "all threads" if resolved else "unresolved threads"
    if pretty:
        click.echo(f"🔍 Fetching {thread_type} for PR #{pr_number} (limit: {limit})")
    else:
        # For JSON output, we'll just return the data without progress messages
        pass

    # TODO: Implement actual fetch logic in subsequent tasks
    # For now, show placeholder behavior
    if pretty:
        click.echo("📝 Found 0 review threads")
    else:
        click.echo("[]")


@cli.command()
@click.option(
    "--comment-id", required=True, type=str, help="ID of the comment to reply to"
)
@click.option("--body", required=True, type=str, help="Reply message body")
def reply(comment_id: str, body: str) -> None:
    """Post a reply to a specific review comment."""
    click.echo(f"Replying to comment {comment_id}")
    # TODO: Implement reply logic


@cli.command()
@click.option(
    "--thread-id", required=True, type=str, help="ID of the thread to resolve/unresolve"
)
@click.option("--undo", is_flag=True, help="Unresolve the thread instead of resolving")
def resolve(thread_id: str, undo: bool) -> None:
    """Mark a review thread as resolved or unresolved."""
    action = "Unresolving" if undo else "Resolving"
    click.echo(f"{action} thread {thread_id}")
    # TODO: Implement resolve logic


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
