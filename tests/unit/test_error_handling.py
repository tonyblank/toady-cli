"""Tests for error handling and user-friendly error messages."""

import sys
from unittest.mock import patch

from toady.error_handling import (
    ErrorMessageFormatter,
    ErrorMessageTemplates,
    ExitCode,
    create_user_friendly_error,
    handle_error,
)
from toady.exceptions import (
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


class TestExitCode:
    """Test exit code constants."""

    def test_exit_code_values(self):
        """Test that exit codes have expected values."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.GENERAL_ERROR == 1
        assert ExitCode.VALIDATION_ERROR == 10
        assert ExitCode.GITHUB_AUTH_ERROR == 41
        assert ExitCode.GITHUB_CLI_NOT_FOUND == 45


class TestErrorMessageFormatter:
    """Test error message formatting."""

    def test_format_github_cli_not_found_error(self):
        """Test formatting of GitHub CLI not found error."""
        error = GitHubCLINotFoundError()
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ GitHub CLI (gh) not found" in formatted
        assert "Install GitHub CLI" in formatted
        assert "gh auth login" in formatted

    def test_format_github_auth_error(self):
        """Test formatting of GitHub authentication error."""
        error = GitHubAuthenticationError("Authentication failed")
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ GitHub authentication failed" in formatted
        assert "gh auth login" in formatted
        assert "gh auth status" in formatted

    def test_format_github_rate_limit_error(self):
        """Test formatting of GitHub rate limit error."""
        error = GitHubRateLimitError(
            "Rate limit exceeded", reset_time="2024-01-01T12:00:00Z"
        )
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ GitHub API rate limit exceeded" in formatted
        assert "Rate limit resets at: 2024-01-01T12:00:00Z" in formatted
        assert "Wait for the rate limit to reset" in formatted

    def test_format_github_not_found_error(self):
        """Test formatting of GitHub not found error."""
        error = GitHubNotFoundError("Resource not found", resource_type="pull request")
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ GitHub pull request not found" in formatted
        assert "Verify the ID or number is correct" in formatted

    def test_format_validation_error(self):
        """Test formatting of validation error."""
        error = ValidationError(
            "Invalid PR number",
            field_name="pr_number",
            expected_format="positive integer",
        )
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ Invalid input provided" in formatted
        assert "Problem with: pr_number" in formatted
        assert "Expected format: positive integer" in formatted

    def test_format_network_error(self):
        """Test formatting of network error."""
        error = NetworkError("Connection failed")
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ Network connection failed" in formatted
        assert "Check your internet connection" in formatted

    def test_format_command_execution_error(self):
        """Test formatting of command execution error."""
        error = CommandExecutionError("Command failed", command="gh api")
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ Command execution failed" in formatted
        assert "Failed command: gh api" in formatted

    def test_format_file_operation_error(self):
        """Test formatting of file operation error."""
        error = FileOperationError("File not found", file_path="/path/to/file")
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ File operation failed" in formatted
        assert "File path: /path/to/file" in formatted

    def test_format_toady_error_with_suggestions(self):
        """Test formatting of ToadyError with suggestions."""
        error = ToadyError("Custom error", suggestions=["Try this", "Try that"])
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ Custom error" in formatted
        assert "🔧 Suggestions:" in formatted
        assert "• Try this" in formatted
        assert "• Try that" in formatted

    def test_format_unexpected_error(self):
        """Test formatting of unexpected error."""
        error = ValueError("Unexpected error")
        formatted = ErrorMessageFormatter.format_error(error)

        assert "❌ An unexpected error occurred" in formatted
        assert "Error details: Unexpected error" in formatted

    def test_get_exit_code_github_errors(self):
        """Test exit code mapping for GitHub errors."""
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubCLINotFoundError())
            == ExitCode.GITHUB_CLI_NOT_FOUND
        )
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubAuthenticationError())
            == ExitCode.GITHUB_AUTH_ERROR
        )
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubRateLimitError())
            == ExitCode.GITHUB_RATE_LIMIT
        )
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubNotFoundError("Not found"))
            == ExitCode.GITHUB_NOT_FOUND
        )
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubPermissionError("Forbidden"))
            == ExitCode.GITHUB_PERMISSION_ERROR
        )
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubTimeoutError())
            == ExitCode.GITHUB_TIMEOUT
        )
        assert (
            ErrorMessageFormatter.get_exit_code(GitHubAPIError("API error"))
            == ExitCode.GITHUB_ERROR
        )

    def test_get_exit_code_other_errors(self):
        """Test exit code mapping for other error types."""
        assert (
            ErrorMessageFormatter.get_exit_code(ValidationError("Invalid"))
            == ExitCode.VALIDATION_ERROR
        )
        assert (
            ErrorMessageFormatter.get_exit_code(NetworkError("Network"))
            == ExitCode.NETWORK_ERROR
        )
        assert (
            ErrorMessageFormatter.get_exit_code(CommandExecutionError("Command"))
            == ExitCode.COMMAND_ERROR
        )
        assert (
            ErrorMessageFormatter.get_exit_code(FileOperationError("File"))
            == ExitCode.FILE_NOT_FOUND
        )
        assert (
            ErrorMessageFormatter.get_exit_code(ConfigurationError("Config"))
            == ExitCode.CONFIGURATION_ERROR
        )

    def test_get_exit_code_service_errors(self):
        """Test exit code mapping for service-specific errors."""
        fetch_error = ToadyError(
            "Fetch failed", error_code=ErrorCode.FETCH_SERVICE_ERROR
        )
        reply_error = ToadyError(
            "Reply failed", error_code=ErrorCode.REPLY_SERVICE_ERROR
        )
        resolve_error = ToadyError(
            "Resolve failed", error_code=ErrorCode.RESOLVE_SERVICE_ERROR
        )

        assert ErrorMessageFormatter.get_exit_code(fetch_error) == ExitCode.FETCH_ERROR
        assert ErrorMessageFormatter.get_exit_code(reply_error) == ExitCode.REPLY_ERROR
        assert (
            ErrorMessageFormatter.get_exit_code(resolve_error) == ExitCode.RESOLVE_ERROR
        )

    def test_get_exit_code_unexpected_error(self):
        """Test exit code for unexpected errors."""
        error = ValueError("Unexpected")
        assert ErrorMessageFormatter.get_exit_code(error) == ExitCode.GENERAL_ERROR


class TestHandleError:
    """Test error handling function."""

    @patch("sys.exit")
    @patch("builtins.print")
    def test_handle_error_basic(self, mock_print, mock_exit):
        """Test basic error handling."""
        error = GitHubCLINotFoundError()

        handle_error(error, show_traceback=False)

        # Check that error message was printed to stderr
        mock_print.assert_called()
        call_args = mock_print.call_args
        assert call_args[1]["file"] == sys.stderr

        # Check that exit was called with correct code
        mock_exit.assert_called_once_with(ExitCode.GITHUB_CLI_NOT_FOUND)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("traceback.print_exc")
    def test_handle_error_with_traceback(self, mock_traceback, mock_print, mock_exit):
        """Test error handling with traceback."""
        error = ValidationError("Test error")

        handle_error(error, show_traceback=True)

        # Check that traceback was printed
        mock_traceback.assert_called_once()

        # Check that exit was called with correct code
        mock_exit.assert_called_once_with(ExitCode.VALIDATION_ERROR)


class TestCreateUserFriendlyError:
    """Test user-friendly error message creation."""

    def test_create_basic_error(self):
        """Test creating basic error message."""
        message = create_user_friendly_error("Invalid input provided")

        assert "❌ Invalid input provided" in message

    def test_create_error_with_suggestions(self):
        """Test creating error message with suggestions."""
        message = create_user_friendly_error(
            "Authentication failed",
            suggestions=["Run 'gh auth login'", "Check permissions"],
        )

        assert "❌ Authentication failed" in message
        assert "🔧 To fix this issue:" in message
        assert "1. Run 'gh auth login'" in message
        assert "2. Check permissions" in message

    def test_create_error_with_context(self):
        """Test creating error message with context."""
        message = create_user_friendly_error(
            "File operation failed",
            context={"file_path": "/path/to/file", "operation": "read"},
        )

        assert "❌ File operation failed" in message
        assert "🔍 Additional details:" in message
        assert "• file_path: /path/to/file" in message
        assert "• operation: read" in message

    def test_create_error_with_suggestions_and_context(self):
        """Test creating error message with both suggestions and context."""
        message = create_user_friendly_error(
            "Connection failed",
            suggestions=["Check internet connection"],
            context={"url": "https://api.github.com"},
        )

        assert "❌ Connection failed" in message
        assert "🔧 To fix this issue:" in message
        assert "1. Check internet connection" in message
        assert "🔍 Additional details:" in message
        assert "• url: https://api.github.com" in message


class TestErrorMessageTemplates:
    """Test error message templates."""

    def test_templates_exist(self):
        """Test that all expected templates exist."""
        assert hasattr(ErrorMessageTemplates, "GITHUB_CLI_NOT_FOUND")
        assert hasattr(ErrorMessageTemplates, "GITHUB_AUTH_ERROR")
        assert hasattr(ErrorMessageTemplates, "GITHUB_RATE_LIMIT")
        assert hasattr(ErrorMessageTemplates, "GITHUB_NOT_FOUND")
        assert hasattr(ErrorMessageTemplates, "GITHUB_PERMISSION_ERROR")
        assert hasattr(ErrorMessageTemplates, "VALIDATION_ERROR")
        assert hasattr(ErrorMessageTemplates, "NETWORK_ERROR")
        assert hasattr(ErrorMessageTemplates, "COMMAND_EXECUTION_ERROR")
        assert hasattr(ErrorMessageTemplates, "FILE_OPERATION_ERROR")
        assert hasattr(ErrorMessageTemplates, "GENERIC_ERROR")

    def test_templates_contain_emojis(self):
        """Test that templates contain user-friendly emojis."""
        assert "❌" in ErrorMessageTemplates.GITHUB_CLI_NOT_FOUND
        assert "🔧" in ErrorMessageTemplates.GITHUB_CLI_NOT_FOUND
        assert "💡" in ErrorMessageTemplates.GITHUB_CLI_NOT_FOUND

    def test_templates_contain_actionable_guidance(self):
        """Test that templates contain actionable guidance."""
        # GitHub CLI template should have install instructions
        assert "Install GitHub CLI" in ErrorMessageTemplates.GITHUB_CLI_NOT_FOUND
        assert "https://cli.github.com/" in ErrorMessageTemplates.GITHUB_CLI_NOT_FOUND

        # Auth template should have auth instructions
        assert "gh auth login" in ErrorMessageTemplates.GITHUB_AUTH_ERROR
        assert "gh auth status" in ErrorMessageTemplates.GITHUB_AUTH_ERROR

        # Rate limit template should have wait instructions
        assert (
            "Wait for the rate limit to reset"
            in ErrorMessageTemplates.GITHUB_RATE_LIMIT
        )
        assert "gh api rate_limit" in ErrorMessageTemplates.GITHUB_RATE_LIMIT
