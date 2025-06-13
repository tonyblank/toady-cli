"""Tests for the formatters module."""

from datetime import datetime
import json
from unittest.mock import patch

import pytest

from toady.formatters.formatters import (
    JSONFormatter,
    OutputFormatter,
    PrettyFormatter,
    format_fetch_output,
)
from toady.models.models import Comment, ReviewThread


@pytest.mark.formatter
@pytest.mark.unit
class TestJSONFormatter:
    """Test the JSONFormatter class."""

    def test_format_empty_threads(self) -> None:
        """Test formatting empty thread list."""
        result = JSONFormatter.format_threads([])
        expected = "[]"
        assert result == expected

    def test_format_single_thread(self, sample_review_thread) -> None:
        """Test formatting single thread."""

        result = JSONFormatter.format_threads([sample_review_thread])
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["thread_id"] == "RT_kwDOABcD12MAAAABcDE3fg"
        assert parsed[0]["title"] == "Sample review thread for testing"
        assert parsed[0]["status"] == "UNRESOLVED"
        assert parsed[0]["author"] == "reviewer"

    def test_format_multiple_threads(self, thread_factory) -> None:
        """Test formatting multiple threads."""
        thread1 = thread_factory(
            thread_id="RT_1",
            title="First thread",
            status="UNRESOLVED",
            author="user1",
        )

        thread2 = thread_factory(
            thread_id="RT_2",
            title="Second thread",
            status="RESOLVED",
            author="user2",
        )

        result = JSONFormatter.format_threads([thread1, thread2])
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["thread_id"] == "RT_1"
        assert parsed[0]["status"] == "UNRESOLVED"
        assert parsed[1]["thread_id"] == "RT_2"
        assert parsed[1]["status"] == "RESOLVED"

    def test_json_structure_completeness(self) -> None:
        """Test that JSON output includes all expected fields."""
        comment = Comment(
            comment_id="IC_123",
            content="Test comment",
            author="testuser",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            parent_id=None,
            thread_id="RT_456",
        )

        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[comment],
        )

        result = JSONFormatter.format_threads([thread])
        parsed = json.loads(result)
        thread_data = parsed[0]

        # Check all expected fields are present
        expected_fields = [
            "thread_id",
            "title",
            "created_at",
            "updated_at",
            "status",
            "author",
            "comments",
        ]
        for field in expected_fields:
            assert field in thread_data, f"Missing field: {field}"


@pytest.mark.formatter
@pytest.mark.unit
class TestPrettyFormatter:
    """Test the PrettyFormatter class."""

    def test_format_empty_threads(self) -> None:
        """Test formatting empty thread list."""
        result = PrettyFormatter.format_threads([])
        assert result == "No review threads found."

    def test_format_single_unresolved_thread(self) -> None:
        """Test formatting single unresolved thread."""
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test unresolved thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[],
        )

        result = PrettyFormatter.format_threads([thread])

        # Check for expected content
        assert "📋 Review Threads:" in result
        assert "❌ Test unresolved thread" in result
        assert "📝 ID: RT_456" in result
        assert "👤 Author: reviewer1" in result
        assert "💬 Comments: 0" in result
        assert "📊 Summary: 1 total threads" in result
        assert "❌ Unresolved: 1" in result

    def test_format_single_resolved_thread(self) -> None:
        """Test formatting single resolved thread."""
        thread = ReviewThread(
            thread_id="RT_789",
            title="Test resolved thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="RESOLVED",
            author="reviewer2",
            comments=[],
        )

        result = PrettyFormatter.format_threads([thread])

        # Check for resolved-specific content
        assert "✅ Test resolved thread" in result
        assert "📝 ID: RT_789" in result
        assert "👤 Author: reviewer2" in result
        assert "✅ Resolved: 1" in result

    def test_format_multiple_threads_mixed_status(self) -> None:
        """Test formatting multiple threads with mixed status."""
        thread1 = ReviewThread(
            thread_id="RT_1",
            title="Unresolved thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="user1",
            comments=[],
        )

        thread2 = ReviewThread(
            thread_id="RT_2",
            title="Resolved thread",
            created_at=datetime(2024, 1, 15, 11, 0, 0),
            updated_at=datetime(2024, 1, 15, 11, 15, 0),
            status="RESOLVED",
            author="user2",
            comments=[],
        )

        result = PrettyFormatter.format_threads([thread1, thread2])

        # Check for both threads
        assert "❌ Unresolved thread" in result
        assert "✅ Resolved thread" in result
        assert "📊 Summary: 2 total threads" in result
        assert "✅ Resolved: 1" in result
        assert "❌ Unresolved: 1" in result

    def test_format_thread_with_comments(self) -> None:
        """Test formatting thread with multiple comments."""
        comments = [
            Comment(
                comment_id="IC_1",
                content="First comment",
                author="user1",
                created_at=datetime(2024, 1, 15, 10, 30, 0),
                updated_at=datetime(2024, 1, 15, 10, 30, 0),
                parent_id=None,
                thread_id="RT_456",
            ),
            Comment(
                comment_id="IC_2",
                content="Second comment",
                author="user2",
                created_at=datetime(2024, 1, 15, 10, 45, 0),
                updated_at=datetime(2024, 1, 15, 10, 45, 0),
                parent_id="IC_1",
                thread_id="RT_456",
            ),
        ]

        thread = ReviewThread(
            thread_id="RT_456",
            title="Thread with comments",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 45, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=comments,
        )

        result = PrettyFormatter.format_threads([thread])
        assert "💬 Comments: 2" in result

    def test_format_progress_message(self) -> None:
        """Test formatting progress message."""
        result = PrettyFormatter.format_progress_message(123, "unresolved threads", 50)
        expected = "🔍 Fetching unresolved threads for PR #123 (limit: 50)"
        assert result == expected

    def test_format_result_summary(self) -> None:
        """Test formatting result summary."""
        result = PrettyFormatter.format_result_summary(5, "review threads")
        expected = "📝 Found 5 review threads"
        assert result == expected

    def test_datetime_formatting(self) -> None:
        """Test that datetime fields are properly formatted."""
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[],
        )

        result = PrettyFormatter.format_threads([thread])

        # Check datetime formatting
        assert "📅 Created: 2024-01-15 10:00:00" in result
        assert "🔄 Updated: 2024-01-15 10:30:00" in result


@pytest.mark.formatter
@pytest.mark.unit
class TestOutputFormatter:
    """Test the OutputFormatter class."""

    def test_format_threads_json_mode(self) -> None:
        """Test format_threads in JSON mode."""
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[],
        )

        result = OutputFormatter.format_threads([thread], pretty=False)

        # Should be valid JSON
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["thread_id"] == "RT_456"

    def test_format_threads_pretty_mode(self) -> None:
        """Test format_threads in pretty mode."""
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[],
        )

        result = OutputFormatter.format_threads([thread], pretty=True)

        # Should contain pretty format elements
        assert "📋 Review Threads:" in result
        assert "❌ Test thread" in result
        assert "📝 ID: RT_456" in result


@pytest.mark.formatter
@pytest.mark.unit
class TestFormatFetchOutput:
    """Test the format_fetch_output function."""

    @patch("toady.formatters.formatters.click.echo")
    def test_format_fetch_output_json_mode(self, mock_echo) -> None:
        """Test format_fetch_output in JSON mode."""
        threads = []

        format_fetch_output(
            threads=threads,
            pretty=False,
            show_progress=True,
            pr_number=123,
            thread_type="unresolved threads",
            limit=50,
        )

        # Should only call echo once with JSON output (no progress messages)
        assert mock_echo.call_count == 1
        call_args = mock_echo.call_args[0][0]
        assert call_args == "[]"

    @patch("toady.formatters.formatters.click.echo")
    def test_format_fetch_output_pretty_mode_with_progress(self, mock_echo) -> None:
        """Test format_fetch_output in pretty mode with progress."""
        threads = []

        format_fetch_output(
            threads=threads,
            pretty=True,
            show_progress=True,
            pr_number=123,
            thread_type="unresolved threads",
            limit=50,
        )

        # Should call echo 3 times: progress, threads, summary
        assert mock_echo.call_count == 3

        # Check call arguments
        calls = [call[0][0] for call in mock_echo.call_args_list]
        assert "🔍 Fetching unresolved threads for PR #123 (limit: 50)" in calls[0]
        assert "No review threads found." in calls[1]
        assert "📝 Found 0 unresolved threads" in calls[2]

    @patch("toady.formatters.formatters.click.echo")
    def test_format_fetch_output_pretty_mode_no_progress(self, mock_echo) -> None:
        """Test format_fetch_output in pretty mode without progress."""
        threads = []

        format_fetch_output(threads=threads, pretty=True, show_progress=False)

        # Should only call echo once with threads output
        assert mock_echo.call_count == 1
        call_args = mock_echo.call_args[0][0]
        assert call_args == "No review threads found."

    @patch("toady.formatters.formatters.click.echo")
    def test_format_fetch_output_with_threads(self, mock_echo) -> None:
        """Test format_fetch_output with actual threads."""
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[],
        )

        format_fetch_output(
            threads=[thread],
            pretty=True,
            show_progress=True,
            pr_number=123,
            thread_type="unresolved threads",
            limit=50,
        )

        # Should call echo 3 times
        assert mock_echo.call_count == 3

        # Check that thread content is in the output
        calls = [call[0][0] for call in mock_echo.call_args_list]
        assert any("❌ Test thread" in call for call in calls)
        assert "📝 Found 1 unresolved threads" in calls[2]


@pytest.mark.formatter
@pytest.mark.unit
class TestFormatterIntegration:
    """Integration tests for formatter functionality."""

    def test_end_to_end_json_formatting(self) -> None:
        """Test complete JSON formatting workflow."""
        # Create sample data
        comment = Comment(
            comment_id="IC_123",
            content="This needs to be fixed",
            author="reviewer1",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            parent_id=None,
            thread_id="RT_456",
        )

        thread = ReviewThread(
            thread_id="RT_456",
            title="Consider using const instead of let",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[comment],
        )

        # Format as JSON
        result = JSONFormatter.format_threads([thread])

        # Parse and validate
        parsed = json.loads(result)
        assert len(parsed) == 1

        thread_data = parsed[0]
        assert thread_data["thread_id"] == "RT_456"
        assert thread_data["title"] == "Consider using const instead of let"
        assert thread_data["status"] == "UNRESOLVED"
        assert thread_data["author"] == "reviewer1"
        assert len(thread_data["comments"]) == 1

    def test_end_to_end_pretty_formatting(self) -> None:
        """Test complete pretty formatting workflow."""
        # Create sample data with mixed statuses
        threads = [
            ReviewThread(
                thread_id="RT_1",
                title="Use const instead of let",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 30, 0),
                status="UNRESOLVED",
                author="reviewer1",
                comments=[],
            ),
            ReviewThread(
                thread_id="RT_2",
                title="Add error handling",
                created_at=datetime(2024, 1, 15, 11, 0, 0),
                updated_at=datetime(2024, 1, 15, 11, 15, 0),
                status="RESOLVED",
                author="reviewer2",
                comments=[],
            ),
        ]

        # Format as pretty
        result = PrettyFormatter.format_threads(threads)

        # Validate content
        assert "📋 Review Threads:" in result
        assert "❌ Use const instead of let" in result
        assert "✅ Add error handling" in result
        assert "📊 Summary: 2 total threads" in result
        assert "✅ Resolved: 1" in result
        assert "❌ Unresolved: 1" in result

    def test_formatter_consistency(self) -> None:
        """Test that both formatters handle the same data consistently."""
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[],
        )

        # Format with both formatters
        json_result = JSONFormatter.format_threads([thread])
        pretty_result = PrettyFormatter.format_threads([thread])

        # Parse JSON to validate data consistency
        parsed = json.loads(json_result)
        thread_data = parsed[0]

        # Check that pretty output contains the same key information
        assert thread_data["thread_id"] in pretty_result
        assert thread_data["title"] in pretty_result
        assert thread_data["author"] in pretty_result


@pytest.mark.formatter
@pytest.mark.unit
class TestPrettyFormatterFileContext:
    """Test PrettyFormatter file context functionality."""

    def test_wrap_text_empty_string(self) -> None:
        """Test wrap_text with empty string."""
        result = PrettyFormatter._wrap_text("", width=80, indent="  ")
        assert result == ""

    def test_format_file_context_no_file_path(self) -> None:
        """Test file context formatting when no file path is present."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            # No file_path set
        )

        result = PrettyFormatter._format_file_context(thread)
        assert result == ""

    def test_format_file_context_with_file_path_only(self) -> None:
        """Test file context with only file path."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/main.py",
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/main.py" in result

    def test_format_file_context_with_line_info(self) -> None:
        """Test file context with line information."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/main.py",
            line=42,
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/main.py" in result
        assert "📍 Line: 42" in result

    def test_format_file_context_with_line_range(self) -> None:
        """Test file context with line range."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/main.py",
            line=45,
            start_line=42,
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/main.py" in result
        assert "📍 Lines: 42-45" in result

    def test_format_file_context_with_diff_side_left(self) -> None:
        """Test file context with LEFT diff side."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/main.py",
            diff_side="LEFT",
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/main.py" in result
        assert "◀️ Side: LEFT" in result

    def test_format_file_context_with_diff_side_right(self) -> None:
        """Test file context with RIGHT diff side."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/main.py",
            diff_side="RIGHT",
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/main.py" in result
        assert "▶️ Side: RIGHT" in result

    def test_format_file_context_outdated(self) -> None:
        """Test file context with outdated flag."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/main.py",
            is_outdated=True,
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/main.py" in result
        assert "⚠️ Outdated" in result

    def test_format_file_context_all_attributes(self) -> None:
        """Test file context with all attributes present."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
            file_path="src/components/Button.tsx",
            line=67,
            start_line=65,
            diff_side="RIGHT",
            is_outdated=True,
        )

        result = PrettyFormatter._format_file_context(thread)
        assert "📁 File: src/components/Button.tsx" in result
        assert "📍 Lines: 65-67" in result
        assert "▶️ Side: RIGHT" in result
        assert "⚠️ Outdated" in result
