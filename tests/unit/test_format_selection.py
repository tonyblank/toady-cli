"""Tests for format selection utilities."""

import os
from unittest.mock import patch

import pytest

from toady.formatters.format_selection import (
    FormatSelectionError,
    create_formatter,
    get_default_format,
    resolve_format_from_options,
    validate_format,
)


class TestGetDefaultFormat:
    """Test default format retrieval."""

    def test_default_format_from_env_json(self):
        """Test getting JSON format from environment."""
        with patch.dict(os.environ, {"TOADY_DEFAULT_FORMAT": "json"}):
            assert get_default_format() == "json"

    def test_default_format_from_env_pretty(self):
        """Test getting pretty format from environment."""
        with patch.dict(os.environ, {"TOADY_DEFAULT_FORMAT": "pretty"}):
            assert get_default_format() == "pretty"

    def test_default_format_from_env_uppercase(self):
        """Test environment variable is case insensitive."""
        with patch.dict(os.environ, {"TOADY_DEFAULT_FORMAT": "JSON"}):
            assert get_default_format() == "json"

    def test_default_format_invalid_env(self):
        """Test invalid environment value falls back to default."""
        with patch.dict(os.environ, {"TOADY_DEFAULT_FORMAT": "invalid"}):
            assert get_default_format() == "json"

    def test_default_format_no_env(self):
        """Test default when no environment variable is set."""
        with patch.dict(os.environ, {}, clear=True):
            if "TOADY_DEFAULT_FORMAT" in os.environ:
                del os.environ["TOADY_DEFAULT_FORMAT"]
            assert get_default_format() == "json"


class TestValidateFormat:
    """Test format validation."""

    def test_validate_json_format(self):
        """Test validating JSON format."""
        result = validate_format("json")
        assert result == "json"

    def test_validate_pretty_format(self):
        """Test validating pretty format."""
        result = validate_format("pretty")
        assert result == "pretty"

    def test_validate_invalid_format(self):
        """Test validating invalid format raises error."""
        with pytest.raises(FormatSelectionError) as exc_info:
            validate_format("invalid")

        assert "Format 'invalid' is not available" in str(exc_info.value)
        assert "json" in str(exc_info.value)
        assert "pretty" in str(exc_info.value)


class TestResolveFormatFromOptions:
    """Test format resolution from command options."""

    def test_explicit_format_option_json(self):
        """Test explicit format option takes precedence."""
        result = resolve_format_from_options("json", True)
        assert result == "json"

    def test_explicit_format_option_pretty(self):
        """Test explicit format option takes precedence."""
        result = resolve_format_from_options("pretty", False)
        assert result == "pretty"

    def test_pretty_flag_backward_compatibility(self):
        """Test --pretty flag backward compatibility."""
        result = resolve_format_from_options(None, True)
        assert result == "pretty"

    def test_no_pretty_flag_uses_default(self):
        """Test no pretty flag uses default format."""
        with patch("toady.format_selection.get_default_format", return_value="json"):
            result = resolve_format_from_options(None, False)
            assert result == "json"

    def test_invalid_explicit_format(self):
        """Test invalid explicit format raises error."""
        with pytest.raises(FormatSelectionError):
            resolve_format_from_options("invalid", False)


class TestCreateFormatter:
    """Test formatter creation."""

    def test_create_json_formatter(self):
        """Test creating JSON formatter."""
        formatter = create_formatter("json")
        assert formatter is not None
        # Should have the expected interface methods
        assert hasattr(formatter, "format_threads")
        assert hasattr(formatter, "format_comments")
        assert hasattr(formatter, "format_object")

    def test_create_pretty_formatter(self):
        """Test creating pretty formatter."""
        formatter = create_formatter("pretty")
        assert formatter is not None
        # Should have the expected interface methods
        assert hasattr(formatter, "format_threads")
        assert hasattr(formatter, "format_comments")
        assert hasattr(formatter, "format_object")

    def test_create_formatter_with_options(self):
        """Test creating formatter with options."""
        formatter = create_formatter("json", indent=4, sort_keys=True)
        assert formatter is not None

    def test_create_invalid_formatter(self):
        """Test creating invalid formatter raises error."""
        with pytest.raises(FormatSelectionError) as exc_info:
            create_formatter("invalid")

        assert "Failed to create formatter 'invalid'" in str(exc_info.value)


class TestFormatSelectionError:
    """Test FormatSelectionError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = FormatSelectionError("Test message")
        assert str(error) == "Test message"
        assert error.available_formats == []

    def test_error_with_available_formats(self):
        """Test error with available formats."""
        formats = ["json", "pretty"]
        error = FormatSelectionError("Test message", available_formats=formats)
        assert str(error) == "Test message"
        assert error.available_formats == formats


class TestFormatSelectionIntegration:
    """Integration tests for format selection."""

    def test_end_to_end_json_selection(self):
        """Test complete JSON format selection workflow."""
        # Simulate --format json
        format_name = resolve_format_from_options("json", False)
        formatter = create_formatter(format_name)

        # Test basic functionality
        result = formatter.format_object({"test": "data"})
        assert "test" in result
        assert "data" in result

    def test_end_to_end_pretty_selection(self):
        """Test complete pretty format selection workflow."""
        # Simulate --format pretty
        format_name = resolve_format_from_options("pretty", False)
        formatter = create_formatter(format_name)

        # Test basic functionality
        result = formatter.format_object({"test": "data"})
        assert "test" in result
        assert "data" in result

    def test_backward_compatibility_pretty_flag(self):
        """Test backward compatibility with --pretty flag."""
        # Simulate --pretty flag (no --format option)
        format_name = resolve_format_from_options(None, True)
        assert format_name == "pretty"

        formatter = create_formatter(format_name)
        result = formatter.format_object({"test": "data"})
        assert "test" in result

    def test_environment_variable_integration(self):
        """Test environment variable integration."""
        with patch.dict(os.environ, {"TOADY_DEFAULT_FORMAT": "pretty"}):
            # No explicit options - should use env var
            format_name = resolve_format_from_options(None, False)
            assert format_name == "pretty"

    def test_option_precedence_order(self):
        """Test option precedence: explicit > pretty flag > env > default."""
        with patch.dict(os.environ, {"TOADY_DEFAULT_FORMAT": "pretty"}):
            # Explicit format should override everything
            format_name = resolve_format_from_options("json", True)
            assert format_name == "json"

            # Pretty flag should override env
            format_name = resolve_format_from_options(None, True)
            assert format_name == "pretty"

            # Env should be used when no options given
            format_name = resolve_format_from_options(None, False)
            assert format_name == "pretty"
