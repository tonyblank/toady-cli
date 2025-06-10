"""Tests for command utilities."""

from unittest.mock import Mock, patch

import click
import pytest

from toady.command_utils import (
    handle_command_errors,
    validate_limit,
    validate_pr_number,
)
from toady.exceptions import ToadyError, ValidationError


class TestValidatePrNumber:
    """Test PR number validation."""

    def test_valid_pr_numbers(self):
        """Test validation passes for valid PR numbers."""
        # Should not raise any exceptions
        validate_pr_number(1)
        validate_pr_number(123)
        validate_pr_number(999999)

    def test_zero_pr_number(self):
        """Test that zero PR number raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_pr_number(0)

        assert "PR number must be positive" in str(exc_info.value)
        assert exc_info.value.param_hint == "--pr"

    def test_negative_pr_number(self):
        """Test that negative PR number raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_pr_number(-1)

        assert "PR number must be positive" in str(exc_info.value)
        assert exc_info.value.param_hint == "--pr"

    def test_oversized_pr_number(self):
        """Test that oversized PR number raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_pr_number(1000000)

        assert "PR number appears unreasonably large" in str(exc_info.value)
        assert "999999" in str(exc_info.value)
        assert exc_info.value.param_hint == "--pr"


class TestValidateLimit:
    """Test limit validation."""

    def test_valid_limits(self):
        """Test validation passes for valid limits."""
        # Should not raise any exceptions
        validate_limit(1)
        validate_limit(50)
        validate_limit(1000)

    def test_valid_limits_with_custom_max(self):
        """Test validation with custom maximum."""
        validate_limit(500, max_limit=500)
        validate_limit(1, max_limit=100)

    def test_zero_limit(self):
        """Test that zero limit raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_limit(0)

        assert "Limit must be positive" in str(exc_info.value)
        assert exc_info.value.param_hint == "--limit"

    def test_negative_limit(self):
        """Test that negative limit raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_limit(-1)

        assert "Limit must be positive" in str(exc_info.value)
        assert exc_info.value.param_hint == "--limit"

    def test_oversized_limit_default_max(self):
        """Test that oversized limit raises error with default max."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_limit(1001)

        assert "Limit cannot exceed 1000" in str(exc_info.value)
        assert exc_info.value.param_hint == "--limit"

    def test_oversized_limit_custom_max(self):
        """Test that oversized limit raises error with custom max."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_limit(501, max_limit=500)

        assert "Limit cannot exceed 500" in str(exc_info.value)
        assert exc_info.value.param_hint == "--limit"


class TestHandleCommandErrors:
    """Test command error handling decorator."""

    def test_successful_function_execution(self):
        """Test that decorator doesn't interfere with successful execution."""

        @handle_command_errors
        def test_function(value):
            return value * 2

        result = test_function(5)
        assert result == 10

    @patch("toady.command_utils.handle_error")
    @patch("click.get_current_context")
    def test_toady_error_handling(self, mock_get_context, mock_handle_error):
        """Test that ToadyError is handled by the error handler."""
        # Mock the click context
        mock_ctx = Mock()
        mock_ctx.obj = {"debug": False}
        mock_get_context.return_value = mock_ctx

        @handle_command_errors
        def test_function():
            raise ValidationError("Test validation error")

        test_function()

        # Verify that handle_error was called with the exception and debug flag
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args[0]
        assert isinstance(call_args[0], ValidationError)
        assert mock_handle_error.call_args[1]["show_traceback"] is False

    @patch("toady.command_utils.handle_error")
    @patch("click.get_current_context")
    def test_toady_error_handling_with_debug(self, mock_get_context, mock_handle_error):
        """Test that ToadyError is handled with debug flag."""
        # Mock the click context with debug enabled
        mock_ctx = Mock()
        mock_ctx.obj = {"debug": True}
        mock_get_context.return_value = mock_ctx

        @handle_command_errors
        def test_function():
            raise ToadyError("Test error")

        test_function()

        # Verify that handle_error was called with debug enabled
        mock_handle_error.assert_called_once()
        assert mock_handle_error.call_args[1]["show_traceback"] is True

    @patch("click.get_current_context")
    def test_toady_error_handling_no_context(self, mock_get_context):
        """Test error handling when no context is available."""
        # Mock get_current_context to return None
        mock_get_context.return_value = None

        @handle_command_errors
        def test_function():
            raise ValidationError("Test validation error")

        # Should not raise an exception - error should be handled
        with patch("toady.command_utils.handle_error") as mock_handle_error:
            test_function()
            mock_handle_error.assert_called_once()
            assert mock_handle_error.call_args[1]["show_traceback"] is False

    @patch("click.get_current_context")
    def test_toady_error_handling_invalid_context(self, mock_get_context):
        """Test error handling when context object is invalid."""
        # Mock context with invalid obj
        mock_ctx = Mock()
        mock_ctx.obj = None
        mock_get_context.return_value = mock_ctx

        @handle_command_errors
        def test_function():
            raise ValidationError("Test validation error")

        with patch("toady.command_utils.handle_error") as mock_handle_error:
            test_function()
            mock_handle_error.assert_called_once()
            assert mock_handle_error.call_args[1]["show_traceback"] is False

    def test_non_toady_error_propagation(self):
        """Test that non-ToadyError exceptions are propagated."""

        @handle_command_errors
        def test_function():
            raise ValueError("This should propagate")

        with pytest.raises(ValueError) as exc_info:
            test_function()

        assert "This should propagate" in str(exc_info.value)

    def test_function_with_args_and_kwargs(self):
        """Test that decorator preserves function arguments."""

        @handle_command_errors
        def test_function(a, b, c=None, d=None):
            return (a, b, c, d)

        result = test_function(1, 2, c=3, d=4)
        assert result == (1, 2, 3, 4)

    def test_function_metadata_preservation(self):
        """Test that decorator preserves function metadata."""

        @handle_command_errors
        def test_function():
            """Test function docstring."""
            pass

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."

    @patch("toady.command_utils.handle_error")
    @patch("click.get_current_context")
    def test_multiple_error_types(self, mock_get_context, mock_handle_error):
        """Test handling of different ToadyError subclasses."""
        mock_ctx = Mock()
        mock_ctx.obj = {"debug": False}
        mock_get_context.return_value = mock_ctx

        # Test ValidationError
        @handle_command_errors
        def validation_error_function():
            raise ValidationError("Validation failed")

        validation_error_function()
        assert mock_handle_error.call_count == 1

        # Test generic ToadyError
        @handle_command_errors
        def generic_error_function():
            raise ToadyError("Generic error")

        generic_error_function()
        assert mock_handle_error.call_count == 2

    @patch("click.get_current_context", side_effect=RuntimeError("Context error"))
    def test_context_exception_handling(self, mock_get_context):
        """Test that context retrieval exceptions don't break error handling."""

        @handle_command_errors
        def test_function():
            raise ValidationError("Test error")

        with patch("toady.command_utils.handle_error") as mock_handle_error:
            test_function()
            # Should still call handle_error with default debug=False
            mock_handle_error.assert_called_once()
            assert mock_handle_error.call_args[1]["show_traceback"] is False
