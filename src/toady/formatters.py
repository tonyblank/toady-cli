"""Output formatters for Toady CLI commands."""

import json
from typing import List, Optional

import click

from .models import ReviewThread


class OutputFormatter:
    """Base class for output formatters."""

    @staticmethod
    def format_threads(threads: List[ReviewThread], pretty: bool = False) -> str:
        """Format a list of review threads for output.

        Args:
            threads: List of ReviewThread objects to format
            pretty: If True, use human-readable format; if False, use JSON

        Returns:
            Formatted string output
        """
        if pretty:
            return PrettyFormatter.format_threads(threads)
        else:
            return JSONFormatter.format_threads(threads)


class JSONFormatter:
    """JSON output formatter."""

    @staticmethod
    def format_threads(threads: List[ReviewThread]) -> str:
        """Format threads as JSON array.

        Args:
            threads: List of ReviewThread objects

        Returns:
            JSON string representation
        """
        thread_dicts = [thread.to_dict() for thread in threads]
        return json.dumps(thread_dicts, indent=2)


class PrettyFormatter:
    """Human-readable output formatter with colors and emojis."""

    @staticmethod
    def format_threads(threads: List[ReviewThread]) -> str:
        """Format threads in a human-readable table format.

        Args:
            threads: List of ReviewThread objects

        Returns:
            Pretty formatted string
        """
        if not threads:
            return "No review threads found."

        lines = []

        # Header
        lines.append("📋 Review Threads:")
        lines.append("=" * 80)

        for i, thread in enumerate(threads, 1):
            # Thread header with status emoji
            status_emoji = "✅" if thread.status == "RESOLVED" else "❌"
            lines.append(f"\n{i}. {status_emoji} {thread.title}")

            # Thread details
            lines.append(f"   📝 ID: {thread.thread_id}")
            lines.append(f"   👤 Author: {thread.author}")
            lines.append(
                f"   📅 Created: {thread.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            lines.append(
                f"   🔄 Updated: {thread.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            lines.append(f"   💬 Comments: {len(thread.comments)}")

            # Status with color
            status_color = "green" if thread.status == "RESOLVED" else "red"
            status_text = click.style(thread.status, fg=status_color, bold=True)
            lines.append(f"   🏷️  Status: {status_text}")

            # Separator between threads (except for last one)
            if i < len(threads):
                lines.append("   " + "-" * 60)

        # Summary footer
        resolved_count = sum(1 for t in threads if t.status == "RESOLVED")
        unresolved_count = len(threads) - resolved_count

        lines.append("\n" + "=" * 80)
        lines.append(f"📊 Summary: {len(threads)} total threads")
        if resolved_count > 0:
            lines.append(f"   ✅ Resolved: {resolved_count}")
        if unresolved_count > 0:
            lines.append(f"   ❌ Unresolved: {unresolved_count}")

        return "\n".join(lines)

    @staticmethod
    def format_progress_message(pr_number: int, thread_type: str, limit: int) -> str:
        """Format progress message for fetching.

        Args:
            pr_number: Pull request number
            thread_type: Type of threads being fetched
            limit: Maximum number to fetch

        Returns:
            Formatted progress message
        """
        return f"🔍 Fetching {thread_type} for PR #{pr_number} (limit: {limit})"

    @staticmethod
    def format_result_summary(count: int, thread_type: str) -> str:
        """Format result summary message.

        Args:
            count: Number of threads found
            thread_type: Type of threads that were fetched

        Returns:
            Formatted summary message
        """
        return f"📝 Found {count} {thread_type}"


def format_fetch_output(
    threads: List[ReviewThread],
    pretty: bool = False,
    show_progress: bool = True,
    pr_number: Optional[int] = None,
    thread_type: str = "review threads",
    limit: Optional[int] = None,
) -> None:
    """Format and output fetch command results.

    Args:
        threads: List of ReviewThread objects to display
        pretty: If True, use pretty format; if False, use JSON
        show_progress: If True, show progress messages (only in pretty mode)
        pr_number: Pull request number (for progress messages)
        thread_type: Type of threads being displayed
        limit: Limit used for fetching
    """
    if pretty:
        # Show progress message if requested
        if show_progress and pr_number and limit:
            progress_msg = PrettyFormatter.format_progress_message(
                pr_number, thread_type, limit
            )
            click.echo(progress_msg)

        # Show formatted threads
        output = PrettyFormatter.format_threads(threads)
        click.echo(output)

        # Show summary if we showed progress
        if show_progress:
            summary_msg = PrettyFormatter.format_result_summary(
                len(threads), thread_type
            )
            click.echo(summary_msg)
    else:
        # JSON output - no progress messages
        output = JSONFormatter.format_threads(threads)
        click.echo(output)
