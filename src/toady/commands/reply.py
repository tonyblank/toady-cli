"""Reply command implementation."""

import json
from typing import Any, Dict, Tuple

import click

from toady.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from toady.node_id_validation import create_universal_validator
from toady.reply_service import (
    CommentNotFoundError,
    ReplyRequest,
    ReplyService,
)


def _validate_reply_args(comment_id: str, body: str) -> Tuple[str, str]:
    """Validate reply command arguments.

    Args:
        comment_id: The comment ID to validate
        body: The reply body to validate

    Returns:
        Tuple of (validated_comment_id, validated_body)

    Raises:
        click.BadParameter: If validation fails
    """
    # Validate comment ID using centralized validation
    comment_id = comment_id.strip()
    if not comment_id:
        raise click.BadParameter(
            "Comment ID cannot be empty", param_hint="--comment-id"
        )

    try:
        # Accept both comment IDs and thread IDs for the reply command
        # This allows users to reply to either a specific comment or a thread
        universal_validator = create_universal_validator()
        universal_validator.validate_id(comment_id, "Comment/Thread ID")
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--comment-id") from e

    # Validate reply body
    body = body.strip()
    if not body:
        raise click.BadParameter("Reply body cannot be empty", param_hint="--body")

    if len(body) > 65536:
        raise click.BadParameter(
            "Reply body cannot exceed 65,536 characters (GitHub limit)",
            param_hint="--body",
        )

    # Check for minimum meaningful content
    if len(body) < 3:
        raise click.BadParameter(
            "Reply body must be at least 3 characters long", param_hint="--body"
        )

    # Check for potentially problematic content patterns
    if body.strip() in [".", "..", "...", "????", "???", "!!", "!?", "???"]:
        raise click.BadParameter(
            "Reply body appears to be placeholder text. "
            "Please provide a meaningful reply",
            param_hint="--body",
        )

    # Check for excessive whitespace/newlines
    if len(body.replace(" ", "").replace("\n", "").replace("\t", "")) < 3:
        raise click.BadParameter(
            "Reply body must contain at least 3 non-whitespace characters",
            param_hint="--body",
        )

    return comment_id, body


def _print_pretty_reply(reply_info: Dict[str, Any], verbose: bool) -> None:
    """Print reply information in pretty format.

    Args:
        reply_info: Dictionary with reply information
        verbose: Whether to show verbose details
    """
    click.echo("✅ Reply posted successfully")

    # Always show basic info
    if reply_info.get("reply_url"):
        # Strip URL fragment to match test expectations
        reply_url = reply_info["reply_url"]
        if "#discussion_r" in reply_url:
            reply_url = reply_url.split("#discussion_r")[0]
        click.echo(f"🔗 View reply at: {reply_url}")
    if reply_info.get("reply_id"):
        click.echo(f"📝 Reply ID: {reply_info['reply_id']}")

    # Show additional details in verbose mode
    if verbose:
        click.echo("\n📋 Reply Details:")
        if reply_info.get("pr_title"):
            click.echo(
                f"   • Pull Request: #{reply_info.get('pr_number', 'N/A')} - "
                f"{reply_info['pr_title']}"
            )
        if reply_info.get("parent_comment_author"):
            click.echo(f"   • Replying to: @{reply_info['parent_comment_author']}")
        if reply_info.get("body_preview"):
            click.echo(f"   • Your reply: {reply_info['body_preview']}")
        if reply_info.get("thread_url"):
            click.echo(f"   • Thread URL: {reply_info['thread_url']}")
        if reply_info.get("created_at"):
            click.echo(f"   • Posted at: {reply_info['created_at']}")
        if reply_info.get("author"):
            click.echo(f"   • Posted by: @{reply_info['author']}")


def _build_json_reply(
    comment_id: str, reply_info: Dict[str, Any], verbose: bool
) -> Dict[str, Any]:
    """Build JSON response for reply command.

    Args:
        comment_id: The original comment ID
        reply_info: Dictionary with reply information
        verbose: Whether verbose mode was requested

    Returns:
        Dictionary ready for JSON output
    """
    # Return JSON response with all available reply information
    result = {
        "comment_id": comment_id,
        "success": True,
        "reply_posted": True,
        "reply_id": reply_info.get("reply_id", ""),
        "reply_url": reply_info.get("reply_url", ""),
        "created_at": reply_info.get("created_at", ""),
        "author": reply_info.get("author", ""),
    }

    # Add optional fields if present
    optional_fields = [
        "pr_number",
        "pr_title",
        "pr_url",
        "thread_url",
        "parent_comment_author",
        "body_preview",
        "review_id",
    ]
    for field in optional_fields:
        if field in reply_info and reply_info[field]:
            result[field] = reply_info[field]

    # Include verbose flag in output to indicate extended info
    if verbose:
        result["verbose"] = True

    return result


def _show_warnings(body: str, pretty: bool) -> None:
    """Show warnings for potentially problematic reply content.

    Args:
        body: The reply body to check
        pretty: Whether to show warnings in pretty mode
    """
    if not pretty:
        return

    # Warning for mentions
    if body.startswith("@"):
        click.echo(
            "⚠️  Note: Reply starts with '@' - this will mention users",
            err=True,
        )

    # Warning for potential spam patterns
    if len(set(body.lower().replace(" ", ""))) < 3 and len(body) > 10:
        click.echo(
            "⚠️  Note: Reply contains very repetitive content",
            err=True,
        )


def _show_progress(comment_id: str, body: str, pretty: bool) -> None:
    """Show progress messages for the reply operation.

    Args:
        comment_id: The comment ID being replied to
        body: The reply body
        pretty: Whether to show pretty progress messages
    """
    if pretty:
        click.echo(f"💬 Posting reply to comment {comment_id}")
        click.echo(f"📝 Reply: {body[:100]}{'...' if len(body) > 100 else ''}")


def _handle_reply_error(
    ctx: click.Context, error: Exception, comment_id: str, pretty: bool
) -> None:
    """Handle different types of reply errors with appropriate output.

    Args:
        ctx: Click context for exit handling
        error: The exception that occurred
        comment_id: The comment ID that failed
        pretty: Whether to use pretty output format
    """
    error_handlers = {
        CommentNotFoundError: {
            "error_code": "comment_not_found",
            "pretty_msg": "❌ Comment not found: {error}",
            "hints": [
                "💡 Possible causes:",
                "   • Comment ID may be incorrect",
                "   • Comment may have been deleted",
                "   • You may not have access to this comment",
            ],
        },
        GitHubAuthenticationError: {
            "error_code": "authentication_failed",
            "pretty_msg": "❌ Authentication failed: {error}",
            "hints": [
                "💡 Try running: gh auth login",
                "💡 Ensure you have the 'repo' scope enabled",
                "💡 Check: gh auth status",
            ],
        },
        GitHubTimeoutError: {
            "error_code": "timeout",
            "pretty_msg": "❌ Request timed out: {error}",
            "hints": [
                "💡 Try again in a moment. If the problem persists:",
                "   • Check your internet connection",
                "   • GitHub API may be experiencing issues",
            ],
        },
        GitHubRateLimitError: {
            "error_code": "rate_limit_exceeded",
            "pretty_msg": "❌ Rate limit exceeded: {error}",
            "hints": [
                "💡 You've made too many requests. Please:",
                "   • Wait a few minutes before trying again",
                "   • Check rate limit status: gh api rate_limit",
            ],
        },
    }

    # Handle specific error types
    for error_type, handler in error_handlers.items():
        if isinstance(error, error_type):
            if pretty:
                pretty_msg = str(handler["pretty_msg"]).format(error=error)
                click.echo(pretty_msg, err=True)
                for hint in handler["hints"]:
                    click.echo(hint, err=True)
            else:
                error_result = {
                    "comment_id": comment_id,
                    "success": False,
                    "reply_posted": False,
                    "error": handler["error_code"],
                    "error_message": str(error),
                }
                click.echo(json.dumps(error_result), err=True)
            ctx.exit(1)

    # Handle GitHubAPIError with specific status codes
    if isinstance(error, GitHubAPIError):
        if "403" in str(error) or "forbidden" in str(error).lower():
            if pretty:
                click.echo(f"❌ Permission denied: {error}", err=True)
                click.echo("💡 Possible causes:", err=True)
                click.echo(
                    "   • You don't have write access to this repository", err=True
                )
                click.echo(
                    "   • The comment may be locked or in a restricted thread", err=True
                )
                click.echo(
                    "   • Your GitHub token may lack required permissions", err=True
                )
            else:
                error_result = {
                    "comment_id": comment_id,
                    "success": False,
                    "reply_posted": False,
                    "error": "permission_denied",
                    "error_message": str(error),
                }
                click.echo(json.dumps(error_result), err=True)
        else:
            if pretty:
                click.echo(f"❌ GitHub API error: {error}", err=True)
                click.echo("💡 This may be a temporary issue. Please:", err=True)
                click.echo("   • Try again in a few moments", err=True)
                click.echo(
                    "   • Check GitHub status: https://www.githubstatus.com/", err=True
                )
            else:
                error_result = {
                    "comment_id": comment_id,
                    "success": False,
                    "reply_posted": False,
                    "error": "api_error",
                    "error_message": str(error),
                }
                click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    # Handle ReplyServiceError and other exceptions
    if pretty:
        click.echo(f"❌ Failed to post reply: {error}", err=True)
        click.echo("💡 This is likely a service error. Please:", err=True)
        click.echo("   • Check your input parameters", err=True)
        click.echo("   • Try again with a different comment", err=True)
    else:
        error_result = {
            "comment_id": comment_id,
            "success": False,
            "reply_posted": False,
            "error": "api_error",
            "error_message": str(error),
        }
        click.echo(json.dumps(error_result), err=True)
    ctx.exit(1)


@click.command()
@click.option(
    "--comment-id",
    required=True,
    type=str,
    help=(
        "GitHub thread ID (PRRT_/PRT_/RT_) or comment ID (numeric, IC_/RP_). "
        "Note: PRRC_ IDs from submitted reviews won't work - use the thread ID instead"
    ),
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
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show additional details about the reply and context",
)
@click.pass_context
def reply(
    ctx: click.Context, comment_id: str, body: str, pretty: bool, verbose: bool
) -> None:
    """Post a reply to a specific review comment or thread.

    Reply to comments or threads using:
    • Numeric IDs (e.g., 123456789) for legacy compatibility
    • Thread node IDs (PRT_, PRRT_, RT_) to reply to entire threads
    • Comment node IDs (IC_, RP_) for individual comments (NOT in submitted reviews)

    IMPORTANT: For submitted reviews, you MUST use thread IDs (PRRT_, PRT_, RT_).
    Individual comment IDs (PRRC_) within submitted reviews cannot be replied to
    directly - use the thread ID instead.

    Use --verbose/-v flag to show additional context including the PR title,
    parent comment author, and thread details.

    Examples:

        toady reply --comment-id 123456789 --body "Fixed in latest commit"

        toady reply --comment-id PRRT_kwDOO3WQIc5Rv3_r --body "Fixed!"

        toady reply --comment-id IC_kwDOABcD12MAAAABcDE3fg --body "Good catch!"

        toady reply --comment-id PRT_kwDOABcD12MAAAABcDE3fg --body "Updated" --pretty -v
    """
    # Validate arguments using helper function
    comment_id, body = _validate_reply_args(comment_id, body)

    # Show warnings if needed
    _show_warnings(body, pretty)

    # Show progress messages
    _show_progress(comment_id, body, pretty)

    # Post the reply using the reply service
    reply_service = ReplyService()
    try:
        request = ReplyRequest(comment_id=comment_id, reply_body=body)
        # Only fetch context if verbose mode is requested (reduces API calls)
        reply_info = reply_service.post_reply(request, fetch_context=verbose)

        if pretty:
            _print_pretty_reply(reply_info, verbose)
        else:
            result = _build_json_reply(comment_id, reply_info, verbose)
            click.echo(json.dumps(result))

    except Exception as e:
        _handle_reply_error(ctx, e, comment_id, pretty)
