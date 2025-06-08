"""Main CLI interface for Toady."""

import json

import click

from toady import __version__
from toady.github_service import GitHubAPIError, GitHubAuthenticationError
from toady.reply_service import (
    CommentNotFoundError,
    ReplyRequest,
    ReplyService,
    ReplyServiceError,
)


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

    # Post the reply using the reply service
    reply_service = ReplyService()
    try:
        request = ReplyRequest(comment_id=comment_id, reply_body=body)
        reply_info = reply_service.post_reply(request)

        if pretty:
            click.echo("✅ Reply posted successfully")
            if reply_info["reply_url"]:
                click.echo(f"🔗 View reply at: {reply_info['reply_url']}")
            if reply_info["reply_id"]:
                click.echo(f"📝 Reply ID: {reply_info['reply_id']}")
        else:
            # Return JSON response with actual reply information
            result = {
                "comment_id": comment_id,
                "reply_posted": True,
                "reply_id": reply_info["reply_id"],
                "reply_url": reply_info["reply_url"],
                "created_at": reply_info["created_at"],
                "author": reply_info["author"],
            }
            click.echo(json.dumps(result))

    except CommentNotFoundError as e:
        if pretty:
            click.echo(f"❌ Comment not found: {e}", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "comment_not_found",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except GitHubAuthenticationError as e:
        if pretty:
            click.echo(f"❌ Authentication failed: {e}", err=True)
            click.echo("💡 Try running: gh auth login", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "authentication_failed",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except (ReplyServiceError, GitHubAPIError) as e:
        if pretty:
            click.echo(f"❌ Failed to post reply: {e}", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "api_error",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)


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
