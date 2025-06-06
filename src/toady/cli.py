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
@click.option("--pr", "pr_number", required=True, type=int, help="Pull request number")
@click.option("--pretty", is_flag=True, help="Output in human-readable format")
def fetch(pr_number: int, pretty: bool) -> None:
    """Fetch unresolved review threads from a pull request."""
    click.echo(f"Fetching unresolved threads for PR #{pr_number}")
    # TODO: Implement fetch logic


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
