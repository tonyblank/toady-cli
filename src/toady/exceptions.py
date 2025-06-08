"""Comprehensive exception hierarchy for toady CLI application.

This module defines all custom exception classes used throughout the toady application,
providing a centralized hierarchy for error handling and reporting.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCode(Enum):
    """Standardized error codes for different error types."""

    # General errors (1000-1099)
    UNKNOWN_ERROR = 1000
    CONFIGURATION_ERROR = 1001
    DEPENDENCY_ERROR = 1002

    # Validation errors (1100-1199)
    VALIDATION_ERROR = 1100
    INVALID_INPUT = 1101
    INVALID_FORMAT = 1102
    MISSING_REQUIRED_FIELD = 1103
    VALUE_OUT_OF_RANGE = 1104

    # File operation errors (1200-1299)
    FILE_NOT_FOUND = 1200
    FILE_PERMISSION_ERROR = 1201
    FILE_READ_ERROR = 1202
    FILE_WRITE_ERROR = 1203
    DIRECTORY_NOT_FOUND = 1204

    # Network errors (1300-1399)
    NETWORK_ERROR = 1300
    CONNECTION_TIMEOUT = 1301
    CONNECTION_REFUSED = 1302
    DNS_RESOLUTION_ERROR = 1303

    # GitHub API errors (1400-1499)
    GITHUB_API_ERROR = 1400
    GITHUB_AUTHENTICATION_ERROR = 1401
    GITHUB_RATE_LIMIT_ERROR = 1402
    GITHUB_TIMEOUT_ERROR = 1403
    GITHUB_NOT_FOUND_ERROR = 1404
    GITHUB_PERMISSION_ERROR = 1405
    GITHUB_CLI_NOT_FOUND = 1406

    # Command execution errors (1500-1599)
    COMMAND_EXECUTION_ERROR = 1500
    COMMAND_NOT_FOUND = 1501
    COMMAND_TIMEOUT = 1502
    COMMAND_PERMISSION_ERROR = 1503

    # Service-specific errors (1600-1699)
    FETCH_SERVICE_ERROR = 1600
    REPLY_SERVICE_ERROR = 1601
    RESOLVE_SERVICE_ERROR = 1602
    COMMENT_NOT_FOUND = 1603
    THREAD_NOT_FOUND = 1604


class ToadyError(Exception):
    """Base exception class for all toady application errors.

    This is the root exception class that all other toady-specific exceptions
    inherit from. It provides common functionality for error codes, severity
    levels, and contextual information.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        """Initialize a ToadyError.

        Args:
            message: Human-readable error message.
            error_code: Standardized error code for this error type.
            severity: Severity level of the error.
            context: Additional context information about the error.
            suggestions: List of suggestions for resolving the error.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.suggestions = suggestions or []

    def __str__(self) -> str:
        """Return a string representation of the error."""
        return f"[{self.error_code.name}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary representation.

        Returns:
            Dictionary containing error details for JSON serialization.
        """
        return {
            "error": self.error_code.name,
            "error_code": self.error_code.value,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context,
            "suggestions": self.suggestions,
        }


class ValidationError(ToadyError):
    """Raised when input validation fails.

    This exception is used for all types of input validation failures,
    including invalid command-line arguments, malformed data, and
    constraint violations.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        expected_format: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a ValidationError.

        Args:
            message: Human-readable error message.
            field_name: Name of the field that failed validation.
            invalid_value: The value that failed validation.
            expected_format: Description of the expected format.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.VALIDATION_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.MEDIUM),
            **kwargs,
        )
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.expected_format = expected_format

        # Add field-specific context
        if field_name:
            self.context["field_name"] = field_name
        if invalid_value is not None:
            self.context["invalid_value"] = str(invalid_value)
        if expected_format:
            self.context["expected_format"] = expected_format


class ConfigurationError(ToadyError):
    """Raised when configuration-related errors occur.

    This includes missing configuration files, invalid configuration values,
    and environment setup issues.
    """

    def __init__(
        self, message: str, config_key: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a ConfigurationError.

        Args:
            message: Human-readable error message.
            config_key: The configuration key that caused the error.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.CONFIGURATION_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.HIGH),
            **kwargs,
        )
        self.config_key = config_key
        if config_key:
            self.context["config_key"] = config_key


class FileOperationError(ToadyError):
    """Raised when file system operations fail.

    This includes file not found, permission denied, and other I/O errors.
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a FileOperationError.

        Args:
            message: Human-readable error message.
            file_path: Path to the file that caused the error.
            operation: The operation that was being performed.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.FILE_NOT_FOUND),
            severity=kwargs.pop("severity", ErrorSeverity.MEDIUM),
            **kwargs,
        )
        self.file_path = file_path
        self.operation = operation
        if file_path:
            self.context["file_path"] = file_path
        if operation:
            self.context["operation"] = operation


class NetworkError(ToadyError):
    """Raised when network-related operations fail.

    This includes connection timeouts, DNS resolution failures, and
    other network connectivity issues.
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a NetworkError.

        Args:
            message: Human-readable error message.
            url: The URL that caused the error.
            status_code: HTTP status code if applicable.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.NETWORK_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.HIGH),
            **kwargs,
        )
        self.url = url
        self.status_code = status_code
        if url:
            self.context["url"] = url
        if status_code:
            self.context["status_code"] = status_code


class GitHubServiceError(ToadyError):
    """Base exception for GitHub service errors.

    This is the parent class for all GitHub-related errors, including
    API failures, authentication issues, and CLI errors.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize a GitHubServiceError.

        Args:
            message: Human-readable error message.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.GITHUB_API_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.HIGH),
            **kwargs,
        )


class GitHubCLINotFoundError(GitHubServiceError):
    """Raised when gh CLI is not found or not installed."""

    def __init__(
        self, message: str = "GitHub CLI (gh) not found", **kwargs: Any
    ) -> None:
        """Initialize a GitHubCLINotFoundError.

        Args:
            message: Human-readable error message.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_CLI_NOT_FOUND,
            severity=ErrorSeverity.CRITICAL,
            suggestions=[
                "Install GitHub CLI: https://cli.github.com/",
                "Ensure 'gh' is in your PATH",
                "Run 'gh auth login' to authenticate",
            ],
            **kwargs,
        )


class GitHubAuthenticationError(GitHubServiceError):
    """Raised when gh CLI authentication fails."""

    def __init__(
        self, message: str = "GitHub authentication failed", **kwargs: Any
    ) -> None:
        """Initialize a GitHubAuthenticationError.

        Args:
            message: Human-readable error message.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_AUTHENTICATION_ERROR,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Run 'gh auth login' to authenticate",
                "Check your authentication status: 'gh auth status'",
                "Ensure you have the required permissions",
            ],
            **kwargs,
        )


class GitHubAPIError(GitHubServiceError):
    """Raised when GitHub API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        api_endpoint: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a GitHubAPIError.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the API response.
            api_endpoint: The API endpoint that failed.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_API_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )
        self.status_code = status_code
        self.api_endpoint = api_endpoint
        if status_code:
            self.context["status_code"] = status_code
        if api_endpoint:
            self.context["api_endpoint"] = api_endpoint


class GitHubTimeoutError(GitHubServiceError):
    """Raised when GitHub CLI commands timeout."""

    def __init__(
        self,
        message: str = "GitHub CLI command timed out",
        timeout_duration: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a GitHubTimeoutError.

        Args:
            message: Human-readable error message.
            timeout_duration: The timeout duration in seconds.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_TIMEOUT_ERROR,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Try again with a longer timeout",
                "Check your internet connection",
                "Verify GitHub API status",
            ],
            **kwargs,
        )
        self.timeout_duration = timeout_duration
        if timeout_duration:
            self.context["timeout_duration"] = timeout_duration


class GitHubRateLimitError(GitHubServiceError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_time: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a GitHubRateLimitError.

        Args:
            message: Human-readable error message.
            reset_time: When the rate limit resets.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_RATE_LIMIT_ERROR,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Wait for the rate limit to reset",
                "Use authenticated requests for higher limits",
                "Check rate limit status: 'gh api rate_limit'",
            ],
            **kwargs,
        )
        self.reset_time = reset_time
        if reset_time:
            self.context["reset_time"] = reset_time


class GitHubNotFoundError(GitHubServiceError):
    """Raised when GitHub resources are not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a GitHubNotFoundError.

        Args:
            message: Human-readable error message.
            resource_type: Type of resource (e.g., 'pull_request', 'comment').
            resource_id: ID of the resource that was not found.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_NOT_FOUND_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id
        if resource_type:
            self.context["resource_type"] = resource_type
        if resource_id:
            self.context["resource_id"] = resource_id


class GitHubPermissionError(GitHubServiceError):
    """Raised when user lacks permission for GitHub operations."""

    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a GitHubPermissionError.

        Args:
            message: Human-readable error message.
            required_permission: The permission that is required.
            resource: The resource that requires permission.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_PERMISSION_ERROR,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Ensure you have the required permissions",
                "Contact the repository owner if needed",
                "Check if the repository is private",
            ],
            **kwargs,
        )
        self.required_permission = required_permission
        self.resource = resource
        if required_permission:
            self.context["required_permission"] = required_permission
        if resource:
            self.context["resource"] = resource


class CommandExecutionError(ToadyError):
    """Raised when external command execution fails."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a CommandExecutionError.

        Args:
            message: Human-readable error message.
            command: The command that failed.
            exit_code: Exit code from the failed command.
            stderr: Standard error output from the command.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.COMMAND_EXECUTION_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.HIGH),
            **kwargs,
        )
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        if command:
            self.context["command"] = command
        if exit_code is not None:
            self.context["exit_code"] = exit_code
        if stderr:
            self.context["stderr"] = stderr


# Service-specific exceptions
class FetchServiceError(ToadyError):
    """Base exception for fetch service errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize a FetchServiceError.

        Args:
            message: Human-readable error message.
            **kwargs: Additional arguments passed to ToadyError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.FETCH_SERVICE_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.MEDIUM),
            **kwargs,
        )


class ReplyServiceError(GitHubServiceError):
    """Base exception for reply service errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize a ReplyServiceError.

        Args:
            message: Human-readable error message.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.REPLY_SERVICE_ERROR),
            **kwargs,
        )


class CommentNotFoundError(ReplyServiceError):
    """Raised when the specified comment cannot be found."""

    def __init__(
        self, message: str, comment_id: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a CommentNotFoundError.

        Args:
            message: Human-readable error message.
            comment_id: The comment ID that was not found.
            **kwargs: Additional arguments passed to ReplyServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.COMMENT_NOT_FOUND,
            suggestions=[
                "Verify the comment ID is correct",
                "Check if the comment has been deleted",
                "Ensure you have access to the repository",
            ],
            **kwargs,
        )
        self.comment_id = comment_id
        if comment_id:
            self.context["comment_id"] = comment_id


class ResolveServiceError(GitHubServiceError):
    """Base exception for resolve service errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize a ResolveServiceError.

        Args:
            message: Human-readable error message.
            **kwargs: Additional arguments passed to GitHubServiceError.
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.RESOLVE_SERVICE_ERROR),
            **kwargs,
        )


class ThreadNotFoundError(ResolveServiceError):
    """Raised when the specified thread cannot be found."""

    def __init__(
        self, message: str, thread_id: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a ThreadNotFoundError.

        Args:
            message: Human-readable error message.
            thread_id: The thread ID that was not found.
            **kwargs: Additional arguments passed to ResolveServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.THREAD_NOT_FOUND,
            suggestions=[
                "Verify the thread ID is correct",
                "Check if the thread exists in the pull request",
                "Ensure you have access to the repository",
            ],
            **kwargs,
        )
        self.thread_id = thread_id
        if thread_id:
            self.context["thread_id"] = thread_id


class ThreadPermissionError(ResolveServiceError):
    """Raised when user lacks permission to resolve/unresolve the thread."""

    def __init__(
        self, message: str, thread_id: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a ThreadPermissionError.

        Args:
            message: Human-readable error message.
            thread_id: The thread ID that requires permission.
            **kwargs: Additional arguments passed to ResolveServiceError.
        """
        super().__init__(
            message,
            error_code=ErrorCode.GITHUB_PERMISSION_ERROR,
            suggestions=[
                "Ensure you have write access to the repository",
                "Contact the repository owner for permissions",
                "Check if you are the thread author or have maintainer access",
            ],
            **kwargs,
        )
        self.thread_id = thread_id
        if thread_id:
            self.context["thread_id"] = thread_id


# Backward compatibility aliases for existing code
# These can be removed in a future version after migrating all imports
GitHubCLINotFound = GitHubCLINotFoundError  # For backward compatibility


def create_validation_error(
    field_name: str,
    invalid_value: Any,
    expected_format: str,
    message: Optional[str] = None,
) -> ValidationError:
    """Create a standardized validation error.

    Args:
        field_name: Name of the field that failed validation.
        invalid_value: The value that failed validation.
        expected_format: Description of the expected format.
        message: Optional custom message. If not provided, generates a standard message.

    Returns:
        Configured ValidationError instance.
    """
    if message is None:
        message = (
            f"Invalid {field_name}: '{invalid_value}'. Expected {expected_format}."
        )

    return ValidationError(
        message=message,
        field_name=field_name,
        invalid_value=invalid_value,
        expected_format=expected_format,
    )


def create_github_error(
    message: str,
    status_code: Optional[int] = None,
    api_endpoint: Optional[str] = None,
) -> GitHubAPIError:
    """Create a standardized GitHub API error.

    Args:
        message: Human-readable error message.
        status_code: HTTP status code from the API response.
        api_endpoint: The API endpoint that failed.

    Returns:
        Configured GitHubAPIError instance.
    """
    return GitHubAPIError(
        message=message,
        status_code=status_code,
        api_endpoint=api_endpoint,
    )
