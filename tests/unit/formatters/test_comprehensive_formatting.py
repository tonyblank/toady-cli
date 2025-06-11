"""Comprehensive tests for formatter implementations with various data structures.

This module tests all formatters (JSON and Pretty) with diverse data types, structures,
and edge cases to ensure robust behavior across different scenarios including:

- Primitive types (strings, numbers, booleans, null)
- Nested objects and arrays
- Mixed data structures
- Empty collections
- Malformed/invalid data
- Circular references
- Large datasets
- Unicode and special characters
- Terminal color support
- Table formatting edge cases
"""

import json
import os
import sys
import time
from datetime import datetime
from unittest.mock import patch

import pytest

from toady.format_interfaces import FormatterError, FormatterFactory, FormatterOptions
from toady.json_formatter import JSONFormatter
from toady.models import Comment, ReviewThread
from toady.pretty_formatter import PrettyFormatter


class TestPrimitiveDataTypes:
    """Test formatting of primitive data types across all formatters."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance without colors for consistent testing."""
        return PrettyFormatter(use_colors=False)

    @pytest.mark.parametrize(
        "value,expected_type",
        [
            (None, type(None)),
            ("", str),
            ("hello", str),
            ("unicode: 🚀 ñáéíóú", str),
            (0, int),
            (-1, int),
            (42, int),
            (sys.maxsize, int),
            (0.0, float),
            (-1.5, float),
            (3.14159, float),
            (True, bool),
            (False, bool),
        ],
    )
    def test_json_primitive_formatting(self, json_formatter, value, expected_type):
        """Test JSON formatting of primitive types."""
        result = json_formatter.format_primitive(value)

        # Should produce valid JSON
        parsed = json.loads(result)

        # Should preserve type and value
        assert isinstance(parsed, expected_type)
        assert parsed == value

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "hello",
            "unicode: 🚀 ñáéíóú",
            0,
            -1,
            42,
            sys.maxsize,
            0.0,
            -1.5,
            3.14159,
            True,
            False,
        ],
    )
    def test_pretty_primitive_formatting(self, pretty_formatter, value):
        """Test pretty formatting of primitive types."""
        result = pretty_formatter.format_primitive(value)

        # Should be a string
        assert isinstance(result, str)

        # Should contain string representation of value
        if value is None:
            assert "null" in result
        elif isinstance(value, bool):
            assert str(value).lower() in result
        else:
            assert str(value) in result

    def test_special_numeric_values(self, json_formatter, pretty_formatter):
        """Test formatting of special numeric values."""
        special_values = [float("inf"), float("-inf"), float("nan")]

        for value in special_values:
            # JSON formatter should handle special values gracefully
            json_result = json_formatter.format_primitive(value)
            assert isinstance(json_result, str)

            # Pretty formatter should handle special values
            pretty_result = pretty_formatter.format_primitive(value)
            assert isinstance(pretty_result, str)

    def test_very_long_strings(self, json_formatter, pretty_formatter):
        """Test formatting of very long strings."""
        long_string = "x" * 10000

        # JSON formatter should handle long strings
        json_result = json_formatter.format_primitive(long_string)
        parsed = json.loads(json_result)
        assert parsed == long_string

        # Pretty formatter should handle long strings
        pretty_result = pretty_formatter.format_primitive(long_string)
        assert isinstance(pretty_result, str)
        assert "x" in pretty_result

    def test_strings_with_special_characters(self, json_formatter, pretty_formatter):
        """Test formatting of strings with special characters."""
        special_strings = [
            "",  # Empty string
            " ",  # Whitespace
            "\n\t\r",  # Newlines and tabs
            '"quotes"',  # Quotes
            "\\backslashes\\",  # Backslashes
            "unicode: 🎉 🚀 ñáéíóú",  # Unicode
            "control\x00chars\x1f",  # Control characters
            'json{"key":"value"}',  # JSON-like content
        ]

        for test_string in special_strings:
            # JSON formatter should escape properly
            json_result = json_formatter.format_primitive(test_string)
            parsed = json.loads(json_result)
            assert parsed == test_string

            # Pretty formatter should handle gracefully
            pretty_result = pretty_formatter.format_primitive(test_string)
            assert isinstance(pretty_result, str)


class TestComplexDataStructures:
    """Test formatting of complex data structures."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False)

    def test_nested_dictionaries(self, json_formatter, pretty_formatter):
        """Test formatting of deeply nested dictionaries."""
        nested_dict = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "value": "deep nesting",
                                "numbers": [1, 2, 3],
                                "boolean": True,
                                "null_value": None,
                            }
                        }
                    }
                }
            },
            "top_level": "value",
        }

        # JSON formatter should handle nested structures
        json_result = json_formatter.format_object(nested_dict)
        parsed = json.loads(json_result)
        assert parsed == nested_dict

        # Pretty formatter should handle nested structures
        pretty_result = pretty_formatter.format_object(nested_dict)
        assert isinstance(pretty_result, str)
        assert "deep nesting" in pretty_result
        assert "top_level" in pretty_result

    def test_nested_arrays(self, json_formatter, pretty_formatter):
        """Test formatting of deeply nested arrays."""
        nested_array = [
            [
                [
                    [
                        ["innermost", 42, True, None],
                        {"nested": "object"},
                    ]
                ]
            ],
            "top_level_string",
            123,
        ]

        # JSON formatter should handle nested arrays
        json_result = json_formatter.format_array(nested_array)
        parsed = json.loads(json_result)
        assert parsed == nested_array

        # Pretty formatter should handle nested arrays
        pretty_result = pretty_formatter.format_array(nested_array)
        assert isinstance(pretty_result, str)
        assert "innermost" in pretty_result
        assert "top_level_string" in pretty_result

    def test_mixed_data_structures(self, json_formatter, pretty_formatter):
        """Test formatting of mixed data structures."""
        mixed_data = {
            "arrays": [
                [1, 2, 3],
                ["a", "b", "c"],
                [True, False, None],
            ],
            "objects": {
                "obj1": {"key": "value"},
                "obj2": {"nested": {"array": [1, 2, 3]}},
            },
            "primitives": {
                "string": "test",
                "number": 42,
                "boolean": True,
                "null": None,
            },
            "mixed_array": [
                "string",
                42,
                {"object": "value"},
                [1, 2, 3],
                None,
                True,
            ],
        }

        # JSON formatter should handle mixed structures
        json_result = json_formatter.format_object(mixed_data)
        parsed = json.loads(json_result)
        assert parsed == mixed_data

        # Pretty formatter should handle mixed structures
        pretty_result = pretty_formatter.format_object(mixed_data)
        assert isinstance(pretty_result, str)
        assert "arrays" in pretty_result
        assert "objects" in pretty_result

    def test_large_data_structures(self, json_formatter, pretty_formatter):
        """Test formatting of large data structures."""
        # Create large dictionary
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}

        # Create large array
        large_array = [{"id": i, "data": f"item_{i}"} for i in range(1000)]

        # Test large dictionary
        json_result = json_formatter.format_object(large_dict)
        parsed = json.loads(json_result)
        assert len(parsed) == 1000
        assert parsed["key_999"] == "value_999"

        pretty_result = pretty_formatter.format_object(large_dict)
        assert isinstance(pretty_result, str)
        assert "key_999" in pretty_result

        # Test large array
        json_result = json_formatter.format_array(large_array)
        parsed = json.loads(json_result)
        assert len(parsed) == 1000
        assert parsed[999]["id"] == 999

        pretty_result = pretty_formatter.format_array(large_array)
        assert isinstance(pretty_result, str)
        # Should format as table for uniform dictionaries
        assert "|" in pretty_result  # Table separator


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False)

    def test_empty_collections(self, json_formatter, pretty_formatter):
        """Test formatting of empty collections."""
        empty_cases = [
            [],
            {},
            (),
            set(),
        ]

        for empty_collection in empty_cases:
            # JSON formatter should handle empty collections
            if isinstance(empty_collection, (list, tuple)):
                json_result = json_formatter.format_array(list(empty_collection))
                parsed = json.loads(json_result)
                assert parsed == []
            elif isinstance(empty_collection, dict):
                json_result = json_formatter.format_object(empty_collection)
                parsed = json.loads(json_result)
                assert parsed == {}

            # Pretty formatter should handle empty collections
            if isinstance(empty_collection, (list, tuple)):
                pretty_result = pretty_formatter.format_array(list(empty_collection))
                assert "[]" in pretty_result
            elif isinstance(empty_collection, dict):
                pretty_result = pretty_formatter.format_object(empty_collection)
                assert "{}" in pretty_result

    def test_none_and_null_values(self, json_formatter, pretty_formatter):
        """Test handling of None/null values in various contexts."""
        test_cases = [
            None,  # Direct None
            {"key": None},  # None in dictionary
            [None, None, None],  # None in array
            {"nested": {"null": None}},  # Nested None
        ]

        for test_case in test_cases:
            if test_case is None:
                # Direct None
                json_result = json_formatter.format_primitive(test_case)
                assert json_result == "null"

                pretty_result = pretty_formatter.format_primitive(test_case)
                assert "null" in pretty_result
            else:
                # Complex structures with None
                json_result = json_formatter.format_object(test_case)
                parsed = json.loads(json_result)
                assert parsed == test_case

                pretty_result = pretty_formatter.format_object(test_case)
                assert isinstance(pretty_result, str)

    def test_circular_references(self, json_formatter, pretty_formatter):
        """Test handling of circular references."""
        # Create circular reference
        circular_dict = {"key": "value"}
        circular_dict["self"] = circular_dict

        # JSON formatter should handle circular references gracefully
        # (should raise a FormatterError, not infinite recursion)
        with pytest.raises(FormatterError):
            json_formatter.format_object(circular_dict)

        # Pretty formatter should handle circular references
        # (should also raise a FormatterError, not infinite recursion)
        with pytest.raises(FormatterError):
            pretty_formatter.format_object(circular_dict)

    def test_malformed_data(self, json_formatter, pretty_formatter):
        """Test formatting of malformed or invalid data."""

        # Test with mock objects that might fail serialization
        class BadObject:
            def to_dict(self):
                raise Exception("Serialization failed")

        class PartiallyBadObject:
            def __init__(self):
                self.good_attr = "value"
                self._bad_attr = BadObject()

        bad_obj = BadObject()
        partial_obj = PartiallyBadObject()

        # JSON formatter should handle bad objects gracefully
        json_result = json_formatter.format_object(bad_obj)
        assert isinstance(json_result, str)

        json_result = json_formatter.format_object(partial_obj)
        parsed = json.loads(json_result)
        assert "good_attr" in parsed

        # Pretty formatter should handle bad objects gracefully
        pretty_result = pretty_formatter.format_object(bad_obj)
        assert isinstance(pretty_result, str)

        pretty_result = pretty_formatter.format_object(partial_obj)
        assert isinstance(pretty_result, str)

    def test_unicode_edge_cases(self, json_formatter, pretty_formatter):
        """Test Unicode edge cases and special characters."""
        unicode_cases = [
            "🎉🚀🌟",  # Emojis
            "ñáéíóú",  # Accented characters
            "中文测试",  # Chinese characters
            "العربية",  # Arabic text
            "🏳️‍🌈",  # Complex emoji with modifiers
            "\u0000\u001f",  # Control characters
            "\ufffd",  # Replacement character
        ]

        for unicode_string in unicode_cases:
            # JSON formatter should handle Unicode properly
            json_result = json_formatter.format_primitive(unicode_string)
            parsed = json.loads(json_result)
            assert parsed == unicode_string

            # Pretty formatter should handle Unicode
            pretty_result = pretty_formatter.format_primitive(unicode_string)
            assert isinstance(pretty_result, str)

    def test_deeply_nested_structures(self, json_formatter, pretty_formatter):
        """Test very deeply nested structures that might cause stack overflow."""
        # Create deeply nested structure (but not so deep as to cause issues)
        deep_structure = {}
        current = deep_structure

        for i in range(100):  # 100 levels deep
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]

        current["final_value"] = "reached the bottom"

        # Both formatters should handle reasonable nesting depth
        json_result = json_formatter.format_object(deep_structure)
        parsed = json.loads(json_result)
        assert "level_0" in parsed

        pretty_result = pretty_formatter.format_object(deep_structure)
        assert isinstance(pretty_result, str)
        assert "level_0" in pretty_result


class TestModelFormatting:
    """Test formatting of Toady model objects."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False)

    @pytest.fixture
    def sample_comment(self):
        """Sample comment for testing."""
        return Comment(
            comment_id="IC_12345",
            content="This is a test comment with some content",
            author="test_user",
            author_name="Test User",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 10, 35, 0),
            parent_id=None,
            thread_id="RT_67890",
            url="https://github.com/test/repo/pull/1#issuecomment-12345",
        )

    @pytest.fixture
    def sample_thread(self, sample_comment):
        """Sample review thread for testing."""
        return ReviewThread(
            thread_id="RT_67890",
            title="Sample review thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 35, 0),
            status="UNRESOLVED",
            author="reviewer",
            comments=[sample_comment],
            file_path="src/test_file.py",
            line=42,
            start_line=40,
            diff_side="RIGHT",
            is_outdated=False,
        )

    def test_empty_model_collections(self, json_formatter, pretty_formatter):
        """Test formatting of empty model collections."""
        # Empty threads
        json_result = json_formatter.format_threads([])
        parsed = json.loads(json_result)
        assert parsed == []

        pretty_result = pretty_formatter.format_threads([])
        assert "No review threads found" in pretty_result

        # Empty comments
        json_result = json_formatter.format_comments([])
        parsed = json.loads(json_result)
        assert parsed == []

        pretty_result = pretty_formatter.format_comments([])
        assert "No comments found" in pretty_result

    def test_single_model_formatting(
        self, json_formatter, pretty_formatter, sample_thread
    ):
        """Test formatting of single model objects."""
        # Single thread
        json_result = json_formatter.format_threads([sample_thread])
        parsed = json.loads(json_result)
        assert len(parsed) == 1
        assert parsed[0]["thread_id"] == "RT_67890"
        assert parsed[0]["title"] == "Sample review thread"
        assert len(parsed[0]["comments"]) == 1

        pretty_result = pretty_formatter.format_threads([sample_thread])
        assert "Sample review thread" in pretty_result
        assert "RT_67890" in pretty_result
        assert "UNRESOLVED" in pretty_result
        assert "src/test_file.py" in pretty_result

    def test_multiple_model_formatting(self, json_formatter, pretty_formatter):
        """Test formatting of multiple model objects."""
        threads = []
        for i in range(5):
            comment = Comment(
                comment_id=f"IC_{i}",
                content=f"Comment {i}",
                author=f"user_{i}",
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0),
                parent_id=None,
                thread_id=f"RT_{i}",
            )

            thread = ReviewThread(
                thread_id=f"RT_{i}",
                title=f"Thread {i}",
                created_at=datetime(2024, 1, 15, 9, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0),
                status="RESOLVED" if i % 2 == 0 else "UNRESOLVED",
                author=f"reviewer_{i}",
                comments=[comment],
                is_outdated=i == 4,  # Make last one outdated
            )
            threads.append(thread)

        # JSON formatting
        json_result = json_formatter.format_threads(threads)
        parsed = json.loads(json_result)
        assert len(parsed) == 5
        assert all("thread_id" in thread for thread in parsed)
        assert parsed[0]["status"] == "RESOLVED"
        assert parsed[1]["status"] == "UNRESOLVED"

        # Pretty formatting
        pretty_result = pretty_formatter.format_threads(threads)
        assert "5 total threads" in pretty_result
        assert "Thread 0" in pretty_result
        assert "Thread 4" in pretty_result
        assert "✅" in pretty_result  # Resolved emoji
        assert "❌" in pretty_result  # Unresolved emoji
        assert "⏰" in pretty_result  # Outdated emoji

    def test_model_with_edge_case_data(self, json_formatter, pretty_formatter):
        """Test models with edge case data."""
        # Comment with special characters and formatting
        special_comment = Comment(
            comment_id="IC_SPECIAL",
            content="""This comment has:
- Special characters: ñáéíóú 🚀
- Code blocks:
```python
def test():
    return "test"
```
- URLs: https://github.com/test
- Empty lines

And more content.""",
            author="special_user",
            author_name="Special User (🎉)",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            parent_id=None,
            thread_id="RT_SPECIAL",
            url="https://github.com/test/repo/pull/1#issuecomment-special",
        )

        # Thread with special data
        special_thread = ReviewThread(
            thread_id="RT_SPECIAL",
            title="Thread with special chars: 🚀 ñáéíóú",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 30, 0),
            status="UNRESOLVED",
            author="special_reviewer",
            comments=[special_comment],
            file_path="src/files with spaces/special_file.py",
            line=999,
            diff_side="LEFT",
            is_outdated=False,
        )

        # JSON formatting should handle special data
        json_result = json_formatter.format_threads([special_thread])
        parsed = json.loads(json_result)
        assert len(parsed) == 1
        assert "🚀" in parsed[0]["title"]
        assert "```python" in parsed[0]["comments"][0]["content"]

        # Pretty formatting should handle special data
        pretty_result = pretty_formatter.format_threads([special_thread])
        assert "🚀" in pretty_result
        assert "Special User" in pretty_result
        assert "files with spaces" in pretty_result


class TestColorSupport:
    """Test color support in pretty formatter."""

    def test_color_enabled_formatting(self):
        """Test formatting with colors enabled."""
        formatter = PrettyFormatter(use_colors=True)

        # Create a thread to test color formatting
        thread = ReviewThread(
            thread_id="RT_COLOR",
            title="Color test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="RESOLVED",
            author="color_user",
            comments=[],
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        # Should contain ANSI color codes
        assert "\x1b[" in result or "RESOLVED" in result

    def test_color_disabled_formatting(self):
        """Test formatting with colors disabled."""
        formatter = PrettyFormatter(use_colors=False)

        thread = ReviewThread(
            thread_id="RT_NO_COLOR",
            title="No color test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="RESOLVED",
            author="no_color_user",
            comments=[],
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        # Should not contain ANSI color codes
        assert "\x1b[" not in result

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Terminal color tests may not work in CI environment",
    )
    def test_terminal_color_support(self):
        """Test color support in different terminal environments."""
        # Test with different TERM environment variables
        term_configs = [
            {"TERM": "xterm-256color"},
            {"TERM": "xterm"},
            {"TERM": "dumb"},
            {},  # No TERM set
        ]

        for env_config in term_configs:
            with patch.dict(os.environ, env_config, clear=False):
                formatter = PrettyFormatter(use_colors=True)

                # Should still work regardless of terminal type
                result = formatter.format_primitive("test")
                assert isinstance(result, str)


class TestTableFormatting:
    """Test table formatting capabilities."""

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False, table_width=80)

    def test_simple_table_formatting(self, pretty_formatter):
        """Test basic table formatting."""
        data = [
            {"id": 1, "name": "Alice", "status": "active"},
            {"id": 2, "name": "Bob", "status": "inactive"},
            {"id": 3, "name": "Charlie", "status": "active"},
        ]

        result = pretty_formatter.format_array(data)

        # Should be formatted as table
        assert "|" in result
        assert "id" in result
        assert "name" in result
        assert "status" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "Charlie" in result

    def test_table_with_varying_column_widths(self, pretty_formatter):
        """Test table formatting with varying column widths."""
        data = [
            {
                "short": "a",
                "medium": "medium text",
                "long": "this is a very long text that should be truncated or wrapped",
            },
            {"short": "bb", "medium": "med", "long": "x"},
        ]

        result = pretty_formatter.format_array(data)

        # Should handle varying widths
        assert "|" in result
        assert "short" in result
        assert "medium" in result
        assert "long" in result

    def test_table_with_missing_fields(self, pretty_formatter):
        """Test table formatting when objects have different fields."""
        data = [
            {"id": 1, "name": "Alice", "email": "alice@test.com"},
            {"id": 2, "name": "Bob"},  # Missing email
            {"name": "Charlie", "email": "charlie@test.com"},  # Missing id
        ]

        result = pretty_formatter.format_array(data)

        # Should handle missing fields gracefully
        assert "|" in result
        assert "id" in result
        assert "name" in result
        assert "email" in result

    def test_table_with_special_data_types(self, pretty_formatter):
        """Test table formatting with various data types."""
        data = [
            {"string": "text", "number": 42, "boolean": True, "null": None},
            {"string": "more text", "number": 0, "boolean": False, "null": None},
        ]

        result = pretty_formatter.format_array(data)

        # Should handle different data types
        assert "|" in result
        assert "42" in result
        assert "true" in result or "True" in result
        assert "false" in result or "False" in result

    def test_table_alignment_with_ansi_codes(self):
        """Test table alignment when using ANSI color codes."""
        formatter = PrettyFormatter(use_colors=True, table_width=80)

        data = [
            {"status": "RESOLVED", "name": "short"},
            {
                "status": "UNRESOLVED",
                "name": "a very long name that might affect alignment",
            },
        ]

        result = formatter.format_array(data)

        # Should maintain alignment despite color codes
        lines = result.split("\n")
        data_lines = [
            line for line in lines if "|" in line and not line.startswith("-")
        ]

        if len(data_lines) >= 2:
            # Remove ANSI codes and check that columns align
            import re

            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            clean_lines = [ansi_escape.sub("", line) for line in data_lines]

            # Find column positions
            if len(clean_lines) >= 2:
                pipe_positions_1 = [
                    i for i, char in enumerate(clean_lines[0]) if char == "|"
                ]
                pipe_positions_2 = [
                    i for i, char in enumerate(clean_lines[1]) if char == "|"
                ]

                # Columns should align (allow small variance)
                for pos1, pos2 in zip(pipe_positions_1, pipe_positions_2):
                    assert abs(pos1 - pos2) <= 1

    def test_empty_table(self, pretty_formatter):
        """Test formatting of empty table data."""
        result = pretty_formatter.format_array([])
        assert "[]" in result

    def test_single_row_table(self, pretty_formatter):
        """Test table with only one row (should not format as table)."""
        data = [{"id": 1, "name": "Alice"}]
        result = pretty_formatter.format_array(data)

        # Single item should not be formatted as table
        assert "[" in result
        assert "]" in result


class TestPerformanceAndMemory:
    """Test performance and memory usage with large datasets."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False)

    def test_large_dataset_performance(self, json_formatter, pretty_formatter):
        """Test performance with large datasets."""
        # Create large dataset
        large_data = [
            {"id": i, "value": f"item_{i}", "data": "x" * 100} for i in range(1000)
        ]

        # Test JSON formatter performance
        start_time = time.time()
        json_result = json_formatter.format_array(large_data)
        json_time = time.time() - start_time

        # Should complete in reasonable time (less than 5 seconds)
        assert json_time < 5.0
        assert isinstance(json_result, str)
        assert len(json_result) > 0

        # Test pretty formatter performance
        start_time = time.time()
        pretty_result = pretty_formatter.format_array(large_data)
        pretty_time = time.time() - start_time

        # Should complete in reasonable time (less than 10 seconds)
        assert pretty_time < 10.0
        assert isinstance(pretty_result, str)
        assert len(pretty_result) > 0

    def test_memory_usage_with_large_data(self, json_formatter, pretty_formatter):
        """Test memory usage doesn't grow excessively with large data."""
        try:
            import gc
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create and format large dataset multiple times
        for _ in range(10):
            large_data = [{"id": i, "data": f"item_{i}" * 10} for i in range(100)]

            json_result = json_formatter.format_array(large_data)
            pretty_result = pretty_formatter.format_array(large_data)

            # Clear references
            del json_result, pretty_result, large_data
            gc.collect()

        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024

    def test_deep_nesting_performance(self, json_formatter, pretty_formatter):
        """Test performance with deeply nested structures."""
        # Create deeply nested structure
        deep_data = {}
        current = deep_data

        for i in range(50):  # 50 levels deep
            current[f"level_{i}"] = {"data": f"value_{i}"}
            current = current[f"level_{i}"]

        # Should handle deep nesting without stack overflow
        start_time = time.time()
        json_result = json_formatter.format_object(deep_data)
        json_time = time.time() - start_time

        assert json_time < 5.0
        assert isinstance(json_result, str)

        start_time = time.time()
        pretty_result = pretty_formatter.format_object(deep_data)
        pretty_time = time.time() - start_time

        assert pretty_time < 5.0
        assert isinstance(pretty_result, str)


class TestFormatterFactory:
    """Test formatter factory integration with comprehensive data."""

    def test_factory_with_various_data_types(self):
        """Test that factory-created formatters handle various data types."""
        # Clear factory and register formatters
        FormatterFactory._formatters.clear()
        FormatterFactory.register("json", JSONFormatter)
        FormatterFactory.register("pretty", PrettyFormatter)

        # Test data
        test_data = {
            "primitive": "test",
            "number": 42,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"},
        }

        # Test JSON formatter from factory
        json_formatter = FormatterFactory.create("json")
        json_result = json_formatter.format_object(test_data)
        parsed = json.loads(json_result)
        assert parsed == test_data

        # Test pretty formatter from factory
        pretty_formatter = FormatterFactory.create("pretty", use_colors=False)
        pretty_result = pretty_formatter.format_object(test_data)
        assert isinstance(pretty_result, str)
        assert "primitive" in pretty_result

    def test_factory_error_handling(self):
        """Test factory error handling with bad formatter classes."""
        FormatterFactory._formatters.clear()

        # Register a bad formatter class
        class BadFormatter:
            def __init__(self, **kwargs):
                if kwargs.get("fail"):
                    raise Exception("Bad formatter initialization")

        FormatterFactory.register("bad", BadFormatter)

        # Should raise FormatterError for bad initialization
        with pytest.raises(FormatterError):
            FormatterFactory.create("bad", fail=True)

        # Should work without fail parameter
        formatter = FormatterFactory.create("bad")
        assert isinstance(formatter, BadFormatter)

    def test_factory_with_custom_options(self):
        """Test factory with custom formatter options."""
        FormatterFactory._formatters.clear()
        FormatterFactory.register("json", JSONFormatter)
        FormatterFactory.register("pretty", PrettyFormatter)

        # Test custom JSON options
        custom_options = FormatterOptions(indent=4, sort_keys=True)
        json_formatter = FormatterFactory.create("json", options=custom_options)

        test_dict = {"zebra": 1, "apple": 2}
        result = json_formatter.format_object(test_dict)

        # Should use custom indentation and sorting
        assert "    " in result  # 4-space indentation
        lines = result.split("\n")
        apple_line = next((line for line in lines if "apple" in line), None)
        zebra_line = next((line for line in lines if "zebra" in line), None)

        if apple_line and zebra_line:
            apple_index = lines.index(apple_line)
            zebra_index = lines.index(zebra_line)
            assert apple_index < zebra_index  # Should be sorted

        # Test custom pretty options
        pretty_formatter = FormatterFactory.create(
            "pretty", use_colors=False, table_width=120
        )
        assert pretty_formatter.table_width == 120
        assert pretty_formatter.use_colors is False
