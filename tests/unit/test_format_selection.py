"""Tests for format selection utilities."""

import os
from unittest.mock import MagicMock, patch

import pytest

from toady.formatters.format_selection import (
    FormatSelectionError,
    _ensure_formatters_registered,
    create_format_option,
    create_formatter,
    create_legacy_pretty_option,
    format_error_message,
    format_object_output,
    format_success_message,
    format_threads_output,
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
        with patch(
            "toady.formatters.format_selection.get_default_format", return_value="json"
        ):
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


class TestEnsureFormattersRegistered:
    """Test formatter registration functionality."""

    @patch("toady.formatters.format_selection.FormatterFactory.list_formatters")
    def test_ensure_formatters_json_not_registered(self, mock_list_formatters):
        """Test JSON formatter registration when not present."""
        mock_list_formatters.return_value = []

        with patch(
            "toady.formatters.format_selection.FormatterFactory.register"
        ) as mock_register:
            _ensure_formatters_registered()

            # Should try to register JSON formatter
            mock_register.assert_called()

    @patch("toady.formatters.format_selection.FormatterFactory.list_formatters")
    @patch("toady.formatters.format_selection.FormatterFactory.register")
    def test_ensure_formatters_json_import_error(
        self, mock_register, mock_list_formatters
    ):
        """Test fallback JSON formatter registration on import error."""
        mock_list_formatters.return_value = []

        # Simulate the specific import failing by manipulating sys.modules
        import sys

        original_modules = sys.modules.copy()

        # Remove the json_formatter module if it exists
        if "toady.formatters.json_formatter" in sys.modules:
            del sys.modules["toady.formatters.json_formatter"]

        # Mock an import error when trying to import JSONFormatter
        def mock_import(name, *args, **kwargs):
            if "json_formatter" in name:
                raise ImportError("Cannot import JSONFormatter")
            return original_import(name, *args, **kwargs)

        original_import = __import__
        with patch("builtins.__import__", side_effect=mock_import):
            _ensure_formatters_registered()

            # Should register simple JSON formatter as fallback
            assert mock_register.call_count >= 1

        # Restore original modules
        sys.modules.update(original_modules)

    @patch("toady.formatters.format_selection.FormatterFactory.list_formatters")
    def test_ensure_formatters_pretty_not_registered(self, mock_list_formatters):
        """Test pretty formatter registration when not present."""
        mock_list_formatters.return_value = ["json"]  # JSON present, pretty not

        with patch(
            "toady.formatters.format_selection.FormatterFactory.register"
        ) as mock_register:
            _ensure_formatters_registered()

            # Should attempt to import pretty formatter
            mock_register.assert_called()

    @patch("toady.formatters.format_selection.FormatterFactory.list_formatters")
    def test_ensure_formatters_pretty_import_error(self, mock_list_formatters):
        """Test handling of pretty formatter import error."""
        mock_list_formatters.return_value = ["json"]  # JSON present, pretty not

        with patch("toady.formatters.format_selection.FormatterFactory.register"):
            # Mock import error for PrettyFormatter
            with patch("builtins.__import__", side_effect=ImportError):
                _ensure_formatters_registered()

                # Should not raise error, just continue


class TestFormatOutputFunctions:
    """Test format output utility functions."""

    def test_format_threads_output_json(self):
        """Test formatting threads output as JSON."""
        threads = [MagicMock()]
        threads[0].to_dict.return_value = {"id": "1", "resolved": False}

        with patch(
            "toady.formatters.format_selection.format_fetch_output"
        ) as mock_format:
            format_threads_output(threads, "json")
            mock_format.assert_called_once_with(threads=threads, pretty=False)

    def test_format_threads_output_pretty(self):
        """Test formatting threads output as pretty."""
        threads = [MagicMock()]
        threads[0].to_dict.return_value = {"id": "1", "resolved": False}

        with patch(
            "toady.formatters.format_selection.format_fetch_output"
        ) as mock_format:
            format_threads_output(threads, "pretty")
            mock_format.assert_called_once_with(threads=threads, pretty=True)

    def test_format_threads_output_other_format(self):
        """Test formatting threads output with other format."""
        threads = [MagicMock()]
        mock_formatter = MagicMock()
        mock_formatter.format_threads.return_value = "formatted output"

        with patch(
            "toady.formatters.format_selection.create_formatter",
            return_value=mock_formatter,
        ) as mock_create:
            with patch("click.echo") as mock_echo:
                format_threads_output(threads, "custom")

                mock_create.assert_called_once_with("custom")
                mock_formatter.format_threads.assert_called_once_with(threads)
                mock_echo.assert_called_once_with("formatted output")

    def test_format_object_output_json(self):
        """Test formatting object output as JSON."""
        obj = {"test": "data"}

        with patch("click.echo") as mock_echo:
            format_object_output(obj, "json")

            mock_echo.assert_called_once()
            # Verify JSON format in output
            call_args = mock_echo.call_args[0][0]
            assert '"test"' in call_args
            assert '"data"' in call_args

    def test_format_object_output_pretty(self):
        """Test formatting object output as pretty."""
        obj = {"test": "data"}
        mock_formatter = MagicMock()
        mock_formatter.format_object.return_value = "pretty output"

        with patch(
            "toady.formatters.format_selection.create_formatter",
            return_value=mock_formatter,
        ) as mock_create:
            with patch("click.echo") as mock_echo:
                format_object_output(obj, "pretty")

                mock_create.assert_called_once_with("pretty")
                mock_formatter.format_object.assert_called_once_with(obj)
                mock_echo.assert_called_once_with("pretty output")

    def test_format_object_output_other_format(self):
        """Test formatting object output with other format."""
        obj = {"test": "data"}
        mock_formatter = MagicMock()
        mock_formatter.format_object.return_value = "custom output"

        with patch(
            "toady.formatters.format_selection.create_formatter",
            return_value=mock_formatter,
        ) as mock_create:
            with patch("click.echo") as mock_echo:
                format_object_output(obj, "custom")

                mock_create.assert_called_once_with("custom")
                mock_formatter.format_object.assert_called_once_with(obj)
                mock_echo.assert_called_once_with("custom output")

    def test_format_success_message_json(self):
        """Test formatting success message as JSON."""
        message = "Operation successful"
        details = {"operation": "test"}

        with patch("click.echo") as mock_echo:
            format_success_message(message, "json", details)

            mock_echo.assert_called_once()
            call_args = mock_echo.call_args[0][0]
            assert '"success": true' in call_args
            assert '"message": "Operation successful"' in call_args
            assert '"details"' in call_args

    def test_format_success_message_json_no_details(self):
        """Test formatting success message as JSON without details."""
        message = "Operation successful"

        with patch("click.echo") as mock_echo:
            format_success_message(message, "json")

            mock_echo.assert_called_once()
            call_args = mock_echo.call_args[0][0]
            assert '"success": true' in call_args
            assert '"message": "Operation successful"' in call_args
            assert '"details"' not in call_args

    def test_format_success_message_other_format(self):
        """Test formatting success message with other format."""
        message = "Operation successful"
        details = {"operation": "test"}
        mock_formatter = MagicMock()
        mock_formatter.format_success_message.return_value = "success output"

        with patch(
            "toady.formatters.format_selection.create_formatter",
            return_value=mock_formatter,
        ) as mock_create:
            with patch("click.echo") as mock_echo:
                format_success_message(message, "custom", details)

                mock_create.assert_called_once_with("custom")
                mock_formatter.format_success_message.assert_called_once_with(
                    message, details
                )
                mock_echo.assert_called_once_with("success output")

    def test_format_error_message_json(self):
        """Test formatting error message as JSON."""
        error = {"error": "Something went wrong", "code": 500}

        with patch("click.echo") as mock_echo:
            format_error_message(error, "json")

            mock_echo.assert_called_once()
            call_args = mock_echo.call_args
            # Should be called with err=True
            assert call_args[1]["err"] is True
            output = call_args[0][0]
            assert '"error": "Something went wrong"' in output

    def test_format_error_message_other_format(self):
        """Test formatting error message with other format."""
        error = {"error": "Something went wrong", "code": 500}
        mock_formatter = MagicMock()
        mock_formatter.format_error.return_value = "error output"

        with patch(
            "toady.formatters.format_selection.create_formatter",
            return_value=mock_formatter,
        ) as mock_create:
            with patch("click.echo") as mock_echo:
                format_error_message(error, "custom")

                mock_create.assert_called_once_with("custom")
                mock_formatter.format_error.assert_called_once_with(error)
                mock_echo.assert_called_once_with("error output", err=True)


class TestClickOptions:
    """Test Click option creation utilities."""

    def test_create_format_option_basic(self):
        """Test creating a basic format option."""
        option_decorator = create_format_option()

        # Should return a callable decorator
        assert callable(option_decorator)

    def test_create_format_option_with_kwargs(self):
        """Test creating format option with additional kwargs."""
        option_decorator = create_format_option(default="json", required=False)

        # Should return a callable decorator
        assert callable(option_decorator)

    def test_create_legacy_pretty_option_basic(self):
        """Test creating a basic legacy pretty option."""
        option_decorator = create_legacy_pretty_option()

        # Should return a callable decorator
        assert callable(option_decorator)

    def test_create_legacy_pretty_option_with_kwargs(self):
        """Test creating legacy pretty option with additional kwargs."""
        option_decorator = create_legacy_pretty_option(hidden=True)

        # Should return a callable decorator
        assert callable(option_decorator)
