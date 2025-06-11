"""Format selection utilities for CLI commands.

This module provides utilities for handling format selection in CLI commands,
including Click options, validation, and formatter instantiation.
"""

import os
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

import click

# Ensure formatters are registered by importing the module
# This triggers the FormatterFactory.register() calls at module level
from . import formatters  # noqa: F401
from .format_interfaces import FormatterError, FormatterFactory
from .formatters import format_fetch_output

# TypeVar for decorator functions
F = TypeVar("F", bound=Callable[..., Any])


class FormatSelectionError(Exception):
    """Exception raised when format selection fails."""

    def __init__(self, message: str, available_formats: Optional[List[str]] = None):
        """Initialize format selection error.

        Args:
            message: Error message.
            available_formats: List of available format names.
        """
        self.available_formats = available_formats or []
        super().__init__(message)


def get_default_format() -> str:
    """Get the default format from environment or configuration.

    Returns:
        Default format name ('json' or 'pretty').
    """
    # Check environment variable first
    default_format = os.environ.get("TOADY_DEFAULT_FORMAT", "").lower()

    if default_format in ["json", "pretty"]:
        return default_format

    # Default to JSON for programmatic use
    return "json"


def validate_format(format_name: str) -> str:
    """Validate that the format is available.

    Args:
        format_name: Name of the format to validate.

    Returns:
        Validated format name.

    Raises:
        FormatSelectionError: If format is not available.
    """
    available_formats = FormatterFactory.list_formatters()

    if format_name not in available_formats:
        raise FormatSelectionError(
            f"Format '{format_name}' is not available. "
            f"Available formats: {', '.join(available_formats)}",
            available_formats=available_formats,
        )

    return format_name


def resolve_format_from_options(format_option: Optional[str], pretty_flag: bool) -> str:
    """Resolve format from command options with backward compatibility.

    Args:
        format_option: Value from --format option (if provided).
        pretty_flag: Value from --pretty flag (for backward compatibility).

    Returns:
        Resolved format name.

    Raises:
        FormatSelectionError: If format resolution fails.
    """
    # If --format is explicitly provided, use it
    if format_option is not None:
        return validate_format(format_option)

    # Backward compatibility: if --pretty is used, use pretty format
    if pretty_flag:
        return "pretty"

    # Otherwise, use default format
    return get_default_format()


def create_formatter(format_name: str, **options: Any) -> Any:
    """Create a formatter instance with the given options.

    Args:
        format_name: Name of the formatter to create.
        **options: Options to pass to the formatter constructor.

    Returns:
        Formatter instance.

    Raises:
        FormatSelectionError: If formatter creation fails.
    """
    try:
        return FormatterFactory.create(format_name, **options)
    except FormatterError as e:
        raise FormatSelectionError(
            f"Failed to create formatter '{format_name}': {e}"
        ) from e


def create_format_option(**kwargs: Any) -> Callable[[F], F]:
    """Create a Click option for format selection.

    Args:
        **kwargs: Additional arguments for the Click option.

    Returns:
        Click option decorator.
    """
    available_formats = FormatterFactory.list_formatters()
    choices = available_formats if available_formats else ["json", "pretty"]

    default_kwargs = {
        "type": click.Choice(choices, case_sensitive=False),
        "help": (
            f"Output format ({', '.join(choices)}). "
            "Default can be set with TOADY_DEFAULT_FORMAT environment variable."
        ),
        "metavar": f"{'|'.join(choices)}",
    }
    default_kwargs.update(kwargs)

    return cast(Callable[[F], F], click.option("--format", **default_kwargs))  # type: ignore[call-overload]


def create_legacy_pretty_option(**kwargs: Any) -> Callable[[F], F]:
    """Create a Click option for legacy --pretty flag.

    Args:
        **kwargs: Additional arguments for the Click option.

    Returns:
        Click option decorator.
    """
    default_kwargs = {
        "is_flag": True,
        "help": (
            "Output in human-readable format instead of JSON "
            "(deprecated, use --format pretty)"
        ),
    }
    default_kwargs.update(kwargs)

    return cast(Callable[[F], F], click.option("--pretty", **default_kwargs))  # type: ignore[call-overload]


# Format-specific output functions


def format_threads_output(threads: Any, format_name: str, **kwargs: Any) -> None:
    """Format and output threads using the specified format.

    Args:
        threads: List of thread objects to format.
        format_name: Name of the format to use.
        **kwargs: Additional options for formatting.
    """
    if format_name == "json":
        # Use existing JSON formatting logic
        format_fetch_output(threads=threads, pretty=False, **kwargs)
    elif format_name == "pretty":
        # Use existing pretty formatting logic
        format_fetch_output(threads=threads, pretty=True, **kwargs)
    else:
        # Use new formatter interface for other formats
        formatter = create_formatter(format_name)
        output = formatter.format_threads(threads)
        click.echo(output)


def format_object_output(obj: Any, format_name: str) -> None:
    """Format and output an object using the specified format.

    Args:
        obj: Object to format.
        format_name: Name of the format to use.
    """
    if format_name == "json":
        import json

        click.echo(json.dumps(obj, indent=2))
    elif format_name == "pretty":
        # Handle pretty format consistently with format_threads_output
        formatter = create_formatter(format_name)
        output = formatter.format_object(obj)
        click.echo(output)
    else:
        # Use formatter interface for other formats
        formatter = create_formatter(format_name)
        output = formatter.format_object(obj)
        click.echo(output)


def format_success_message(
    message: str, format_name: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """Format and output a success message.

    Args:
        message: Success message text.
        format_name: Name of the format to use.
        details: Optional additional details.
    """
    if format_name == "json":
        import json

        success_data = {"success": True, "message": message}
        if details:
            success_data["details"] = details
        click.echo(json.dumps(success_data, indent=2))
    else:
        # Use formatter interface
        formatter = create_formatter(format_name)
        output = formatter.format_success_message(message, details)
        click.echo(output)


def format_error_message(error: Dict[str, Any], format_name: str) -> None:
    """Format and output an error message.

    Args:
        error: Error dictionary with error details.
        format_name: Name of the format to use.
    """
    if format_name == "json":
        import json

        click.echo(json.dumps(error, indent=2), err=True)
    else:
        # Use formatter interface
        formatter = create_formatter(format_name)
        output = formatter.format_error(error)
        click.echo(output, err=True)
