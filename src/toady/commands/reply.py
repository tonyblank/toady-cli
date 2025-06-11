"""Reply command implementation."""

import json
from typing import Any, Dict, Optional, Tuple

import click

from toady.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from toady.formatters.format_selection import (
    create_format_option,
    create_legacy_pretty_option,
    format_object_output,
    resolve_format_from_options,
)
from toady.services.reply_service import (
    CommentNotFoundError,
    ReplyRequest,
    ReplyService,
)
from toady.validators.node_id_validation import create_universal_validator


def _show_id_help(ctx: click.Context) -> None:
    """Show detailed help about ID types and how to find them.

    Args:
        ctx: Click context for exit handling
    """
    help_text = """
🎯 GitHub ID Types for Reply Command

📋 SUPPORTED ID TYPES:

1. Thread IDs (Recommended):
   • PRRT_kwDOABcD12MAAAABcDE3fg  - Pull Request Review Thread
   • PRT_kwDOABcD12MAAAABcDE3fg   - Pull Request Thread
   • RT_kwDOABcD12MAAAABcDE3fg    - Review Thread

2. Comment IDs:
   • IC_kwDOABcD12MAAAABcDE3fg    - Issue Comment
   • RP_kwDOABcD12MAAAABcDE3fg    - Reply Comment
   • 123456789                    - Numeric ID (legacy)

⚠️  NOT SUPPORTED:
   • PRRC_kwDOABcD12MAAAABcDE3fg  - Individual comments in submitted reviews
     (Use the thread ID instead)

🔍 HOW TO FIND THE RIGHT ID:

1. Use the fetch command:
   toady fetch --pr <PR_NUMBER> --pretty

2. Look for:
   • "Thread ID:" for thread-level replies (recommended)
   • "Comment ID:" for comment-specific replies

3. Copy the ID and use it with --reply-to-id

💡 BEST PRACTICES:

• Use thread IDs when possible - they're more reliable
• For submitted reviews, always use thread IDs (PRRT_, PRT_, RT_)
• Thread IDs allow replies to be grouped properly in GitHub's UI
• Comment IDs are best for individual, standalone comments

📚 EXAMPLES:

Reply to a thread:
  toady reply --reply-to-id PRRT_kwDOO3WQIc5Rv3_r --body "Thanks for the review!"

Reply to a specific comment:
  toady reply --reply-to-id IC_kwDOABcD12MAAAABcDE3fg --body "Good catch!"

Reply with legacy numeric ID:
  toady reply --reply-to-id 123456789 --body "Fixed!"

🆘 TROUBLESHOOTING:

If you get an error about PRRC_ IDs:
1. Run: toady fetch --pr <PR_NUMBER> --pretty
2. Find the "Thread ID" for that comment
3. Use the thread ID instead

For more help: toady reply --help
"""
    click.echo(help_text)
    ctx.exit(0)


def validate_reply_target_id(reply_to_id: str) -> str:
    """Validate and potentially suggest corrections for reply target ID.

    This function implements intelligent ID validation that can distinguish
    between comment IDs and thread IDs, providing helpful guidance when
    users provide the wrong type.

    Args:
        reply_to_id: The ID to validate

    Returns:
        The validated reply target ID

    Raises:
        click.BadParameter: If validation fails with detailed guidance
    """
    reply_to_id = reply_to_id.strip()
    if not reply_to_id:
        raise click.BadParameter(
            "Reply target ID cannot be empty", param_hint="--reply-to-id"
        )

    try:
        # Accept both comment IDs and thread IDs for the reply command
        # This allows users to reply to either a specific comment or a thread
        universal_validator = create_universal_validator()
        entity_type = universal_validator.validate_id(reply_to_id, "Reply target ID")

        # Check if user provided a submitted review comment ID (PRRC_)
        if entity_type and entity_type.value == "PRRC_":
            raise click.BadParameter(
                "Individual comment IDs from submitted reviews (PRRC_) "
                "cannot be replied to directly.\n"
                "\n💡 Use the thread ID instead:\n"
                "   • Run: toady fetch --pr <PR_NUMBER> --pretty\n"
                "   • Look for the thread ID (starts with PRRT_, PRT_, or RT_)\n"
                "   • Use that thread ID with --reply-to-id\n"
                "\n📖 For more help with ID types, use: toady reply --help-ids",
                param_hint="--reply-to-id",
            )

        return reply_to_id

    except ValueError as e:
        error_msg = str(e)

        # Enhance error message with helpful guidance
        if "must start with one of" in error_msg:
            enhanced_msg = (
                f"{error_msg}\n\n"
                "💡 Common ID types for replies:\n"
                "   • Thread IDs: PRRT_, PRT_, RT_ (recommended)\n"
                "   • Comment IDs: IC_, RP_ (individual comments)\n"
                "   • Numeric IDs: 123456789 (legacy format)\n\n"
                "🔍 To find the correct ID:\n"
                "   • Run: toady fetch --pr <PR_NUMBER> --pretty\n"
                "   • Look for 'Thread ID' or 'Comment ID' in the output\n\n"
                "📖 For detailed ID help: toady reply --help-ids"
            )
        else:
            enhanced_msg = (
                f"{error_msg}\n\n📖 For help with ID formats: toady reply --help-ids"
            )

        raise click.BadParameter(enhanced_msg, param_hint="--reply-to-id") from e


def _validate_reply_args(reply_to_id: str, body: str) -> Tuple[str, str]:
    """Validate reply command arguments.

    Args:
        reply_to_id: The reply target ID to validate
        body: The reply body to validate

    Returns:
        Tuple of (validated_reply_to_id, validated_body)

    Raises:
        click.BadParameter: If validation fails
    """
    # Validate reply target ID with enhanced error messaging
    reply_to_id = validate_reply_target_id(reply_to_id)

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

    return reply_to_id, body


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
    reply_to_id: str, reply_info: Dict[str, Any], verbose: bool
) -> Dict[str, Any]:
    """Build JSON response for reply command.

    Args:
        reply_to_id: The original reply target ID
        reply_info: Dictionary with reply information
        verbose: Whether verbose mode was requested

    Returns:
        Dictionary ready for JSON output
    """
    # Return JSON response with all available reply information
    result = {
        "reply_to_id": reply_to_id,
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


def _show_progress(reply_to_id: str, body: str, pretty: bool) -> None:
    """Show progress messages for the reply operation.

    Args:
        reply_to_id: The reply target ID being replied to
        body: The reply body
        pretty: Whether to show pretty progress messages
    """
    if pretty:
        click.echo(f"💬 Posting reply to {reply_to_id}")
        click.echo(f"📝 Reply: {body[:100]}{'...' if len(body) > 100 else ''}")


def _handle_reply_error(
    ctx: click.Context, error: Exception, reply_to_id: str, pretty: bool
) -> None:
    """Handle different types of reply errors with appropriate output.

    Args:
        ctx: Click context for exit handling
        error: The exception that occurred
        reply_to_id: The reply target ID that failed
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
                    "reply_to_id": reply_to_id,
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
                    "reply_to_id": reply_to_id,
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
                    "reply_to_id": reply_to_id,
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
            "reply_to_id": reply_to_id,
            "success": False,
            "reply_posted": False,
            "error": "api_error",
            "error_message": str(error),
        }
        click.echo(json.dumps(error_result), err=True)
    ctx.exit(1)


@click.command()
@click.option(
    "--reply-to-id",
    type=str,
    help=(
        "ID to reply to: thread ID (PRRT_/PRT_/RT_) or comment ID (numeric, IC_/RP_). "
        "Use thread IDs for submitted reviews. Use --help-ids for detailed guidance."
    ),
    metavar="ID",
)
@click.option(
    "--body",
    type=str,
    help="Reply message body (1-65536 characters)",
    metavar="TEXT",
)
@create_format_option()
@create_legacy_pretty_option()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show additional details about the reply and context",
)
@click.option(
    "--help-ids",
    is_flag=True,
    help="Show detailed help about ID types and how to find them",
)
@click.pass_context
def reply(
    ctx: click.Context,
    reply_to_id: str,
    body: str,
    format: Optional[str],
    pretty: bool,
    verbose: bool,
    help_ids: bool,
) -> None:
    """Post a reply to a specific review comment or thread.

    Reply to comments or threads using:
    • Thread IDs (PRRT_, PRT_, RT_) - recommended for most cases
    • Comment IDs (IC_, RP_) - for individual comments
    • Numeric IDs (e.g., 123456789) - legacy format

    IMPORTANT: For submitted reviews, you MUST use thread IDs (PRRT_, PRT_, RT_).
    Individual comment IDs (PRRC_) within submitted reviews cannot be replied to
    directly - use the thread ID instead.

    Use --verbose/-v flag to show additional context including the PR title,
    parent comment author, and thread details.

    Use --help-ids to get detailed help about ID types and how to find them.

    Examples:

        toady reply --reply-to-id 123456789 --body "Fixed in latest commit"

        toady reply --reply-to-id PRRT_kwDOO3WQIc5Rv3_r --body "Fixed!"

        toady reply --reply-to-id IC_kwDOABcD12MAAAABcDE3fg --body "Good catch!"

        toady reply --reply-to-id PRT_kwDOABcD12MAAAABcDE3fg \\
            --body "Updated" --pretty -v
    """
    # Show ID help if requested
    if help_ids:
        _show_id_help(ctx)
        return

    # Check for required arguments
    if not reply_to_id:
        raise click.UsageError("Missing option '--reply-to-id'.")
    if not body:
        raise click.UsageError("Missing option '--body'.")

    # Resolve format from options
    try:
        output_format = resolve_format_from_options(format, pretty)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

    # Validate arguments using helper function
    reply_to_id, body = _validate_reply_args(reply_to_id, body)

    # Show warnings if needed
    _show_warnings(body, output_format == "pretty")

    # Show progress messages
    _show_progress(reply_to_id, body, output_format == "pretty")

    # Post the reply using the reply service
    reply_service = ReplyService()
    try:
        request = ReplyRequest(comment_id=reply_to_id, reply_body=body)
        # Only fetch context if verbose mode is requested (reduces API calls)
        reply_info = reply_service.post_reply(request, fetch_context=verbose)

        if output_format == "pretty":
            _print_pretty_reply(reply_info, verbose)
        else:
            result = _build_json_reply(reply_to_id, reply_info, verbose)
            format_object_output(result, output_format)

    except Exception as e:
        _handle_reply_error(ctx, e, reply_to_id, output_format == "pretty")
