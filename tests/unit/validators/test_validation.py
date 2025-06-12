"""Unit tests for the validation module (src/toady/validators/validation.py).

This module provides comprehensive unit tests for all validation functions,
including parameter validation, data validation, error handling, edge cases,
boundary conditions, and warning systems.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from toady.exceptions import ValidationError
from toady.validators.validation import (
    EMAIL_REGEX,
    MAX_LIMIT_VALUE,
    MAX_REPLY_BODY_LENGTH,
    MIN_LIMIT_VALUE,
    MIN_MEANINGFUL_CONTENT_LENGTH,
    MIN_REPLY_BODY_LENGTH,
    PLACEHOLDER_PATTERNS,
    URL_REGEX,
    USERNAME_REGEX,
    ResolveOptions,
    validate_boolean_flag,
    validate_choice,
    validate_comment_id,
    validate_datetime_string,
    validate_dict_keys,
    validate_email,
    validate_fetch_command_args,
    validate_limit,
    validate_non_empty_string,
    validate_pr_number,
    validate_reply_body,
    validate_reply_command_args,
    validate_reply_content_warnings,
    validate_resolve_command_args,
    validate_thread_id,
    validate_url,
    validate_username,
)


class TestConstants:
    """Test validation constants are properly defined."""

    def test_constants_exist(self):
        """Test that all validation constants are defined."""
        assert MIN_REPLY_BODY_LENGTH == 3
        assert MAX_REPLY_BODY_LENGTH == 65536
        assert MIN_MEANINGFUL_CONTENT_LENGTH == 3
        assert MAX_LIMIT_VALUE == 1000
        assert MIN_LIMIT_VALUE == 1

    def test_regex_patterns_compile(self):
        """Test that all regex patterns compile correctly."""
        assert EMAIL_REGEX.pattern is not None
        assert URL_REGEX.pattern is not None
        assert USERNAME_REGEX.pattern is not None

        # Test that they can be used for matching
        assert EMAIL_REGEX.match("test@example.com") is not None
        assert URL_REGEX.match("https://example.com") is not None
        assert USERNAME_REGEX.match("testuser") is not None

    def test_placeholder_patterns_set(self):
        """Test that placeholder patterns are properly defined."""
        assert isinstance(PLACEHOLDER_PATTERNS, set)
        assert len(PLACEHOLDER_PATTERNS) > 0
        assert "test" in PLACEHOLDER_PATTERNS
        assert "..." in PLACEHOLDER_PATTERNS


class TestValidatePRNumber:
    """Test PR number validation with comprehensive coverage."""

    def test_valid_pr_numbers_integers(self):
        """Test valid PR numbers as integers."""
        assert validate_pr_number(1) == 1
        assert validate_pr_number(123) == 123
        assert validate_pr_number(999999) == 999999

    def test_valid_pr_numbers_strings(self):
        """Test valid PR numbers as strings."""
        assert validate_pr_number("1") == 1
        assert validate_pr_number("123") == 123
        assert validate_pr_number("999999") == 999999

    def test_pr_number_string_whitespace_handling(self):
        """Test PR number validation with whitespace."""
        assert validate_pr_number("  123  ") == 123
        assert validate_pr_number("\t456\n") == 456
        assert validate_pr_number(" \t 789 \n ") == 789

    def test_pr_number_none_values(self):
        """Test None handling with allow_none parameter."""
        assert validate_pr_number(None, allow_none=True) is None

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "PR number"

    def test_pr_number_none_with_custom_field_name(self):
        """Test None handling with custom field name."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(None, field_name="Custom PR")
        error = exc_info.value
        assert "Custom PR cannot be None" in error.message
        assert error.field_name == "Custom PR"

    def test_pr_number_zero_and_negative(self):
        """Test zero and negative PR numbers."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(0)
        assert "must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-1)
        assert "must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-999)
        assert "must be positive" in str(exc_info.value)

    def test_pr_number_too_large(self):
        """Test PR numbers that are too large."""
        from toady.utils import MAX_PR_NUMBER

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(MAX_PR_NUMBER + 1)
        assert "unreasonably large" in str(exc_info.value)

    def test_pr_number_empty_string(self):
        """Test empty string handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_pr_number_non_numeric_strings(self):
        """Test non-numeric string handling."""
        invalid_values = ["abc", "12abc", "abc12", "12.34", "1.0", "not-a-number"]

        for invalid_value in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_pr_number(invalid_value)
            assert "must be numeric" in str(exc_info.value)

    def test_pr_number_float_values(self):
        """Test float value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(123.45)
        assert "must be an integer" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(123.0)
        assert "must be an integer" in str(exc_info.value)

    def test_pr_number_other_types(self):
        """Test other invalid types."""
        invalid_types = [[], {}, set(), object(), lambda x: x]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_pr_number(invalid_type)
            assert "must be an integer" in str(exc_info.value)

    def test_pr_number_boundary_values(self):
        """Test boundary values."""
        # Test minimum valid value
        assert validate_pr_number(1) == 1

        # Test just below maximum
        from toady.utils import MAX_PR_NUMBER

        assert validate_pr_number(MAX_PR_NUMBER) == MAX_PR_NUMBER
        assert validate_pr_number(MAX_PR_NUMBER - 1) == MAX_PR_NUMBER - 1


class TestValidateCommentID:
    """Test comment ID validation with comprehensive coverage."""

    def test_valid_numeric_comment_ids(self):
        """Test valid numeric comment IDs."""
        assert validate_comment_id("123456789") == "123456789"
        assert validate_comment_id(123456789) == "123456789"
        assert validate_comment_id("1") == "1"

    def test_valid_github_node_comment_ids(self):
        """Test valid GitHub node comment IDs."""
        valid_comment_ids = [
            "IC_kwDOABcD12MAAAABcDE3fg",
            "PRRC_kwDOABcD12MAAAABcDE3fg",
            "RP_kwDOABcD12MAAAABcDE3fg",
        ]

        for comment_id in valid_comment_ids:
            assert validate_comment_id(comment_id) == comment_id

    def test_comment_id_whitespace_handling(self):
        """Test comment ID validation with whitespace."""
        assert (
            validate_comment_id("  IC_kwDOABcD12MAAAABcDE3fg  ")
            == "IC_kwDOABcD12MAAAABcDE3fg"
        )
        assert validate_comment_id("\t123456789\n") == "123456789"

    def test_comment_id_thread_ids_when_allowed(self):
        """Test accepting thread IDs when allow_thread_ids=True."""
        thread_ids = [
            "PRT_kwDOABcD12MAAAABcDE3fg",
            "PRRT_kwDOABcD12MAAAABcDE3fg",
            "RT_kwDOABcD12MAAAABcDE3fg",
        ]

        for thread_id in thread_ids:
            result = validate_comment_id(thread_id, allow_thread_ids=True)
            assert result == thread_id

    def test_comment_id_thread_ids_when_not_allowed(self):
        """Test rejecting thread IDs when allow_thread_ids=False."""
        thread_ids = [
            "PRT_kwDOABcD12MAAAABcDE3fg",
            "PRRT_kwDOABcD12MAAAABcDE3fg",
            "RT_kwDOABcD12MAAAABcDE3fg",
        ]

        for thread_id in thread_ids:
            with pytest.raises(ValidationError):
                validate_comment_id(thread_id, allow_thread_ids=False)

    def test_comment_id_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_comment_id(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Comment ID"

    def test_comment_id_empty_string(self):
        """Test empty string handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_comment_id("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_comment_id("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_comment_id_invalid_node_format(self):
        """Test invalid node ID formats."""
        invalid_ids = [
            "INVALID_kwDOABcD12MAAAABcDE3fg",
            "IC_",  # Too short
            "NotANodeID",
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError):
                validate_comment_id(invalid_id)

    def test_comment_id_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_comment_id(None, field_name="Custom Comment ID")
        error = exc_info.value
        assert error.field_name == "Custom Comment ID"
        assert "Custom Comment ID cannot be None" in error.message

    @patch("toady.validators.validation.create_comment_validator")
    def test_comment_id_validator_integration(self, mock_create_validator):
        """Test integration with node ID validator."""
        mock_validator = Mock()
        mock_create_validator.return_value = mock_validator

        validate_comment_id("IC_test123")

        mock_create_validator.assert_called_once()
        mock_validator.validate_id.assert_called_once_with("IC_test123", "Comment ID")

    @patch("toady.validators.validation.create_universal_validator")
    def test_comment_id_universal_validator_when_thread_ids_allowed(
        self, mock_create_validator
    ):
        """Test integration with universal validator when thread IDs are allowed."""
        mock_validator = Mock()
        mock_create_validator.return_value = mock_validator

        validate_comment_id("IC_test123", allow_thread_ids=True)

        mock_create_validator.assert_called_once()
        mock_validator.validate_id.assert_called_once_with("IC_test123", "Comment ID")


class TestValidateThreadID:
    """Test thread ID validation with comprehensive coverage."""

    def test_valid_numeric_thread_ids(self):
        """Test valid numeric thread IDs."""
        assert validate_thread_id("123456789") == "123456789"
        assert validate_thread_id(123456789) == "123456789"
        assert validate_thread_id("1") == "1"

    def test_valid_github_node_thread_ids(self):
        """Test valid GitHub node thread IDs."""
        valid_thread_ids = [
            "PRT_kwDOABcD12MAAAABcDE3fg",
            "PRRT_kwDOABcD12MAAAABcDE3fg",
            "RT_kwDOABcD12MAAAABcDE3fg",
        ]

        for thread_id in valid_thread_ids:
            assert validate_thread_id(thread_id) == thread_id

    def test_thread_id_whitespace_handling(self):
        """Test thread ID validation with whitespace."""
        assert (
            validate_thread_id("  PRT_kwDOABcD12MAAAABcDE3fg  ")
            == "PRT_kwDOABcD12MAAAABcDE3fg"
        )
        assert validate_thread_id("\t123456789\n") == "123456789"

    def test_thread_id_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_thread_id(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Thread ID"

    def test_thread_id_empty_string(self):
        """Test empty string handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_thread_id("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_thread_id("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_thread_id_comment_ids_rejected(self):
        """Test that comment IDs are rejected."""
        comment_ids = [
            "IC_kwDOABcD12MAAAABcDE3fg",
            "PRRC_kwDOABcD12MAAAABcDE3fg",
            "RP_kwDOABcD12MAAAABcDE3fg",
        ]

        for comment_id in comment_ids:
            with pytest.raises(ValidationError):
                validate_thread_id(comment_id)

    def test_thread_id_invalid_node_format(self):
        """Test invalid node ID formats."""
        invalid_ids = [
            "INVALID_kwDOABcD12MAAAABcDE3fg",
            "PRT_",  # Too short
            "NotANodeID",
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError):
                validate_thread_id(invalid_id)

    def test_thread_id_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_thread_id(None, field_name="Custom Thread ID")
        error = exc_info.value
        assert error.field_name == "Custom Thread ID"
        assert "Custom Thread ID cannot be None" in error.message

    @patch("toady.validators.validation.create_thread_validator")
    def test_thread_id_validator_integration(self, mock_create_validator):
        """Test integration with thread ID validator."""
        mock_validator = Mock()
        mock_create_validator.return_value = mock_validator

        validate_thread_id("PRT_test123")

        mock_create_validator.assert_called_once()
        mock_validator.validate_id.assert_called_once_with("PRT_test123", "Thread ID")


class TestValidateReplyBody:
    """Test reply body validation with comprehensive coverage."""

    def test_valid_reply_bodies(self):
        """Test valid reply bodies."""
        valid_bodies = [
            "This is a valid reply",
            "Short but meaningful",
            "A" * MAX_REPLY_BODY_LENGTH,  # Maximum length
            "This has some\nnewlines\nand\ttabs",
            "Valid reply with @mention in middle",
            "123 numbers are fine too",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        ]

        for body in valid_bodies:
            result = validate_reply_body(body)
            assert result == body.strip()

    def test_reply_body_whitespace_trimming(self):
        """Test reply body whitespace trimming."""
        assert (
            validate_reply_body("  This is a valid reply  ") == "This is a valid reply"
        )
        assert validate_reply_body("\t\nValid reply\n\t") == "Valid reply"

    def test_reply_body_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Reply body"

    def test_reply_body_non_string_types(self):
        """Test non-string type handling."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(invalid_type)
            assert "must be a string" in str(exc_info.value)

    def test_reply_body_empty_after_stripping(self):
        """Test empty string after stripping."""
        empty_values = ["", "   ", "\t\n\r", "    \t\n    "]

        for empty_value in empty_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(empty_value)
            assert "cannot be empty" in str(exc_info.value)

    def test_reply_body_too_short(self):
        """Test reply bodies that are too short."""
        short_bodies = ["a", "ab", "  a  ", "\tab\t"]

        for short_body in short_bodies:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(short_body)
            assert "must be at least 3 characters" in str(exc_info.value)

    def test_reply_body_too_long(self):
        """Test reply bodies that are too long."""
        too_long_body = "A" * (MAX_REPLY_BODY_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body(too_long_body)
        assert "cannot exceed 65,536 characters" in str(exc_info.value)
        assert "GitHub limit" in str(exc_info.value)

    def test_reply_body_insufficient_meaningful_content(self):
        """Test replies with insufficient meaningful content."""
        # Content with less than MIN_MEANINGFUL_CONTENT_LENGTH non-whitespace chars
        insufficient_content = [
            "a  \n\t  b",  # Only 2 non-whitespace chars
            "   x   y   ",  # Only 2 non-whitespace chars
            "a \t\n b",  # Only 2 non-whitespace chars when meaningful calculated
        ]

        for content in insufficient_content:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(content)
            # The error can be either length or meaningful content
            # depending on which fails first
            error_msg = str(exc_info.value)
            assert (
                "non-whitespace characters" in error_msg
                or "must be at least 3 characters" in error_msg
            )

    def test_reply_body_placeholder_patterns(self):
        """Test detection of placeholder patterns."""
        # Test patterns that are long enough but are placeholders
        placeholder_bodies = ["...", "????", "test", "testing", "placeholder"]

        for placeholder in placeholder_bodies:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(placeholder)
            assert "placeholder text" in str(exc_info.value)

    def test_reply_body_custom_length_constraints(self):
        """Test custom length constraints."""
        # Test with custom min_length
        assert validate_reply_body("hello", min_length=5) == "hello"

        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("hi", min_length=5)
        assert "must be at least 5 characters" in str(exc_info.value)

        # Test with custom max_length
        assert validate_reply_body("hello", max_length=10) == "hello"

        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("this is too long", max_length=10)
        assert "cannot exceed 10 characters" in str(exc_info.value)

    def test_reply_body_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body(None, field_name="Custom Body")
        error = exc_info.value
        assert error.field_name == "Custom Body"
        assert "Custom Body cannot be None" in error.message

    def test_reply_body_boundary_lengths(self):
        """Test boundary length conditions."""
        # Test minimum valid length
        min_valid = "a" * MIN_REPLY_BODY_LENGTH
        assert validate_reply_body(min_valid) == min_valid

        # Test maximum valid length
        max_valid = "a" * MAX_REPLY_BODY_LENGTH
        assert validate_reply_body(max_valid) == max_valid


class TestValidateLimit:
    """Test limit validation with comprehensive coverage."""

    def test_valid_limits_integers(self):
        """Test valid limit values as integers."""
        assert validate_limit(1) == 1
        assert validate_limit(100) == 100
        assert validate_limit(MAX_LIMIT_VALUE) == MAX_LIMIT_VALUE

    def test_valid_limits_strings(self):
        """Test valid limit values as strings."""
        assert validate_limit("1") == 1
        assert validate_limit("100") == 100
        assert validate_limit(str(MAX_LIMIT_VALUE)) == MAX_LIMIT_VALUE

    def test_limit_whitespace_handling(self):
        """Test limit validation with whitespace."""
        assert validate_limit("  100  ") == 100
        assert validate_limit("\t456\n") == 456

    def test_limit_custom_ranges(self):
        """Test custom min/max ranges."""
        assert validate_limit(5, min_value=5, max_value=10) == 5
        assert validate_limit(10, min_value=5, max_value=10) == 10
        assert validate_limit(7, min_value=5, max_value=10) == 7

    def test_limit_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Limit"

    def test_limit_zero_and_negative(self):
        """Test zero and negative limit values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(0)
        assert "must be at least 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_limit(-1)
        assert "must be at least 1" in str(exc_info.value)

    def test_limit_too_large(self):
        """Test limit values that are too large."""
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(MAX_LIMIT_VALUE + 1)
        assert f"cannot exceed {MAX_LIMIT_VALUE}" in str(exc_info.value)

    def test_limit_empty_string(self):
        """Test empty string handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_limit("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_limit("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_limit_non_numeric_strings(self):
        """Test non-numeric string handling."""
        invalid_values = ["abc", "12abc", "abc12", "12.34", "not-a-number"]

        for invalid_value in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_limit(invalid_value)
            assert "must be numeric" in str(exc_info.value)

    def test_limit_other_types(self):
        """Test other invalid types."""
        invalid_types = [[], {}, set(), object(), 123.45]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_limit(invalid_type)
            assert "must be an integer" in str(exc_info.value)

    def test_limit_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(None, field_name="Custom Limit")
        error = exc_info.value
        assert error.field_name == "Custom Limit"

    def test_limit_custom_range_validation(self):
        """Test custom range validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(4, min_value=5, max_value=10)
        assert "must be at least 5" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_limit(11, min_value=5, max_value=10)
        assert "cannot exceed 10" in str(exc_info.value)


class TestValidateDatetimeString:
    """Test datetime string validation with comprehensive coverage."""

    def test_valid_datetime_strings(self):
        """Test valid datetime strings."""
        valid_dates = [
            "2024-01-01T12:00:00",
            "2024-12-31T23:59:59",
            "2024-01-01T12:00:00.123456",
            "2024-06-15T08:30:45",
        ]

        for date_str in valid_dates:
            result = validate_datetime_string(date_str)
            assert isinstance(result, datetime)

    def test_datetime_string_whitespace_handling(self):
        """Test datetime string with whitespace."""
        result = validate_datetime_string("  2024-01-01T12:00:00  ")
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_datetime_string_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Date"

    def test_datetime_string_non_string_types(self):
        """Test non-string type handling."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_datetime_string(invalid_type)
            assert "must be a string" in str(exc_info.value)

    def test_datetime_string_empty_after_stripping(self):
        """Test empty string after stripping."""
        empty_values = ["", "   ", "\t\n\r"]

        for empty_value in empty_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_datetime_string(empty_value)
            assert "cannot be empty" in str(exc_info.value)

    def test_datetime_string_invalid_formats(self):
        """Test invalid datetime formats."""
        invalid_dates = [
            "not-a-date",
            "2024-13-01T12:00:00",  # Invalid month
            "2024-01-32T12:00:00",  # Invalid day
            "2024-01-01T25:00:00",  # Invalid hour
            "2024-01-01",  # Missing time
            "12:00:00",  # Missing date
            "2024/01/01 12:00:00",  # Wrong format
        ]

        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError) as exc_info:
                validate_datetime_string(invalid_date)
            assert "Invalid" in str(exc_info.value)

    def test_datetime_string_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string(None, field_name="Custom Date")
        error = exc_info.value
        assert error.field_name == "Custom Date"

    @patch("toady.utils.parse_datetime")
    def test_datetime_string_parse_datetime_integration(self, mock_parse_datetime):
        """Test integration with parse_datetime utility."""
        mock_parse_datetime.return_value = datetime(2024, 1, 1, 12, 0, 0)

        result = validate_datetime_string("2024-01-01T12:00:00")

        mock_parse_datetime.assert_called_once_with("2024-01-01T12:00:00")
        assert result == datetime(2024, 1, 1, 12, 0, 0)

    @patch("toady.utils.parse_datetime")
    def test_datetime_string_validation_error_from_parse_datetime(
        self, mock_parse_datetime
    ):
        """Test handling of ValidationError from parse_datetime."""
        mock_parse_datetime.side_effect = ValidationError("Parse error")

        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string("invalid-date")

        assert "Invalid date format" in str(exc_info.value)

    @patch("toady.utils.parse_datetime")
    def test_datetime_string_value_error_from_parse_datetime(self, mock_parse_datetime):
        """Test handling of ValueError from parse_datetime."""
        mock_parse_datetime.side_effect = ValueError("Parse error message")

        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string("invalid-date")

        assert "Invalid date format" in str(exc_info.value)
        assert "Parse error message" in str(exc_info.value)


class TestValidateEmail:
    """Test email validation with comprehensive coverage."""

    def test_valid_emails(self):
        """Test valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@example.org",
            "user-name@example-domain.com",
            "user_name@example.com",
            "123@example.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert validate_email(email) == email

    def test_email_whitespace_handling(self):
        """Test email validation with whitespace."""
        assert validate_email("  user@example.com  ") == "user@example.com"
        assert validate_email("\tuser@example.com\n") == "user@example.com"

    def test_email_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_email(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Email"

    def test_email_non_string_types(self):
        """Test non-string type handling."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_email(invalid_type)
            assert "must be a string" in str(exc_info.value)

    def test_email_empty_after_stripping(self):
        """Test empty string after stripping."""
        empty_values = ["", "   ", "\t\n\r"]

        for empty_value in empty_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_email(empty_value)
            assert "cannot be empty" in str(exc_info.value)

    def test_email_invalid_formats(self):
        """Test invalid email formats."""
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user.example.com",
            "user@@example.com",
            "user@.com",
            "user@example.",
            "user name@example.com",  # Space in local part
            "user@exam ple.com",  # Space in domain
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                validate_email(invalid_email)
            assert "Invalid email format" in str(exc_info.value)

    def test_email_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_email(None, field_name="User Email")
        error = exc_info.value
        assert error.field_name == "User Email"

    def test_email_regex_integration(self):
        """Test integration with EMAIL_REGEX."""
        # Test that the function uses the EMAIL_REGEX pattern
        valid_email = "test@example.com"
        assert EMAIL_REGEX.match(valid_email) is not None
        assert validate_email(valid_email) == valid_email


class TestValidateURL:
    """Test URL validation with comprehensive coverage."""

    def test_valid_urls(self):
        """Test valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path",
            "https://example.com/path?query=1",
            "https://example.com/path?query=1#fragment",
            "https://sub.example.com",
            "https://example.com:8080",
            "https://example.com:8080/path?query=1#fragment",
        ]

        for url in valid_urls:
            assert validate_url(url) == url

    def test_url_whitespace_handling(self):
        """Test URL validation with whitespace."""
        assert validate_url("  https://example.com  ") == "https://example.com"
        assert validate_url("\thttps://example.com\n") == "https://example.com"

    def test_url_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "URL"

    def test_url_non_string_types(self):
        """Test non-string type handling."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_url(invalid_type)
            assert "must be a string" in str(exc_info.value)

    def test_url_empty_after_stripping(self):
        """Test empty string after stripping."""
        empty_values = ["", "   ", "\t\n\r"]

        for empty_value in empty_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_url(empty_value)
            assert "cannot be empty" in str(exc_info.value)

    def test_url_invalid_formats(self):
        """Test invalid URL formats."""
        invalid_urls = [
            "ftp://example.com",  # Wrong protocol
            "not-a-url",
            "example.com",  # Missing protocol
            "https://",  # Missing domain
            "https:///path",  # Missing domain
        ]

        for invalid_url in invalid_urls:
            with pytest.raises(ValidationError) as exc_info:
                validate_url(invalid_url)
            assert "Invalid url format" in str(exc_info.value)

    def test_url_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url(None, field_name="Website URL")
        error = exc_info.value
        assert error.field_name == "Website URL"

    def test_url_regex_integration(self):
        """Test integration with URL_REGEX."""
        # Test that the function uses the URL_REGEX pattern
        valid_url = "https://example.com"
        assert URL_REGEX.match(valid_url) is not None
        assert validate_url(valid_url) == valid_url


class TestValidateUsername:
    """Test username validation with comprehensive coverage."""

    def test_valid_usernames(self):
        """Test valid GitHub usernames."""
        valid_usernames = [
            "user",
            "user-name",
            "user123",
            "123user",
            "a",
            "a" * 39,  # Maximum length
            "user-123",
            "test-user-name",
        ]

        for username in valid_usernames:
            assert validate_username(username) == username

    def test_username_whitespace_handling(self):
        """Test username validation with whitespace."""
        assert validate_username("  user  ") == "user"
        assert validate_username("\tuser123\n") == "user123"

    def test_username_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_username(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Username"

    def test_username_non_string_types(self):
        """Test non-string type handling."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_username(invalid_type)
            assert "must be a string" in str(exc_info.value)

    def test_username_empty_after_stripping(self):
        """Test empty string after stripping."""
        empty_values = ["", "   ", "\t\n\r"]

        for empty_value in empty_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_username(empty_value)
            assert "cannot be empty" in str(exc_info.value)

    def test_username_invalid_formats(self):
        """Test invalid username formats."""
        invalid_usernames = [
            "-user",  # Starts with hyphen
            "user-",  # Ends with hyphen
            "user..name",  # Double dot
            "user.name",  # Contains dot
            "a" * 40,  # Too long
            "user name",  # Contains space
            "user@name",  # Contains @
            "user#name",  # Contains #
        ]

        for invalid_username in invalid_usernames:
            with pytest.raises(ValidationError) as exc_info:
                validate_username(invalid_username)
            assert "Invalid username format" in str(exc_info.value)

    def test_username_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_username(None, field_name="GitHub User")
        error = exc_info.value
        assert error.field_name == "GitHub User"

    def test_username_regex_integration(self):
        """Test integration with USERNAME_REGEX."""
        # Test that the function uses the USERNAME_REGEX pattern
        valid_username = "test-user123"
        assert USERNAME_REGEX.match(valid_username) is not None
        assert validate_username(valid_username) == valid_username


class TestValidateNonEmptyString:
    """Test non-empty string validation with comprehensive coverage."""

    def test_valid_non_empty_strings(self):
        """Test valid non-empty strings."""
        valid_strings = [
            "hello",
            "a",
            "test string",
            "123",
            "!@#$%^&*()",
        ]

        for string in valid_strings:
            assert validate_non_empty_string(string) == string

    def test_non_empty_string_whitespace_handling(self):
        """Test non-empty string with whitespace."""
        assert validate_non_empty_string("  hello  ") == "hello"
        assert validate_non_empty_string("\ttest\n") == "test"

    def test_non_empty_string_custom_length_constraints(self):
        """Test custom length constraints."""
        assert validate_non_empty_string("hello", min_length=5) == "hello"
        assert validate_non_empty_string("hello", max_length=10) == "hello"
        assert (
            validate_non_empty_string("hello", min_length=3, max_length=10) == "hello"
        )

    def test_non_empty_string_none_value(self):
        """Test None value handling."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Value"

    def test_non_empty_string_non_string_types(self):
        """Test non-string type handling."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_non_empty_string(invalid_type)
            assert "must be a string" in str(exc_info.value)

    def test_non_empty_string_empty_after_stripping(self):
        """Test empty string after stripping."""
        empty_values = ["", "   ", "\t\n\r"]

        for empty_value in empty_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_non_empty_string(empty_value)
            assert "cannot be empty" in str(exc_info.value)

    def test_non_empty_string_too_short(self):
        """Test strings that are too short."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("ab", min_length=3)
        assert "must be at least 3 characters" in str(exc_info.value)

    def test_non_empty_string_too_long(self):
        """Test strings that are too long."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("toolong", max_length=5)
        assert "cannot exceed 5 characters" in str(exc_info.value)

    def test_non_empty_string_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string(None, field_name="Custom Field")
        error = exc_info.value
        assert error.field_name == "Custom Field"

    def test_non_empty_string_boundary_lengths(self):
        """Test boundary length conditions."""
        # Test minimum valid length with custom constraint
        assert validate_non_empty_string("abc", min_length=3) == "abc"

        # Test maximum valid length with custom constraint
        assert validate_non_empty_string("abcde", max_length=5) == "abcde"


class TestValidateBooleanFlag:
    """Test boolean flag validation with comprehensive coverage."""

    def test_valid_boolean_values(self):
        """Test valid boolean values."""
        assert validate_boolean_flag(True) is True
        assert validate_boolean_flag(False) is False

    def test_valid_string_boolean_representations(self):
        """Test valid string boolean representations."""
        true_values = [
            "true",
            "TRUE",
            "True",
            "1",
            "yes",
            "YES",
            "Yes",
            "on",
            "ON",
            "On",
        ]
        false_values = [
            "false",
            "FALSE",
            "False",
            "0",
            "no",
            "NO",
            "No",
            "off",
            "OFF",
            "Off",
        ]

        for true_value in true_values:
            assert validate_boolean_flag(true_value) is True

        for false_value in false_values:
            assert validate_boolean_flag(false_value) is False

    def test_boolean_flag_string_whitespace_handling(self):
        """Test boolean flag string with whitespace."""
        assert validate_boolean_flag("  true  ") is True
        assert validate_boolean_flag("\tfalse\n") is False

    def test_boolean_flag_none_value_with_allow_none(self):
        """Test None value handling with allow_none=True."""
        assert validate_boolean_flag(None, allow_none=True) is False

    def test_boolean_flag_none_value_without_allow_none(self):
        """Test None value handling with allow_none=False."""
        with pytest.raises(ValidationError) as exc_info:
            validate_boolean_flag(None)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Flag"

    def test_boolean_flag_invalid_string_values(self):
        """Test invalid string boolean values."""
        invalid_values = ["invalid", "maybe", "2", "-1", "TRUE_FALSE", "yes_no"]

        for invalid_value in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                validate_boolean_flag(invalid_value)
            assert "must be a boolean value" in str(exc_info.value)

    def test_boolean_flag_invalid_types(self):
        """Test invalid types for boolean flag."""
        invalid_types = [123, [], {}, set(), object()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_boolean_flag(invalid_type)
            assert "must be a boolean value" in str(exc_info.value)

    def test_boolean_flag_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_boolean_flag(None, field_name="Custom Flag")
        error = exc_info.value
        assert error.field_name == "Custom Flag"


class TestValidateChoice:
    """Test choice validation with comprehensive coverage."""

    def test_valid_choices(self):
        """Test valid choice values."""
        choices = ["option1", "option2", "option3"]

        for choice in choices:
            assert validate_choice(choice, choices) == choice

    def test_choice_case_sensitive_matching(self):
        """Test case-sensitive choice matching."""
        choices = ["Option1", "Option2"]

        assert validate_choice("Option1", choices) == "Option1"

        # Should fail with different case when case_sensitive=True
        with pytest.raises(ValidationError):
            validate_choice("option1", choices, case_sensitive=True)

    def test_choice_case_insensitive_matching(self):
        """Test case-insensitive choice matching."""
        choices = ["Option1", "Option2"]

        assert validate_choice("option1", choices, case_sensitive=False) == "Option1"
        assert validate_choice("OPTION2", choices, case_sensitive=False) == "Option2"
        assert validate_choice("OpTiOn1", choices, case_sensitive=False) == "Option1"

    def test_choice_non_string_values(self):
        """Test choice validation with non-string values."""
        choices = [1, 2, 3]

        assert validate_choice(1, choices) == 1
        assert validate_choice(2, choices) == 2

    def test_choice_mixed_type_choices(self):
        """Test choice validation with mixed type choices."""
        choices = ["string", 123, True]

        assert validate_choice("string", choices) == "string"
        assert validate_choice(123, choices) == 123
        assert validate_choice(True, choices) is True

    def test_choice_none_value(self):
        """Test None value handling."""
        choices = ["option1", "option2"]

        with pytest.raises(ValidationError) as exc_info:
            validate_choice(None, choices)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Value"

    def test_choice_invalid_choice(self):
        """Test invalid choice values."""
        choices = ["option1", "option2"]

        with pytest.raises(ValidationError) as exc_info:
            validate_choice("invalid", choices)
        assert "must be one of the allowed values" in str(exc_info.value)

    def test_choice_custom_field_name(self):
        """Test custom field name in error messages."""
        choices = ["option1", "option2"]

        with pytest.raises(ValidationError) as exc_info:
            validate_choice(None, choices, field_name="Custom Choice")
        error = exc_info.value
        assert error.field_name == "Custom Choice"

    def test_choice_error_message_includes_choices(self):
        """Test that error messages include available choices."""
        choices = ["option1", "option2", "option3"]

        with pytest.raises(ValidationError) as exc_info:
            validate_choice("invalid", choices)

        error = exc_info.value
        # The choices are included in the expected_format field
        for choice in choices:
            assert str(choice) in error.expected_format


class TestValidateDictKeys:
    """Test dictionary key validation with comprehensive coverage."""

    def test_valid_dictionary_with_required_keys(self):
        """Test valid dictionary with all required keys."""
        data = {"key1": "value1", "key2": "value2"}
        required_keys = ["key1", "key2"]

        result = validate_dict_keys(data, required_keys)
        assert result == data

    def test_valid_dictionary_with_optional_keys(self):
        """Test valid dictionary with optional keys."""
        data = {"key1": "value1", "key2": "value2", "optional": "value"}
        required_keys = ["key1", "key2"]
        optional_keys = ["optional"]

        result = validate_dict_keys(data, required_keys, optional_keys)
        assert result == data

    def test_valid_dictionary_with_extra_keys_allowed(self):
        """Test valid dictionary with extra keys when optional_keys is None."""
        data = {"key1": "value1", "key2": "value2", "extra": "value"}
        required_keys = ["key1", "key2"]

        # When optional_keys is None, extra keys are allowed
        result = validate_dict_keys(data, required_keys, optional_keys=None)
        assert result == data

    def test_dictionary_none_value(self):
        """Test None value handling."""
        required_keys = ["key1", "key2"]

        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(None, required_keys)
        error = exc_info.value
        assert "cannot be None" in error.message
        assert error.field_name == "Data"

    def test_dictionary_non_dict_types(self):
        """Test non-dictionary type handling."""
        required_keys = ["key1", "key2"]
        invalid_types = ["not-a-dict", 123, [], set()]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validate_dict_keys(invalid_type, required_keys)
            assert "must be a dictionary" in str(exc_info.value)

    def test_dictionary_missing_required_keys(self):
        """Test dictionary with missing required keys."""
        data = {"key1": "value1"}  # Missing key2
        required_keys = ["key1", "key2"]

        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys)

        error_message = str(exc_info.value)
        assert "Missing required keys" in error_message
        assert "key2" in error_message

    def test_dictionary_multiple_missing_required_keys(self):
        """Test dictionary with multiple missing required keys."""
        data = {"key1": "value1"}  # Missing key2 and key3
        required_keys = ["key1", "key2", "key3"]

        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys)

        error_message = str(exc_info.value)
        assert "Missing required keys" in error_message
        assert "key2" in error_message
        assert "key3" in error_message

    def test_dictionary_unexpected_keys(self):
        """Test dictionary with unexpected keys."""
        data = {"key1": "value1", "key2": "value2", "unexpected": "value"}
        required_keys = ["key1", "key2"]
        optional_keys = []  # No optional keys allowed

        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys, optional_keys)

        error_message = str(exc_info.value)
        assert "Unexpected keys" in error_message
        assert "unexpected" in error_message

    def test_dictionary_multiple_unexpected_keys(self):
        """Test dictionary with multiple unexpected keys."""
        data = {
            "key1": "value1",
            "key2": "value2",
            "unexpected1": "value",
            "unexpected2": "value",
        }
        required_keys = ["key1", "key2"]
        optional_keys = []

        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys, optional_keys)

        error_message = str(exc_info.value)
        assert "Unexpected keys" in error_message
        assert "unexpected1" in error_message
        assert "unexpected2" in error_message

    def test_dictionary_custom_field_name(self):
        """Test custom field name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(None, ["key1"], field_name="Configuration")
        error = exc_info.value
        assert error.field_name == "Configuration"

    def test_dictionary_empty_required_keys(self):
        """Test dictionary with empty required keys list."""
        data = {"key1": "value1"}
        required_keys = []

        result = validate_dict_keys(data, required_keys)
        assert result == data

    def test_dictionary_empty_optional_keys(self):
        """Test dictionary with empty optional keys list."""
        data = {"key1": "value1"}
        required_keys = ["key1"]
        optional_keys = []

        result = validate_dict_keys(data, required_keys, optional_keys)
        assert result == data


class TestValidateReplyContentWarnings:
    """Test reply content warning system with comprehensive coverage."""

    def test_no_warnings_for_normal_content(self):
        """Test that normal content produces no warnings."""
        normal_content = [
            "This is a normal reply",
            "Here's some feedback on your code",
            "Looks good to me!",
            "Could you please update the documentation?",
        ]

        for content in normal_content:
            warnings = validate_reply_content_warnings(content)
            assert warnings == []

    def test_mention_warning(self):
        """Test mention warning detection."""
        mention_content = [
            "@user this is a mention",
            "@someone can you help?",
            "@dev-team please review",
        ]

        for content in mention_content:
            warnings = validate_reply_content_warnings(content)
            assert len(warnings) == 1
            assert "mention users" in warnings[0]

    def test_no_mention_warning_for_mention_in_middle(self):
        """Test that mentions in the middle don't trigger warning."""
        non_mention_content = [
            "This reply mentions @user in the middle",
            "Contact support at support@company.com",
            "The email address is user@example.com",
        ]

        for content in non_mention_content:
            warnings = validate_reply_content_warnings(content)
            mention_warnings = [w for w in warnings if "mention" in w]
            assert len(mention_warnings) == 0

    def test_repetitive_content_warning(self):
        """Test repetitive content warning detection."""
        repetitive_content = [
            "aaaaaaaaaaaaaaaa",  # Same character repeated
            "abababababababab",  # Same pattern repeated
            "xxxxxxxxxxxxxxxxxxx",  # Long repetition
        ]

        for content in repetitive_content:
            warnings = validate_reply_content_warnings(content)
            repetitive_warnings = [w for w in warnings if "repetitive" in w]
            assert len(repetitive_warnings) == 1

    def test_no_repetitive_warning_for_short_content(self):
        """Test that short content doesn't trigger repetitive warning."""
        short_content = [
            "aaaaaaa",  # Short repetition
            "abcdef",  # Normal short content
        ]

        for content in short_content:
            warnings = validate_reply_content_warnings(content)
            repetitive_warnings = [w for w in warnings if "repetitive" in w]
            assert len(repetitive_warnings) == 0

    def test_all_caps_warning(self):
        """Test all caps warning detection."""
        all_caps_content = [
            "THIS IS ALL CAPS CONTENT",
            "WHY ARE YOU SHOUTING?",
            "PLEASE FIX THIS IMMEDIATELY!",
        ]

        for content in all_caps_content:
            warnings = validate_reply_content_warnings(content)
            caps_warnings = [w for w in warnings if "ALL CAPS" in w]
            assert len(caps_warnings) == 1

    def test_no_all_caps_warning_for_short_content(self):
        """Test that short all caps content doesn't trigger warning."""
        short_caps_content = [
            "OK",
            "YES",
            "NO",
            "API",
            "HTTP",
        ]

        for content in short_caps_content:
            warnings = validate_reply_content_warnings(content)
            caps_warnings = [w for w in warnings if "ALL CAPS" in w]
            assert len(caps_warnings) == 0

    def test_excessive_punctuation_warning(self):
        """Test excessive punctuation warning detection."""
        excessive_punctuation_content = [
            "What?!?!?! Why?!?!?!",  # Excessive exclamation and question marks
            "This is crazy!!!!!!",  # Too many exclamation marks
            "Are you sure??????",  # Too many question marks
        ]

        for content in excessive_punctuation_content:
            warnings = validate_reply_content_warnings(content)
            punct_warnings = [w for w in warnings if "excessive punctuation" in w]
            assert len(punct_warnings) == 1

    def test_no_excessive_punctuation_warning_for_normal_use(self):
        """Test that normal punctuation doesn't trigger warning."""
        normal_punctuation_content = [
            "What? Why!",  # Normal use
            "This is great!",  # Single exclamation
            "Are you sure?",  # Single question mark
            "Really?! That's amazing!",  # Mixed but reasonable
        ]

        for content in normal_punctuation_content:
            warnings = validate_reply_content_warnings(content)
            punct_warnings = [w for w in warnings if "excessive punctuation" in w]
            assert len(punct_warnings) == 0

    def test_multiple_warnings(self):
        """Test content that triggers multiple warnings."""
        problematic_content = "@USER WHAT?!?!?! WHY?!?!?!"

        warnings = validate_reply_content_warnings(problematic_content)

        # Should have mention, all caps, and excessive punctuation warnings
        assert len(warnings) == 3

        warning_text = " ".join(warnings)
        assert "mention users" in warning_text
        assert "ALL CAPS" in warning_text
        assert "excessive punctuation" in warning_text

    def test_warning_combinations(self):
        """Test various combinations of warnings."""
        test_cases = [
            ("@USER THIS IS CAPS", ["mention", "ALL CAPS"]),
            ("@user !!!!!!", ["mention", "excessive punctuation"]),
            ("AAAAAAAAAAAAAAAA", ["repetitive", "ALL CAPS"]),
            ("THIS IS CAPS!!!!!!", ["ALL CAPS", "excessive punctuation"]),
            ("aaaaaaaaaaaaa!!!!!!", ["repetitive", "excessive punctuation"]),
        ]

        for content, expected_warning_types in test_cases:
            warnings = validate_reply_content_warnings(content)
            warning_text = " ".join(warnings).lower()

            assert len(warnings) == len(expected_warning_types)
            for expected_type in expected_warning_types:
                assert expected_type.lower() in warning_text

    def test_edge_cases_for_warnings(self):
        """Test edge cases for warning detection."""
        edge_cases = [
            ("CAPS", 0),  # Short caps, shouldn't warn
            ("!", 0),  # Single punctuation
            ("aaaaaaaaa", 0),  # Just under the repetition threshold
            ("x@y", 0),  # @ symbol in middle, not a mention
        ]

        for content, expected_warning_count in edge_cases:
            warnings = validate_reply_content_warnings(content)
            assert len(warnings) == expected_warning_count


class TestCompositeValidationFunctions:
    """Test composite validation functions for commands."""

    def test_validate_fetch_command_args_valid(self):
        """Test valid fetch command arguments."""
        result = validate_fetch_command_args(
            pr_number=123, pretty=True, resolved=False, limit=50
        )

        expected = {"pr_number": 123, "pretty": True, "resolved": False, "limit": 50}
        assert result == expected

    def test_validate_fetch_command_args_string_pr_number(self):
        """Test fetch command args with string PR number."""
        result = validate_fetch_command_args(
            pr_number="456", pretty=False, resolved=True, limit="25"
        )

        expected = {"pr_number": 456, "pretty": False, "resolved": True, "limit": 25}
        assert result == expected

    def test_validate_fetch_command_args_defaults(self):
        """Test fetch command args with default values."""
        result = validate_fetch_command_args(pr_number=123)

        expected = {"pr_number": 123, "pretty": False, "resolved": False, "limit": 100}
        assert result == expected

    def test_validate_fetch_command_args_invalid_pr_number(self):
        """Test fetch command args with invalid PR number."""
        with pytest.raises(ValidationError):
            validate_fetch_command_args(pr_number=-1)

    def test_validate_fetch_command_args_invalid_limit(self):
        """Test fetch command args with invalid limit."""
        with pytest.raises(ValidationError):
            validate_fetch_command_args(pr_number=123, limit=0)

    def test_validate_reply_command_args_valid(self):
        """Test valid reply command arguments."""
        result = validate_reply_command_args(
            comment_id="123456789",
            body="This is a valid reply",
            pretty=True,
            verbose=False,
        )

        expected = {
            "comment_id": "123456789",
            "body": "This is a valid reply",
            "pretty": True,
            "verbose": False,
        }
        assert result == expected

    def test_validate_reply_command_args_node_id(self):
        """Test reply command args with GitHub node ID."""
        result = validate_reply_command_args(
            comment_id="IC_kwDOABcD12MAAAABcDE3fg",
            body="Valid reply to node ID",
            pretty=False,
            verbose=True,
        )

        expected = {
            "comment_id": "IC_kwDOABcD12MAAAABcDE3fg",
            "body": "Valid reply to node ID",
            "pretty": False,
            "verbose": True,
        }
        assert result == expected

    def test_validate_reply_command_args_defaults(self):
        """Test reply command args with default values."""
        result = validate_reply_command_args(comment_id="123456789", body="Valid reply")

        expected = {
            "comment_id": "123456789",
            "body": "Valid reply",
            "pretty": False,
            "verbose": False,
        }
        assert result == expected

    def test_validate_reply_command_args_allows_thread_ids(self):
        """Test that reply command args allows thread IDs."""
        result = validate_reply_command_args(
            comment_id="PRT_kwDOABcD12MAAAABcDE3fg", body="Reply to thread"
        )

        assert result["comment_id"] == "PRT_kwDOABcD12MAAAABcDE3fg"

    def test_validate_reply_command_args_invalid_comment_id(self):
        """Test reply command args with invalid comment ID."""
        with pytest.raises(ValidationError):
            validate_reply_command_args(comment_id=None, body="Valid reply")

    def test_validate_reply_command_args_invalid_body(self):
        """Test reply command args with invalid body."""
        with pytest.raises(ValidationError):
            validate_reply_command_args(comment_id="123456789", body="ab")  # Too short


class TestResolveOptions:
    """Test ResolveOptions dataclass."""

    def test_resolve_options_defaults(self):
        """Test ResolveOptions default values."""
        options = ResolveOptions()

        assert options.bulk_resolve is False
        assert options.undo is False
        assert options.yes is False
        assert options.pretty is False
        assert options.limit == 100

    def test_resolve_options_custom_values(self):
        """Test ResolveOptions with custom values."""
        options = ResolveOptions(
            bulk_resolve=True, undo=True, yes=True, pretty=True, limit=50
        )

        assert options.bulk_resolve is True
        assert options.undo is True
        assert options.yes is True
        assert options.pretty is True
        assert options.limit == 50

    def test_resolve_options_partial_values(self):
        """Test ResolveOptions with partial custom values."""
        options = ResolveOptions(bulk_resolve=True, limit=25)

        assert options.bulk_resolve is True
        assert options.undo is False  # Default
        assert options.yes is False  # Default
        assert options.pretty is False  # Default
        assert options.limit == 25


class TestValidateResolveCommandArgs:
    """Test resolve command argument validation."""

    def test_validate_resolve_command_args_single_thread(self):
        """Test resolve command args for single thread resolution."""
        options = ResolveOptions(
            bulk_resolve=False, undo=False, yes=False, pretty=True, limit=100
        )

        result = validate_resolve_command_args(
            thread_id="123456789", pr_number=None, options=options
        )

        expected = {
            "thread_id": "123456789",
            "bulk_resolve": False,
            "pr_number": None,
            "undo": False,
            "yes": False,
            "pretty": True,
            "limit": 100,
        }
        assert result == expected

    def test_validate_resolve_command_args_bulk_operation(self):
        """Test resolve command args for bulk operation."""
        options = ResolveOptions(
            bulk_resolve=True, undo=False, yes=True, pretty=False, limit=50
        )

        result = validate_resolve_command_args(
            thread_id=None, pr_number=123, options=options
        )

        expected = {
            "thread_id": None,
            "bulk_resolve": True,
            "pr_number": 123,
            "undo": False,
            "yes": True,
            "pretty": False,
            "limit": 50,
        }
        assert result == expected

    def test_validate_resolve_command_args_default_options(self):
        """Test resolve command with default options (None)."""
        result = validate_resolve_command_args(
            thread_id="123456789",
            pr_number=None,
            options=None,  # Should use default ResolveOptions
        )

        expected = {
            "thread_id": "123456789",
            "bulk_resolve": False,
            "pr_number": None,
            "undo": False,
            "yes": False,
            "pretty": False,
            "limit": 100,
        }
        assert result == expected

    def test_validate_resolve_command_args_bulk_with_thread_id_conflict(self):
        """Test resolve command args with bulk_resolve and thread_id conflict."""
        options = ResolveOptions(bulk_resolve=True)

        with pytest.raises(ValidationError) as exc_info:
            validate_resolve_command_args(
                thread_id="123456789", pr_number=123, options=options
            )

        assert "Cannot use bulk resolve and thread ID together" in str(exc_info.value)

    def test_validate_resolve_command_args_neither_bulk_nor_thread_id(self):
        """Test resolve command args without bulk_resolve or thread_id."""
        options = ResolveOptions(bulk_resolve=False)

        with pytest.raises(ValidationError) as exc_info:
            validate_resolve_command_args(
                thread_id=None, pr_number=None, options=options
            )

        assert "Must specify either thread ID or bulk resolve" in str(exc_info.value)

    def test_validate_resolve_command_args_bulk_without_pr_number(self):
        """Test resolve command args with bulk_resolve but no PR number."""
        options = ResolveOptions(bulk_resolve=True)

        with pytest.raises(ValidationError) as exc_info:
            validate_resolve_command_args(
                thread_id=None, pr_number=None, options=options
            )

        assert "PR number is required when using bulk resolve" in str(exc_info.value)

    def test_validate_resolve_command_args_invalid_thread_id(self):
        """Test resolve command args with invalid thread ID."""
        options = ResolveOptions(bulk_resolve=False)

        with pytest.raises(ValidationError):
            validate_resolve_command_args(
                thread_id="INVALID_ID", pr_number=None, options=options
            )

    def test_validate_resolve_command_args_invalid_pr_number(self):
        """Test resolve command args with invalid PR number."""
        options = ResolveOptions(bulk_resolve=True)

        with pytest.raises(ValidationError):
            validate_resolve_command_args(thread_id=None, pr_number=-1, options=options)

    def test_validate_resolve_command_args_invalid_limit(self):
        """Test resolve command args with invalid limit."""
        options = ResolveOptions(limit=0)

        with pytest.raises(ValidationError):
            validate_resolve_command_args(
                thread_id="123456789", pr_number=None, options=options
            )

    def test_validate_resolve_command_args_string_limit_in_options(self):
        """Test resolve command args with string limit in options."""
        options = ResolveOptions(limit="50")

        result = validate_resolve_command_args(
            thread_id="123456789", pr_number=None, options=options
        )

        assert result["limit"] == 50


class TestValidationErrorHandling:
    """Test validation error handling and messages."""

    def test_validation_error_properties_from_pr_number(self):
        """Test ValidationError properties from PR number validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-1)

        error = exc_info.value
        assert error.field_name == "PR number"
        assert error.invalid_value == -1
        assert error.expected_format == "positive integer"
        assert "must be positive" in error.message

    def test_validation_error_properties_from_reply_body(self):
        """Test ValidationError properties from reply body validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("ab")

        error = exc_info.value
        assert error.field_name == "Reply body"
        assert error.invalid_value == "ab"
        assert "must be at least 3 characters" in error.message

    def test_custom_field_names_in_errors(self):
        """Test custom field names in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-1, field_name="Custom PR Field")

        error = exc_info.value
        assert error.field_name == "Custom PR Field"
        assert "Custom PR Field must be positive" in error.message

    def test_error_context_information_comprehensive(self):
        """Test that validation errors include comprehensive context."""
        test_cases = [
            (lambda: validate_pr_number(None), ["cannot be None"], "PR number"),
            (lambda: validate_comment_id(""), ["cannot be empty"], "Comment ID"),
            (lambda: validate_limit(-1), ["must be at least 1"], "Limit"),
            (lambda: validate_email("invalid"), ["Invalid email format"], "Email"),
            (lambda: validate_url("not-a-url"), ["Invalid url format"], "URL"),
        ]

        for test_func, expected_message_strings, expected_field_name in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                test_func()

            error = exc_info.value
            error_message = str(error)
            for expected_string in expected_message_strings:
                assert expected_string in error_message
            assert error.field_name == expected_field_name

    def test_validation_error_field_name_consistency(self):
        """Test that field names are consistent across similar validations."""
        field_name_tests = [
            (validate_pr_number, None, "PR number"),
            (validate_comment_id, None, "Comment ID"),
            (validate_thread_id, None, "Thread ID"),
            (validate_reply_body, None, "Reply body"),
            (validate_limit, None, "Limit"),
            (validate_email, None, "Email"),
            (validate_url, None, "URL"),
            (validate_username, None, "Username"),
        ]

        for validator_func, invalid_value, expected_field_name in field_name_tests:
            with pytest.raises(ValidationError) as exc_info:
                validator_func(invalid_value)

            error = exc_info.value
            assert error.field_name == expected_field_name

    def test_validation_error_expected_format_specificity(self):
        """Test that expected format messages are specific and helpful."""
        format_tests = [
            (lambda: validate_pr_number("abc"), "positive integer"),
            (
                lambda: validate_limit("abc", min_value=1, max_value=100),
                "integer between 1 and 100",
            ),
            (lambda: validate_email("invalid"), "valid email address"),
            (lambda: validate_url("invalid"), "valid HTTP or HTTPS URL"),
            (lambda: validate_username("invalid..name"), "valid GitHub username"),
        ]

        for test_func, expected_format_substring in format_tests:
            with pytest.raises(ValidationError) as exc_info:
                test_func()

            error = exc_info.value
            assert expected_format_substring in error.expected_format


class TestValidationIntegration:
    """Test validation integration and comprehensive scenarios."""

    def test_all_validators_handle_none_consistently(self):
        """Test that all validators handle None values consistently."""
        validators_without_allow_none = [
            validate_comment_id,
            validate_thread_id,
            validate_reply_body,
            validate_limit,
            validate_datetime_string,
            validate_email,
            validate_url,
            validate_username,
            validate_non_empty_string,
            validate_choice,
            validate_dict_keys,
        ]

        for validator in validators_without_allow_none:
            with pytest.raises(ValidationError) as exc_info:
                if validator == validate_choice:
                    validator(None, ["option1", "option2"])
                elif validator == validate_dict_keys:
                    validator(None, ["key1"])
                else:
                    validator(None)

            assert "cannot be None" in str(exc_info.value)

    def test_all_validators_have_consistent_error_structure(self):
        """Test that all validators produce consistent error structures."""
        test_cases = [
            (validate_pr_number, None),
            (validate_comment_id, None),
            (validate_thread_id, None),
            (validate_reply_body, None),
            (validate_limit, None),
            (validate_datetime_string, None),
            (validate_email, None),
            (validate_url, None),
            (validate_username, None),
            (validate_non_empty_string, None),
            (validate_boolean_flag, None),
        ]

        for validator, invalid_value in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                validator(invalid_value)

            error = exc_info.value
            assert hasattr(error, "field_name")
            assert hasattr(error, "invalid_value")
            assert hasattr(error, "expected_format")
            assert hasattr(error, "message")
            assert error.field_name is not None
            assert error.message is not None

    def test_validation_with_realistic_github_data(self):
        """Test validation with realistic GitHub data structures."""
        # Test realistic PR numbers
        realistic_pr_numbers = [1, 42, 1337, 9999, 123456]
        for pr_num in realistic_pr_numbers:
            assert validate_pr_number(pr_num) == pr_num

        # Test realistic GitHub node IDs
        realistic_comment_ids = [
            "IC_kwDOABcD12MAAAABcDE3fg",
            "PRRC_kwDOBGHtJMAAAAB1234567",
            "RP_kwDOABcD12MAAAABcDE3fh",
        ]
        for comment_id in realistic_comment_ids:
            assert validate_comment_id(comment_id) == comment_id

        # Test realistic thread IDs
        realistic_thread_ids = [
            "PRT_kwDOABcD12MAAAABcDE3fg",
            "PRRT_kwDOBGHtJMAAAAB1234567",
            "RT_kwDOABcD12MAAAABcDE3fh",
        ]
        for thread_id in realistic_thread_ids:
            assert validate_thread_id(thread_id) == thread_id

    def test_validation_performance_with_large_inputs(self):
        """Test validation performance with large inputs."""
        # Test with maximum length reply body
        large_reply = "A" * MAX_REPLY_BODY_LENGTH
        assert validate_reply_body(large_reply) == large_reply

        # Test with large dictionary
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        required_keys = [f"key_{i}" for i in range(50)]
        result = validate_dict_keys(large_dict, required_keys)
        assert len(result) == 100

        # Test with large choice list
        large_choices = [f"option_{i}" for i in range(1000)]
        assert validate_choice("option_500", large_choices) == "option_500"

    def test_validation_thread_safety_simulation(self):
        """Test validation functions with concurrent-like usage patterns."""
        # Simulate concurrent validation of different data types
        test_data = [
            (validate_pr_number, 123, 123),
            (validate_comment_id, "IC_test", "IC_test"),
            (validate_thread_id, "PRT_test", "PRT_test"),
            (validate_reply_body, "Valid reply", "Valid reply"),
            (validate_limit, 50, 50),
            (validate_email, "test@example.com", "test@example.com"),
            (validate_url, "https://example.com", "https://example.com"),
            (validate_username, "testuser", "testuser"),
        ]

        # Run multiple validation cycles
        for _ in range(10):
            for validator, input_val, expected in test_data:
                if validator in [validate_comment_id, validate_thread_id]:
                    # Skip these as they require proper node ID validation
                    continue
                result = validator(input_val)
                assert result == expected
