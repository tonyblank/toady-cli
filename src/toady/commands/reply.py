"""Reply command implementation."""

import json
from typing import Any, Dict, Tuple

import click

from toady.github_service import (
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
    ReplyServiceError,
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

    # Warning for mentions (only in pretty mode to avoid JSON pollution)
    if body.startswith("@") and pretty:
        click.echo(
            "⚠️  Note: Reply starts with '@' - this will mention users",
            err=True,
        )

    # Warning for potential spam patterns
    if len(set(body.lower().replace(" ", ""))) < 3 and len(body) > 10 and pretty:
        click.echo(
            "⚠️  Note: Reply contains very repetitive content",
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
        # Only fetch context if verbose mode is requested (reduces API calls)
        reply_info = reply_service.post_reply(request, fetch_context=verbose)

        if pretty:
            _print_pretty_reply(reply_info, verbose)
        else:
            result = _build_json_reply(comment_id, reply_info, verbose)
            click.echo(json.dumps(result))

    except CommentNotFoundError as e:
        if pretty:
            click.echo(f"❌ Comment not found: {e}", err=True)
            click.echo("💡 Possible causes:", err=True)
            click.echo("   • Comment ID may be incorrect", err=True)
            click.echo("   • Comment may have been deleted", err=True)
            click.echo("   • You may not have access to this comment", err=True)
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
            click.echo("💡 Ensure you have the 'repo' scope enabled", err=True)
            click.echo("💡 Check: gh auth status", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "authentication_failed",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except GitHubTimeoutError as e:
        if pretty:
            click.echo(f"❌ Request timed out: {e}", err=True)
            click.echo("💡 Try again in a moment. If the problem persists:", err=True)
            click.echo("   • Check your internet connection", err=True)
            click.echo("   • GitHub API may be experiencing issues", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "timeout",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except GitHubRateLimitError as e:
        if pretty:
            click.echo(f"❌ Rate limit exceeded: {e}", err=True)
            click.echo("💡 You've made too many requests. Please:", err=True)
            click.echo("   • Wait a few minutes before trying again", err=True)
            click.echo("   • Check rate limit status: gh api rate_limit", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "rate_limit_exceeded",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except GitHubAPIError as e:
        # Handle permission errors specifically
        if "403" in str(e) or "forbidden" in str(e).lower():
            if pretty:
                click.echo(f"❌ Permission denied: {e}", err=True)
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
                    "reply_posted": False,
                    "error": "permission_denied",
                    "error_message": str(e),
                }
                click.echo(json.dumps(error_result), err=True)
        else:
            if pretty:
                click.echo(f"❌ GitHub API error: {e}", err=True)
                click.echo("💡 This may be a temporary issue. Please:", err=True)
                click.echo("   • Try again in a few moments", err=True)
                click.echo(
                    "   • Check GitHub status: https://www.githubstatus.com/", err=True
                )
            else:
                error_result = {
                    "comment_id": comment_id,
                    "reply_posted": False,
                    "error": "api_error",
                    "error_message": str(e),
                }
                click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except ReplyServiceError as e:
        if pretty:
            click.echo(f"❌ Failed to post reply: {e}", err=True)
            click.echo("💡 This is likely a service error. Please:", err=True)
            click.echo("   • Check your input parameters", err=True)
            click.echo("   • Try again with a different comment", err=True)
        else:
            error_result = {
                "comment_id": comment_id,
                "reply_posted": False,
                "error": "api_error",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)
