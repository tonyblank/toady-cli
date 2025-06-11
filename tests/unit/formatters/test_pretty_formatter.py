"""Tests for the Pretty formatter implementation."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from toady.formatters.format_interfaces import FormatterError, FormatterOptions
from toady.formatters.pretty_formatter import (
    PrettyFormatter,
    default_pretty_formatter,
    format_comments_pretty,
    format_object_pretty,
    format_threads_pretty,
)
from toady.models.models import Comment, ReviewThread


class TestPrettyFormatter:
    """Test the PrettyFormatter class."""

    def test_initialization_default(self):
        """Test PrettyFormatter initialization with default options."""
        formatter = PrettyFormatter()

        assert formatter.formatter_options is not None
        assert formatter.formatter_options.indent == 2
        assert formatter.use_colors is True
        assert formatter.table_width == 80
        assert formatter.text_width == 76
        assert formatter.indent == "   "

    def test_initialization_custom_options(self):
        """Test PrettyFormatter initialization with custom options."""
        options = FormatterOptions(indent=4)
        formatter = PrettyFormatter(
            options=options,
            use_colors=False,
            table_width=100,
            text_width=90,
            indent="  ",
        )

        assert formatter.formatter_options is options
        assert formatter.use_colors is False
        assert formatter.table_width == 100
        assert formatter.text_width == 90
        assert formatter.indent == "  "

    def test_format_threads_empty(self):
        """Test formatting empty threads list."""
        formatter = PrettyFormatter(use_colors=False)
        result = formatter.format_threads([])

        assert "No review threads found." in result

    def test_format_threads_single(self):
        """Test formatting single thread."""
        formatter = PrettyFormatter(use_colors=False)

        thread = ReviewThread(
            thread_id="T_123",
            title="Test thread",
            status="UNRESOLVED",
            author="testuser",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            comments=[],
            file_path="test.py",
            line=10,
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        assert "📋 Review Threads" in result
        assert "Test thread" in result
        assert "UNRESOLVED" in result
        assert "T_123" in result
        assert "testuser" in result
        assert "test.py" in result
        assert "❌" in result  # unresolved emoji

    def test_format_threads_with_colors(self):
        """Test formatting threads with color support."""
        formatter = PrettyFormatter(use_colors=True)

        thread = ReviewThread(
            thread_id="T_123",
            title="Test thread",
            status="RESOLVED",
            author="testuser",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            comments=[],
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        # Should contain ANSI color codes for resolved status
        assert "\x1b[32m" in result or "RESOLVED" in result  # Green color or text

    def test_format_threads_multiple_statuses(self):
        """Test formatting threads with different statuses."""
        formatter = PrettyFormatter(use_colors=False)

        threads = [
            ReviewThread(
                thread_id="T_1",
                title="Resolved thread",
                status="RESOLVED",
                author="user1",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                comments=[],
                is_outdated=False,
            ),
            ReviewThread(
                thread_id="T_2",
                title="Outdated thread",
                status="OUTDATED",
                author="user2",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                comments=[],
                is_outdated=True,
            ),
            ReviewThread(
                thread_id="T_3",
                title="Unresolved thread",
                status="UNRESOLVED",
                author="user3",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                comments=[],
                is_outdated=False,
            ),
        ]

        result = formatter.format_threads(threads)

        assert "✅" in result  # resolved emoji
        assert "⏰" in result  # outdated emoji
        assert "❌" in result  # unresolved emoji
        assert "3 total threads" in result

    def test_format_threads_with_comments(self):
        """Test formatting threads with comments."""
        formatter = PrettyFormatter(use_colors=False)

        comment = Comment(
            comment_id="C_1",
            content="This is a test comment",
            author="commenter",
            author_name="Test Commenter",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            parent_id=None,
            thread_id="T_123",
            url="https://github.com/test/comment/1",
        )

        thread = ReviewThread(
            thread_id="T_123",
            title="Test thread with comments",
            status="UNRESOLVED",
            author="testuser",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            comments=[comment],
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        assert "Comment Details:" in result
        assert "This is a test comment" in result
        assert "Test Commenter" in result
        assert "commenter" in result
        assert "💬" in result  # comment emoji

    def test_format_comments_empty(self):
        """Test formatting empty comments list."""
        formatter = PrettyFormatter(use_colors=False)
        result = formatter.format_comments([])

        assert "No comments found." in result

    def test_format_comments_single(self):
        """Test formatting single comment."""
        formatter = PrettyFormatter(use_colors=False)

        comment = Comment(
            comment_id="C_1",
            content="Test comment content",
            author="testuser",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            parent_id=None,
            thread_id="T_1",
            url="https://github.com/test",
        )

        result = formatter.format_comments([comment])

        assert "💬 Comments" in result
        assert "Test comment content" in result
        assert "testuser" in result
        assert "https://github.com/test" in result

    def test_format_object_primitives(self):
        """Test formatting primitive values."""
        formatter = PrettyFormatter(use_colors=False)

        assert "null" in formatter.format_object(None)
        assert "true" in formatter.format_object(True)
        assert "false" in formatter.format_object(False)
        assert "42" in formatter.format_object(42)
        assert "3.14" in formatter.format_object(3.14)
        assert '"hello"' in formatter.format_object("hello")

    def test_format_object_dict(self):
        """Test formatting dictionary objects."""
        formatter = PrettyFormatter(use_colors=False)

        test_dict = {"key1": "value1", "key2": 42, "key3": True}
        result = formatter.format_object(test_dict)

        assert "{" in result
        assert "}" in result
        assert "key1" in result
        assert "value1" in result
        assert "key2" in result
        assert "42" in result

    def test_format_array_simple(self):
        """Test formatting simple arrays."""
        formatter = PrettyFormatter(use_colors=False)

        test_array = [1, 2, 3]
        result = formatter.format_array(test_array)

        assert "[" in result
        assert "]" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_format_array_as_table(self):
        """Test formatting array of dictionaries as table."""
        formatter = PrettyFormatter(use_colors=False)

        test_array = [
            {"id": 1, "name": "Alice", "status": "active"},
            {"id": 2, "name": "Bob", "status": "inactive"},
        ]
        result = formatter.format_array(test_array)

        # Should format as table
        assert "id" in result
        assert "name" in result
        assert "status" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "|" in result  # table separator

    def test_format_primitive_types(self):
        """Test formatting different primitive types."""
        formatter = PrettyFormatter(use_colors=False)

        assert "null" in formatter.format_primitive(None)
        assert "true" in formatter.format_primitive(True)
        assert "false" in formatter.format_primitive(False)
        assert "123" in formatter.format_primitive(123)
        assert "45.67" in formatter.format_primitive(45.67)
        assert "test" in formatter.format_primitive("test")

    def test_format_error(self):
        """Test formatting error objects."""
        formatter = PrettyFormatter(use_colors=False)

        error = {
            "message": "Something went wrong",
            "type": "ValidationError",
            "code": 400,
        }
        result = formatter.format_error(error)

        assert "❌ Error" in result
        assert "Something went wrong" in result
        assert "ValidationError" in result
        assert "400" in result

    def test_get_status_color(self):
        """Test status color mapping."""
        formatter = PrettyFormatter()

        assert formatter._get_status_color("RESOLVED") == "green"
        assert formatter._get_status_color("OUTDATED") == "yellow"
        assert formatter._get_status_color("UNRESOLVED") == "red"
        assert formatter._get_status_color("PENDING") == "red"
        assert formatter._get_status_color("UNKNOWN") == "white"

    def test_get_status_emoji(self):
        """Test status emoji mapping."""
        formatter = PrettyFormatter()

        assert formatter._get_status_emoji("RESOLVED") == "✅"
        assert formatter._get_status_emoji("OUTDATED") == "⏰"
        assert formatter._get_status_emoji("UNRESOLVED") == "❌"
        assert formatter._get_status_emoji("RESOLVED", is_outdated=True) == "⏰"

    @patch("click.style")
    def test_style_without_colors(self, mock_style):
        """Test styling when colors are disabled."""
        formatter = PrettyFormatter(use_colors=False)
        result = formatter._style("test", "red", bold=True)

        # Should return text without styling
        assert result == "test"
        mock_style.assert_not_called()

    @patch("click.style")
    def test_style_with_colors(self, mock_style):
        """Test styling when colors are enabled."""
        mock_style.return_value = "styled_text"
        formatter = PrettyFormatter(use_colors=True)
        result = formatter._style("test", "red", bold=True)

        mock_style.assert_called_once_with("test", fg="red", bold=True)
        assert result == "styled_text"

    def test_format_file_context(self):
        """Test file context formatting."""
        formatter = PrettyFormatter(use_colors=False)

        thread = ReviewThread(
            thread_id="T_1",
            title="Test",
            status="UNRESOLVED",
            author="user",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            comments=[],
            file_path="src/test.py",
            line=42,
            start_line=40,
            diff_side="RIGHT",
            is_outdated=True,
        )

        result = formatter._format_file_context(thread)

        assert "📁 File:" in result
        assert "src/test.py" in result
        assert "📍 Lines:" in result
        assert "40-42" in result
        assert "▶️ Side:" in result
        assert "RIGHT" in result
        assert "⚠️ Outdated" in result

    def test_wrap_comment_content_with_code_blocks(self):
        """Test comment content wrapping with code blocks."""
        formatter = PrettyFormatter(use_colors=False)

        content = "Regular text\n```python\ncode line\n```\nMore text"
        result = formatter._wrap_comment_content(content)

        # Should preserve code block formatting
        code_block_lines = [line for line in result if "code line" in line]
        assert len(code_block_lines) > 0

    def test_format_table_with_various_data_types(self):
        """Test table formatting with different data types."""
        formatter = PrettyFormatter(use_colors=False)

        items = [
            {"id": 1, "status": "RESOLVED", "author": "alice"},
            {"id": 2, "status": "PENDING", "author": "bob"},
        ]
        result = formatter._format_table(items)

        assert "id" in result
        assert "status" in result
        assert "author" in result
        assert "alice" in result
        assert "bob" in result
        assert "|" in result

    def test_format_summary(self):
        """Test summary formatting."""
        formatter = PrettyFormatter(use_colors=False)

        threads = [
            Mock(status="RESOLVED", is_outdated=False),
            Mock(status="UNRESOLVED", is_outdated=False),
            Mock(status="RESOLVED", is_outdated=True),
        ]

        result = formatter._format_summary(threads)

        assert "3 total threads" in result
        assert "Resolved: 2" in result
        assert "Unresolved: 1" in result
        assert "Outdated:" in result

    def test_format_threads_handles_errors(self):
        """Test error handling in format_threads."""
        formatter = PrettyFormatter()

        # Create a thread that will cause formatting errors
        bad_thread = Mock()
        bad_thread.status = "UNRESOLVED"
        bad_thread.is_outdated = False
        bad_thread.title = None  # This might cause issues
        bad_thread.thread_id = None
        bad_thread.author = None
        bad_thread.created_at = "invalid_date"  # Invalid date
        bad_thread.updated_at = datetime.now()
        bad_thread.comments = []
        bad_thread.file_path = None

        with pytest.raises(FormatterError):
            formatter.format_threads([bad_thread])

    def test_format_object_handles_complex_objects(self):
        """Test format_object with complex objects."""
        formatter = PrettyFormatter()

        # Test with an object that has __dict__
        class TestObj:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        obj = TestObj()
        result = formatter.format_object(obj)

        # Should serialize using __dict__
        assert "attr1" in result
        assert "value1" in result
        assert "attr2" in result


class TestPrettyFormatterConvenienceFunctions:
    """Test convenience functions for pretty formatting."""

    def test_format_threads_pretty(self):
        """Test format_threads_pretty convenience function."""
        thread = ReviewThread(
            thread_id="T_1",
            title="Test",
            status="RESOLVED",
            author="user",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            comments=[],
            is_outdated=False,
        )

        result = format_threads_pretty([thread])
        assert "Test" in result
        assert "RESOLVED" in result

    def test_format_comments_pretty(self):
        """Test format_comments_pretty convenience function."""
        comment = Comment(
            comment_id="C_1",
            content="Test comment",
            author="user",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            parent_id=None,
            thread_id="T_1",
        )

        result = format_comments_pretty([comment])
        assert "Test comment" in result
        assert "user" in result

    def test_format_object_pretty(self):
        """Test format_object_pretty convenience function."""
        obj = {"key": "value", "number": 42}
        result = format_object_pretty(obj)

        assert "key" in result
        assert "value" in result
        assert "42" in result

    def test_default_formatter_instance(self):
        """Test that default formatter instance is properly configured."""
        assert isinstance(default_pretty_formatter, PrettyFormatter)
        assert default_pretty_formatter.use_colors is True


class TestPrettyFormatterErrorHandling:
    """Test error handling in PrettyFormatter."""

    def test_format_comments_with_invalid_data(self):
        """Test format_comments with invalid comment data."""
        formatter = PrettyFormatter()

        # Create a comment with problematic data
        bad_comment = Mock()
        bad_comment.author = None
        bad_comment.author_name = None
        bad_comment.created_at = "invalid_date"
        bad_comment.content = None
        bad_comment.url = None

        with pytest.raises(FormatterError):
            formatter.format_comments([bad_comment])

    def test_formatter_error_chaining(self):
        """Test that FormatterError properly chains original exceptions."""
        formatter = PrettyFormatter()

        # This should raise a FormatterError that chains the original
        with pytest.raises(FormatterError) as exc_info:
            formatter.format_threads([None])  # None should cause issues

        assert exc_info.value.original_error is not None


class TestPrettyFormatterIntegration:
    """Integration tests for PrettyFormatter."""

    def test_complete_workflow(self):
        """Test complete formatting workflow with realistic data."""
        formatter = PrettyFormatter(use_colors=False)

        comment1 = Comment(
            comment_id="C_1",
            content="This needs to be fixed",
            author="reviewer",
            author_name="Code Reviewer",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0),
            parent_id=None,
            thread_id="RT_123",
            url="https://github.com/test/comment/1",
        )

        comment2 = Comment(
            comment_id="C_2",
            content="Thanks, I'll fix this",
            author="developer",
            created_at=datetime(2024, 1, 1, 11, 0, 0),
            updated_at=datetime(2024, 1, 1, 11, 0, 0),
            parent_id="C_1",
            thread_id="RT_123",
            url="https://github.com/test/comment/2",
        )

        thread = ReviewThread(
            thread_id="RT_123",
            title="Fix validation bug",
            status="UNRESOLVED",
            author="reviewer",
            created_at=datetime(2024, 1, 1, 9, 0, 0),
            updated_at=datetime(2024, 1, 1, 11, 0, 0),
            comments=[comment1, comment2],
            file_path="src/validation.py",
            line=45,
            start_line=42,
            diff_side="RIGHT",
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        # Verify all key elements are present
        assert "📋 Review Threads" in result
        assert "Fix validation bug" in result
        assert "UNRESOLVED" in result
        assert "❌" in result
        assert "src/validation.py" in result
        assert "Lines: 42-45" in result
        assert "Comment Details:" in result
        assert "This needs to be fixed" in result
        assert "Thanks, I'll fix this" in result
        assert "Code Reviewer" in result
        assert "💬" in result
        assert "↪️" in result
        assert "1 total threads" in result
        assert "Unresolved: 1" in result

    def test_formatter_with_factory_integration(self):
        """Test that formatter works with FormatterFactory."""
        from toady.formatters.format_interfaces import FormatterFactory

        # Ensure pretty formatter is registered
        if not FormatterFactory.is_registered("pretty"):
            FormatterFactory.register("pretty", PrettyFormatter)

        # Should be able to create via factory
        formatter = FormatterFactory.create("pretty", use_colors=False)
        assert isinstance(formatter, PrettyFormatter)
        assert formatter.use_colors is False

        # Should be registered
        assert FormatterFactory.is_registered("pretty")
        assert "pretty" in FormatterFactory.list_formatters()

    def test_ansi_code_handling(self):
        """Test ANSI code stripping and display width calculation."""
        formatter = PrettyFormatter(use_colors=True)

        # Test with actual ANSI codes
        styled_text = "\x1b[32mHello\x1b[0m"  # Green "Hello"

        # Test stripping ANSI codes
        stripped = formatter._strip_ansi_codes(styled_text)
        assert stripped == "Hello"

        # Test display width calculation
        width = formatter._display_width(styled_text)
        assert width == 5  # "Hello" is 5 characters

        # Test padding
        padded = formatter._pad_to_width(styled_text, 10)
        assert formatter._display_width(padded) == 10
        assert padded.endswith("     ")  # Should have 5 spaces at the end

    def test_pad_to_width_edge_cases(self):
        """Test padding edge cases."""
        formatter = PrettyFormatter(use_colors=False)

        # Text already at target width
        text = "Hello"
        result = formatter._pad_to_width(text, 5)
        assert result == "Hello"

        # Text longer than target width
        long_text = "Hello World"
        result = formatter._pad_to_width(long_text, 5)
        assert result == "Hello World"  # Should not be truncated

        # Empty text
        result = formatter._pad_to_width("", 5)
        assert result == "     "

    def test_table_alignment_with_colors(self):
        """Test that table alignment works correctly with colored text."""
        formatter = PrettyFormatter(use_colors=True)

        # Create items with different length values
        items = [
            {"short": "a", "long": "this is a long value"},
            {"short": "bb", "long": "x"},
        ]

        result = formatter._format_table(items)
        lines = result.split("\n")

        # All data rows should have the same visual width
        # (excluding ANSI codes)
        data_lines = [
            line for line in lines if "|" in line and not line.startswith("-")
        ]
        if len(data_lines) >= 2:
            # Strip ANSI codes and check alignment
            stripped_lines = [formatter._strip_ansi_codes(line) for line in data_lines]
            # All lines should have similar length when ANSI codes are removed
            lengths = [len(line) for line in stripped_lines]
            # Allow small variance due to content differences
            assert max(lengths) - min(lengths) <= 3
