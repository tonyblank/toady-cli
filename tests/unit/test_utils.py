"""Unit tests for utility functions."""

import json
from datetime import datetime
from unittest.mock import patch

import click
import pytest

from toady.exceptions import ValidationError
from toady.utils import MAX_PR_NUMBER, emit_error, parse_datetime


@pytest.mark.unit
class TestConstants:
    """Test module constants."""

    def test_max_pr_number_constant(self):
        """Test that MAX_PR_NUMBER has expected value."""
        assert MAX_PR_NUMBER == 999999
        assert isinstance(MAX_PR_NUMBER, int)


@pytest.mark.unit
class TestParseDatetime:
    """Test the parse_datetime function."""

    def test_valid_datetime_with_microseconds(self):
        """Test parsing datetime with microseconds."""
        date_str = "2024-01-15T10:30:45.123456"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45, 123456)
        assert result == expected

    def test_valid_datetime_without_microseconds(self):
        """Test parsing datetime without microseconds."""
        date_str = "2024-01-15T10:30:45"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45)
        assert result == expected

    def test_datetime_with_z_timezone(self):
        """Test parsing datetime with Z timezone indicator."""
        date_str = "2024-01-15T10:30:45Z"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45)
        assert result == expected

    def test_datetime_with_z_and_microseconds(self):
        """Test parsing datetime with Z timezone and microseconds."""
        date_str = "2024-01-15T10:30:45.123456Z"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45, 123456)
        assert result == expected

    def test_datetime_with_positive_timezone(self):
        """Test parsing datetime with positive timezone offset."""
        date_str = "2024-01-15T10:30:45+05:00"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45)
        assert result == expected

    def test_datetime_with_negative_timezone(self):
        """Test parsing datetime with negative timezone offset."""
        date_str = "2024-01-15T10:30:45-05:00"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45)
        assert result == expected

    def test_datetime_with_microseconds_and_positive_timezone(self):
        """Test parsing datetime with microseconds and positive timezone."""
        date_str = "2024-01-15T10:30:45.123456+02:00"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45, 123456)
        assert result == expected

    def test_datetime_with_microseconds_and_negative_timezone(self):
        """Test parsing datetime with microseconds and negative timezone."""
        date_str = "2024-01-15T10:30:45.987654-08:00"
        result = parse_datetime(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 45, 987654)
        assert result == expected

    def test_invalid_input_type_none(self):
        """Test parsing with None input."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime(None)

        error = exc_info.value
        assert "Date string must be a string" in str(error)
        assert error.field_name == "date_str"

    def test_invalid_input_type_integer(self):
        """Test parsing with integer input."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime(12345)

        error = exc_info.value
        assert "Date string must be a string" in str(error)
        assert error.field_name == "date_str"

    def test_invalid_input_type_list(self):
        """Test parsing with list input."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime(["2024-01-15"])

        error = exc_info.value
        assert "Date string must be a string" in str(error)
        assert error.field_name == "date_str"

    def test_empty_string(self):
        """Test parsing empty string."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("")

        error = exc_info.value
        assert "Date string cannot be empty" in str(error)
        assert error.field_name == "date_str"

    def test_whitespace_only_string(self):
        """Test parsing whitespace-only string."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("   ")

        error = exc_info.value
        assert "Date string cannot be empty" in str(error)
        assert error.field_name == "date_str"

    def test_invalid_datetime_format(self):
        """Test parsing invalid datetime format."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("not-a-datetime")

        error = exc_info.value
        assert "Unable to parse datetime" in str(error)
        assert error.field_name == "date_str"

    def test_invalid_iso_format(self):
        """Test parsing invalid ISO format."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("2024/01/15 10:30:45")

        error = exc_info.value
        assert "Unable to parse datetime" in str(error)
        assert error.field_name == "date_str"

    def test_partial_datetime(self):
        """Test parsing partial datetime (date only)."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("2024-01-15")

        error = exc_info.value
        assert "Unable to parse datetime" in str(error)
        assert error.field_name == "date_str"

    def test_invalid_date_values(self):
        """Test parsing with invalid date values."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("2024-13-45T25:70:90")

        error = exc_info.value
        assert "Unable to parse datetime" in str(error)
        assert error.field_name == "date_str"

    def test_malformed_timezone_format(self):
        """Test parsing datetime with malformed timezone."""
        with pytest.raises(ValidationError) as exc_info:
            parse_datetime("2024-01-15T10:30:45+invalid")

        error = exc_info.value
        assert "Unable to parse datetime" in str(error)
        assert error.field_name == "date_str"

    @pytest.mark.parametrize(
        "date_str,expected",
        [
            ("2024-01-15T10:30:45", datetime(2024, 1, 15, 10, 30, 45)),
            ("2024-12-31T23:59:59.999999", datetime(2024, 12, 31, 23, 59, 59, 999999)),
            ("2020-02-29T12:00:00", datetime(2020, 2, 29, 12, 0, 0)),  # Leap year
            ("2024-01-01T00:00:00.000001", datetime(2024, 1, 1, 0, 0, 0, 1)),
        ],
    )
    def test_various_valid_formats(self, date_str, expected):
        """Test parsing various valid datetime formats."""
        result = parse_datetime(date_str)
        assert result == expected

    def test_timezone_processing_exception_handling(self):
        """Test exception handling during timezone processing."""
        # This test actually hits the type validation first
        # The timezone processing only happens after type validation passes
        # So let's test a string that would cause AttributeError during processing
        with patch("toady.utils.datetime") as mock_datetime:
            mock_datetime.strptime.side_effect = ValueError("test parsing error")

            with pytest.raises(ValidationError) as exc_info:
                parse_datetime("2024-01-15T10:30:45+05:00")

            error = exc_info.value
            assert "Unable to parse datetime" in str(error)
            assert error.field_name == "date_str"

    def test_unexpected_exception_wrapping(self):
        """Test that unexpected exceptions are wrapped in ValidationError."""
        # Mock datetime.strptime to raise an unexpected exception
        with patch("toady.utils.datetime") as mock_datetime:
            mock_datetime.strptime.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(ValidationError) as exc_info:
                parse_datetime("2024-01-15T10:30:45")

            error = exc_info.value
            assert "Unexpected error parsing datetime" in str(error)
            assert error.field_name == "date_str"

    def test_validation_error_re_raise(self):
        """Test that ValidationError is re-raised without wrapping."""
        original_error = ValidationError("Original error")

        with patch("toady.utils.datetime") as mock_datetime:
            mock_datetime.strptime.side_effect = original_error

            with pytest.raises(ValidationError) as exc_info:
                parse_datetime("2024-01-15T10:30:45")

            # Should be the same ValidationError, not wrapped
            assert exc_info.value is original_error


@pytest.mark.unit
class TestEmitError:
    """Test the emit_error function."""

    def test_emit_error_pretty_format(self):
        """Test emit_error with pretty format."""
        ctx = click.Context(click.Command("test"))

        with (
            pytest.raises(click.exceptions.Exit) as exc_info,
            patch("click.echo") as mock_echo,
        ):
            emit_error(ctx, 123, "test_error", "Test error message", True)

        assert exc_info.value.exit_code == 1
        mock_echo.assert_called_once_with("Test error message", err=True)

    def test_emit_error_json_format(self):
        """Test emit_error with JSON format."""
        ctx = click.Context(click.Command("test"))

        with (
            pytest.raises(click.exceptions.Exit) as exc_info,
            patch("click.echo") as mock_echo,
        ):
            emit_error(ctx, 123, "test_error", "Test error message", False)

        assert exc_info.value.exit_code == 1

        # Verify JSON output
        mock_echo.assert_called_once()
        call_args = mock_echo.call_args
        assert call_args[1]["err"] is True

        json_output = call_args[0][0]
        parsed = json.loads(json_output)

        assert parsed == {
            "pr_number": 123,
            "success": False,
            "error": "test_error",
            "error_message": "Test error message",
        }

    def test_emit_error_invalid_pr_number_zero(self):
        """Test emit_error with zero PR number."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 0, "test_error", "Test message", False)

        # Should use fallback PR number of 0
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["pr_number"] == 0

    def test_emit_error_invalid_pr_number_negative(self):
        """Test emit_error with negative PR number."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, -5, "test_error", "Test message", False)

        # Should use fallback PR number of 0
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["pr_number"] == 0

    def test_emit_error_invalid_pr_number_non_integer(self):
        """Test emit_error with non-integer PR number."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, "not_an_int", "test_error", "Test message", False)

        # Should use fallback PR number of 0
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["pr_number"] == 0

    def test_emit_error_invalid_code_empty(self):
        """Test emit_error with empty error code."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, "", "Test message", False)

        # Should use fallback error code
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["error"] == "UNKNOWN_ERROR"

    def test_emit_error_invalid_code_whitespace(self):
        """Test emit_error with whitespace-only error code."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, "   ", "Test message", False)

        # Should use fallback error code
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["error"] == "UNKNOWN_ERROR"

    def test_emit_error_invalid_code_non_string(self):
        """Test emit_error with non-string error code."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, 404, "Test message", False)

        # Should use fallback error code
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["error"] == "UNKNOWN_ERROR"

    def test_emit_error_invalid_message_none(self):
        """Test emit_error with None message."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, "test_error", None, False)

        # Should use fallback message
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["error_message"] == "Unknown error occurred"

    def test_emit_error_invalid_message_empty_string(self):
        """Test emit_error with empty string message."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, "test_error", "", False)

        # Empty string passes through (not converted to fallback)
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["error_message"] == ""

    def test_emit_error_invalid_message_non_string(self):
        """Test emit_error with non-string message."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, "test_error", 404, False)

        # Should convert to string
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)
        assert parsed["error_message"] == "404"

    def test_emit_error_json_serialization_failure(self):
        """Test emit_error when JSON serialization fails."""
        ctx = click.Context(click.Command("test"))

        # Create an object that can't be JSON serialized
        class NonSerializable:
            pass

        with (
            pytest.raises(click.exceptions.Exit),
            patch("click.echo") as mock_echo,
            patch("json.dumps", side_effect=TypeError("Not serializable")),
        ):
            emit_error(ctx, 123, "test_error", "Test message", False)

        # Should fall back to simple text output
        mock_echo.assert_called_once_with(
            "Error (code: test_error): Test message", err=True
        )

    def test_emit_error_comprehensive_fallbacks(self):
        """Test emit_error with all invalid inputs to verify fallback behavior."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, "bad_pr", None, "", False)

        # Should use all fallbacks
        call_args = mock_echo.call_args
        json_output = call_args[0][0]
        parsed = json.loads(json_output)

        assert parsed["pr_number"] == 0
        assert parsed["error"] == "UNKNOWN_ERROR"
        assert parsed["error_message"] == ""  # Empty string passes through
        assert parsed["success"] is False

    @pytest.mark.parametrize(
        "pretty,expected_calls",
        [
            (True, 1),  # Pretty format calls echo once
            (False, 1),  # JSON format calls echo once
        ],
    )
    def test_emit_error_call_counts(self, pretty, expected_calls):
        """Test that emit_error makes expected number of echo calls."""
        ctx = click.Context(click.Command("test"))

        with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
            emit_error(ctx, 123, "test_error", "Test message", pretty)

        assert mock_echo.call_count == expected_calls


@pytest.mark.unit
class TestUtilsIntegration:
    """Integration tests for utility functions."""

    def test_parse_datetime_and_emit_error_integration(self):
        """Test integration between parse_datetime and emit_error."""
        ctx = click.Context(click.Command("test"))

        # Test that parse_datetime errors can be handled by emit_error
        try:
            parse_datetime("invalid-date")
        except ValidationError as e:
            with pytest.raises(click.exceptions.Exit), patch("click.echo") as mock_echo:
                emit_error(ctx, 123, "parse_error", str(e), True)

            mock_echo.assert_called_once()
            call_args = mock_echo.call_args
            assert call_args[1]["err"] is True
            assert "Unable to parse datetime" in call_args[0][0]

    def test_parse_datetime_timezone_edge_cases(self):
        """Test parse_datetime with complex timezone scenarios."""
        test_cases = [
            # Test date with multiple dashes but no timezone
            ("2024-01-15T10:30:45", datetime(2024, 1, 15, 10, 30, 45)),
            # Test date with timezone that has multiple colons
            ("2024-01-15T10:30:45-05:00", datetime(2024, 1, 15, 10, 30, 45)),
            # Test microseconds with Z
            ("2024-01-15T10:30:45.123Z", datetime(2024, 1, 15, 10, 30, 45, 123000)),
        ]

        for date_str, expected in test_cases:
            result = parse_datetime(date_str)
            assert result == expected

    def test_utils_module_constants_and_functions(self):
        """Test that all expected module exports are available."""
        from toady import utils

        # Test constants
        assert hasattr(utils, "MAX_PR_NUMBER")
        assert utils.MAX_PR_NUMBER == 999999

        # Test functions
        assert hasattr(utils, "parse_datetime")
        assert hasattr(utils, "emit_error")
        assert callable(utils.parse_datetime)
        assert callable(utils.emit_error)
