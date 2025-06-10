"""Resolve command implementation."""

import json
import time
from typing import Any, Dict, List, Tuple

import click

from toady.exceptions import (
    ResolveServiceError,
    ThreadNotFoundError,
    ThreadPermissionError,
)
from toady.fetch_service import FetchService, FetchServiceError
from toady.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
)
from toady.node_id_validation import validate_thread_id
from toady.resolve_service import ResolveService
from toady.utils import MAX_PR_NUMBER


def _fetch_and_filter_threads(
    pr_number: int, undo: bool, pretty: bool, limit: int
) -> List[Any]:
    """Fetch and filter threads based on resolution action.

    Args:
        pr_number: Pull request number
        undo: Whether to fetch resolved threads (for unresolve) or unresolved (resolve)
        pretty: Whether to show pretty progress messages
        limit: Maximum number of threads to fetch

    Returns:
        List of filtered threads ready for processing
    """
    if pretty:
        click.echo(f"🔍 Fetching threads from PR #{pr_number} (limit: {limit})...")

    fetch_service = FetchService()
    # For unresolve, we need to fetch resolved threads; for resolve, unresolved threads
    include_resolved = undo
    threads = fetch_service.fetch_review_threads_from_current_repo(
        pr_number=pr_number,
        include_resolved=include_resolved,
        limit=limit,
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


def _get_action_labels(undo: bool) -> Tuple[str, str, str, str]:
    """Get action labels for bulk operations.

    Args:
        undo: Whether this is an undo operation

    Returns:
        Tuple of (action, action_past, action_present, action_symbol)
    """
    if undo:
        return "unresolve", "unresolved", "Unresolving", "🔓"
    else:
        return "resolve", "resolved", "Resolving", "🔒"


def _handle_empty_threads(
    pr_number: int, action: str, undo: bool, pretty: bool
) -> None:
    """Handle the case when no threads are found for bulk operations.

    Args:
        pr_number: Pull request number
        action: Action being performed (resolve/unresolve)
        undo: Whether this is an undo operation
        pretty: Whether to use pretty output format
    """
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
            "message": (f"No {'resolved' if undo else 'unresolved'} threads found"),
        }
        click.echo(json.dumps(result))


def _handle_bulk_resolve_error(
    ctx: click.Context,
    error: Exception,
    pr_number: int,
    action: str,
    pretty: bool,
) -> None:
    """Handle different types of errors during bulk resolve operations.

    Args:
        ctx: Click context for exit handling
        error: The exception that occurred
        pr_number: Pull request number
        action: Action being performed (resolve/unresolve)
        pretty: Whether to use pretty output format
    """
    error_handlers = {
        FetchServiceError: {
            "error_code": "fetch_failed",
            "pretty_msg": "❌ Failed to fetch threads: {error}",
        },
        GitHubAuthenticationError: {
            "error_code": "authentication_failed",
            "pretty_msg": "❌ Authentication failed: {error}",
            "hint": "💡 Try running: gh auth login",
        },
    }

    # Handle specific error types
    for error_type, handler in error_handlers.items():
        if isinstance(error, error_type):
            if pretty:
                pretty_msg = str(handler["pretty_msg"]).format(error=error)
                click.echo(pretty_msg, err=True)
                if "hint" in handler:
                    click.echo(handler["hint"], err=True)
            else:
                error_result = {
                    "pr_number": pr_number,
                    "action": action,
                    "success": False,
                    "error": handler["error_code"],
                    "error_message": str(error),
                }
                click.echo(json.dumps(error_result), err=True)
            ctx.exit(1)

    # Handle click.exceptions.Exit (user cancellation)
    if isinstance(error, click.exceptions.Exit):
        ctx.exit(error.exit_code)

    # Handle all other exceptions
    if pretty:
        click.echo(f"❌ Unexpected error during bulk {action}: {error}", err=True)
    else:
        error_result = {
            "pr_number": pr_number,
            "action": action,
            "success": False,
            "error": "internal_error",
            "error_message": str(error),
        }
        click.echo(json.dumps(error_result), err=True)
    ctx.exit(1)


def _handle_bulk_resolve(
    ctx: click.Context, pr_number: int, undo: bool, yes: bool, pretty: bool, limit: int
) -> None:
    """Handle bulk resolution of all threads in a pull request.

    Args:
        ctx: Click context for exit handling
        pr_number: Pull request number
        undo: Whether to unresolve instead of resolve
        yes: Whether to skip confirmation prompt
        pretty: Whether to use pretty output format
        limit: Maximum number of threads to process
    """
    action, action_past, action_present, action_symbol = _get_action_labels(undo)

    try:
        # Fetch and filter threads
        target_threads = _fetch_and_filter_threads(pr_number, undo, pretty, limit)

        # Handle empty result
        if not target_threads:
            _handle_empty_threads(pr_number, action, undo, pretty)
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

    except Exception as e:
        _handle_bulk_resolve_error(ctx, e, pr_number, action, pretty)


def _validate_resolve_parameters(
    bulk_resolve: bool, thread_id: str, pr_number: int, limit: int
) -> None:
    """Validate resolve command parameters.

    Args:
        bulk_resolve: Whether bulk resolution is requested
        thread_id: Thread ID for single resolution
        pr_number: Pull request number
        limit: Maximum number of threads to process

    Raises:
        click.BadParameter: If validation fails
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

    # Validate limit parameter
    if limit <= 0:
        raise click.BadParameter("Limit must be positive", param_hint="--limit")
    if limit > 1000:
        raise click.BadParameter("Limit cannot exceed 1000", param_hint="--limit")


def _validate_and_prepare_thread_id(thread_id: str) -> str:
    """Validate and prepare thread ID for single resolution.

    Args:
        thread_id: Raw thread ID from user input

    Returns:
        Cleaned and validated thread ID

    Raises:
        click.BadParameter: If validation fails
    """
    thread_id = thread_id.strip()
    if not thread_id:
        raise click.BadParameter("Thread ID cannot be empty", param_hint="--thread-id")

    try:
        validate_thread_id(thread_id)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--thread-id") from e

    return thread_id


def _show_single_resolve_progress(thread_id: str, undo: bool, pretty: bool) -> None:
    """Show progress messages for single thread resolution.

    Args:
        thread_id: Thread ID being processed
        undo: Whether this is an unresolve operation
        pretty: Whether to show pretty progress messages
    """
    if pretty:
        action = "Unresolving" if undo else "Resolving"
        action_symbol = "🔓" if undo else "🔒"
        click.echo(f"{action_symbol} {action} thread {thread_id}")


def _handle_single_resolve_success(
    result: Dict[str, Any], undo: bool, pretty: bool
) -> None:
    """Handle successful single thread resolution.

    Args:
        result: Resolution result from service
        undo: Whether this was an unresolve operation
        pretty: Whether to use pretty output format
    """
    if pretty:
        action_past = "unresolved" if undo else "resolved"
        click.echo(f"✅ Thread {action_past} successfully")
        if result.get("thread_url"):
            click.echo(f"🔗 View thread at: {result['thread_url']}")
    else:
        click.echo(json.dumps(result))


def _handle_single_resolve_error(
    ctx: click.Context,
    error: Exception,
    thread_id: str,
    undo: bool,
    pretty: bool,
) -> None:
    """Handle errors during single thread resolution.

    Args:
        ctx: Click context for exit handling
        error: The exception that occurred
        thread_id: Thread ID that failed
        undo: Whether this was an unresolve operation
        pretty: Whether to use pretty output format
    """
    action = "unresolve" if undo else "resolve"

    error_handlers = {
        ThreadNotFoundError: {
            "error_code": "thread_not_found",
            "pretty_msg": "❌ Thread not found: {error}",
        },
        ThreadPermissionError: {
            "error_code": "permission_denied",
            "pretty_msg": "❌ Permission denied: {error}",
            "hint": "💡 Ensure you have write access to the repository",
        },
        GitHubAuthenticationError: {
            "error_code": "authentication_failed",
            "pretty_msg": "❌ Authentication failed: {error}",
            "hint": "💡 Try running: gh auth login",
        },
    }

    # Handle specific error types
    for error_type, handler in error_handlers.items():
        if isinstance(error, error_type):
            if pretty:
                pretty_msg = str(handler["pretty_msg"]).format(error=error)
                click.echo(pretty_msg, err=True)
                if "hint" in handler:
                    click.echo(handler["hint"], err=True)
            else:
                error_result = {
                    "thread_id": thread_id,
                    "action": action,
                    "success": False,
                    "error": handler["error_code"],
                    "error_message": str(error),
                }
                click.echo(json.dumps(error_result), err=True)
            ctx.exit(1)

    # Handle ResolveServiceError and GitHubAPIError
    if isinstance(error, (ResolveServiceError, GitHubAPIError)):
        if pretty:
            click.echo(f"❌ Failed to resolve thread: {error}", err=True)
        else:
            error_result = {
                "thread_id": thread_id,
                "action": action,
                "success": False,
                "error": "api_error",
                "error_message": str(error),
            }
            click.echo(json.dumps(error_result), err=True)
        ctx.exit(1)


def _handle_single_resolve(
    ctx: click.Context, thread_id: str, undo: bool, pretty: bool
) -> None:
    """Handle single thread resolution.

    Args:
        ctx: Click context for exit handling
        thread_id: Thread ID to resolve/unresolve
        undo: Whether to unresolve instead of resolve
        pretty: Whether to use pretty output format
    """
    # Validate and prepare thread ID
    thread_id = _validate_and_prepare_thread_id(thread_id)

    # Show progress
    _show_single_resolve_progress(thread_id, undo, pretty)

    # Execute the resolve/unresolve operation
    try:
        resolve_service = ResolveService()

        if undo:
            result = resolve_service.unresolve_thread(thread_id)
        else:
            result = resolve_service.resolve_thread(thread_id)

        _handle_single_resolve_success(result, undo, pretty)

    except Exception as e:
        _handle_single_resolve_error(ctx, e, thread_id, undo, pretty)


@click.command()
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
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of threads to process (default: 100, max: 1000)",
    metavar="COUNT",
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
    limit: int,
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

        toady resolve --all --pr 123 --limit 500
    """
    # Validate all parameters
    _validate_resolve_parameters(bulk_resolve, thread_id, pr_number, limit)

    # Handle bulk resolution mode
    if bulk_resolve:
        try:
            _handle_bulk_resolve(ctx, pr_number, undo, yes, pretty, limit)
        except SystemExit:
            # Re-raise SystemExit to avoid being caught by outer exception handlers
            raise
        return

    # Handle single thread resolution mode
    _handle_single_resolve(ctx, thread_id, undo, pretty)
