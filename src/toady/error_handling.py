"""User-friendly error message system and exit code handling for toady CLI.

This module provides centralized error message templates, exit code constants,
and utilities for translating technical errors into user-friendly messages
with helpful guidance for resolution.
"""

import sys
from enum import IntEnum
from typing import Any, Dict, List, Optional

from .exceptions import (
    CommandExecutionError,
    ConfigurationError,
    ErrorCode,
    FileOperationError,
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubCLINotFoundError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubTimeoutError,
    NetworkError,
    ToadyError,
    ValidationError,
)


class ExitCode(IntEnum):
    """Standard exit codes for the toady CLI application."""

    # Success
    SUCCESS = 0

    # General errors (1-9)
    GENERAL_ERROR = 1
    INVALID_USAGE = 2
    CONFIGURATION_ERROR = 3
    DEPENDENCY_ERROR = 4

    # Validation errors (10-19)
    VALIDATION_ERROR = 10
    INVALID_INPUT = 11
    INVALID_FORMAT = 12

    # File operation errors (20-29)
    FILE_NOT_FOUND = 20
    FILE_PERMISSION_ERROR = 21
    FILE_READ_ERROR = 22
    FILE_WRITE_ERROR = 23

    # Network errors (30-39)
    NETWORK_ERROR = 30
    CONNECTION_TIMEOUT = 31
    CONNECTION_REFUSED = 32

    # GitHub errors (40-59)
    GITHUB_ERROR = 40
    GITHUB_AUTH_ERROR = 41
    GITHUB_RATE_LIMIT = 42
    GITHUB_NOT_FOUND = 43
    GITHUB_PERMISSION_ERROR = 44
    GITHUB_CLI_NOT_FOUND = 45
    GITHUB_TIMEOUT = 46

    # Command execution errors (60-69)
    COMMAND_ERROR = 60
    COMMAND_NOT_FOUND = 61
    COMMAND_TIMEOUT = 62

    # Service-specific errors (70-89)
    FETCH_ERROR = 70
    REPLY_ERROR = 71
    RESOLVE_ERROR = 72


class ErrorMessageTemplates:
    """Templates for user-friendly error messages."""

    # GitHub CLI related messages
    GITHUB_CLI_NOT_FOUND = """
❌ GitHub CLI (gh) not found

The toady CLI requires GitHub CLI to interact with GitHub APIs.

🔧 To fix this issue:
   1. Install GitHub CLI: https://cli.github.com/
   2. Ensure 'gh' is in your PATH
   3. Run 'gh auth login' to authenticate

💡 Quick install options:
   • macOS: brew install gh
   • Windows: winget install GitHub.cli
   • Linux: See https://github.com/cli/cli/blob/trunk/docs/install_linux.md
"""

    GITHUB_AUTH_ERROR = """
❌ GitHub authentication failed

You need to authenticate with GitHub to use toady commands.

🔧 To fix this issue:
   1. Run 'gh auth login' to authenticate
   2. Check your authentication: 'gh auth status'
   3. Ensure you have access to the repository

💡 Authentication help:
   • Personal access tokens need 'repo' scope
   • For organizations, ensure SSO is enabled if required
"""

    GITHUB_RATE_LIMIT = """
❌ GitHub API rate limit exceeded

You've hit the GitHub API rate limit. Please wait before trying again.

🔧 To fix this issue:
   1. Wait for the rate limit to reset (usually within an hour)
   2. Use authenticated requests for higher limits
   3. Check current rate limit: 'gh api rate_limit'

💡 Rate limit tips:
   • Authenticated users get 5,000 requests/hour
   • Unauthenticated users get 60 requests/hour
"""

    GITHUB_NOT_FOUND = """
❌ GitHub resource not found

The requested resource (PR, comment, or thread) could not be found.

🔧 To fix this issue:
   1. Verify the ID or number is correct
   2. Check if the resource has been deleted
   3. Ensure you have access to the repository
   4. Confirm you're in the correct repository context

💡 Common causes:
   • Typos in PR numbers or IDs
   • Resources from private repositories
   • Deleted comments or threads
"""

    GITHUB_PERMISSION_ERROR = """
❌ Insufficient permissions

You don't have the required permissions to perform this action.

🔧 To fix this issue:
   1. Ensure you have write access to the repository
   2. Contact the repository owner for permissions
   3. Check if you're the author or have maintainer access

💡 Permission requirements:
   • Replying to comments: read access
   • Resolving threads: write access or be the thread author
   • Fetching data: read access
"""

    VALIDATION_ERROR = """
❌ Invalid input provided

The command received invalid or malformed input.

🔧 To fix this issue:
   1. Check the command syntax: 'toady --help'
   2. Verify all required parameters are provided
   3. Ensure input formats match requirements

💡 Common validation issues:
   • Missing required flags (--pr, --comment-id, etc.)
   • Invalid ID formats
   • Out-of-range values
"""

    NETWORK_ERROR = """
❌ Network connection failed

Unable to connect to GitHub or complete the network request.

🔧 To fix this issue:
   1. Check your internet connection
   2. Verify GitHub's status: https://www.githubstatus.com/
   3. Try again in a few moments
   4. Check for firewall or proxy restrictions

💡 Network troubleshooting:
   • Test connection: ping github.com
   • Check DNS: nslookup github.com
   • Verify proxy settings if applicable
"""

    COMMAND_EXECUTION_ERROR = """
❌ Command execution failed

An external command failed to execute properly.

🔧 To fix this issue:
   1. Ensure all required tools are installed
   2. Check that commands are in your PATH
   3. Verify command syntax and parameters
   4. Check file permissions if applicable

💡 Common causes:
   • Missing dependencies
   • Incorrect PATH configuration
   • Permission issues
"""

    FILE_OPERATION_ERROR = """
❌ File operation failed

Unable to read, write, or access the specified file.

🔧 To fix this issue:
   1. Verify the file path is correct
   2. Check file and directory permissions
   3. Ensure the parent directory exists
   4. Check available disk space

💡 File troubleshooting:
   • Use absolute paths when possible
   • Check file ownership and permissions
   • Verify the file hasn't been moved or deleted
"""

    GENERIC_ERROR = """
❌ An unexpected error occurred

Something went wrong while processing your request.

🔧 To fix this issue:
   1. Try the command again
   2. Check the command syntax and parameters
   3. Ensure all dependencies are properly installed
   4. If the problem persists, please report it as a bug

💡 Getting help:
   • Use 'toady --help' for command reference
   • Check the documentation for troubleshooting
   • Report bugs with details about what you were trying to do
"""


class ErrorMessageFormatter:
    """Formats error messages for user-friendly display."""

    @staticmethod
    def format_error(error: Exception) -> str:
        """Format an error for user-friendly display.

        Args:
            error: The exception to format.

        Returns:
            Formatted error message with suggestions.
        """
        # Dictionary mapping for simple error types with static templates
        simple_error_templates = {
            GitHubCLINotFoundError: ErrorMessageTemplates.GITHUB_CLI_NOT_FOUND,
            GitHubAuthenticationError: ErrorMessageTemplates.GITHUB_AUTH_ERROR,
            GitHubPermissionError: ErrorMessageTemplates.GITHUB_PERMISSION_ERROR,
            NetworkError: ErrorMessageTemplates.NETWORK_ERROR,
        }

        # Check simple mappings first
        error_type = type(error)
        if error_type in simple_error_templates:
            return simple_error_templates[error_type]

        # Handle errors requiring dynamic content assembly
        if isinstance(error, GitHubRateLimitError):
            template = ErrorMessageTemplates.GITHUB_RATE_LIMIT
            if hasattr(error, "reset_time") and error.reset_time:
                template += f"\n🕒 Rate limit resets at: {error.reset_time}"
            return template

        if isinstance(error, GitHubNotFoundError):
            template = ErrorMessageTemplates.GITHUB_NOT_FOUND
            if hasattr(error, "resource_type") and error.resource_type:
                template = template.replace("resource", error.resource_type)
            return template

        if isinstance(error, ValidationError):
            template = ErrorMessageTemplates.VALIDATION_ERROR
            if hasattr(error, "field_name") and error.field_name:
                template += f"\n❌ Problem with: {error.field_name}"
            if hasattr(error, "expected_format") and error.expected_format:
                template += f"\n📋 Expected format: {error.expected_format}"
            return template

        if isinstance(error, CommandExecutionError):
            template = ErrorMessageTemplates.COMMAND_EXECUTION_ERROR
            if hasattr(error, "command") and error.command:
                template += f"\n💻 Failed command: {error.command}"
            return template

        if isinstance(error, FileOperationError):
            template = ErrorMessageTemplates.FILE_OPERATION_ERROR
            if hasattr(error, "file_path") and error.file_path:
                template += f"\n📁 File path: {error.file_path}"
            return template

        if isinstance(error, ToadyError):
            # For other ToadyError subclasses, show the message with suggestions
            message = f"❌ {error.message}\n"
            if error.suggestions:
                message += "\n🔧 Suggestions:\n"
                for suggestion in error.suggestions:
                    message += f"   • {suggestion}\n"
            return message

        # For unexpected errors, use the generic template
        return (
            ErrorMessageTemplates.GENERIC_ERROR + f"\n\n🔍 Error details: {str(error)}"
        )

    @staticmethod
    def get_exit_code(error: Exception) -> int:
        """Get the appropriate exit code for an error.

        Args:
            error: The exception to get an exit code for.

        Returns:
            Appropriate exit code integer.
        """
        # Dictionary mapping for direct exception type to exit code mapping
        exit_code_mapping = {
            GitHubCLINotFoundError: ExitCode.GITHUB_CLI_NOT_FOUND,
            GitHubAuthenticationError: ExitCode.GITHUB_AUTH_ERROR,
            GitHubRateLimitError: ExitCode.GITHUB_RATE_LIMIT,
            GitHubNotFoundError: ExitCode.GITHUB_NOT_FOUND,
            GitHubPermissionError: ExitCode.GITHUB_PERMISSION_ERROR,
            GitHubTimeoutError: ExitCode.GITHUB_TIMEOUT,
            GitHubAPIError: ExitCode.GITHUB_ERROR,
            ValidationError: ExitCode.VALIDATION_ERROR,
            NetworkError: ExitCode.NETWORK_ERROR,
            CommandExecutionError: ExitCode.COMMAND_ERROR,
            FileOperationError: ExitCode.FILE_NOT_FOUND,
            ConfigurationError: ExitCode.CONFIGURATION_ERROR,
        }

        # Check direct exception type mapping
        error_type = type(error)
        if error_type in exit_code_mapping:
            return exit_code_mapping[error_type]

        # Handle ToadyError with error code mapping
        if isinstance(error, ToadyError):
            error_code_mapping = {
                ErrorCode.FETCH_SERVICE_ERROR: ExitCode.FETCH_ERROR,
                ErrorCode.REPLY_SERVICE_ERROR: ExitCode.REPLY_ERROR,
                ErrorCode.RESOLVE_SERVICE_ERROR: ExitCode.RESOLVE_ERROR,
            }
            return error_code_mapping.get(error.error_code, ExitCode.GENERAL_ERROR)

        # Default fallback
        return ExitCode.GENERAL_ERROR


def handle_error(error: Exception, show_traceback: bool = False) -> None:
    """Handle an error by displaying user-friendly message and exiting.

    Args:
        error: The exception to handle.
        show_traceback: Whether to show the full traceback for debugging.
    """
    # Format and display the error message
    message = ErrorMessageFormatter.format_error(error)
    print(message, file=sys.stderr)

    # Show traceback if requested (for debugging)
    if show_traceback:
        import traceback

        print("\n🔍 Technical details:", file=sys.stderr)
        traceback.print_exc()

    # Exit with appropriate code
    exit_code = ErrorMessageFormatter.get_exit_code(error)
    sys.exit(exit_code)


def create_user_friendly_error(
    message: str,
    suggestions: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a user-friendly error message.

    Args:
        message: The main error message.
        suggestions: List of suggestions for resolving the error.
        context: Additional context information.

    Returns:
        Formatted user-friendly error message.
    """
    formatted_message = f"❌ {message}\n"

    if suggestions:
        formatted_message += "\n🔧 To fix this issue:\n"
        for i, suggestion in enumerate(suggestions, 1):
            formatted_message += f"   {i}. {suggestion}\n"

    if context:
        formatted_message += "\n🔍 Additional details:\n"
        for key, value in context.items():
            formatted_message += f"   • {key}: {value}\n"

    return formatted_message
