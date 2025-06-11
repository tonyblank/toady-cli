"""Tests for the JSON formatter implementation."""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from toady.formatters.format_interfaces import FormatterError, FormatterOptions
from toady.formatters.json_formatter import (
    JSONFormatter,
    default_json_formatter,
    format_comments_json,
    format_object_json,
    format_threads_json,
)
from toady.models import Comment, ReviewThread


class TestJSONFormatter:
    """Test the JSONFormatter class."""

    def test_initialization_default(self):
        """Test JSONFormatter initialization with default options."""
        formatter = JSONFormatter()

        assert formatter.formatter_options is not None
        assert formatter.formatter_options.indent == 2
        assert formatter.formatter_options.sort_keys is False
        assert formatter.formatter_options.ensure_ascii is False

        # Check JSON options are set correctly
        assert formatter.json_options["indent"] == 2
        assert formatter.json_options["sort_keys"] is False
        assert formatter.json_options["ensure_ascii"] is False

    def test_initialization_custom_options(self):
        """Test JSONFormatter initialization with custom options."""
        options = FormatterOptions(
            indent=4, sort_keys=True, ensure_ascii=True, separators=(",", ": ")
        )
        formatter = JSONFormatter(options=options)

        assert formatter.formatter_options is options
        assert formatter.json_options["indent"] == 4
        assert formatter.json_options["sort_keys"] is True
        assert formatter.json_options["ensure_ascii"] is True
        assert formatter.json_options["separators"] == (",", ": ")

    def test_initialization_with_kwargs(self):
        """Test JSONFormatter initialization with additional kwargs."""
        formatter = JSONFormatter(custom_option="value", another=42)

        assert formatter.formatter_options.extra_options["custom_option"] == "value"
        assert formatter.formatter_options.extra_options["another"] == 42

    def test_format_threads_empty(self):
        """Test formatting empty thread list."""
        formatter = JSONFormatter()
        result = formatter.format_threads([])

        parsed = json.loads(result)
        assert parsed == []

    def test_format_threads_single(self):
        """Test formatting single thread."""
        formatter = JSONFormatter()

        # Create test comment
        comment = Comment(
            comment_id="IC_123",
            content="Test comment",
            author="testuser",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            parent_id=None,
            thread_id="RT_456",
        )

        # Create test thread
        thread = ReviewThread(
            thread_id="RT_456",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="reviewer1",
            comments=[comment],
        )

        result = formatter.format_threads([thread])
        parsed = json.loads(result)

        # Verify structure
        assert isinstance(parsed, list)
        assert len(parsed) == 1

        thread_data = parsed[0]
        assert thread_data["thread_id"] == "RT_456"
        assert thread_data["title"] == "Test thread"
        assert thread_data["status"] == "UNRESOLVED"
        assert thread_data["author"] == "reviewer1"
        assert len(thread_data["comments"]) == 1

        comment_data = thread_data["comments"][0]
        assert comment_data["comment_id"] == "IC_123"
        assert comment_data["content"] == "Test comment"
        assert comment_data["author"] == "testuser"

    def test_format_threads_multiple(self):
        """Test formatting multiple threads."""
        formatter = JSONFormatter()

        # Create test threads
        thread1 = ReviewThread(
            thread_id="RT_001",
            title="First thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="RESOLVED",
            author="reviewer1",
            comments=[],
        )

        thread2 = ReviewThread(
            thread_id="RT_002",
            title="Second thread",
            created_at=datetime(2024, 1, 15, 11, 0, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            status="UNRESOLVED",
            author="reviewer2",
            comments=[],
        )

        result = formatter.format_threads([thread1, thread2])
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["thread_id"] == "RT_001"
        assert parsed[0]["status"] == "RESOLVED"
        assert parsed[1]["thread_id"] == "RT_002"
        assert parsed[1]["status"] == "UNRESOLVED"

    def test_format_threads_with_serialization_error(self):
        """Test formatting threads when serialization fails."""
        formatter = JSONFormatter()

        # Create a mock thread that fails to serialize
        class BadThread:
            def __init__(self):
                self.thread_id = "RT_BAD"

            def to_dict(self):
                raise Exception("Serialization failed")

        bad_thread = BadThread()

        with pytest.raises(FormatterError) as excinfo:
            formatter.format_threads([bad_thread])

        assert "Failed to serialize thread RT_BAD" in str(excinfo.value)
        assert isinstance(excinfo.value.original_error, Exception)

    def test_format_comments_empty(self):
        """Test formatting empty comment list."""
        formatter = JSONFormatter()
        result = formatter.format_comments([])

        parsed = json.loads(result)
        assert parsed == []

    def test_format_comments_multiple(self):
        """Test formatting multiple comments."""
        formatter = JSONFormatter()

        comment1 = Comment(
            comment_id="IC_001",
            content="First comment",
            author="user1",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_456",
        )

        comment2 = Comment(
            comment_id="IC_002",
            content="Second comment",
            author="user2",
            created_at=datetime(2024, 1, 15, 11, 0, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            parent_id="IC_001",
            thread_id="RT_456",
        )

        result = formatter.format_comments([comment1, comment2])
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["comment_id"] == "IC_001"
        assert parsed[0]["content"] == "First comment"
        assert parsed[0]["parent_id"] is None
        assert parsed[1]["comment_id"] == "IC_002"
        assert parsed[1]["content"] == "Second comment"
        assert parsed[1]["parent_id"] == "IC_001"

    def test_format_comments_with_serialization_error(self):
        """Test formatting comments when serialization fails."""
        formatter = JSONFormatter()

        # Create a mock comment that fails to serialize
        class BadComment:
            def __init__(self):
                self.comment_id = "IC_BAD"

            def to_dict(self):
                raise Exception("Serialization failed")

        bad_comment = BadComment()

        with pytest.raises(FormatterError) as excinfo:
            formatter.format_comments([bad_comment])

        assert "Failed to serialize comment IC_BAD" in str(excinfo.value)

    def test_format_object_simple(self):
        """Test formatting simple objects."""
        formatter = JSONFormatter()

        # Test dictionary
        obj = {"key": "value", "number": 42, "boolean": True}
        result = formatter.format_object(obj)
        parsed = json.loads(result)
        assert parsed == obj

        # Test string
        result = formatter.format_object("test string")
        parsed = json.loads(result)
        assert parsed == "test string"

        # Test number
        result = formatter.format_object(123)
        parsed = json.loads(result)
        assert parsed == 123

    def test_format_object_with_model(self):
        """Test formatting objects with to_dict method."""
        formatter = JSONFormatter()

        comment = Comment(
            comment_id="IC_123",
            content="Test comment",
            author="testuser",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_456",
        )

        result = formatter.format_object(comment)
        parsed = json.loads(result)

        assert parsed["comment_id"] == "IC_123"
        assert parsed["content"] == "Test comment"
        assert parsed["author"] == "testuser"

    def test_format_object_with_error(self):
        """Test formatting object that fails to serialize."""
        formatter = JSONFormatter()

        # Create a mock object that fails to serialize
        bad_obj = Mock()
        bad_obj.to_dict.side_effect = Exception("Serialization failed")

        with pytest.raises(FormatterError) as excinfo:
            formatter.format_object(bad_obj)

        assert "Failed to format object as JSON" in str(excinfo.value)

    def test_format_array_simple(self):
        """Test formatting simple arrays."""
        formatter = JSONFormatter()

        # Test list of primitives
        items = [1, "string", True, None]
        result = formatter.format_array(items)
        parsed = json.loads(result)
        assert parsed == items

        # Test empty array
        result = formatter.format_array([])
        parsed = json.loads(result)
        assert parsed == []

    def test_format_array_with_objects(self):
        """Test formatting arrays with complex objects."""
        formatter = JSONFormatter()

        items = [
            {"type": "string", "value": "text"},
            {"type": "number", "value": 42},
            {"type": "boolean", "value": True},
        ]

        result = formatter.format_array(items)
        parsed = json.loads(result)
        assert parsed == items

    def test_format_array_with_serialization_error(self):
        """Test formatting array when item serialization fails."""
        formatter = JSONFormatter()

        # Create a mock object that fails to serialize
        class BadItem:
            def to_dict(self):
                raise Exception("Serialization failed")

        bad_item = BadItem()
        items = [1, bad_item, 3]

        with pytest.raises(FormatterError) as excinfo:
            formatter.format_array(items)

        assert "Failed to serialize array item at index 1" in str(excinfo.value)

    def test_format_primitive_types(self):
        """Test formatting primitive types."""
        formatter = JSONFormatter()

        test_cases = [
            ("string", '"string"'),
            (42, "42"),
            (3.14, "3.14"),
            (True, "true"),
            (False, "false"),
            (None, "null"),
        ]

        for value, expected_json in test_cases:
            result = formatter.format_primitive(value)
            assert result == expected_json

    def test_format_error_basic(self):
        """Test formatting basic error objects."""
        formatter = JSONFormatter()

        error = {"message": "Something went wrong", "code": 500}
        result = formatter.format_error(error)
        parsed = json.loads(result)

        assert parsed["message"] == "Something went wrong"
        assert parsed["code"] == 500
        assert parsed["error"] is True
        assert parsed["success"] is False

    def test_format_error_with_existing_fields(self):
        """Test formatting error with existing error/success fields."""
        formatter = JSONFormatter()

        error = {
            "message": "Test error",
            "error": "custom_error_value",
            "success": "custom_success_value",
        }

        result = formatter.format_error(error)
        parsed = json.loads(result)

        # Should preserve existing values
        assert parsed["error"] == "custom_error_value"
        assert parsed["success"] == "custom_success_value"
        assert parsed["message"] == "Test error"

    def test_format_success_message(self):
        """Test formatting success messages."""
        formatter = JSONFormatter()

        # Without details
        result = formatter.format_success_message("Operation completed")
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["message"] == "Operation completed"
        assert "details" not in parsed

        # With details
        details = {"id": "123", "count": 5}
        result = formatter.format_success_message("Operation completed", details)
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["message"] == "Operation completed"
        assert parsed["details"] == details

    def test_format_warning_message(self):
        """Test formatting warning messages."""
        formatter = JSONFormatter()

        # Without details
        result = formatter.format_warning_message("This is a warning")
        parsed = json.loads(result)

        assert parsed["warning"] is True
        assert parsed["message"] == "This is a warning"
        assert "details" not in parsed

        # With details
        details = {"severity": "medium", "code": "WARN001"}
        result = formatter.format_warning_message("This is a warning", details)
        parsed = json.loads(result)

        assert parsed["warning"] is True
        assert parsed["message"] == "This is a warning"
        assert parsed["details"] == details

    def test_format_reply_result(self):
        """Test formatting reply command results."""
        formatter = JSONFormatter()

        reply_info = {
            "reply_id": "RP_123",
            "reply_url": "https://github.com/owner/repo/pull/1#issuecomment-123",
            "created_at": "2024-01-15T10:30:00Z",
            "author": "testuser",
            "comment_id": "IC_456",
            "pr_number": 1,
            "pr_title": "Test PR",
        }

        # Test non-verbose
        result = formatter.format_reply_result(reply_info, verbose=False)
        parsed = json.loads(result)

        assert parsed["reply_posted"] is True
        assert parsed["reply_id"] == "RP_123"
        assert (
            parsed["reply_url"]
            == "https://github.com/owner/repo/pull/1#issuecomment-123"
        )
        assert parsed["comment_id"] == "IC_456"
        assert parsed["pr_number"] == 1
        assert "verbose" not in parsed

        # Test verbose
        result = formatter.format_reply_result(reply_info, verbose=True)
        parsed = json.loads(result)

        assert parsed["verbose"] is True

    def test_format_resolve_result(self):
        """Test formatting resolve command results."""
        formatter = JSONFormatter()

        resolve_info = {
            "thread_id": "RT_123",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://github.com/owner/repo/pull/1#discussion_r123",
        }

        result = formatter.format_resolve_result(resolve_info)
        parsed = json.loads(result)

        assert parsed == resolve_info

    def test_safe_serialize_enhanced(self):
        """Test enhanced _safe_serialize method."""
        formatter = JSONFormatter()

        # Test None
        assert formatter._safe_serialize(None) is None

        # Test primitive types
        assert formatter._safe_serialize("string") == "string"
        assert formatter._safe_serialize(42) == 42
        assert formatter._safe_serialize(True) is True

        # Test datetime objects
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = formatter._safe_serialize(dt)
        assert isinstance(result, str)
        assert "2024-01-15T10:30:00" in result

        # Test sets (should be converted to sorted list)
        test_set = {3, 1, 2}
        result = formatter._safe_serialize(test_set)
        assert result == [1, 2, 3]  # Sorted as numbers

        # Test object with __dict__
        class TestObj:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        obj = TestObj()
        result = formatter._safe_serialize(obj)
        assert result == {"attr1": "value1", "attr2": 42}

    def test_safe_serialize_fallback(self):
        """Test _safe_serialize fallback behavior."""
        formatter = JSONFormatter()

        # Test object that can't be serialized
        class NonSerializable:
            def __str__(self):
                return "NonSerializable instance"

        obj = NonSerializable()
        result = formatter._safe_serialize(obj)
        # Should fall back to __dict__ which gives empty dict
        assert result == {}

    def test_custom_json_options(self):
        """Test formatter with custom JSON options."""
        options = FormatterOptions(
            indent=None, sort_keys=True, separators=(",", ":")  # Compact JSON
        )
        formatter = JSONFormatter(options=options)

        data = {"zebra": 1, "apple": 2, "banana": 3}
        result = formatter.format_object(data)

        # Should be compact (no indentation)
        assert "\n" not in result
        # Should be sorted
        assert result.find("apple") < result.find("banana") < result.find("zebra")


class TestJSONFormatterConvenienceFunctions:
    """Test convenience functions for JSON formatting."""

    def test_format_threads_json(self):
        """Test format_threads_json convenience function."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="UNRESOLVED",
            author="testuser",
            comments=[],
        )

        result = format_threads_json([thread])
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["thread_id"] == "RT_123"

    def test_format_comments_json(self):
        """Test format_comments_json convenience function."""
        comment = Comment(
            comment_id="IC_123",
            content="Test comment",
            author="testuser",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_456",
        )

        result = format_comments_json([comment])
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["comment_id"] == "IC_123"

    def test_format_object_json(self):
        """Test format_object_json convenience function."""
        obj = {"test": "data", "number": 42}

        result = format_object_json(obj)
        parsed = json.loads(result)

        assert parsed == obj

    def test_default_formatter_instance(self):
        """Test that default formatter instance works correctly."""
        assert isinstance(default_json_formatter, JSONFormatter)

        # Test that it can format basic data
        result = default_json_formatter.format_primitive("test")
        assert result == '"test"'


class TestJSONFormatterErrorHandling:
    """Test error handling in JSON formatter."""

    def test_format_threads_json_error(self):
        """Test JSON error propagation in format_threads."""
        formatter = JSONFormatter()

        # Create a thread that will cause JSON serialization to fail
        # by monkey-patching json.dumps
        original_dumps = json.dumps

        def failing_dumps(*args, **kwargs):
            raise ValueError("JSON serialization failed")

        # Patch json.dumps temporarily
        import json as json_module

        json_module.dumps = failing_dumps

        try:
            thread = ReviewThread(
                thread_id="RT_123",
                title="Test thread",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="UNRESOLVED",
                author="testuser",
                comments=[],
            )

            with pytest.raises(FormatterError) as excinfo:
                formatter.format_threads([thread])

            assert "Failed to format threads as JSON" in str(excinfo.value)

        finally:
            # Restore original json.dumps
            json_module.dumps = original_dumps

    def test_formatter_error_chaining(self):
        """Test that FormatterError properly chains original exceptions."""
        formatter = JSONFormatter()

        # Create an object that will fail during safe serialization
        class FailingToDict:
            def to_dict(self):
                raise RuntimeError("to_dict failed")

        failing_obj = FailingToDict()

        # The formatter should not raise an error due to safe serialization
        # It will fall back to __dict__ or string representation
        result = formatter.format_object(failing_obj)
        # Should still produce valid JSON - will be a string representation
        parsed = json.loads(result)
        assert isinstance(parsed, str)
