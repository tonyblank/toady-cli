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
        from toady.error_handling import ErrorMessageFormatter
        from toady.exceptions import (
            FetchServiceError,
            GitHubAPIError,
            GitHubAuthenticationError,
            GitHubRateLimitError,
            GitHubTimeoutError,
        )
        from toady.utils import emit_error

        # Unified error handling approach - use new system for both modes
        if pretty:
            message = ErrorMessageFormatter.format_error(e)
            click.echo(message, err=True)
            exit_code = ErrorMessageFormatter.get_exit_code(e)
            ctx.exit(exit_code)
        else:
            # JSON mode: use centralized error mapping for consistency
            error_mapping = {
                GitHubAuthenticationError: "authentication_failed",
                GitHubTimeoutError: "timeout",
                GitHubRateLimitError: "rate_limit_exceeded",
                FetchServiceError: "service_error",
            }

            error_type = "internal_error"  # default
            for exception_class, error_code in error_mapping.items():
                if isinstance(e, exception_class):
                    error_type = error_code
                    break

            # Special handling for GitHubAPIError based on message content
            if isinstance(e, GitHubAPIError):
                error_msg = str(e).lower()
                if "404" in error_msg or "not found" in error_msg:
                    error_type = "pr_not_found"
                elif "403" in error_msg or "forbidden" in error_msg:
                    error_type = "permission_denied"
                else:
                    error_type = "api_error"

            emit_error(ctx, pr_number, error_type, str(e), pretty)
