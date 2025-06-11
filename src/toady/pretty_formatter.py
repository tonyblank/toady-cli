"""Pretty formatter implementation for toady CLI output.

This module provides a human-readable formatter that implements the IFormatter
interface, offering colorized output with table formatting and visual enhancements
for better readability in terminal environments.
"""

import re
import textwrap
from typing import Any, Dict, List, Optional, Union

import click

from .format_interfaces import BaseFormatter, FormatterError, FormatterOptions
from .models import Comment, ReviewThread


class PrettyFormatter(BaseFormatter):
    """Pretty formatter that produces human-readable colorized output.

    This formatter provides visually appealing output with color coding,
    table formatting, and proper text wrapping for terminal display.
    """

    def __init__(
        self, options: Optional[FormatterOptions] = None, **kwargs: Any
    ) -> None:
        """Initialize the pretty formatter.

        Args:
            options: FormatterOptions instance with pretty formatting settings.
            **kwargs: Additional options passed to the base formatter.
        """
        super().__init__(**kwargs)
        self.formatter_options = options or FormatterOptions(**kwargs)

        # Pretty formatter specific options
        self.use_colors = kwargs.get("use_colors", True)
        self.table_width = kwargs.get("table_width", 80)
        self.text_width = kwargs.get("text_width", 76)
        self.indent = kwargs.get("indent", "   ")

    def format_threads(self, threads: List[ReviewThread]) -> str:
        """Format a list of review threads in pretty format.

        Args:
            threads: List of ReviewThread objects to format.

        Returns:
            Pretty formatted string representation of the threads.

        Raises:
            FormatterError: If formatting fails.
        """
        try:
            if not threads:
                return self._style("No review threads found.", "yellow")

            lines = []

            # Header
            header = "📋 Review Threads"
            lines.append(self._style(header, "bright_blue", bold=True))
            lines.append("=" * self.table_width)

            for i, thread in enumerate(threads, 1):
                # Thread status styling
                status_color = self._get_status_color(thread.status)
                status_emoji = self._get_status_emoji(thread.status, thread.is_outdated)

                # Thread title with status
                status_text = self._style(thread.status, status_color, bold=True)
                title_line = f"\n{i}. {status_emoji} {thread.title} ({status_text})"
                lines.append(title_line)

                # File context
                file_context = self._format_file_context(thread)
                if file_context:
                    lines.append(f"{self.indent}{file_context}")

                # Thread metadata
                lines.append(
                    f"{self.indent}📝 ID: {self._style(thread.thread_id, 'cyan')}"
                )
                lines.append(
                    f"{self.indent}👤 Author: {self._style(thread.author, 'green')}"
                )

                created_str = thread.created_at.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(
                    f"{self.indent}📅 Created: {self._style(created_str, 'blue')}"
                )

                updated_str = thread.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(
                    f"{self.indent}🔄 Updated: {self._style(updated_str, 'blue')}"
                )

                comment_count = str(len(thread.comments))
                lines.append(
                    f"{self.indent}💬 Comments: {self._style(comment_count, 'magenta')}"
                )

                # Show comments if present
                if thread.comments:
                    lines.append("")
                    lines.append(f"{self.indent}📝 Comment Details:")

                    sorted_comments = sorted(
                        thread.comments, key=lambda c: c.created_at
                    )
                    for j, comment in enumerate(sorted_comments):
                        is_first = j == 0
                        comment_text = self._format_comment(comment, is_first)
                        lines.append(comment_text)

                        if j < len(sorted_comments) - 1:
                            lines.append("")

                # Separator between threads
                if i < len(threads):
                    lines.append("")
                    lines.append(
                        f"{self.indent}" + "─" * (self.table_width - len(self.indent))
                    )

            # Summary footer
            lines.append(self._format_summary(threads))

            return "\n".join(lines)

        except Exception as e:
            raise FormatterError(
                f"Failed to format threads in pretty format: {str(e)}", original_error=e
            ) from e

    def format_comments(self, comments: List[Comment]) -> str:
        """Format a list of comments in pretty format.

        Args:
            comments: List of Comment objects to format.

        Returns:
            Pretty formatted string representation of the comments.

        Raises:
            FormatterError: If formatting fails.
        """
        try:
            if not comments:
                return self._style("No comments found.", "yellow")

            lines = []

            # Header
            header = "💬 Comments"
            lines.append(self._style(header, "bright_blue", bold=True))
            lines.append("=" * self.table_width)

            for i, comment in enumerate(comments, 1):
                lines.append(f"\n{i}. {self._format_comment(comment, is_first=True)}")

                if i < len(comments):
                    lines.append("")
                    lines.append("─" * self.table_width)

            return "\n".join(lines)

        except Exception as e:
            raise FormatterError(
                f"Failed to format comments in pretty format: {str(e)}",
                original_error=e,
            ) from e

    def format_object(self, obj: Any) -> str:
        """Format a single object in pretty format.

        Args:
            obj: Object to format (can be any type).

        Returns:
            Pretty formatted string representation of the object.

        Raises:
            FormatterError: If formatting fails.
        """
        try:
            if obj is None:
                return self._style("null", "dim")

            if isinstance(obj, bool):
                return self._style(str(obj).lower(), "green" if obj else "red")

            if isinstance(obj, (int, float)):
                return self._style(str(obj), "cyan")

            if isinstance(obj, str):
                return self._style(f'"{obj}"', "yellow")

            if isinstance(obj, dict):
                return self._format_dict(obj)

            if isinstance(obj, (list, tuple)):
                return self.format_array(list(obj))

            # For complex objects, try to serialize safely
            try:
                serialized = self._safe_serialize(obj)
                if isinstance(serialized, dict):
                    return self._format_dict(serialized)
                else:
                    return str(serialized)
            except Exception:
                return self._style(f"<{type(obj).__name__}>", "dim")

        except Exception as e:
            raise FormatterError(
                f"Failed to format object in pretty format: {str(e)}", original_error=e
            ) from e

    def format_array(self, items: List[Any]) -> str:
        """Format an array of items in pretty format.

        Args:
            items: List of items to format.

        Returns:
            Pretty formatted string representation of the array.

        Raises:
            FormatterError: If formatting fails.
        """
        try:
            if not items:
                return self._style("[]", "dim")

            # Check if items are uniform dictionaries (table format)
            if all(isinstance(item, dict) for item in items) and len(items) > 1:
                return self._format_table(items)

            # Regular array formatting
            lines = ["["]
            for i, item in enumerate(items):
                formatted_item = self.format_object(item)
                comma = "," if i < len(items) - 1 else ""
                lines.append(f"  {formatted_item}{comma}")
            lines.append("]")

            return "\n".join(lines)

        except Exception as e:
            raise FormatterError(
                f"Failed to format array in pretty format: {str(e)}", original_error=e
            ) from e

    def format_primitive(self, value: Union[str, int, float, bool, None]) -> str:
        """Format a primitive value in pretty format.

        Args:
            value: Primitive value to format.

        Returns:
            Pretty formatted string representation of the value.

        Raises:
            FormatterError: If formatting fails.
        """
        try:
            if value is None:
                return self._style("null", "dim")

            if isinstance(value, bool):
                return self._style(str(value).lower(), "green" if value else "red")

            if isinstance(value, (int, float)):
                return self._style(str(value), "cyan")

            if isinstance(value, str):
                return self._style(value, "white")

            return str(value)

        except Exception as e:
            raise FormatterError(
                f"Failed to format primitive value in pretty format: {str(e)}",
                original_error=e,
            ) from e

    def format_error(self, error: Dict[str, Any]) -> str:
        """Format an error object in pretty format.

        Args:
            error: Error dictionary with error details.

        Returns:
            Pretty formatted string representation of the error.

        Raises:
            FormatterError: If formatting fails.
        """
        try:
            lines = []

            # Error header
            header = "❌ Error"
            lines.append(self._style(header, "red", bold=True))
            lines.append("=" * 40)

            # Error message
            if "message" in error:
                lines.append(f"Message: {self._style(error['message'], 'red')}")

            # Error type
            if "type" in error:
                lines.append(f"Type: {self._style(error['type'], 'yellow')}")

            # Additional details
            for key, value in error.items():
                if key not in ["message", "type", "error", "success"]:
                    lines.append(f"{key.title()}: {self.format_object(value)}")

            return "\n".join(lines)

        except Exception as e:
            raise FormatterError(
                f"Failed to format error in pretty format: {str(e)}", original_error=e
            ) from e

    def _style(self, text: str, color: str, bold: bool = False) -> str:
        """Apply color styling to text if colors are enabled.

        Args:
            text: Text to style.
            color: Color name.
            bold: Whether to make text bold.

        Returns:
            Styled text string.
        """
        if not self.use_colors:
            return text

        return click.style(text, fg=color, bold=bold)

    def _strip_ansi_codes(self, text: str) -> str:
        """Strip ANSI escape codes from text.

        Args:
            text: Text that may contain ANSI escape codes.

        Returns:
            Text with ANSI codes removed.
        """
        # ANSI escape sequence pattern
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def _display_width(self, text: str) -> int:
        """Get the display width of text, excluding ANSI escape codes.

        Args:
            text: Text that may contain ANSI escape codes.

        Returns:
            Display width of the text.
        """
        return len(self._strip_ansi_codes(text))

    def _pad_to_width(self, text: str, width: int, fill_char: str = " ") -> str:
        """Pad text to a specific display width, accounting for ANSI codes.

        Args:
            text: Text to pad (may contain ANSI codes).
            width: Target display width.
            fill_char: Character to use for padding.

        Returns:
            Padded text with correct display width.
        """
        current_width = self._display_width(text)
        if current_width >= width:
            return text

        padding_needed = width - current_width
        return text + (fill_char * padding_needed)

    def _get_status_color(self, status: str) -> str:
        """Get color for thread status.

        Args:
            status: Thread status string.

        Returns:
            Color name for the status.
        """
        color_map = {
            "RESOLVED": "green",
            "OUTDATED": "yellow",
            "PENDING": "red",
            "UNRESOLVED": "red",
        }
        return color_map.get(status.upper(), "white")

    def _get_status_emoji(self, status: str, is_outdated: bool = False) -> str:
        """Get emoji for thread status.

        Args:
            status: Thread status string.
            is_outdated: Whether thread is outdated.

        Returns:
            Emoji string for the status.
        """
        if is_outdated or status.upper() == "OUTDATED":
            return "⏰"
        elif status.upper() == "RESOLVED":
            return "✅"
        else:
            return "❌"

    def _format_file_context(self, thread: ReviewThread) -> str:
        """Format file context information for a thread.

        Args:
            thread: ReviewThread with file context.

        Returns:
            Formatted file context string.
        """
        if not thread.file_path:
            return ""

        context_parts = []

        # File path
        file_path = self._style(thread.file_path, "blue")
        context_parts.append(f"📁 File: {file_path}")

        # Line information
        if thread.line is not None:
            if thread.start_line is not None and thread.start_line != thread.line:
                line_info = self._style(f"{thread.start_line}-{thread.line}", "cyan")
                context_parts.append(f"📍 Lines: {line_info}")
            else:
                line_info = self._style(str(thread.line), "cyan")
                context_parts.append(f"📍 Line: {line_info}")

        # Diff side
        if thread.diff_side:
            side_emoji = "◀️" if thread.diff_side == "LEFT" else "▶️"
            side_text = self._style(thread.diff_side, "magenta")
            context_parts.append(f"{side_emoji} Side: {side_text}")

        # Outdated indicator
        if thread.is_outdated:
            context_parts.append(self._style("⚠️ Outdated", "yellow"))

        return f"\n{self.indent}".join(context_parts)

    def _format_comment(self, comment: Comment, is_first: bool = False) -> str:
        """Format a single comment with proper styling.

        Args:
            comment: Comment object to format.
            is_first: Whether this is the first comment in thread.

        Returns:
            Formatted comment string.
        """
        lines = []

        # Comment header
        author_display = self._style(comment.author, "green", bold=True)
        if comment.author_name and comment.author_name != comment.author:
            name_styled = self._style(comment.author_name, "green")
            author_styled = self._style(comment.author, "green")
            author_display = f"{name_styled} (@{author_styled})"

        timestamp = self._style(
            comment.created_at.strftime("%Y-%m-%d %H:%M:%S"), "blue"
        )

        if is_first:
            header = f"💬 {author_display} • {timestamp}"
        else:
            header = f"↪️ {author_display} • {timestamp}"

        lines.append(f"{self.indent}{header}")

        # Comment content with proper wrapping
        if comment.content:
            content_lines = self._wrap_comment_content(comment.content)
            lines.extend(content_lines)

        # Comment URL
        if comment.url:
            url_text = self._style(comment.url, "cyan", bold=False)
            lines.append(f"{self.indent}   🔗 {url_text}")

        return "\n".join(lines)

    def _wrap_comment_content(self, content: str) -> List[str]:
        """Wrap comment content with proper formatting.

        Args:
            content: Comment content to wrap.

        Returns:
            List of wrapped content lines.
        """
        lines = []
        content_lines = content.split("\n")
        in_code_block = False

        for line in content_lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                lines.append(f"{self.indent}   {self._style(line, 'dim')}")
            elif in_code_block:
                # Preserve code formatting
                lines.append(f"{self.indent}   {self._style(line, 'white')}")
            else:
                # Wrap regular text
                if line.strip():
                    wrapped = textwrap.fill(
                        line.strip(),
                        width=self.text_width - len(self.indent) - 3,
                        initial_indent="",
                        subsequent_indent="",
                    )
                    for wrapped_line in wrapped.split("\n"):
                        if wrapped_line.strip():
                            lines.append(f"{self.indent}   {wrapped_line}")
                else:
                    lines.append("")

        return lines

    def _format_dict(self, obj: Dict[str, Any]) -> str:
        """Format a dictionary in pretty format.

        Args:
            obj: Dictionary to format.

        Returns:
            Pretty formatted dictionary string.
        """
        if not obj:
            return "{}"

        lines = ["{"]
        items = list(obj.items())

        for i, (key, value) in enumerate(items):
            key_str = self._style(f'"{key}"', "yellow")
            value_str = self.format_object(value)
            comma = "," if i < len(items) - 1 else ""
            lines.append(f"  {key_str}: {value_str}{comma}")

        lines.append("}")
        return "\n".join(lines)

    def _format_table(self, items: List[Dict[str, Any]]) -> str:
        """Format a list of dictionaries as a table.

        Args:
            items: List of dictionaries to format as table.

        Returns:
            Table formatted string.
        """
        if not items:
            return "No data"

        # Get all unique keys
        all_keys: set[str] = set()
        for item in items:
            all_keys.update(item.keys())

        headers = sorted(all_keys)

        # Calculate column widths based on display width (excluding ANSI codes)
        col_widths = {}
        for header in headers:
            col_widths[header] = len(header)
            for item in items:
                value = str(item.get(header, ""))
                # Use display width in case value contains ANSI codes
                display_width = self._display_width(value)
                col_widths[header] = max(col_widths[header], display_width)

        # Limit column widths
        max_col_width = max(10, (self.table_width - len(headers) * 3) // len(headers))
        for header in headers:
            col_widths[header] = min(col_widths[header], max_col_width)

        lines = []

        # Header row
        header_parts = []
        for header in headers:
            truncated_header = header[: col_widths[header]]
            header_text = self._style(truncated_header, "bright_blue", bold=True)
            padded_header = self._pad_to_width(header_text, col_widths[header])
            header_parts.append(padded_header)
        lines.append(" | ".join(header_parts))

        # Separator
        sep_parts = ["-" * col_widths[header] for header in headers]
        lines.append("-|-".join(sep_parts))

        # Data rows
        for item in items:
            row_parts = []
            for header in headers:
                value = str(item.get(header, ""))
                if len(value) > col_widths[header]:
                    value = value[: col_widths[header] - 3] + "..."

                # Style different data types
                if header.lower() in ["id", "number"]:
                    styled_value = self._style(value, "cyan")
                elif header.lower() in ["status", "state"]:
                    color = self._get_status_color(value)
                    styled_value = self._style(value, color)
                elif header.lower() in ["author", "user"]:
                    styled_value = self._style(value, "green")
                else:
                    styled_value = value

                padded_value = self._pad_to_width(styled_value, col_widths[header])
                row_parts.append(padded_value)
            lines.append(" | ".join(row_parts))

        return "\n".join(lines)

    def _format_summary(self, threads: List[ReviewThread]) -> str:
        """Format summary footer for threads.

        Args:
            threads: List of threads to summarize.

        Returns:
            Formatted summary string.
        """
        resolved_count = sum(1 for t in threads if t.status == "RESOLVED")
        unresolved_count = len(threads) - resolved_count
        outdated_count = sum(
            1 for t in threads if t.is_outdated or t.status == "OUTDATED"
        )

        lines = ["\n" + "=" * self.table_width]

        total_text = self._style(
            f"{len(threads)} total threads", "bright_blue", bold=True
        )
        lines.append(f"📊 Summary: {total_text}")

        if resolved_count > 0:
            resolved_text = self._style(str(resolved_count), "green", bold=True)
            lines.append(f"   ✅ Resolved: {resolved_text}")

        if unresolved_count > 0:
            unresolved_text = self._style(str(unresolved_count), "red", bold=True)
            lines.append(f"   ❌ Unresolved: {unresolved_text}")

        if outdated_count > 0:
            outdated_text = self._style(str(outdated_count), "yellow", bold=True)
            lines.append(f"   ⏰ Outdated: {outdated_text}")

        return "\n".join(lines)


# Create a default pretty formatter instance for backward compatibility
default_pretty_formatter = PrettyFormatter()


def format_threads_pretty(threads: List[ReviewThread]) -> str:
    """Convenience function for formatting threads in pretty format.

    Args:
        threads: List of ReviewThread objects to format.

    Returns:
        Pretty formatted string representation of the threads.
    """
    return default_pretty_formatter.format_threads(threads)


def format_comments_pretty(comments: List[Comment]) -> str:
    """Convenience function for formatting comments in pretty format.

    Args:
        comments: List of Comment objects to format.

    Returns:
        Pretty formatted string representation of the comments.
    """
    return default_pretty_formatter.format_comments(comments)


def format_object_pretty(obj: Any) -> str:
    """Convenience function for formatting any object in pretty format.

    Args:
        obj: Object to format.

    Returns:
        Pretty formatted string representation of the object.
    """
    return default_pretty_formatter.format_object(obj)
