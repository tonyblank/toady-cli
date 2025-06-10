"""Fetch command implementation."""

import click

from toady.exceptions import (
    FetchServiceError,
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from toady.fetch_service import FetchService
from toady.formatters import format_fetch_output
from toady.utils import MAX_PR_NUMBER, emit_error


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
            emit_error(ctx, pr_number, "authentication_failed", str(e), pretty)

    except GitHubTimeoutError as e:
        if pretty:
            click.echo(f"❌ Request timed out: {e}", err=True)
            click.echo("💡 The request took too long. Please:", err=True)
            click.echo("   • Try again with a smaller --limit", err=True)
            click.echo("   • Check your internet connection", err=True)
            click.echo("   • GitHub API may be experiencing issues", err=True)
            ctx.exit(1)
        else:
            emit_error(ctx, pr_number, "timeout", str(e), pretty)

    except GitHubRateLimitError as e:
        if pretty:
            click.echo(f"❌ Rate limit exceeded: {e}", err=True)
            click.echo("💡 You've made too many requests. Please:", err=True)
            click.echo("   • Wait a few minutes before trying again", err=True)
            click.echo("   • Consider using a smaller --limit", err=True)
            click.echo("   • Check rate limit status: gh api rate_limit", err=True)
            ctx.exit(1)
        else:
            emit_error(ctx, pr_number, "rate_limit_exceeded", str(e), pretty)

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
                emit_error(ctx, pr_number, "pr_not_found", str(e), pretty)
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
                emit_error(ctx, pr_number, "permission_denied", str(e), pretty)
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
                emit_error(ctx, pr_number, "api_error", str(e), pretty)

    except FetchServiceError as e:
        if pretty:
            click.echo(f"❌ Failed to fetch threads: {e}", err=True)
            click.echo("💡 This may be a service error. Please:", err=True)
            click.echo("   • Check your repository setup", err=True)
            click.echo("   • Ensure you're in a git repository", err=True)
            click.echo("   • Try again with different parameters", err=True)
            ctx.exit(1)
        else:
            emit_error(ctx, pr_number, "service_error", str(e), pretty)

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
            emit_error(ctx, pr_number, "internal_error", str(e), pretty)
