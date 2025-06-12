"""Comprehensive validation functions for all input types in toady CLI.

This module provides centralized validation for all user inputs, command-line arguments,
configuration parameters, and data types used throughout the application.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..exceptions import ValidationError, create_validation_error
from ..utils import MAX_PR_NUMBER
from .node_id_validation import (
    create_comment_validator,
    create_thread_validator,
    create_universal_validator,
)

# Constants for validation
MIN_REPLY_BODY_LENGTH = 3
MAX_REPLY_BODY_LENGTH = 65536  # GitHub's limit
MIN_MEANINGFUL_CONTENT_LENGTH = 3
MAX_LIMIT_VALUE = 1000
MIN_LIMIT_VALUE = 1

# Regular expressions for validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
URL_REGEX = re.compile(
    r"^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$"
)
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")

# Placeholder and spam patterns
PLACEHOLDER_PATTERNS = {
    ".",
    "..",
    "...",
    "????",
    "???",
    "!!",
    "!?",
    "test",
    "testing",
    "placeholder",
    "xxx",
    "yyy",
    "zzz",
}


def validate_pr_number(
    pr_number: Union[int, str, None],
    field_name: str = "PR number",
    allow_none: bool = False,
) -> Optional[int]:
    """Validate a pull request number.

    Args:
        pr_number: The PR number to validate (int or string)
        field_name: Name of the field for error messages
        allow_none: Whether to allow None values

    Returns:
        Validated PR number as integer, or None if allow_none=True and input is None

    Raises:
        ValidationError: If validation fails
    """
    if pr_number is None:
        if allow_none:
            return None
        raise create_validation_error(
            field_name=field_name,
            invalid_value=pr_number,
            expected_format="positive integer",
            message=f"{field_name} cannot be None",
        )

    # Convert to int if it's a string
    if isinstance(pr_number, str):
        pr_number = pr_number.strip()
        if not pr_number:
            raise create_validation_error(
                field_name=field_name,
                invalid_value=pr_number,
                expected_format="positive integer",
                message=f"{field_name} cannot be empty",
            )

        if not pr_number.isdigit():
            raise create_validation_error(
                field_name=field_name,
                invalid_value=pr_number,
                expected_format="positive integer",
                message=f"{field_name} must be numeric",
            )

        try:
            pr_number = int(pr_number)
        except ValueError as e:
            raise create_validation_error(
                field_name=field_name,
                invalid_value=pr_number,
                expected_format="positive integer",
                message=f"{field_name} must be a valid integer",
            ) from e

    # Validate range
    if not isinstance(pr_number, int):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=pr_number,
            expected_format="positive integer",
            message=f"{field_name} must be an integer",
        )

    if pr_number <= 0:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=pr_number,
            expected_format="positive integer",
            message=f"{field_name} must be positive",
        )

    if pr_number > MAX_PR_NUMBER:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=pr_number,
            expected_format=f"integer between 1 and {MAX_PR_NUMBER}",
            message=(
                f"{field_name} appears unreasonably large "
                f"(maximum: {MAX_PR_NUMBER:,})"
            ),
        )

    return pr_number


def validate_comment_id(
    comment_id: Union[str, int],
    field_name: str = "Comment ID",
    allow_thread_ids: bool = False,
) -> str:
    """Validate a comment ID (numeric or GitHub node ID).

    Args:
        comment_id: The comment ID to validate
        field_name: Name of the field for error messages
        allow_thread_ids: Whether to also accept thread IDs

    Returns:
        Validated comment ID as string

    Raises:
        ValidationError: If validation fails
    """
    if comment_id is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=comment_id,
            expected_format="numeric ID or GitHub node ID",
            message=f"{field_name} cannot be None",
        )

    # Convert to string and strip
    comment_id_str = str(comment_id).strip()
    if not comment_id_str:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=comment_id,
            expected_format="numeric ID or GitHub node ID",
            message=f"{field_name} cannot be empty",
        )

    try:
        if allow_thread_ids:
            # Accept both comment and thread IDs
            validator = create_universal_validator()
            validator.validate_id(comment_id_str, field_name)
        else:
            # Only accept comment IDs
            validator = create_comment_validator()
            validator.validate_id(comment_id_str, field_name)
    except ValueError as e:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=comment_id,
            expected_format="numeric ID or GitHub node ID",
            message=str(e),
        ) from e

    return comment_id_str


def validate_thread_id(
    thread_id: Union[str, int], field_name: str = "Thread ID"
) -> str:
    """Validate a thread ID (numeric or GitHub node ID).

    Args:
        thread_id: The thread ID to validate
        field_name: Name of the field for error messages

    Returns:
        Validated thread ID as string

    Raises:
        ValidationError: If validation fails
    """
    if thread_id is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=thread_id,
            expected_format="numeric ID or GitHub thread node ID",
            message=f"{field_name} cannot be None",
        )

    # Convert to string and strip
    thread_id_str = str(thread_id).strip()
    if not thread_id_str:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=thread_id,
            expected_format="numeric ID or GitHub thread node ID",
            message=f"{field_name} cannot be empty",
        )

    try:
        validator = create_thread_validator()
        validator.validate_id(thread_id_str, field_name)
    except ValueError as e:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=thread_id,
            expected_format="numeric ID or GitHub thread node ID",
            message=str(e),
        ) from e

    return thread_id_str


def validate_reply_body(
    body: str,
    field_name: str = "Reply body",
    min_length: int = MIN_REPLY_BODY_LENGTH,
    max_length: int = MAX_REPLY_BODY_LENGTH,
) -> str:
    """Validate a reply body with comprehensive checks.

    Args:
        body: The reply body to validate
        field_name: Name of the field for error messages
        min_length: Minimum length for the body
        max_length: Maximum length for the body

    Returns:
        Validated and cleaned reply body

    Raises:
        ValidationError: If validation fails
    """
    if body is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format=f"text between {min_length} and {max_length} characters",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(body, str):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format=f"text between {min_length} and {max_length} characters",
            message=f"{field_name} must be a string",
        )

    # Strip whitespace
    body = body.strip()

    # Check if empty after stripping
    if not body:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format=f"text between {min_length} and {max_length} characters",
            message=f"{field_name} cannot be empty",
        )

    # Check length limits
    if len(body) < min_length:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format=f"text between {min_length} and {max_length} characters",
            message=f"{field_name} must be at least {min_length} characters long",
        )

    if len(body) > max_length:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format=f"text between {min_length} and {max_length} characters",
            message=(
                f"{field_name} cannot exceed {max_length:,} characters "
                "(GitHub limit)"
            ),
        )

    # Check for meaningful content (non-whitespace characters)
    meaningful_content = body.replace(" ", "").replace("\n", "").replace("\t", "")
    if len(meaningful_content) < MIN_MEANINGFUL_CONTENT_LENGTH:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format=(
                f"meaningful text with at least {MIN_MEANINGFUL_CONTENT_LENGTH} "
                "non-whitespace characters"
            ),
            message=(
                f"{field_name} must contain at least "
                f"{MIN_MEANINGFUL_CONTENT_LENGTH} non-whitespace characters"
            ),
        )

    # Check for placeholder patterns
    body_lower = body.lower().strip()
    if body_lower in PLACEHOLDER_PATTERNS:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=body,
            expected_format="meaningful text content",
            message=(
                f"{field_name} appears to be placeholder text. "
                "Please provide a meaningful reply"
            ),
        )

    return body


def validate_limit(
    limit: Union[int, str],
    field_name: str = "Limit",
    min_value: int = MIN_LIMIT_VALUE,
    max_value: int = MAX_LIMIT_VALUE,
) -> int:
    """Validate a limit/count parameter.

    Args:
        limit: The limit value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Validated limit as integer

    Raises:
        ValidationError: If validation fails
    """
    if limit is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=limit,
            expected_format=f"integer between {min_value} and {max_value}",
            message=f"{field_name} cannot be None",
        )

    # Convert to int if it's a string
    if isinstance(limit, str):
        limit = limit.strip()
        if not limit:
            raise create_validation_error(
                field_name=field_name,
                invalid_value=limit,
                expected_format=f"integer between {min_value} and {max_value}",
                message=f"{field_name} cannot be empty",
            )

        if not limit.isdigit():
            raise create_validation_error(
                field_name=field_name,
                invalid_value=limit,
                expected_format=f"integer between {min_value} and {max_value}",
                message=f"{field_name} must be numeric",
            )

        try:
            limit = int(limit)
        except ValueError as e:
            raise create_validation_error(
                field_name=field_name,
                invalid_value=limit,
                expected_format=f"integer between {min_value} and {max_value}",
                message=f"{field_name} must be a valid integer",
            ) from e

    # Validate type and range
    if not isinstance(limit, int):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=limit,
            expected_format=f"integer between {min_value} and {max_value}",
            message=f"{field_name} must be an integer",
        )

    if limit < min_value:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=limit,
            expected_format=f"integer between {min_value} and {max_value}",
            message=f"{field_name} must be at least {min_value}",
        )

    if limit > max_value:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=limit,
            expected_format=f"integer between {min_value} and {max_value}",
            message=f"{field_name} cannot exceed {max_value}",
        )

    return limit


def validate_datetime_string(date_str: str, field_name: str = "Date") -> datetime:
    """Validate and parse a datetime string.

    Args:
        date_str: The datetime string to validate
        field_name: Name of the field for error messages

    Returns:
        Parsed datetime object

    Raises:
        ValidationError: If validation fails
    """
    if date_str is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=date_str,
            expected_format="ISO datetime string",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(date_str, str):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=date_str,
            expected_format="ISO datetime string",
            message=f"{field_name} must be a string",
        )

    date_str = date_str.strip()
    if not date_str:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=date_str,
            expected_format="ISO datetime string",
            message=f"{field_name} cannot be empty",
        )

    try:
        from ..utils import parse_datetime

        return parse_datetime(date_str)
    except (ValueError, ValidationError) as e:
        # If it's already a ValidationError, check if it has the expected message format
        if isinstance(e, ValidationError):
            # Re-raise with a more user-friendly message but preserve the original
            raise create_validation_error(
                field_name=field_name,
                invalid_value=date_str,
                expected_format="ISO datetime string (e.g., '2024-01-01T12:00:00')",
                message=f"Invalid {field_name.lower()} format",
            ) from e
        else:
            raise create_validation_error(
                field_name=field_name,
                invalid_value=date_str,
                expected_format="ISO datetime string (e.g., '2024-01-01T12:00:00')",
                message=f"Invalid {field_name.lower()} format: {str(e)}",
            ) from e


def validate_email(email: str, field_name: str = "Email") -> str:
    """Validate an email address.

    Args:
        email: The email address to validate
        field_name: Name of the field for error messages

    Returns:
        Validated email address

    Raises:
        ValidationError: If validation fails
    """
    if email is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=email,
            expected_format="valid email address",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(email, str):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=email,
            expected_format="valid email address",
            message=f"{field_name} must be a string",
        )

    email = email.strip()
    if not email:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=email,
            expected_format="valid email address",
            message=f"{field_name} cannot be empty",
        )

    if not EMAIL_REGEX.match(email):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=email,
            expected_format="valid email address (e.g., user@example.com)",
            message=f"Invalid {field_name.lower()} format",
        )

    return email


def validate_url(url: str, field_name: str = "URL") -> str:
    """Validate a URL.

    Args:
        url: The URL to validate
        field_name: Name of the field for error messages

    Returns:
        Validated URL

    Raises:
        ValidationError: If validation fails
    """
    if url is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=url,
            expected_format="valid HTTP or HTTPS URL",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(url, str):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=url,
            expected_format="valid HTTP or HTTPS URL",
            message=f"{field_name} must be a string",
        )

    url = url.strip()
    if not url:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=url,
            expected_format="valid HTTP or HTTPS URL",
            message=f"{field_name} cannot be empty",
        )

    if not URL_REGEX.match(url):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=url,
            expected_format="valid HTTP or HTTPS URL (e.g., https://example.com)",
            message=f"Invalid {field_name.lower()} format",
        )

    return url


def validate_username(username: str, field_name: str = "Username") -> str:
    """Validate a GitHub username.

    Args:
        username: The username to validate
        field_name: Name of the field for error messages

    Returns:
        Validated username

    Raises:
        ValidationError: If validation fails
    """
    if username is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=username,
            expected_format="valid GitHub username",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(username, str):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=username,
            expected_format="valid GitHub username",
            message=f"{field_name} must be a string",
        )

    username = username.strip()
    if not username:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=username,
            expected_format="valid GitHub username",
            message=f"{field_name} cannot be empty",
        )

    if not USERNAME_REGEX.match(username):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=username,
            expected_format=(
                "valid GitHub username (1-39 characters, alphanumeric and hyphens)"
            ),
            message=f"Invalid {field_name.lower()} format",
        )

    return username


def validate_non_empty_string(
    value: str,
    field_name: str = "Value",
    min_length: int = 1,
    max_length: Optional[int] = None,
) -> str:
    """Validate a non-empty string with optional length constraints.

    Args:
        value: The string to validate
        field_name: Name of the field for error messages
        min_length: Minimum length requirement
        max_length: Maximum length requirement (optional)

    Returns:
        Validated string

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format="non-empty string",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(value, str):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format="non-empty string",
            message=f"{field_name} must be a string",
        )

    value = value.strip()
    if not value:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format="non-empty string",
            message=f"{field_name} cannot be empty",
        )

    if len(value) < min_length:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format=f"string with at least {min_length} characters",
            message=f"{field_name} must be at least {min_length} characters long",
        )

    if max_length is not None and len(value) > max_length:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format=f"string with at most {max_length} characters",
            message=f"{field_name} cannot exceed {max_length} characters",
        )

    return value


def validate_boolean_flag(
    value: Any, field_name: str = "Flag", allow_none: bool = False
) -> bool:
    """Validate a boolean flag value.

    Args:
        value: The value to validate as boolean
        field_name: Name of the field for error messages
        allow_none: Whether to allow None values (returns False)

    Returns:
        Validated boolean value

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if allow_none:
            return False
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format="boolean (True/False)",
            message=f"{field_name} cannot be None",
        )

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ("true", "1", "yes", "on"):
            return True
        if value_lower in ("false", "0", "no", "off"):
            return False

    raise create_validation_error(
        field_name=field_name,
        invalid_value=value,
        expected_format="boolean (True/False) or string representation",
        message=f"{field_name} must be a boolean value",
    )


def validate_choice(
    value: Any,
    choices: List[Any],
    field_name: str = "Value",
    case_sensitive: bool = True,
) -> Any:
    """Validate that a value is one of the allowed choices.

    Args:
        value: The value to validate
        choices: List of allowed choices
        field_name: Name of the field for error messages
        case_sensitive: Whether string comparison is case-sensitive

    Returns:
        Validated value (original case preserved)

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=value,
            expected_format=f"one of: {', '.join(map(str, choices))}",
            message=f"{field_name} cannot be None",
        )

    # Direct match first
    if value in choices:
        return value

    # Case-insensitive string matching if enabled
    if not case_sensitive and isinstance(value, str):
        value_lower = value.lower()
        for choice in choices:
            if isinstance(choice, str) and choice.lower() == value_lower:
                return choice

    raise create_validation_error(
        field_name=field_name,
        invalid_value=value,
        expected_format=f"one of: {', '.join(map(str, choices))}",
        message=f"{field_name} must be one of the allowed values",
    )


def validate_dict_keys(
    data: Dict[str, Any],
    required_keys: List[str],
    optional_keys: Optional[List[str]] = None,
    field_name: str = "Data",
) -> Dict[str, Any]:
    """Validate that a dictionary contains required keys and no unexpected keys.

    Args:
        data: The dictionary to validate
        required_keys: List of required keys
        optional_keys: List of optional keys (if None, any additional keys allowed)
        field_name: Name of the field for error messages

    Returns:
        Validated dictionary

    Raises:
        ValidationError: If validation fails
    """
    if data is None:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=data,
            expected_format="dictionary",
            message=f"{field_name} cannot be None",
        )

    if not isinstance(data, dict):
        raise create_validation_error(
            field_name=field_name,
            invalid_value=data,
            expected_format="dictionary",
            message=f"{field_name} must be a dictionary",
        )

    # Check for required keys
    missing_keys = set(required_keys) - set(data.keys())
    if missing_keys:
        raise create_validation_error(
            field_name=field_name,
            invalid_value=data,
            expected_format=(
                f"dictionary with required keys: {', '.join(required_keys)}"
            ),
            message=(
                f"Missing required keys in {field_name.lower()}: "
                f"{', '.join(sorted(missing_keys))}"
            ),
        )

    # Check for unexpected keys if optional_keys is specified
    if optional_keys is not None:
        allowed_keys = set(required_keys) | set(optional_keys)
        unexpected_keys = set(data.keys()) - allowed_keys
        if unexpected_keys:
            raise create_validation_error(
                field_name=field_name,
                invalid_value=data,
                expected_format=(
                    f"dictionary with only allowed keys: "
                    f"{', '.join(sorted(allowed_keys))}"
                ),
                message=(
                    f"Unexpected keys in {field_name.lower()}: "
                    f"{', '.join(sorted(unexpected_keys))}"
                ),
            )

    return data


# Convenience function for validating reply content warnings
def validate_reply_content_warnings(body: str) -> List[str]:
    """Check for potential issues in reply content and return warnings.

    Args:
        body: The reply body to check

    Returns:
        List of warning messages (empty if no warnings)
    """
    warnings = []

    # Warning for mentions
    if body.startswith("@"):
        warnings.append("Reply starts with '@' - this will mention users")

    # Warning for potential spam patterns
    if len(set(body.lower().replace(" ", ""))) < 3 and len(body) > 10:
        warnings.append("Reply contains very repetitive content")

    # Warning for all caps
    if len(body) > 10 and body.isupper():
        warnings.append("Reply is in ALL CAPS - consider using normal case")

    # Warning for excessive punctuation
    if body.count("!") > 5 or body.count("?") > 5:
        warnings.append("Reply contains excessive punctuation")

    return warnings


# Composite validation functions for command-level validation
def validate_fetch_command_args(
    pr_number: Union[int, str],
    pretty: bool = False,
    resolved: bool = False,
    limit: Union[int, str] = 100,
) -> Dict[str, Any]:
    """Validate all arguments for the fetch command.

    Args:
        pr_number: Pull request number
        pretty: Pretty output flag
        resolved: Include resolved threads flag
        limit: Maximum number of threads to fetch

    Returns:
        Dictionary of validated arguments

    Raises:
        ValidationError: If any validation fails
    """
    return {
        "pr_number": validate_pr_number(pr_number),
        "pretty": validate_boolean_flag(pretty, "Pretty flag", allow_none=True),
        "resolved": validate_boolean_flag(resolved, "Resolved flag", allow_none=True),
        "limit": validate_limit(limit),
    }


def validate_reply_command_args(
    comment_id: Union[str, int],
    body: str,
    pretty: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Validate all arguments for the reply command.

    Args:
        comment_id: Comment ID to reply to
        body: Reply body text
        pretty: Pretty output flag
        verbose: Verbose output flag

    Returns:
        Dictionary of validated arguments

    Raises:
        ValidationError: If any validation fails
    """
    return {
        "comment_id": validate_comment_id(comment_id, allow_thread_ids=True),
        "body": validate_reply_body(body),
        "pretty": validate_boolean_flag(pretty, "Pretty flag", allow_none=True),
        "verbose": validate_boolean_flag(verbose, "Verbose flag", allow_none=True),
    }


@dataclass
class ResolveOptions:
    """Options for the resolve command.

    Groups the optional flags to reduce the number of function parameters
    and make the API cleaner and more maintainable.
    """

    bulk_resolve: bool = False
    undo: bool = False
    yes: bool = False
    pretty: bool = False
    limit: Union[int, str] = 100


def validate_resolve_command_args(
    thread_id: Optional[Union[str, int]] = None,
    pr_number: Optional[Union[int, str]] = None,
    options: Optional[ResolveOptions] = None,
) -> Dict[str, Any]:
    """Validate all arguments for the resolve command.

    Args:
        thread_id: Thread ID for single resolution
        pr_number: Pull request number (required for bulk operations)
        options: ResolveOptions containing bulk_resolve, undo, yes, pretty, and limit

    Returns:
        Dictionary of validated arguments

    Raises:
        ValidationError: If any validation fails
    """
    # Create default options if none provided
    if options is None:
        options = ResolveOptions()
    # Validate mutually exclusive options
    if options.bulk_resolve and thread_id is not None:
        raise ValidationError(
            "Cannot use bulk resolve and thread ID together. Choose one.",
            field_name="command options",
        )

    if not options.bulk_resolve and thread_id is None:
        raise ValidationError(
            "Must specify either thread ID or bulk resolve option",
            field_name="command options",
        )

    # Validate PR number requirement for bulk operations
    if options.bulk_resolve and pr_number is None:
        raise ValidationError(
            "PR number is required when using bulk resolve",
            field_name="pr_number",
        )

    return {
        "thread_id": validate_thread_id(thread_id) if thread_id is not None else None,
        "bulk_resolve": validate_boolean_flag(
            options.bulk_resolve, "Bulk resolve flag"
        ),
        "pr_number": validate_pr_number(pr_number, allow_none=not options.bulk_resolve),
        "undo": validate_boolean_flag(options.undo, "Undo flag", allow_none=True),
        "yes": validate_boolean_flag(options.yes, "Yes flag", allow_none=True),
        "pretty": validate_boolean_flag(options.pretty, "Pretty flag", allow_none=True),
        "limit": validate_limit(options.limit),
    }
