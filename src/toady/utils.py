"""Utility functions for the toady package."""

import json
from datetime import datetime

import click

# Constants
MAX_PR_NUMBER = 999999


def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string in various ISO formats.

    Args:
        date_str: Date string in ISO format

    Returns:
        datetime object

    Raises:
        ValueError: If date string cannot be parsed
    """
    from .exceptions import create_validation_error

    try:
        if not isinstance(date_str, str):
            raise create_validation_error(
                field_name="date_str",
                invalid_value=date_str,
                expected_format="string in ISO datetime format",
                message="Date string must be a string",
            )

        if not date_str.strip():
            raise create_validation_error(
                field_name="date_str",
                invalid_value="empty string",
                expected_format="non-empty ISO datetime string",
                message="Date string cannot be empty",
            )

        original_date_str = date_str

        # Remove timezone info if present
        try:
            if date_str.endswith("Z"):
                date_str = date_str[:-1]
            elif "+" in date_str and date_str.count(":") >= 3:
                # Handle timezone like +00:00
                date_str = date_str.split("+")[0]
            elif "-" in date_str and date_str.count(":") >= 3:
                # Handle timezone like -05:00 (but not dates like 2024-01-01)
                parts = date_str.split("-")
                if len(parts) > 3:  # Has timezone
                    date_str = "-".join(parts[:-1])
        except (AttributeError, IndexError) as e:
            raise create_validation_error(
                field_name="date_str",
                invalid_value=original_date_str,
                expected_format="valid ISO datetime string",
                message=f"Failed to process timezone in datetime string: {str(e)}",
            ) from e

        # Try parsing with different formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",  # With microseconds
            "%Y-%m-%dT%H:%M:%S",  # Without microseconds
        ]

        parsing_errors = []
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError as e:
                parsing_errors.append(f"Format '{fmt}': {str(e)}")
                continue

        # If we get here, all formats failed
        raise create_validation_error(
            field_name="date_str",
            invalid_value=original_date_str,
            expected_format="ISO datetime string (YYYY-MM-DDTHH:MM:SS[.ffffff])",
            message=(
                f"Unable to parse datetime. Tried formats: "
                f"{'; '.join(parsing_errors)}"
            ),
        )

    except Exception as e:
        # If it's already a ValidationError, re-raise it
        from .exceptions import ValidationError

        if isinstance(e, ValidationError):
            raise
        # Otherwise, wrap it in a ValidationError
        raise create_validation_error(
            field_name="date_str",
            invalid_value=str(date_str) if "date_str" in locals() else "unknown",
            expected_format="valid ISO datetime string",
            message=f"Unexpected error parsing datetime: {str(e)}",
        ) from e


def emit_error(
    ctx: click.Context, pr_number: int, code: str, msg: str, pretty: bool
) -> None:
    """Helper function to emit consistent error messages in JSON or pretty format.

    Args:
        ctx: Click context for exit handling
        pr_number: PR number for error context
        code: Error code for JSON output
        msg: Error message
        pretty: Whether to use pretty output format
    """
    # Validate inputs with safe fallbacks
    if not isinstance(pr_number, int) or pr_number <= 0:
        pr_number = 0

    if not isinstance(code, str) or not code.strip():
        code = "UNKNOWN_ERROR"

    if not isinstance(msg, str):
        msg = str(msg) if msg is not None and msg != "" else "Unknown error occurred"

    if pretty:
        click.echo(msg, err=True)
    else:
        try:
            error_result = {
                "pr_number": pr_number,
                "success": False,
                "error": code,
                "error_message": msg,
            }
            click.echo(json.dumps(error_result), err=True)
        except (TypeError, ValueError):
            # Fallback if JSON serialization fails
            fallback_msg = f"Error (code: {code}): {msg}"
            click.echo(fallback_msg, err=True)

    ctx.exit(1)
