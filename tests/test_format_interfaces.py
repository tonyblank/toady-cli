"""Tests for the formatter interfaces and base classes."""

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest

from toady.format_interfaces import (
    BaseFormatter,
    FormatterError,
    FormatterFactory,
    FormatterOptions,
    IFormatter,
)
from toady.models import Comment, ReviewThread


class MockFormatter(BaseFormatter):
    """Mock formatter for testing the interface."""

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self.format_calls: List[str] = []

    def format_threads(self, threads: List[ReviewThread]) -> str:
        self.format_calls.append('format_threads')
        return f"MockFormatter: {len(threads)} threads"

    def format_object(self, obj: Any) -> str:
        self.format_calls.append('format_object')
        return f"MockFormatter: object {type(obj).__name__}"

    def format_array(self, items: List[Any]) -> str:
        self.format_calls.append('format_array')
        return f"MockFormatter: array of {len(items)} items"

    def format_primitive(self, value: Any) -> str:
        self.format_calls.append('format_primitive')
        return f"MockFormatter: primitive {value}"

    def format_error(self, error: Dict[str, Any]) -> str:
        self.format_calls.append('format_error')
        return f"MockFormatter: error {error.get('message', 'unknown')}"


class TestIFormatter:
    """Test the IFormatter interface."""

    def test_interface_is_abstract(self):
        """Test that IFormatter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IFormatter()

    def test_interface_defines_required_methods(self):
        """Test that IFormatter defines all required abstract methods."""
        required_methods = [
            'format_threads', 'format_comments', 'format_object',
            'format_array', 'format_primitive', 'format_error'
        ]
        
        for method_name in required_methods:
            assert hasattr(IFormatter, method_name)
            method = getattr(IFormatter, method_name)
            assert hasattr(method, '__isabstractmethod__')
            assert method.__isabstractmethod__ is True

    def test_default_success_message_implementation(self):
        """Test that IFormatter provides default success message implementation."""
        formatter = MockFormatter()
        
        # Test success message without details
        result = formatter.format_success_message("Operation completed")
        # MockFormatter returns "MockFormatter: object dict" for any object
        assert "MockFormatter: object dict" in result
        # Should call format_object
        assert 'format_object' in formatter.format_calls
        
        # Test success message with details
        details = {"id": "123", "count": 5}
        result = formatter.format_success_message("Operation completed", details)
        # MockFormatter returns "MockFormatter: object dict" for any object
        assert "MockFormatter: object dict" in result
        # Should call format_object twice now
        assert formatter.format_calls.count('format_object') == 2

    def test_default_warning_message_implementation(self):
        """Test that IFormatter provides default warning message implementation."""
        formatter = MockFormatter()
        
        # Test warning message without details
        result = formatter.format_warning_message("This is a warning")
        # MockFormatter returns "MockFormatter: object dict" for any object
        assert "MockFormatter: object dict" in result
        # Should call format_object
        assert 'format_object' in formatter.format_calls
        
        # Test warning message with details
        details = {"code": "WARN001", "severity": "medium"}
        result = formatter.format_warning_message("This is a warning", details)
        # MockFormatter returns "MockFormatter: object dict" for any object
        assert "MockFormatter: object dict" in result
        # Should call format_object twice now
        assert formatter.format_calls.count('format_object') == 2


class TestBaseFormatter:
    """Test the BaseFormatter base class."""

    def test_initialization(self):
        """Test BaseFormatter initialization."""
        options = {"indent": 4, "color": True}
        formatter = MockFormatter(**options)
        
        assert formatter.options == options
        assert formatter.format_calls == []

    def test_safe_serialize_with_dict_method(self):
        """Test _safe_serialize with objects that have to_dict method."""
        formatter = MockFormatter()
        
        # Create a mock object with to_dict method
        obj = Mock()
        obj.to_dict.return_value = {"test": "data"}
        
        result = formatter._safe_serialize(obj)
        assert result == {"test": "data"}
        obj.to_dict.assert_called_once()

    def test_safe_serialize_with_list(self):
        """Test _safe_serialize with list objects."""
        formatter = MockFormatter()
        
        # Test list with mixed types
        data = [1, "string", {"key": "value"}]
        result = formatter._safe_serialize(data)
        
        assert result == [1, "string", {"key": "value"}]

    def test_safe_serialize_with_dict(self):
        """Test _safe_serialize with dictionary objects."""
        formatter = MockFormatter()
        
        data = {"key1": "value1", "key2": 42, "key3": None}
        result = formatter._safe_serialize(data)
        
        assert result == data

    def test_safe_serialize_with_primitive_types(self):
        """Test _safe_serialize with primitive types."""
        formatter = MockFormatter()
        
        # Test various primitive types
        test_cases = [
            ("string", "string"),
            (42, 42),
            (3.14, 3.14),
            (True, True),
            (False, False),
            (None, None),
        ]
        
        for input_val, expected in test_cases:
            result = formatter._safe_serialize(input_val)
            assert result == expected

    def test_safe_serialize_with_non_serializable_object(self):
        """Test _safe_serialize with non-serializable objects."""
        formatter = MockFormatter()
        
        # Create an object that's not JSON serializable
        class NonSerializable:
            def __init__(self):
                self.data = set([1, 2, 3])  # sets are not JSON serializable
        
        obj = NonSerializable()
        result = formatter._safe_serialize(obj)
        
        # BaseFormatter should try __dict__ then fall back to string
        assert isinstance(result, (dict, str))

    def test_handle_empty_data(self):
        """Test _handle_empty_data method."""
        formatter = MockFormatter()
        
        # Test various empty cases
        assert formatter._handle_empty_data([]) == "No data available."
        assert formatter._handle_empty_data({}) == "No data available."
        assert formatter._handle_empty_data(()) == "No data available."
        assert formatter._handle_empty_data(None) == "No data available."
        
        # Test custom empty message
        assert formatter._handle_empty_data([], "Custom empty message") == "Custom empty message"
        
        # Test non-empty data
        assert formatter._handle_empty_data([1, 2, 3]) is None
        assert formatter._handle_empty_data({"key": "value"}) is None

    def test_default_comments_formatting(self):
        """Test default implementation of format_comments."""
        formatter = MockFormatter()
        
        # Create test comments
        comment1 = Comment(
            comment_id="IC_123",
            content="Test comment 1",
            author="user1",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_456",
        )
        
        comment2 = Comment(
            comment_id="IC_124",
            content="Test comment 2",
            author="user2",
            created_at=datetime(2024, 1, 15, 11, 0, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            parent_id="IC_123",
            thread_id="RT_456",
        )
        
        comments = [comment1, comment2]
        result = formatter.format_comments(comments)
        
        # Should call format_array
        assert 'format_array' in formatter.format_calls
        assert "array of 2 items" in result


class TestFormatterOptions:
    """Test the FormatterOptions class."""

    def test_default_initialization(self):
        """Test FormatterOptions with default values."""
        options = FormatterOptions()
        
        assert options.indent == 2
        assert options.sort_keys is False
        assert options.ensure_ascii is False
        assert options.separators is None
        assert options.extra_options == {}

    def test_custom_initialization(self):
        """Test FormatterOptions with custom values."""
        options = FormatterOptions(
            indent=4,
            sort_keys=True,
            ensure_ascii=True,
            separators=(',', ': '),
            custom_option="value"
        )
        
        assert options.indent == 4
        assert options.sort_keys is True
        assert options.ensure_ascii is True
        assert options.separators == (',', ': ')
        assert options.extra_options == {"custom_option": "value"}

    def test_to_dict(self):
        """Test FormatterOptions to_dict method."""
        options = FormatterOptions(
            indent=4,
            sort_keys=True,
            custom_option="value",
            another_option=42
        )
        
        result = options.to_dict()
        expected = {
            'indent': 4,
            'sort_keys': True,
            'ensure_ascii': False,
            'separators': None,
            'custom_option': 'value',
            'another_option': 42
        }
        
        assert result == expected


class TestFormatterError:
    """Test the FormatterError exception class."""

    def test_basic_error(self):
        """Test basic FormatterError creation."""
        error = FormatterError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.original_error is None

    def test_error_with_original_exception(self):
        """Test FormatterError with original exception."""
        original = ValueError("Original error")
        error = FormatterError("Formatter error", original_error=original)
        
        assert str(error) == "Formatter error"
        assert error.original_error is original

    def test_error_inheritance(self):
        """Test that FormatterError inherits from Exception."""
        error = FormatterError("Test error")
        assert isinstance(error, Exception)


class TestFormatterFactory:
    """Test the FormatterFactory class."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the factory registry for clean tests
        FormatterFactory._formatters.clear()

    def tearDown(self):
        """Clean up after tests."""
        # Clear the factory registry
        FormatterFactory._formatters.clear()

    def test_register_formatter(self):
        """Test registering a formatter."""
        self.setUp()
        
        FormatterFactory.register('mock', MockFormatter)
        
        assert 'mock' in FormatterFactory._formatters
        assert FormatterFactory._formatters['mock'] is MockFormatter
        
        self.tearDown()

    def test_create_formatter(self):
        """Test creating a formatter instance."""
        self.setUp()
        
        FormatterFactory.register('mock', MockFormatter)
        
        formatter = FormatterFactory.create('mock', test_option="value")
        
        assert isinstance(formatter, MockFormatter)
        assert formatter.options == {"test_option": "value"}
        
        self.tearDown()

    def test_create_unknown_formatter(self):
        """Test creating an unknown formatter raises error."""
        self.setUp()
        
        with pytest.raises(FormatterError) as excinfo:
            FormatterFactory.create('unknown')
        
        assert "Unknown formatter 'unknown'" in str(excinfo.value)
        assert "Available formatters:" in str(excinfo.value)
        
        self.tearDown()

    def test_create_formatter_with_error(self):
        """Test creating a formatter that raises an error during construction."""
        self.setUp()
        
        class FailingFormatter(MockFormatter):
            def __init__(self, **options):
                if options.get('fail'):
                    raise ValueError("Initialization failed")
                super().__init__(**options)
        
        FormatterFactory.register('failing', FailingFormatter)
        
        # Should work without fail option
        formatter = FormatterFactory.create('failing')
        assert isinstance(formatter, FailingFormatter)
        
        # Should raise FormatterError with fail option
        with pytest.raises(FormatterError) as excinfo:
            FormatterFactory.create('failing', fail=True)
        
        assert "Failed to create formatter 'failing'" in str(excinfo.value)
        assert isinstance(excinfo.value.original_error, ValueError)
        
        self.tearDown()

    def test_list_formatters(self):
        """Test listing available formatters."""
        self.setUp()
        
        assert FormatterFactory.list_formatters() == []
        
        FormatterFactory.register('mock1', MockFormatter)
        FormatterFactory.register('mock2', MockFormatter)
        
        formatters = FormatterFactory.list_formatters()
        assert set(formatters) == {'mock1', 'mock2'}
        
        self.tearDown()

    def test_is_registered(self):
        """Test checking if a formatter is registered."""
        self.setUp()
        
        assert FormatterFactory.is_registered('mock') is False
        
        FormatterFactory.register('mock', MockFormatter)
        
        assert FormatterFactory.is_registered('mock') is True
        assert FormatterFactory.is_registered('other') is False
        
        self.tearDown()


class TestFormatterIntegration:
    """Integration tests for the formatter system."""

    def test_complete_workflow(self):
        """Test a complete formatter workflow."""
        # Clear factory
        FormatterFactory._formatters.clear()
        
        # Register formatter
        FormatterFactory.register('test', MockFormatter)
        
        # Create formatter with options
        options = FormatterOptions(indent=4, custom="value")
        formatter = FormatterFactory.create('test', options=options)
        
        # Test various formatting operations
        threads = []  # Empty list for testing
        result = formatter.format_threads(threads)
        assert "0 threads" in result
        
        obj = {"key": "value"}
        result = formatter.format_object(obj)
        assert "object dict" in result
        
        array = [1, 2, 3]
        result = formatter.format_array(array)
        assert "array of 3 items" in result
        
        primitive = "test string"
        result = formatter.format_primitive(primitive)
        assert "primitive test string" in result
        
        error = {"message": "test error", "code": 500}
        result = formatter.format_error(error)
        assert "error test error" in result
        
        # Verify all methods were called
        expected_calls = [
            'format_threads', 'format_object', 'format_array',
            'format_primitive', 'format_error'
        ]
        for call in expected_calls:
            assert call in formatter.format_calls
        
        # Clean up
        FormatterFactory._formatters.clear()

    def test_formatter_chaining(self):
        """Test that formatters can be used in combination."""
        # Clear factory
        FormatterFactory._formatters.clear()
        
        # Register formatter
        FormatterFactory.register('chain', MockFormatter)
        
        formatter = FormatterFactory.create('chain')
        
        # Test success and warning messages
        success = formatter.format_success_message("Success!", {"id": "123"})
        assert "MockFormatter: object dict" in success
        
        warning = formatter.format_warning_message("Warning!", {"level": "high"})
        assert "MockFormatter: object dict" in warning
        
        # Both should have triggered format_object calls
        format_object_calls = [call for call in formatter.format_calls if call == 'format_object']
        assert len(format_object_calls) == 2
        
        # Clean up
        FormatterFactory._formatters.clear()