"""Fetch command implementation."""

from typing import Optional

import click

from toady.command_utils import (
    validate_limit,
    validate_pr_number,
)
from toady.fetch_service import FetchService
from toady.format_selection import (
    create_format_option,
    create_legacy_pretty_option,
    format_threads_output,
    resolve_format_from_options,
)


@click.command()
@click.option(
    "--pr",
    "pr_number",
    required=False,
    type=int,
    help="Pull request number to fetch review threads from. If not provided, "
    "will show interactive PR selection.",
    metavar="NUMBER",
)
@create_format_option()
@create_legacy_pretty_option()
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
    ctx: click.Context,
    pr_number: Optional[int],
    format: Optional[str],
    pretty: bool,
    resolved: bool,
    limit: int,
) -> None:
    """Fetch review threads from a GitHub pull request.

    If --pr is provided, fetches threads from that specific pull request.
    If --pr is omitted, displays an interactive menu to select from open PRs.

    By default, only unresolved review threads are fetched. Use --resolved
    to include resolved threads as well.

    Examples:

        toady fetch --pr 123

        toady fetch --pr 123 --format pretty

        toady fetch --pr 123 --resolved --limit 50

        toady fetch  # Interactive PR selection

        toady fetch --format pretty  # Interactive selection with pretty output

        toady fetch --pretty  # Backward compatibility (deprecated)
    """
    # Validate input parameters
    if pr_number is not None:
        validate_pr_number(pr_number)
    validate_limit(limit, max_limit=1000)

    # Resolve format from options
    try:
        output_format = resolve_format_from_options(format, pretty)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

    # Prepare thread type description for user feedback
    thread_type = "all threads" if resolved else "unresolved threads"

    # Execute fetch operation with comprehensive error handling
    selected_pr_number = pr_number  # Initialize with provided value for error handling
    try:
        # Create fetch service and retrieve threads using integrated PR selection
        fetch_service = FetchService()
        threads, selected_pr_number = (
            fetch_service.fetch_review_threads_with_pr_selection(
                pr_number=pr_number,
                include_resolved=resolved,
                threads_limit=limit,
            )
        )

        # Handle case where user cancelled PR selection or no PR available
        if not threads and selected_pr_number is None:
            ctx.exit(0)

        # Use new format selection system to display output
        format_threads_output(
            threads=threads,
            format_name=output_format,
            show_progress=True,
            pr_number=selected_pr_number,
            thread_type=thread_type,
            limit=limit,
        )

    except click.exceptions.Exit:
        # Re-raise Exit exceptions (normal exit behavior)
        raise
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

        # Unified error handling approach - use new format system
        if output_format == "pretty":
            message = ErrorMessageFormatter.format_error(e)
            click.echo(message, err=True)
            exit_code = ErrorMessageFormatter.get_exit_code(e)
            ctx.exit(exit_code)
        else:
            # JSON/other formats: use centralized error mapping for consistency
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

            emit_error(
                ctx,
                selected_pr_number or 0,
                error_type,
                str(e),
                output_format == "pretty",
            )
