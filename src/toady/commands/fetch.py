"""Fetch command implementation."""

import click

from toady.command_utils import (
    validate_limit,
    validate_pr_number,
)
from toady.fetch_service import FetchService
from toady.formatters import format_fetch_output


@click.command()
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
    # Validate input parameters
    validate_pr_number(pr_number)
    validate_limit(limit, max_limit=1000)

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

    except Exception as e:
        # Import here to avoid circular imports
        from toady.exceptions import (
            FetchServiceError,
            GitHubAPIError,
            GitHubAuthenticationError,
            GitHubRateLimitError,
            GitHubTimeoutError,
        )
        from toady.utils import emit_error

        # Use new error handling for pretty output, old system for JSON
        if pretty:
            from toady.error_handling import ErrorMessageFormatter

            message = ErrorMessageFormatter.format_error(e)
            click.echo(message, err=True)
            exit_code = ErrorMessageFormatter.get_exit_code(e)
            ctx.exit(exit_code)
        else:
            # Handle specific error types for JSON output compatibility
            if isinstance(e, GitHubAuthenticationError):
                emit_error(ctx, pr_number, "authentication_failed", str(e), pretty)
            elif isinstance(e, GitHubTimeoutError):
                emit_error(ctx, pr_number, "timeout", str(e), pretty)
            elif isinstance(e, GitHubRateLimitError):
                emit_error(ctx, pr_number, "rate_limit_exceeded", str(e), pretty)
            elif isinstance(e, GitHubAPIError):
                if "404" in str(e) or "not found" in str(e).lower():
                    emit_error(ctx, pr_number, "pr_not_found", str(e), pretty)
                elif "403" in str(e) or "forbidden" in str(e).lower():
                    emit_error(ctx, pr_number, "permission_denied", str(e), pretty)
                else:
                    emit_error(ctx, pr_number, "api_error", str(e), pretty)
            elif isinstance(e, FetchServiceError):
                emit_error(ctx, pr_number, "service_error", str(e), pretty)
            else:
                emit_error(ctx, pr_number, "internal_error", str(e), pretty)
