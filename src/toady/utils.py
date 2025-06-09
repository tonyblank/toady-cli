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
    # Remove timezone info if present
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

    # Try parsing with different formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",  # With microseconds
        "%Y-%m-%dT%H:%M:%S",  # Without microseconds
    ]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse datetime: {date_str}")


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
    if pretty:
        click.echo(msg, err=True)
    else:
        error_result = {
            "pr_number": pr_number,
            "threads_fetched": False,
            "error": code,
            "error_message": msg,
        }
        click.echo(json.dumps(error_result), err=True)
    ctx.exit(1)
