"""Tests for validation module."""

from datetime import datetime

import pytest

from toady.exceptions import ValidationError
from toady.validation import (
    check_reply_content_warnings,
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
    validate_resolve_command_args,
    validate_thread_id,
    validate_url,
    validate_username,
)


class TestValidatePRNumber:
    """Test PR number validation."""

    def test_valid_pr_numbers(self):
        """Test valid PR numbers."""
        assert validate_pr_number(1) == 1
        assert validate_pr_number(123) == 123
        assert validate_pr_number(999999) == 999999
        assert validate_pr_number("1") == 1
        assert validate_pr_number("123") == 123
        assert validate_pr_number("999999") == 999999
        assert validate_pr_number("  123  ") == 123

    def test_none_values(self):
        """Test None handling."""
        assert validate_pr_number(None, allow_none=True) is None

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(None)
        assert "cannot be None" in str(exc_info.value)

    def test_invalid_pr_numbers(self):
        """Test invalid PR numbers."""
        # Zero and negative numbers
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(0)
        assert "must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-1)
        assert "must be positive" in str(exc_info.value)

        # Too large
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(1000000)
        assert "unreasonably large" in str(exc_info.value)

        # Non-numeric strings
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number("abc")
        assert "must be numeric" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number("")
        assert "cannot be empty" in str(exc_info.value)

        # Float values
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(123.45)
        assert "must be an integer" in str(exc_info.value)


class TestValidateCommentID:
    """Test comment ID validation."""

    def test_valid_numeric_ids(self):
        """Test valid numeric comment IDs."""
        assert validate_comment_id("123456789") == "123456789"
        assert validate_comment_id(123456789) == "123456789"

    def test_valid_node_ids(self):
        """Test valid GitHub node IDs."""
        assert (
            validate_comment_id("IC_kwDOABcD12MAAAABcDE3fg")
            == "IC_kwDOABcD12MAAAABcDE3fg"
        )
        assert (
            validate_comment_id("PRRC_kwDOABcD12MAAAABcDE3fg")
            == "PRRC_kwDOABcD12MAAAABcDE3fg"
        )
        assert (
            validate_comment_id("RP_kwDOABcD12MAAAABcDE3fg")
            == "RP_kwDOABcD12MAAAABcDE3fg"
        )

    def test_thread_ids_with_flag(self):
        """Test accepting thread IDs when allowed."""
        # Should accept thread IDs when allow_thread_ids=True
        assert (
            validate_comment_id("PRT_kwDOABcD12MAAAABcDE3fg", allow_thread_ids=True)
            == "PRT_kwDOABcD12MAAAABcDE3fg"
        )
        assert (
            validate_comment_id("PRRT_kwDOABcD12MAAAABcDE3fg", allow_thread_ids=True)
            == "PRRT_kwDOABcD12MAAAABcDE3fg"
        )

        # Should reject thread IDs when allow_thread_ids=False (default)
        with pytest.raises(ValidationError):
            validate_comment_id("PRT_kwDOABcD12MAAAABcDE3fg")

    def test_invalid_comment_ids(self):
        """Test invalid comment IDs."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_comment_id(None)
        assert "cannot be None" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_comment_id("")
        assert "cannot be empty" in str(exc_info.value)

        # Invalid node ID format
        with pytest.raises(ValidationError):
            validate_comment_id("INVALID_kwDOABcD12MAAAABcDE3fg")


class TestValidateThreadID:
    """Test thread ID validation."""

    def test_valid_thread_ids(self):
        """Test valid thread IDs."""
        assert validate_thread_id("123456789") == "123456789"
        assert validate_thread_id(123456789) == "123456789"
        assert (
            validate_thread_id("PRT_kwDOABcD12MAAAABcDE3fg")
            == "PRT_kwDOABcD12MAAAABcDE3fg"
        )
        assert (
            validate_thread_id("PRRT_kwDOABcD12MAAAABcDE3fg")
            == "PRRT_kwDOABcD12MAAAABcDE3fg"
        )
        assert (
            validate_thread_id("RT_kwDOABcD12MAAAABcDE3fg")
            == "RT_kwDOABcD12MAAAABcDE3fg"
        )

    def test_invalid_thread_ids(self):
        """Test invalid thread IDs."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_thread_id(None)
        assert "cannot be None" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_thread_id("")
        assert "cannot be empty" in str(exc_info.value)

        # Comment ID (not a thread ID)
        with pytest.raises(ValidationError):
            validate_thread_id("IC_kwDOABcD12MAAAABcDE3fg")


class TestValidateReplyBody:
    """Test reply body validation."""

    def test_valid_reply_bodies(self):
        """Test valid reply bodies."""
        assert validate_reply_body("This is a valid reply") == "This is a valid reply"
        assert (
            validate_reply_body("  This is a valid reply  ") == "This is a valid reply"
        )
        assert validate_reply_body("Short") == "Short"
        assert validate_reply_body("A" * 65536) == "A" * 65536

    def test_invalid_reply_bodies(self):
        """Test invalid reply bodies."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body(None)
        assert "cannot be None" in str(exc_info.value)

        # Non-string
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body(123)
        assert "must be a string" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("")
        assert "cannot be empty" in str(exc_info.value)

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("ab")
        assert "must be at least 3 characters" in str(exc_info.value)

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("A" * 65537)
        assert "cannot exceed 65,536 characters" in str(exc_info.value)

        # Placeholder patterns (only test ones that pass length check)
        for placeholder in ["...", "????", "test"]:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(placeholder)
            assert "placeholder text" in str(exc_info.value)

        # Test short placeholder patterns separately
        for placeholder in [".", ".."]:
            with pytest.raises(ValidationError) as exc_info:
                validate_reply_body(placeholder)
            assert "must be at least 3 characters" in str(exc_info.value)

        # Not enough meaningful content
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("a  \n\t  b")  # Has 2 non-whitespace chars, needs 3
        assert "non-whitespace characters" in str(exc_info.value)


class TestValidateLimit:
    """Test limit validation."""

    def test_valid_limits(self):
        """Test valid limit values."""
        assert validate_limit(1) == 1
        assert validate_limit(100) == 100
        assert validate_limit(1000) == 1000
        assert validate_limit("1") == 1
        assert validate_limit("100") == 100
        assert validate_limit("  100  ") == 100

    def test_custom_ranges(self):
        """Test custom min/max ranges."""
        assert validate_limit(5, min_value=5, max_value=10) == 5
        assert validate_limit(10, min_value=5, max_value=10) == 10

    def test_invalid_limits(self):
        """Test invalid limit values."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(None)
        assert "cannot be None" in str(exc_info.value)

        # Zero and negative
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(0)
        assert "must be at least 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_limit(-1)
        assert "must be at least 1" in str(exc_info.value)

        # Too large
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(1001)
        assert "cannot exceed 1000" in str(exc_info.value)

        # Non-numeric strings
        with pytest.raises(ValidationError) as exc_info:
            validate_limit("abc")
        assert "must be numeric" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_limit("")
        assert "cannot be empty" in str(exc_info.value)


class TestValidateDatetimeString:
    """Test datetime string validation."""

    def test_valid_datetime_strings(self):
        """Test valid datetime strings."""
        result = validate_datetime_string("2024-01-01T12:00:00")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

        result = validate_datetime_string("2024-01-01T12:00:00.123456")
        assert isinstance(result, datetime)

    def test_invalid_datetime_strings(self):
        """Test invalid datetime strings."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string(None)
        assert "cannot be None" in str(exc_info.value)

        # Non-string
        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string(123)
        assert "must be a string" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string("")
        assert "cannot be empty" in str(exc_info.value)

        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            validate_datetime_string("not-a-date")
        assert "Invalid date format" in str(exc_info.value)


class TestValidateEmail:
    """Test email validation."""

    def test_valid_emails(self):
        """Test valid email addresses."""
        assert validate_email("user@example.com") == "user@example.com"
        assert (
            validate_email("test.email+tag@domain.co.uk")
            == "test.email+tag@domain.co.uk"
        )
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_invalid_emails(self):
        """Test invalid email addresses."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_email(None)
        assert "cannot be None" in str(exc_info.value)

        # Non-string
        with pytest.raises(ValidationError) as exc_info:
            validate_email(123)
        assert "must be a string" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_email("")
        assert "cannot be empty" in str(exc_info.value)

        # Invalid formats
        for invalid_email in ["invalid", "@example.com", "user@", "user.example.com"]:
            with pytest.raises(ValidationError) as exc_info:
                validate_email(invalid_email)
            assert "Invalid email format" in str(exc_info.value)


class TestValidateURL:
    """Test URL validation."""

    def test_valid_urls(self):
        """Test valid URLs."""
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://example.com") == "http://example.com"
        assert (
            validate_url("https://example.com/path?query=1#fragment")
            == "https://example.com/path?query=1#fragment"
        )
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_invalid_urls(self):
        """Test invalid URLs."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_url(None)
        assert "cannot be None" in str(exc_info.value)

        # Non-string
        with pytest.raises(ValidationError) as exc_info:
            validate_url(123)
        assert "must be a string" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_url("")
        assert "cannot be empty" in str(exc_info.value)

        # Invalid formats
        for invalid_url in ["ftp://example.com", "not-a-url", "example.com"]:
            with pytest.raises(ValidationError) as exc_info:
                validate_url(invalid_url)
            assert "Invalid url format" in str(exc_info.value)


class TestValidateUsername:
    """Test username validation."""

    def test_valid_usernames(self):
        """Test valid GitHub usernames."""
        assert validate_username("user") == "user"
        assert validate_username("user-name") == "user-name"
        assert validate_username("user123") == "user123"
        assert validate_username("123user") == "123user"
        assert validate_username("a" * 39) == "a" * 39
        assert validate_username("  user  ") == "user"

    def test_invalid_usernames(self):
        """Test invalid GitHub usernames."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_username(None)
        assert "cannot be None" in str(exc_info.value)

        # Non-string
        with pytest.raises(ValidationError) as exc_info:
            validate_username(123)
        assert "must be a string" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_username("")
        assert "cannot be empty" in str(exc_info.value)

        # Invalid formats
        for invalid_username in ["-user", "user-", "user..name", "a" * 40]:
            with pytest.raises(ValidationError) as exc_info:
                validate_username(invalid_username)
            assert "Invalid username format" in str(exc_info.value)


class TestValidateNonEmptyString:
    """Test non-empty string validation."""

    def test_valid_strings(self):
        """Test valid non-empty strings."""
        assert validate_non_empty_string("hello") == "hello"
        assert validate_non_empty_string("  hello  ") == "hello"
        assert validate_non_empty_string("a") == "a"

    def test_custom_length_constraints(self):
        """Test custom length constraints."""
        assert validate_non_empty_string("hello", min_length=5) == "hello"
        assert validate_non_empty_string("hello", max_length=10) == "hello"
        assert (
            validate_non_empty_string("hello", min_length=3, max_length=10) == "hello"
        )

    def test_invalid_strings(self):
        """Test invalid strings."""
        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string(None)
        assert "cannot be None" in str(exc_info.value)

        # Non-string
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string(123)
        assert "must be a string" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("")
        assert "cannot be empty" in str(exc_info.value)

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("ab", min_length=3)
        assert "must be at least 3 characters" in str(exc_info.value)

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("toolong", max_length=5)
        assert "cannot exceed 5 characters" in str(exc_info.value)


class TestValidateBooleanFlag:
    """Test boolean flag validation."""

    def test_valid_booleans(self):
        """Test valid boolean values."""
        assert validate_boolean_flag(True) is True
        assert validate_boolean_flag(False) is False
        assert validate_boolean_flag("true") is True
        assert validate_boolean_flag("false") is False
        assert validate_boolean_flag("1") is True
        assert validate_boolean_flag("0") is False
        assert validate_boolean_flag("yes") is True
        assert validate_boolean_flag("no") is False
        assert validate_boolean_flag("on") is True
        assert validate_boolean_flag("off") is False

    def test_none_handling(self):
        """Test None handling."""
        assert validate_boolean_flag(None, allow_none=True) is False

        with pytest.raises(ValidationError) as exc_info:
            validate_boolean_flag(None)
        assert "cannot be None" in str(exc_info.value)

    def test_invalid_booleans(self):
        """Test invalid boolean values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_boolean_flag("invalid")
        assert "must be a boolean value" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_boolean_flag(123)
        assert "must be a boolean value" in str(exc_info.value)


class TestValidateChoice:
    """Test choice validation."""

    def test_valid_choices(self):
        """Test valid choice values."""
        choices = ["option1", "option2", "option3"]
        assert validate_choice("option1", choices) == "option1"
        assert validate_choice("option2", choices) == "option2"

    def test_case_insensitive_matching(self):
        """Test case-insensitive choice matching."""
        choices = ["Option1", "Option2"]
        assert validate_choice("option1", choices, case_sensitive=False) == "Option1"
        assert validate_choice("OPTION2", choices, case_sensitive=False) == "Option2"

    def test_invalid_choices(self):
        """Test invalid choice values."""
        choices = ["option1", "option2"]

        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_choice(None, choices)
        assert "cannot be None" in str(exc_info.value)

        # Invalid choice
        with pytest.raises(ValidationError) as exc_info:
            validate_choice("invalid", choices)
        assert "must be one of the allowed values" in str(exc_info.value)


class TestValidateDictKeys:
    """Test dictionary key validation."""

    def test_valid_dictionaries(self):
        """Test valid dictionaries."""
        data = {"key1": "value1", "key2": "value2"}
        required_keys = ["key1", "key2"]
        result = validate_dict_keys(data, required_keys)
        assert result == data

    def test_optional_keys(self):
        """Test dictionaries with optional keys."""
        data = {"key1": "value1", "key2": "value2", "optional": "value"}
        required_keys = ["key1", "key2"]
        optional_keys = ["optional"]
        result = validate_dict_keys(data, required_keys, optional_keys)
        assert result == data

    def test_invalid_dictionaries(self):
        """Test invalid dictionaries."""
        required_keys = ["key1", "key2"]

        # None value
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(None, required_keys)
        assert "cannot be None" in str(exc_info.value)

        # Non-dictionary
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys("not-a-dict", required_keys)
        assert "must be a dictionary" in str(exc_info.value)

        # Missing required keys
        data = {"key1": "value1"}  # missing key2
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys)
        assert "Missing required keys" in str(exc_info.value)

        # Unexpected keys
        data = {"key1": "value1", "key2": "value2", "unexpected": "value"}
        optional_keys = []
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys, optional_keys)
        assert "Unexpected keys" in str(exc_info.value)


class TestCheckReplyContentWarnings:
    """Test reply content warning checks."""

    def test_no_warnings(self):
        """Test content with no warnings."""
        warnings = check_reply_content_warnings("This is a normal reply")
        assert warnings == []

    def test_mention_warning(self):
        """Test mention warning."""
        warnings = check_reply_content_warnings("@user this is a mention")
        assert len(warnings) == 1
        assert "mention users" in warnings[0]

    def test_repetitive_content_warning(self):
        """Test repetitive content warning."""
        warnings = check_reply_content_warnings("aaaaaaaaaaaaaaaa")
        assert len(warnings) == 1
        assert "repetitive content" in warnings[0]

    def test_all_caps_warning(self):
        """Test all caps warning."""
        warnings = check_reply_content_warnings("THIS IS ALL CAPS CONTENT")
        assert len(warnings) == 1
        assert "ALL CAPS" in warnings[0]

    def test_excessive_punctuation_warning(self):
        """Test excessive punctuation warning."""
        warnings = check_reply_content_warnings("What?!?!?! Why?!?!?!")
        assert len(warnings) == 1
        assert "excessive punctuation" in warnings[0]

    def test_multiple_warnings(self):
        """Test content with multiple warnings."""
        warnings = check_reply_content_warnings("@USER WHAT?!?!?! WHY?!?!?!")
        assert len(warnings) == 3  # mention, all caps, excessive punctuation


class TestCompositeValidationFunctions:
    """Test composite validation functions for commands."""

    def test_validate_fetch_command_args(self):
        """Test fetch command argument validation."""
        result = validate_fetch_command_args(
            pr_number=123, pretty=True, resolved=False, limit=50
        )
        expected = {"pr_number": 123, "pretty": True, "resolved": False, "limit": 50}
        assert result == expected

    def test_validate_reply_command_args(self):
        """Test reply command argument validation."""
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

    def test_validate_resolve_command_args_single(self):
        """Test resolve command argument validation for single thread."""
        result = validate_resolve_command_args(
            thread_id="123456789",
            bulk_resolve=False,
            pr_number=None,
            undo=False,
            yes=False,
            pretty=True,
            limit=100,
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

    def test_validate_resolve_command_args_bulk(self):
        """Test resolve command argument validation for bulk operation."""
        result = validate_resolve_command_args(
            thread_id=None,
            bulk_resolve=True,
            pr_number=123,
            undo=False,
            yes=True,
            pretty=False,
            limit=50,
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

    def test_validate_resolve_command_args_conflicts(self):
        """Test resolve command argument validation with conflicts."""
        # Test bulk_resolve with thread_id
        with pytest.raises(ValidationError) as exc_info:
            validate_resolve_command_args(
                thread_id="123456789", bulk_resolve=True, pr_number=123
            )
        assert "Cannot use bulk resolve and thread ID together" in str(exc_info.value)

        # Test neither bulk_resolve nor thread_id
        with pytest.raises(ValidationError) as exc_info:
            validate_resolve_command_args(thread_id=None, bulk_resolve=False)
        assert "Must specify either thread ID or bulk resolve" in str(exc_info.value)

        # Test bulk_resolve without pr_number
        with pytest.raises(ValidationError) as exc_info:
            validate_resolve_command_args(
                thread_id=None, bulk_resolve=True, pr_number=None
            )
        assert "PR number is required when using bulk resolve" in str(exc_info.value)


class TestValidationErrorHandling:
    """Test validation error handling and messages."""

    def test_validation_error_properties(self):
        """Test ValidationError properties."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-1)

        error = exc_info.value
        assert error.field_name == "PR number"
        assert error.invalid_value == -1
        assert error.expected_format == "positive integer"
        assert "must be positive" in error.message

    def test_error_context_information(self):
        """Test that validation errors include helpful context."""
        with pytest.raises(ValidationError) as exc_info:
            validate_reply_body("ab")

        error = exc_info.value
        assert error.field_name == "Reply body"
        assert error.invalid_value == "ab"
        assert "must be at least 3 characters" in str(error)

    def test_custom_field_names(self):
        """Test custom field names in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pr_number(-1, field_name="Custom PR Field")

        error = exc_info.value
        assert error.field_name == "Custom PR Field"
        assert "Custom PR Field must be positive" in error.message
