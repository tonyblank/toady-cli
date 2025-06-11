"""Output formatters for Toady CLI commands.

This module provides both the legacy formatter implementations and integration
with the new formatter interface system.
"""

import json
import textwrap
from typing import List, Optional

import click

from .format_interfaces import FormatterFactory
from .json_formatter import JSONFormatter as NewJSONFormatter
from .models import Comment, ReviewThread


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
    def _wrap_text(text: str, width: int = 76, indent: str = "   ") -> str:
        """Wrap text to specified width with consistent indentation.

        Args:
            text: Text to wrap
            width: Maximum line width
            indent: Indentation string for wrapped lines

        Returns:
            Wrapped text with proper indentation
        """
        if not text:
            return ""

        wrapper = textwrap.TextWrapper(
            width=width,
            initial_indent=indent,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )

        paragraphs = text.split("\n")
        wrapped_paragraphs = []

        for paragraph in paragraphs:
            if paragraph.strip():
                wrapped_paragraphs.append(wrapper.fill(paragraph))
            else:
                wrapped_paragraphs.append("")

        return "\n".join(wrapped_paragraphs)

    @staticmethod
    def _format_file_context(thread: ReviewThread) -> str:
        """Format file context information for a thread.

        Args:
            thread: ReviewThread with file context

        Returns:
            Formatted file context string
        """
        if not thread.file_path:
            return ""

        context_parts = []

        # File path
        context_parts.append(f"📁 File: {thread.file_path}")

        # Line information
        if thread.line is not None:
            if thread.start_line is not None and thread.start_line != thread.line:
                context_parts.append(f"📍 Lines: {thread.start_line}-{thread.line}")
            else:
                context_parts.append(f"📍 Line: {thread.line}")

        # Diff side
        if thread.diff_side:
            side_emoji = "◀️" if thread.diff_side == "LEFT" else "▶️"
            context_parts.append(f"{side_emoji} Side: {thread.diff_side}")

        # Outdated indicator
        if thread.is_outdated:
            context_parts.append("⚠️ Outdated")

        return "\n   ".join(context_parts)

    @staticmethod
    def _format_comment(
        comment: Comment, is_first: bool = False, indent: str = "   "
    ) -> str:
        """Format a single comment with proper styling.

        Args:
            comment: Comment object to format
            is_first: Whether this is the first comment in thread
            indent: Base indentation level

        Returns:
            Formatted comment string
        """
        lines = []

        # Comment header
        author_display = comment.author
        if comment.author_name and comment.author_name != comment.author:
            author_display = f"{comment.author_name} (@{comment.author})"

        timestamp = comment.created_at.strftime("%Y-%m-%d %H:%M:%S")

        if is_first:
            header = f"💬 {author_display} • {timestamp}"
        else:
            header = f"↪️ {author_display} • {timestamp}"

        lines.append(f"{indent}{header}")

        # Comment content with proper wrapping
        if comment.content:
            # Handle code blocks and preserve formatting
            content_lines = comment.content.split("\n")
            in_code_block = False

            for line in content_lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    lines.append(f"{indent}   {line}")
                elif in_code_block:
                    # Preserve code formatting
                    lines.append(f"{indent}   {line}")
                else:
                    # Wrap regular text
                    if line.strip():
                        wrapped = PrettyFormatter._wrap_text(line, width=70, indent="")
                        for wrapped_line in wrapped.split("\n"):
                            if wrapped_line.strip():
                                lines.append(f"{indent}   {wrapped_line.strip()}")
                    else:
                        lines.append("")

        # Comment URL (if available)
        if comment.url:
            lines.append(f"{indent}   🔗 {comment.url}")

        return "\n".join(lines)

    @staticmethod
    def format_threads(threads: List[ReviewThread]) -> str:
        """Format threads in a human-readable format with full comment content.

        Args:
            threads: List of ReviewThread objects

        Returns:
            Pretty formatted string with enhanced comment preview
        """
        if not threads:
            return "No review threads found."

        lines = []

        # Header
        lines.append("📋 Review Threads:")
        lines.append("=" * 80)

        for i, thread in enumerate(threads, 1):
            # Thread header with enhanced status indicator
            if thread.status == "RESOLVED":
                status_emoji = "✅"
                status_color = "green"
            elif thread.status == "OUTDATED" or thread.is_outdated:
                status_emoji = "⏰"
                status_color = "yellow"
            else:
                status_emoji = "❌"
                status_color = "red"

            # Thread title with status
            status_text = click.style(thread.status, fg=status_color, bold=True)
            lines.append(f"\n{i}. {status_emoji} {thread.title} ({status_text})")

            # File context
            file_context = PrettyFormatter._format_file_context(thread)
            if file_context:
                lines.append(f"   {file_context}")

            # Thread metadata
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
            status_text_colored = click.style(thread.status, fg=status_color, bold=True)
            lines.append(f"   🏷️  Status: {status_text_colored}")

            # Show full comment content if there are comments
            if thread.comments:
                lines.append("")
                lines.append("   📝 Comment Details:")

                # Sort comments by creation date to show conversation flow
                sorted_comments = sorted(thread.comments, key=lambda c: c.created_at)

                for j, comment in enumerate(sorted_comments):
                    is_first = j == 0
                    comment_text = PrettyFormatter._format_comment(comment, is_first)
                    lines.append(comment_text)

                    # Add spacing between comments
                    if j < len(sorted_comments) - 1:
                        lines.append("")

            # Separator between threads (except for last one)
            if i < len(threads):
                lines.append("")
                lines.append("   " + "─" * 76)

        # Summary footer
        resolved_count = sum(1 for t in threads if t.status == "RESOLVED")
        unresolved_count = len(threads) - resolved_count
        outdated_count = sum(
            1 for t in threads if t.is_outdated or t.status == "OUTDATED"
        )

        lines.append("\n" + "=" * 80)
        lines.append(f"📊 Summary: {len(threads)} total threads")
        if resolved_count > 0:
            lines.append(f"   ✅ Resolved: {resolved_count}")
        if unresolved_count > 0:
            lines.append(f"   ❌ Unresolved: {unresolved_count}")
        if outdated_count > 0:
            lines.append(f"   ⏰ Outdated: {outdated_count}")

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


# Register formatters with the factory
FormatterFactory.register("json", NewJSONFormatter)

# Register the new PrettyFormatter (import moved to avoid circular imports)
try:
    from .pretty_formatter import PrettyFormatter as NewPrettyFormatter

    FormatterFactory.register("pretty", NewPrettyFormatter)
except ImportError:
    # PrettyFormatter not available - this is expected during initial module loading
    pass
