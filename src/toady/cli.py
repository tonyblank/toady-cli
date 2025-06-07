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
    "--comment-id",
    required=True,
    type=str,
    help="GitHub comment ID (numeric ID or node ID starting with IC_)",
    metavar="ID",
)
@click.option(
    "--body",
    required=True,
    type=str,
    help="Reply message body (1-65536 characters)",
    metavar="TEXT",
)
@click.option(
    "--pretty",
    is_flag=True,
    help="Output in human-readable format instead of JSON",
)
@click.pass_context
def reply(ctx: click.Context, comment_id: str, body: str, pretty: bool) -> None:
    """Post a reply to a specific review comment.

    Reply to comments using either numeric IDs (e.g., 123456789) or
    GitHub node IDs (e.g., IC_kwDOABcD12MAAAABcDE3fg).

    Examples:

        toady reply --comment-id 123456789 --body "Fixed in latest commit"

        toady reply --comment-id IC_kwDOABcD12MAAAABcDE3fg --body "Good catch!"

        toady reply --comment-id 123456789 --body "Thanks for the review" --pretty
    """
    # Validate comment ID format
    comment_id = comment_id.strip()
    if not comment_id:
        raise click.BadParameter(
            "Comment ID cannot be empty", param_hint="--comment-id"
        )

    # Validate comment ID format - either numeric or GitHub node ID
    if not (comment_id.isdigit() or comment_id.startswith("IC_")):
        raise click.BadParameter(
            "Comment ID must be numeric (e.g., 123456789) or a "
            "GitHub node ID starting with 'IC_'",
            param_hint="--comment-id",
        )

    # Additional validation for node IDs
    if comment_id.startswith("IC_") and len(comment_id) < 10:
        raise click.BadParameter(
            "GitHub node ID appears too short to be valid",
            param_hint="--comment-id",
        )

    # Validate reply body
    body = body.strip()
    if not body:
        raise click.BadParameter("Reply body cannot be empty", param_hint="--body")

    if len(body) > 65536:
        raise click.BadParameter(
            "Reply body cannot exceed 65,536 characters", param_hint="--body"
        )

    # Check for potentially problematic content
    if body.startswith("@") and pretty:
        # This is just a warning, not an error
        click.echo(
            "⚠️  Note: Reply starts with '@' - this will mention users",
            err=True,
        )

    # Show what we're doing
    if pretty:
        click.echo(f"💬 Posting reply to comment {comment_id}")
        click.echo(f"📝 Reply: {body[:100]}{'...' if len(body) > 100 else ''}")
    else:
        # For JSON output, we'll just return the result without progress messages
        pass

    # TODO: Implement actual reply posting logic in subsequent tasks
    # For now, show placeholder behavior
    if pretty:
        click.echo("✅ Reply posted successfully")
        click.echo(
            f"🔗 View reply at: https://github.com/owner/repo/pull/123#discussion_r{comment_id}"
        )
    else:
        # Return minimal JSON response
        import json

        result = {
            "comment_id": comment_id,
            "reply_posted": True,
            "reply_url": f"https://github.com/owner/repo/pull/123#discussion_r{comment_id}",
        }
        click.echo(json.dumps(result))


@cli.command()
@click.option(
    "--thread-id",
    required=True,
    type=str,
    help="GitHub thread ID (numeric ID or node ID starting with PRT_)",
    metavar="ID",
)
@click.option(
    "--undo",
    is_flag=True,
    help="Unresolve the thread instead of resolving it",
)
@click.option(
    "--pretty",
    is_flag=True,
    help="Output in human-readable format instead of JSON",
)
@click.pass_context
def resolve(ctx: click.Context, thread_id: str, undo: bool, pretty: bool) -> None:
    """Mark a review thread as resolved or unresolved.

    Resolve or unresolve review threads using either numeric IDs or
    GitHub node IDs (e.g., PRT_kwDOABcD12MAAAABcDE3fg).

    Examples:

        toady resolve --thread-id 123456789

        toady resolve --thread-id PRT_kwDOABcD12MAAAABcDE3fg --undo

        toady resolve --thread-id 123456789 --pretty
    """
    # Validate thread ID format
    thread_id = thread_id.strip()
    if not thread_id:
        raise click.BadParameter("Thread ID cannot be empty", param_hint="--thread-id")

    # Validate thread ID format - either numeric or GitHub node ID
    if not (thread_id.isdigit() or thread_id.startswith("PRT_")):
        raise click.BadParameter(
            "Thread ID must be numeric (e.g., 123456789) or a "
            "GitHub node ID starting with 'PRT_'",
            param_hint="--thread-id",
        )

    # Additional validation for node IDs
    if thread_id.startswith("PRT_") and len(thread_id) < 12:
        raise click.BadParameter(
            "GitHub node ID appears too short to be valid",
            param_hint="--thread-id",
        )

    # Show what we're doing
    action = "Unresolving" if undo else "Resolving"
    action_past = "unresolved" if undo else "resolved"
    action_symbol = "🔓" if undo else "🔒"

    if pretty:
        click.echo(f"{action_symbol} {action} thread {thread_id}")
    else:
        # For JSON output, we'll just return the result without progress messages
        pass

    # TODO: Implement actual resolve/unresolve logic in subsequent tasks
    # For now, show placeholder behavior
    if pretty:
        click.echo(f"✅ Thread {action_past} successfully")
        click.echo(
            f"🔗 View thread at: https://github.com/owner/repo/pull/123#discussion_r{thread_id}"
        )
    else:
        # Return minimal JSON response
        import json

        result = {
            "thread_id": thread_id,
            "action": "unresolve" if undo else "resolve",
            "success": True,
            "thread_url": f"https://github.com/owner/repo/pull/123#discussion_r{thread_id}",
        }
        click.echo(json.dumps(result))


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
