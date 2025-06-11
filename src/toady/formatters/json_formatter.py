"""JSON formatter implementation for toady CLI output.

This module provides a comprehensive JSON formatter that implements the IFormatter
interface, offering clean and structured JSON output with proper error handling
and customization options.
"""

import json
from typing import Any, Dict, List, Optional, Union

from ..models import Comment, ReviewThread
from .format_interfaces import BaseFormatter, FormatterError, FormatterOptions


class JSONFormatter(BaseFormatter):
    """JSON formatter that produces clean, structured JSON output.

    This formatter converts all data types to JSON format with proper indentation,
    error handling for non-serializable types, and customizable formatting options.
    """

    def __init__(
        self, options: Optional[FormatterOptions] = None, **kwargs: Any
    ) -> None:
        """Initialize the JSON formatter.

        Args:
            options: FormatterOptions instance with JSON formatting settings.
            **kwargs: Additional options passed to the base formatter.
        """
        super().__init__(**kwargs)
        self.formatter_options = options or FormatterOptions(**kwargs)

        # Extract JSON-specific options
        self.json_options: Dict[str, Any] = {
            "indent": self.formatter_options.indent,
            "sort_keys": self.formatter_options.sort_keys,
            "ensure_ascii": self.formatter_options.ensure_ascii,
        }

        if self.formatter_options.separators:
            self.json_options["separators"] = self.formatter_options.separators

    def format_threads(self, threads: List[ReviewThread]) -> str:
        """Format a list of review threads as JSON.

        Args:
            threads: List of ReviewThread objects to format.

        Returns:
            JSON string representation of the threads.

        Raises:
            FormatterError: If serialization fails.
        """
        try:
            # Handle empty case
            if not threads:
                return json.dumps([], **self.json_options)

            # Convert threads to dictionaries
            thread_dicts = []
            for thread in threads:
                try:
                    if hasattr(thread, "to_dict"):
                        thread_dict = thread.to_dict()
                    else:
                        thread_dict = self._safe_serialize(thread)
                    thread_dicts.append(thread_dict)
                except Exception as e:
                    thread_id = getattr(thread, "thread_id", "unknown")
                    raise FormatterError(
                        f"Failed to serialize thread {thread_id}: {str(e)}",
                        original_error=e,
                    ) from e

            return json.dumps(thread_dicts, **self.json_options)

        except Exception as e:
            if isinstance(e, FormatterError):
                raise
            raise FormatterError(
                f"Failed to format threads as JSON: {str(e)}", original_error=e
            ) from e

    def format_comments(self, comments: List[Comment]) -> str:
        """Format a list of comments as JSON.

        Args:
            comments: List of Comment objects to format.

        Returns:
            JSON string representation of the comments.

        Raises:
            FormatterError: If serialization fails.
        """
        try:
            # Handle empty case
            if not comments:
                return json.dumps([], **self.json_options)

            # Convert comments to dictionaries
            comment_dicts = []
            for comment in comments:
                try:
                    if hasattr(comment, "to_dict"):
                        comment_dict = comment.to_dict()
                    else:
                        comment_dict = self._safe_serialize(comment)
                    comment_dicts.append(comment_dict)
                except Exception as e:
                    comment_id = getattr(comment, "comment_id", "unknown")
                    raise FormatterError(
                        f"Failed to serialize comment {comment_id}: {str(e)}",
                        original_error=e,
                    ) from e

            return json.dumps(comment_dicts, **self.json_options)

        except Exception as e:
            if isinstance(e, FormatterError):
                raise
            raise FormatterError(
                f"Failed to format comments as JSON: {str(e)}", original_error=e
            ) from e

    def format_object(self, obj: Any) -> str:
        """Format a single object as JSON.

        Args:
            obj: Object to format (can be any serializable type).

        Returns:
            JSON string representation of the object.

        Raises:
            FormatterError: If serialization fails.
        """
        try:
            serializable_obj = self._safe_serialize(obj)
            return json.dumps(serializable_obj, **self.json_options)
        except Exception as e:
            raise FormatterError(
                f"Failed to format object as JSON: {str(e)}", original_error=e
            ) from e

    def format_array(self, items: List[Any]) -> str:
        """Format an array of items as JSON.

        Args:
            items: List of items to format.

        Returns:
            JSON string representation of the array.

        Raises:
            FormatterError: If serialization fails.
        """
        try:
            # Handle empty case
            if not items:
                return json.dumps([], **self.json_options)

            # Serialize each item safely
            serializable_items = []
            for i, item in enumerate(items):
                try:
                    if hasattr(item, "to_dict"):
                        serializable_item = item.to_dict()
                    else:
                        serializable_item = self._safe_serialize(item)
                    serializable_items.append(serializable_item)
                except Exception as e:
                    raise FormatterError(
                        f"Failed to serialize array item at index {i}: {str(e)}",
                        original_error=e,
                    ) from e

            return json.dumps(serializable_items, **self.json_options)

        except Exception as e:
            if isinstance(e, FormatterError):
                raise
            raise FormatterError(
                f"Failed to format array as JSON: {str(e)}", original_error=e
            ) from e

    def format_primitive(self, value: Union[str, int, float, bool, None]) -> str:
        """Format a primitive value as JSON.

        Args:
            value: Primitive value to format.

        Returns:
            JSON string representation of the value.

        Raises:
            FormatterError: If serialization fails.
        """
        try:
            return json.dumps(value, **self.json_options)
        except Exception as e:
            raise FormatterError(
                f"Failed to format primitive value as JSON: {str(e)}", original_error=e
            ) from e

    def format_error(self, error: Dict[str, Any]) -> str:
        """Format an error object as JSON.

        Args:
            error: Error dictionary with error details.

        Returns:
            JSON string representation of the error.

        Raises:
            FormatterError: If serialization fails.
        """
        try:
            # Ensure error has required fields
            error_dict = dict(error)  # Create a copy
            if "error" not in error_dict:
                error_dict["error"] = True
            if "success" not in error_dict:
                error_dict["success"] = False

            return json.dumps(error_dict, **self.json_options)
        except Exception as e:
            raise FormatterError(
                f"Failed to format error as JSON: {str(e)}", original_error=e
            ) from e

    def format_success_message(
        self, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a success message as JSON.

        Args:
            message: Success message text.
            details: Optional additional details to include.

        Returns:
            JSON string representation of the success message.
        """
        success_data = {"success": True, "message": message}

        if details:
            success_data["details"] = details

        return self.format_object(success_data)

    def format_warning_message(
        self, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a warning message as JSON.

        Args:
            message: Warning message text.
            details: Optional additional details to include.

        Returns:
            JSON string representation of the warning message.
        """
        warning_data = {"warning": True, "message": message}

        if details:
            warning_data["details"] = details

        return self.format_object(warning_data)

    def format_reply_result(
        self, reply_info: Dict[str, Any], verbose: bool = False
    ) -> str:
        """Format reply command result as JSON.

        Args:
            reply_info: Dictionary containing reply information.
            verbose: Whether to include verbose details.

        Returns:
            JSON string representation of the reply result.
        """
        result = {
            "reply_posted": True,
            "reply_id": reply_info.get("reply_id", ""),
            "reply_url": reply_info.get("reply_url", ""),
            "created_at": reply_info.get("created_at", ""),
            "author": reply_info.get("author", ""),
        }

        # Add optional fields if present
        optional_fields = [
            "pr_number",
            "pr_title",
            "pr_url",
            "thread_url",
            "parent_comment_author",
            "body_preview",
            "review_id",
            "comment_id",
        ]

        for field in optional_fields:
            if field in reply_info and reply_info[field]:
                result[field] = reply_info[field]

        # Include verbose flag in output to indicate extended info
        if verbose:
            result["verbose"] = True

        return self.format_object(result)

    def format_resolve_result(self, resolve_info: Dict[str, Any]) -> str:
        """Format resolve command result as JSON.

        Args:
            resolve_info: Dictionary containing resolve operation information.

        Returns:
            JSON string representation of the resolve result.
        """
        return self.format_object(resolve_info)

    def _safe_serialize(self, obj: Any) -> Any:
        """Safely serialize an object with enhanced error handling.

        Args:
            obj: Object to serialize.

        Returns:
            Serializable representation of the object.
        """
        # Handle None explicitly
        if obj is None:
            return None

        # Handle primitive types
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # Handle datetime objects
        if hasattr(obj, "isoformat"):
            try:
                return obj.isoformat()
            except Exception:
                return str(obj)

        # Handle objects with to_dict method (like our models)
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            try:
                return obj.to_dict()
            except Exception:
                # Fallback to string representation
                return f"<{type(obj).__name__}: {str(obj)}>"

        # Handle dictionaries
        if isinstance(obj, dict):
            return {key: self._safe_serialize(value) for key, value in obj.items()}

        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            return [self._safe_serialize(item) for item in obj]

        # Handle sets
        if isinstance(obj, set):
            return [self._safe_serialize(item) for item in sorted(obj)]

        # Handle objects with __dict__ attribute
        if hasattr(obj, "__dict__"):
            try:
                return self._safe_serialize(obj.__dict__)
            except Exception:
                # Fallback to string representation
                try:
                    return str(obj)
                except Exception:
                    return f"<{type(obj).__name__}: serialization failed>"

        # Final fallback - try direct JSON serialization, then string
        try:
            json.dumps(obj)  # Test if it's JSON serializable
            return obj
        except (TypeError, ValueError):
            return str(obj)


# Create a default JSON formatter instance for backward compatibility
default_json_formatter = JSONFormatter()


def format_threads_json(threads: List[ReviewThread]) -> str:
    """Convenience function for formatting threads as JSON.

    Args:
        threads: List of ReviewThread objects to format.

    Returns:
        JSON string representation of the threads.
    """
    return default_json_formatter.format_threads(threads)


def format_comments_json(comments: List[Comment]) -> str:
    """Convenience function for formatting comments as JSON.

    Args:
        comments: List of Comment objects to format.

    Returns:
        JSON string representation of the comments.
    """
    return default_json_formatter.format_comments(comments)


def format_object_json(obj: Any) -> str:
    """Convenience function for formatting any object as JSON.

    Args:
        obj: Object to format.

    Returns:
        JSON string representation of the object.
    """
    return default_json_formatter.format_object(obj)
