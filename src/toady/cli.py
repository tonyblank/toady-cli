"""Main CLI interface for Toady."""

import json
from typing import Any, Dict, List, Tuple

import click

from toady import __version__
from toady.fetch_service import FetchService, FetchServiceError
from toady.formatters import format_fetch_output
from toady.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from toady.node_id_validation import (
    create_universal_validator,
    validate_thread_id,
)
from toady.reply_service import (
    CommentNotFoundError,
    ReplyRequest,
    ReplyService,
    ReplyServiceError,
)
from toady.resolve_service import (
    ResolveService,
    ResolveServiceError,
    ThreadNotFoundError,
    ThreadPermissionError,
)
from toady.schema_cli import schema

# Constants
MAX_PR_NUMBER = 999999


def _emit_error(
    ctx: click.Context, pr_number: int, code: str, msg: str, pretty: bool
) -> None:
    """Helper function to emit consistent error messages in JSON or pretty format.

    Args:
        ctx: Click context for exit handling
        pr_number: PR number for error context
        code: Error code for JSON output
        msg: Error message
        pretty: Whether to use pretty output format
    """
    if pretty:
        click.echo(msg, err=True)
    else:
        error_result = {
            "pr_number": pr_number,
            "threads_fetched": False,
            "error": code,
            "error_message": msg,
        }
        click.echo(json.dumps(error_result), err=True)
    ctx.exit(1)


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

    # Enhanced PR number validation
    if pr_number > MAX_PR_NUMBER:
        raise click.BadParameter(
            "PR number appears unreasonably large (maximum: 999,999)",
            param_hint="--pr",
        )

    # Validate limit
    if limit <= 0:
        raise click.BadParameter("Limit must be positive", param_hint="--limit")
    if limit > 1000:
        raise click.BadParameter("Limit cannot exceed 1000", param_hint="--limit")

    # Prepare thread type description for user feedback
    thread_type = "all threads" if resolved else "unresolved threads"

    # Execute fetch operation with comprehensive error handling
    try:
        # Create fetch service and retrieve threads
        fetch_service = FetchService()
        threads = fetch_service.fetch_review_threads_from_current_repo(
            pr_number=pr_number,
            include_resolved=resolved,
            limit=limit,
        )

        # Use formatters to display output
        format_fetch_output(
            threads=threads,
            pretty=pretty,
            show_progress=True,
            pr_number=pr_number,
            thread_type=thread_type,
            limit=limit,
        )

    except GitHubAuthenticationError as e:
        if pretty:
            click.echo(f"❌ Authentication failed: {e}", err=True)
            click.echo("💡 Try running: gh auth login", err=True)
            click.echo("💡 Ensure you have access to the repository", err=True)
            click.echo("💡 Check: gh auth status", err=True)
            ctx.exit(1)
        else:
            _emit_error(ctx, pr_number, "authentication_failed", str(e), pretty)

    except GitHubTimeoutError as e:
        if pretty:
            click.echo(f"❌ Request timed out: {e}", err=True)
            click.echo("💡 The request took too long. Please:", err=True)
            click.echo("   • Try again with a smaller --limit", err=True)
            click.echo("   • Check your internet connection", err=True)
            click.echo("   • GitHub API may be experiencing issues", err=True)
            ctx.exit(1)
        else:
            _emit_error(ctx, pr_number, "timeout", str(e), pretty)

    except GitHubRateLimitError as e:
        if pretty:
            click.echo(f"❌ Rate limit exceeded: {e}", err=True)
            click.echo("💡 You've made too many requests. Please:", err=True)
            click.echo("   • Wait a few minutes before trying again", err=True)
            click.echo("   • Consider using a smaller --limit", err=True)
            click.echo("   • Check rate limit status: gh api rate_limit", err=True)
            ctx.exit(1)
        else:
            _emit_error(ctx, pr_number, "rate_limit_exceeded", str(e), pretty)

    except GitHubAPIError as e:
        # Handle specific API errors
        if "404" in str(e) or "not found" in str(e).lower():
            if pretty:
                click.echo(f"❌ Pull request not found: {e}", err=True)
                click.echo("💡 Possible causes:", err=True)
                click.echo(f"   • PR #{pr_number} may not exist", err=True)
                click.echo("   • You may not have access to this repository", err=True)
                click.echo("   • The repository may be private", err=True)
                ctx.exit(1)
            else:
                _emit_error(ctx, pr_number, "pr_not_found", str(e), pretty)
        elif "403" in str(e) or "forbidden" in str(e).lower():
            if pretty:
                click.echo(f"❌ Permission denied: {e}", err=True)
                click.echo("💡 Possible causes:", err=True)
                click.echo(
                    "   • You don't have read access to this repository", err=True
                )
                click.echo("   • The repository may be private", err=True)
                click.echo(
                    "   • Your GitHub token may lack required permissions", err=True
                )
                ctx.exit(1)
            else:
                _emit_error(ctx, pr_number, "permission_denied", str(e), pretty)
        else:
            if pretty:
                click.echo(f"❌ GitHub API error: {e}", err=True)
                click.echo("💡 This may be a temporary issue. Please:", err=True)
                click.echo("   • Try again in a few moments", err=True)
                click.echo(
                    "   • Check GitHub status: https://www.githubstatus.com/", err=True
                )
                ctx.exit(1)
            else:
                _emit_error(ctx, pr_number, "api_error", str(e), pretty)

    except FetchServiceError as e:
        if pretty:
            click.echo(f"❌ Failed to fetch threads: {e}", err=True)
            click.echo("💡 This may be a service error. Please:", err=True)
            click.echo("   • Check your repository setup", err=True)
            click.echo("   • Ensure you're in a git repository", err=True)
            click.echo("   • Try again with different parameters", err=True)
            ctx.exit(1)
        else:
            _emit_error(ctx, pr_number, "service_error", str(e), pretty)

    except Exception as e:
        # Catch-all for unexpected errors
        if pretty:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            click.echo("💡 This appears to be an internal error. Please:", err=True)
            click.echo("   • Check your command parameters", err=True)
            click.echo("   • Try again with different options", err=True)
            click.echo("   • Report this issue if it persists", err=True)
            ctx.exit(1)
        else:
            _emit_error(ctx, pr_number, "internal_error", str(e), pretty)


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


def _print_pretty_reply(
    reply_info: Dict[str, Any], verbose: bool, pretty: bool
) -> None:
    """Print reply information in pretty format.

    Args:
        reply_info: Dictionary with reply information
        verbose: Whether to show verbose details
        pretty: Whether to use pretty output (for warnings)
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


@cli.command()
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
            _print_pretty_reply(reply_info, verbose, pretty)
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


@cli.command()
@click.option(
    "--thread-id",
    type=str,
    help="GitHub thread ID (numeric ID or node ID starting with PRT_/PRRT_/RT_)",
    metavar="ID",
)
@click.option(
    "--all",
    "bulk_resolve",
    is_flag=True,
    help="Resolve all unresolved threads in the specified pull request",
)
@click.option(
    "--pr",
    "pr_number",
    type=int,
    help="Pull request number (required when using --all)",
    metavar="NUMBER",
)
@click.option(
    "--undo",
    is_flag=True,
    help="Unresolve the thread instead of resolving it",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt for bulk operations",
)
@click.option(
    "--pretty",
    is_flag=True,
    help="Output in human-readable format instead of JSON",
)
@click.pass_context
def resolve(
    ctx: click.Context,
    thread_id: str,
    bulk_resolve: bool,
    pr_number: int,
    undo: bool,
    yes: bool,
    pretty: bool,
) -> None:
    """Mark a review thread as resolved or unresolved.

    Resolve or unresolve review threads using either numeric IDs or
    GitHub node IDs for threads (PRT_), review threads (PRRT_), or legacy threads (RT_).

    Use --all flag to resolve all unresolved threads in a pull request at once.
    This requires --pr to specify the pull request number.

    Examples:

        toady resolve --thread-id 123456789

        toady resolve --thread-id PRT_kwDOABcD12MAAAABcDE3fg --undo

        toady resolve --thread-id PRRT_kwDOO3WQIc5RvXMO

        toady resolve --thread-id RT_kwDOABcD12MAAAABcDE3fg --pretty

        toady resolve --all --pr 123

        toady resolve --all --pr 123 --yes --pretty
    """
    # Validate mutually exclusive options
    if bulk_resolve and thread_id:
        raise click.BadParameter(
            "Cannot use --all and --thread-id together. Choose one."
        )

    if not bulk_resolve and thread_id is None:
        raise click.BadParameter("Must specify either --thread-id or --all")

    # Validate PR number if provided
    if pr_number is not None:
        if pr_number <= 0:
            raise click.BadParameter("PR number must be positive", param_hint="--pr")
        if pr_number > MAX_PR_NUMBER:
            raise click.BadParameter(
                "PR number appears unreasonably large (maximum: 999,999)",
                param_hint="--pr",
            )

    # Validate --pr requirement when using --all
    if bulk_resolve and pr_number is None:
        raise click.BadParameter("--pr is required when using --all", param_hint="--pr")

    # Handle bulk resolution mode
    if bulk_resolve:
        try:
            _handle_bulk_resolve(ctx, pr_number, undo, yes, pretty)
        except SystemExit:
            # Re-raise SystemExit to avoid being caught by outer exception handlers
            raise
        return

    # Handle single thread resolution mode
    # Validate thread ID using centralized validation
    thread_id = thread_id.strip()
    if not thread_id:
        raise click.BadParameter("Thread ID cannot be empty", param_hint="--thread-id")

    try:
        validate_thread_id(thread_id)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--thread-id") from e

    # Show what we're doing
    action = "Unresolving" if undo else "Resolving"
    action_past = "unresolved" if undo else "resolved"
    action_symbol = "🔓" if undo else "🔒"

    if pretty:
        click.echo(f"{action_symbol} {action} thread {thread_id}")
    else:
        # For JSON output, we'll just return the result without progress messages
        pass

    # Execute the resolve/unresolve operation using the resolve service
    try:
        resolve_service = ResolveService()

        if undo:
            result = resolve_service.unresolve_thread(thread_id)
        else:
            result = resolve_service.resolve_thread(thread_id)

        if pretty:
            click.echo(f"✅ Thread {action_past} successfully")
            if result.get("thread_url"):
                click.echo(f"🔗 View thread at: {result['thread_url']}")
        else:
            # Return JSON response with actual result information
            click.echo(json.dumps(result))

    except ThreadNotFoundError as e:
        if pretty:
            click.echo(f"❌ Thread not found: {e}", err=True)
        else:
            error_result = {
                "thread_id": thread_id,
                "action": "unresolve" if undo else "resolve",
                "success": False,
                "error": "thread_not_found",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except ThreadPermissionError as e:
        if pretty:
            click.echo(f"❌ Permission denied: {e}", err=True)
            click.echo("💡 Ensure you have write access to the repository", err=True)
        else:
            error_result = {
                "thread_id": thread_id,
                "action": "unresolve" if undo else "resolve",
                "success": False,
                "error": "permission_denied",
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
                "thread_id": thread_id,
                "action": "unresolve" if undo else "resolve",
                "success": False,
                "error": "authentication_failed",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except (ResolveServiceError, GitHubAPIError) as e:
        if pretty:
            click.echo(f"❌ Failed to resolve thread: {e}", err=True)
        else:
            error_result = {
                "thread_id": thread_id,
                "action": "unresolve" if undo else "resolve",
                "success": False,
                "error": "api_error",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)


def _fetch_and_filter_threads(pr_number: int, undo: bool, pretty: bool) -> List[Any]:
    """Fetch and filter threads based on resolution action.

    Args:
        pr_number: Pull request number
        undo: Whether to fetch resolved threads (for unresolve) or unresolved (resolve)
        pretty: Whether to show pretty progress messages

    Returns:
        List of filtered threads ready for processing
    """
    if pretty:
        click.echo(f"🔍 Fetching threads from PR #{pr_number}...")

    fetch_service = FetchService()
    # For unresolve, we need to fetch resolved threads; for resolve, unresolved threads
    include_resolved = undo
    threads = fetch_service.fetch_review_threads_from_current_repo(
        pr_number=pr_number,
        include_resolved=include_resolved,
        limit=100,  # Maximum allowed limit for bulk operations
    )

    # Filter threads based on action
    if undo:
        target_threads = [t for t in threads if t.is_resolved]
    else:
        target_threads = [t for t in threads if not t.is_resolved]

    return target_threads


def _handle_confirmation_prompt(
    ctx: click.Context,
    target_threads: List[Any],
    action: str,
    action_symbol: str,
    pr_number: int,
    yes: bool,
    pretty: bool,
) -> None:
    """Handle user confirmation prompt for bulk operations.

    Args:
        ctx: Click context for exit handling
        target_threads: List of threads to be processed
        action: Action being performed (resolve/unresolve)
        action_symbol: Emoji symbol for the action
        pr_number: Pull request number
        yes: Whether to skip confirmation
        pretty: Whether to use pretty output
    """
    if yes:
        return  # Skip confirmation if --yes flag is used

    if pretty:
        click.echo(
            f"\n{action_symbol} About to {action} {len(target_threads)} "
            f"thread(s) in PR #{pr_number}"
        )
        for i, thread in enumerate(target_threads[:5]):  # Show first 5
            click.echo(f"   {i+1}. {thread.thread_id} - {thread.title}")
        if len(target_threads) > 5:
            click.echo(f"   ... and {len(target_threads) - 5} more")
        click.echo()
        if not click.confirm(f"Do you want to {action} these threads?"):
            click.echo("❌ Operation cancelled")
            ctx.exit(0)
    else:
        # For JSON mode, we still need confirmation unless --yes is used
        click.echo(
            f"About to {action} {len(target_threads)} thread(s). "
            "Use --yes to skip this prompt.",
            err=True,
        )
        ctx.exit(1)


def _process_threads(
    target_threads: List[Any],
    undo: bool,
    action_present: str,
    action_symbol: str,
    pretty: bool,
) -> Tuple[int, int, List[Dict[str, str]]]:
    """Process threads for resolution/unresolve with error handling.

    Args:
        target_threads: List of threads to process
        undo: Whether to unresolve (True) or resolve (False)
        action_present: Present tense action description
        action_symbol: Emoji symbol for the action
        pretty: Whether to show pretty progress messages

    Returns:
        Tuple of (succeeded_count, failed_count, failed_threads_list)
    """
    import time

    if pretty:
        click.echo(
            f"\n{action_symbol} {action_present} {len(target_threads)} " "thread(s)..."
        )

    resolve_service = ResolveService()
    succeeded = 0
    failed = 0
    failed_threads = []

    for i, thread in enumerate(target_threads, 1):
        if pretty:
            click.echo(
                f"   {action_symbol} {action_present} thread {i} of "
                f"{len(target_threads)}: {thread.thread_id}"
            )

        try:
            if undo:
                resolve_service.unresolve_thread(thread.thread_id)
            else:
                resolve_service.resolve_thread(thread.thread_id)
            succeeded += 1

            # Add small delay to avoid rate limits
            if i < len(target_threads):  # Don't sleep after the last request
                time.sleep(0.1)

        except GitHubRateLimitError as e:
            failed += 1
            failed_threads.append({"thread_id": thread.thread_id, "error": str(e)})
            if pretty:
                click.echo(f"     ❌ Failed: {e}", err=True)
                click.echo(
                    "     ⏳ Rate limit detected, waiting before continuing...",
                    err=True,
                )
            time.sleep(min(2.0 ** min(failed, 5), 60))  # Exponential backoff, max 60s
        except (ResolveServiceError, GitHubAPIError) as e:
            failed += 1
            failed_threads.append({"thread_id": thread.thread_id, "error": str(e)})
            if pretty:
                click.echo(f"     ❌ Failed: {e}", err=True)

    return succeeded, failed, failed_threads


def _display_summary(
    target_threads: List[Any],
    succeeded: int,
    failed: int,
    failed_threads: List[Dict[str, str]],
    action: str,
    action_past: str,
    pr_number: int,
    pretty: bool,
) -> None:
    """Display summary of bulk resolution results.

    Args:
        target_threads: List of threads that were processed
        succeeded: Number of successful operations
        failed: Number of failed operations
        failed_threads: List of failed thread details
        action: Action performed (resolve/unresolve)
        action_past: Past tense action description
        pr_number: Pull request number
        pretty: Whether to use pretty output format
    """
    if pretty:
        click.echo(f"\n✅ Bulk {action} completed:")
        click.echo(f"   📊 Total threads processed: {len(target_threads)}")
        click.echo(f"   ✅ Successfully {action_past}: {succeeded}")
        if failed > 0:
            click.echo(f"   ❌ Failed: {failed}")
            click.echo("\n❌ Failed threads:")
            for failure in failed_threads:
                click.echo(f"   • {failure['thread_id']}: {failure['error']}")
    else:
        result = {
            "pr_number": pr_number,
            "action": action,
            "threads_processed": len(target_threads),
            "threads_succeeded": succeeded,
            "threads_failed": failed,
            "success": failed == 0,
            "failed_threads": failed_threads,
        }
        click.echo(json.dumps(result))


def _handle_bulk_resolve(
    ctx: click.Context, pr_number: int, undo: bool, yes: bool, pretty: bool
) -> None:
    """Handle bulk resolution of all threads in a pull request.

    Args:
        ctx: Click context for exit handling
        pr_number: Pull request number
        undo: Whether to unresolve instead of resolve
        yes: Whether to skip confirmation prompt
        pretty: Whether to use pretty output format
    """
    action = "unresolve" if undo else "resolve"
    action_past = "unresolved" if undo else "resolved"
    action_present = "Unresolving" if undo else "Resolving"
    action_symbol = "🔓" if undo else "🔒"

    try:
        # Fetch and filter threads
        target_threads = _fetch_and_filter_threads(pr_number, undo, pretty)

        # Handle empty result
        if not target_threads:
            if pretty:
                status = "resolved" if undo else "unresolved"
                click.echo(f"✅ No {status} threads found in PR #{pr_number}")
            else:
                result = {
                    "pr_number": pr_number,
                    "action": action,
                    "threads_processed": 0,
                    "threads_succeeded": 0,
                    "threads_failed": 0,
                    "success": True,
                    "message": (
                        f"No {'resolved' if undo else 'unresolved'} threads found"
                    ),
                }
                click.echo(json.dumps(result))
            return

        # Handle confirmation prompt
        _handle_confirmation_prompt(
            ctx, target_threads, action, action_symbol, pr_number, yes, pretty
        )

        # Process threads
        succeeded, failed, failed_threads = _process_threads(
            target_threads, undo, action_present, action_symbol, pretty
        )

        # Display summary
        _display_summary(
            target_threads,
            succeeded,
            failed,
            failed_threads,
            action,
            action_past,
            pr_number,
            pretty,
        )

        # Exit with error code if any threads failed
        if failed > 0:
            ctx.exit(1)

    except FetchServiceError as e:
        if pretty:
            click.echo(f"❌ Failed to fetch threads: {e}", err=True)
        else:
            error_result = {
                "pr_number": pr_number,
                "action": action,
                "success": False,
                "error": "fetch_failed",
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
                "pr_number": pr_number,
                "action": action,
                "success": False,
                "error": "authentication_failed",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)

    except click.exceptions.Exit:
        # Re-raise Exit exceptions (e.g., from ctx.exit(0) when user cancels)
        raise
    except Exception as e:
        if pretty:
            click.echo(f"❌ Unexpected error during bulk {action}: {e}", err=True)
        else:
            error_result = {
                "pr_number": pr_number,
                "action": action,
                "success": False,
                "error": "internal_error",
                "error_message": str(e),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)


# Add schema command group
cli.add_command(schema)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
