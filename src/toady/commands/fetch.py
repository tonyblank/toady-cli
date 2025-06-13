"""Fetch command implementation."""

from typing import Optional

import click

from toady.command_utils import (
    validate_limit,
    validate_pr_number,
)
from toady.formatters.format_selection import (
    create_format_option,
    create_legacy_pretty_option,
    format_threads_output,
    resolve_format_from_options,
)
from toady.services.fetch_service import FetchService


@click.command()
@click.option(
    "--pr",
    "pr_number",
    required=False,
    type=int,
    help="Pull request number to fetch review threads from. Omit for interactive "
    "PR selection. Must be a positive integer representing an existing PR.",
    metavar="NUMBER",
)
@create_format_option()
@create_legacy_pretty_option()
@click.option(
    "--resolved",
    is_flag=True,
    help="Include resolved threads in addition to unresolved ones. Default behavior "
    "returns only unresolved threads that need responses.",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of threads to fetch (default: 100, max: 1000). "
    "Use to control API usage and response size for large PRs.",
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

    Automatically detects and fetches review threads from GitHub PRs. When run
    without arguments, intelligently selects the appropriate PR or prompts for
    selection when multiple PRs exist.

    \b
    Behavior:
      • Default: Auto-detects PR (single PR: fetches automatically, multiple: prompts)
      • With --pr: Fetches from specified pull request number
      • Default: Only unresolved threads (threads needing responses)
      • With --resolved: Includes both resolved and unresolved threads

    \b
    Output structure (JSON):
      [
        {
          "thread_id": "PRRT_kwDOO3WQIc5Rv3_r",     # Use for replies/resolve
          "comment_id": "IC_kwDOABcD12MAAAABcDE3fg", # Alternative ID
          "body": "Please fix this issue",
          "author": "reviewer-username",
          "created_at": "2023-01-01T12:00:00Z",
          "is_resolved": false,
          "pr_number": 123,
          "file_path": "src/main.py",
          "line_number": 42
        }
      ]

    \b
    Examples:
      Auto-detect PR (recommended):
        toady fetch

      Human-readable output:
        toady fetch --format pretty

      Specific PR:
        toady fetch --pr 123

      Include resolved threads:
        toady fetch --resolved

      Limit results:
        toady fetch --limit 50

      Pipeline with other tools:
        toady fetch | jq '.[].thread_id' | xargs -I {} toady resolve --thread-id {}

    \b
    Agent usage patterns:
      # Get unresolved threads for processing
      toady fetch

      # Get all thread IDs for bulk operations
      toady fetch | jq '.[].thread_id'

      # Find threads by author
      toady fetch | jq '.[] | select(.author == "reviewer")'

      # Target specific PR when multiple exist
      toady fetch --pr 123

    \b
    Error codes:
      • authentication_required: GitHub CLI not authenticated
      • pr_not_found: Pull request doesn't exist or no access
      • no_threads_found: PR has no review threads
      • api_rate_limit: GitHub API rate limit exceeded
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
        fetch_service = FetchService(output_format=output_format)
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
