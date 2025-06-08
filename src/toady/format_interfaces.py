"""Formatter interfaces and base classes for toady CLI output formatting.

This module defines the base interfaces and contracts for all output formatters,
providing a structured approach to handling different output formats like JSON,
pretty-print, tables, etc.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import Comment, ReviewThread


class IFormatter(ABC):
    """Base interface for all output formatters.

    This interface defines the contract that all formatters must implement,
    ensuring consistent behavior across different output formats.
    """

    @abstractmethod
    def format_threads(self, threads: List[ReviewThread]) -> str:
        """Format a list of review threads.

        Args:
            threads: List of ReviewThread objects to format.

        Returns:
            Formatted string representation of the threads.
        """
        pass

    @abstractmethod
    def format_comments(self, comments: List[Comment]) -> str:
        """Format a list of comments.

        Args:
            comments: List of Comment objects to format.

        Returns:
            Formatted string representation of the comments.
        """
        pass

    @abstractmethod
    def format_object(self, obj: Any) -> str:
        """Format a single object.

        Args:
            obj: Object to format (can be any serializable type).

        Returns:
            Formatted string representation of the object.
        """
        pass

    @abstractmethod
    def format_array(self, items: List[Any]) -> str:
        """Format an array of items.

        Args:
            items: List of items to format.

        Returns:
            Formatted string representation of the array.
        """
        pass

    @abstractmethod
    def format_primitive(self, value: Union[str, int, float, bool, None]) -> str:
        """Format a primitive value.

        Args:
            value: Primitive value to format.

        Returns:
            Formatted string representation of the value.
        """
        pass

    @abstractmethod
    def format_error(self, error: Dict[str, Any]) -> str:
        """Format an error object.

        Args:
            error: Error dictionary with error details.

        Returns:
            Formatted string representation of the error.
        """
        pass

    def format_success_message(
        self, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a success message.

        Args:
            message: Success message text.
            details: Optional additional details to include.

        Returns:
            Formatted success message.
        """
        if details:
            return self.format_object(
                {"success": True, "message": message, "details": details}
            )
        return self.format_object({"success": True, "message": message})

    def format_warning_message(
        self, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a warning message.

        Args:
            message: Warning message text.
            details: Optional additional details to include.

        Returns:
            Formatted warning message.
        """
        if details:
            return self.format_object(
                {"warning": True, "message": message, "details": details}
            )
        return self.format_object({"warning": True, "message": message})


class BaseFormatter(IFormatter):
    """Base formatter implementation with common functionality.

    This class provides default implementations for common formatting operations
    and helper methods that can be used by concrete formatter implementations.
    """

    def __init__(self, **options: Any) -> None:
        """Initialize the formatter with options.

        Args:
            **options: Formatter-specific options.
        """
        self.options = options

    def _safe_serialize(self, obj: Any) -> Any:
        """Safely serialize an object, handling non-serializable types.

        Args:
            obj: Object to serialize.

        Returns:
            Serializable representation of the object.
        """
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif isinstance(obj, (list, tuple)):
            return [self._safe_serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._safe_serialize(value) for key, value in obj.items()}
        elif hasattr(obj, "__dict__"):
            return self._safe_serialize(obj.__dict__)
        else:
            # For primitive types and other serializable objects
            try:
                import json

                json.dumps(obj)  # Test if it's JSON serializable
                return obj
            except (TypeError, ValueError):
                return str(obj)

    def _handle_empty_data(
        self, data: Any, empty_message: str = "No data available."
    ) -> Optional[str]:
        """Handle empty data cases.

        Args:
            data: Data to check for emptiness.
            empty_message: Message to return if data is empty.

        Returns:
            Empty message if data is empty, None otherwise.
        """
        if not data:
            return empty_message
        if isinstance(data, (list, tuple, dict)) and len(data) == 0:
            return empty_message
        return None

    def format_comments(self, comments: List[Comment]) -> str:
        """Default implementation for formatting comments.

        Args:
            comments: List of Comment objects to format.

        Returns:
            Formatted string representation of the comments.
        """
        # Default implementation - can be overridden by subclasses
        return self.format_array([comment.to_dict() for comment in comments])

    def format_success_message(
        self, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a success message (implementation in base class)."""
        success_data = {"success": True, "message": message}
        if details:
            success_data["details"] = details
        return self.format_object(success_data)

    def format_warning_message(
        self, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a warning message (implementation in base class)."""
        warning_data = {"warning": True, "message": message}
        if details:
            warning_data["details"] = details
        return self.format_object(warning_data)


class FormatterError(Exception):
    """Exception raised when formatting operations fail."""

    def __init__(
        self, message: str, original_error: Optional[Exception] = None
    ) -> None:
        """Initialize the formatter error.

        Args:
            message: Error message.
            original_error: Original exception that caused the formatting error.
        """
        super().__init__(message)
        self.original_error = original_error


class FormatterOptions:
    """Configuration options for formatters."""

    def __init__(
        self,
        indent: int = 2,
        sort_keys: bool = False,
        ensure_ascii: bool = False,
        separators: Optional[Tuple[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize formatter options.

        Args:
            indent: Number of spaces for indentation.
            sort_keys: Whether to sort dictionary keys.
            ensure_ascii: Whether to ensure ASCII-only output.
            separators: Separators for JSON formatting.
            **kwargs: Additional formatter-specific options.
        """
        self.indent = indent
        self.sort_keys = sort_keys
        self.ensure_ascii = ensure_ascii
        self.separators = separators
        self.extra_options = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert options to dictionary.

        Returns:
            Dictionary representation of the options.
        """
        return {
            "indent": self.indent,
            "sort_keys": self.sort_keys,
            "ensure_ascii": self.ensure_ascii,
            "separators": self.separators,
            **self.extra_options,
        }


class FormatterFactory:
    """Factory for creating formatter instances."""

    _formatters: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, formatter_class: type) -> None:
        """Register a formatter class.

        Args:
            name: Name of the formatter.
            formatter_class: Formatter class to register.
        """
        cls._formatters[name] = formatter_class

    @classmethod
    def create(cls, name: str, **options: Any) -> IFormatter:
        """Create a formatter instance.

        Args:
            name: Name of the formatter to create.
            **options: Options to pass to the formatter constructor.

        Returns:
            Formatter instance.

        Raises:
            FormatterError: If the formatter is not registered.
        """
        if name not in cls._formatters:
            available = ", ".join(cls._formatters.keys())
            raise FormatterError(
                f"Unknown formatter '{name}'. Available formatters: {available}"
            )

        formatter_class = cls._formatters[name]
        try:
            formatter_instance = formatter_class(**options)
            return formatter_instance  # type: ignore[no-any-return]
        except Exception as e:
            raise FormatterError(
                f"Failed to create formatter '{name}': {str(e)}", original_error=e
            ) from e

    @classmethod
    def list_formatters(cls) -> List[str]:
        """List available formatter names.

        Returns:
            List of registered formatter names.
        """
        return list(cls._formatters.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a formatter is registered.

        Args:
            name: Name of the formatter to check.

        Returns:
            True if the formatter is registered, False otherwise.
        """
        return name in cls._formatters
