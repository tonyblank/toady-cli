"""Formatters package for output formatting functionality.

This package contains all output formatting components including JSON and
pretty formatters, format interfaces, and format selection logic.
"""

from .format_interfaces import (
    BaseFormatter,
    FormatterError,
    FormatterFactory,
    FormatterOptions,
    IFormatter,
)
from .format_selection import (
    create_format_option,
    create_legacy_pretty_option,
    format_object_output,
    format_threads_output,
    resolve_format_from_options,
)
from .formatters import (
    JSONFormatter,
    OutputFormatter,
    PrettyFormatter,
    format_fetch_output,
)
from .json_formatter import JSONFormatter as NewJSONFormatter
from .pretty_formatter import PrettyFormatter as NewPrettyFormatter

__all__ = [
    # Core interfaces
    "IFormatter",
    "BaseFormatter",
    "FormatterFactory",
    "FormatterError",
    "FormatterOptions",
    # Legacy formatters
    "JSONFormatter",
    "OutputFormatter",
    "PrettyFormatter",
    "format_fetch_output",
    # New formatters
    "NewJSONFormatter",
    "NewPrettyFormatter",
    # Format selection
    "create_format_option",
    "create_legacy_pretty_option",
    "format_object_output",
    "format_threads_output",
    "resolve_format_from_options",
]
