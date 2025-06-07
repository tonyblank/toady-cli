"""Utility functions for the toady package."""

from datetime import datetime


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
