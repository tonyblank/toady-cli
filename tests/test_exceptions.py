"""Tests for the exception hierarchy in toady.exceptions."""

import pytest
from toady.exceptions import (
    ErrorCode,
    ErrorSeverity,
    ToadyError,
    ValidationError,
    ConfigurationError,
    FileOperationError,
    NetworkError,
    GitHubServiceError,
    GitHubCLINotFoundError,
    GitHubAuthenticationError,
    GitHubAPIError,
    GitHubTimeoutError,
    GitHubRateLimitError,
    GitHubNotFoundError,
    GitHubPermissionError,
    CommandExecutionError,
    FetchServiceError,
    ReplyServiceError,
    CommentNotFoundError,
    ResolveServiceError,
    ThreadNotFoundError,
    ThreadPermissionError,
    create_validation_error,
    create_github_error,
)


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_code_values(self):
        """Test that error codes have expected values."""
        assert ErrorCode.UNKNOWN_ERROR.value == 1000
        assert ErrorCode.VALIDATION_ERROR.value == 1100
        assert ErrorCode.FILE_NOT_FOUND.value == 1200
        assert ErrorCode.NETWORK_ERROR.value == 1300
        assert ErrorCode.GITHUB_API_ERROR.value == 1400
        assert ErrorCode.COMMAND_EXECUTION_ERROR.value == 1500
        assert ErrorCode.FETCH_SERVICE_ERROR.value == 1600

    def test_error_code_names(self):
        """Test that error codes have expected names."""
        assert ErrorCode.GITHUB_AUTHENTICATION_ERROR.name == "GITHUB_AUTHENTICATION_ERROR"
        assert ErrorCode.GITHUB_RATE_LIMIT_ERROR.name == "GITHUB_RATE_LIMIT_ERROR"
        assert ErrorCode.COMMENT_NOT_FOUND.name == "COMMENT_NOT_FOUND"
        assert ErrorCode.THREAD_NOT_FOUND.name == "THREAD_NOT_FOUND"


class TestErrorSeverity:
    """Test ErrorSeverity enum."""

    def test_severity_values(self):
        """Test that severity levels have expected values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestToadyError:
    """Test ToadyError base exception class."""

    def test_basic_creation(self):
        """Test basic ToadyError creation."""
        error = ToadyError("Test error message")
        assert str(error) == "[UNKNOWN_ERROR] Test error message"
        assert error.message == "Test error message"
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context == {}
        assert error.suggestions == []

    def test_creation_with_all_parameters(self):
        """Test ToadyError creation with all parameters."""
        context = {"test_key": "test_value"}
        suggestions = ["Try this", "Or this"]
        
        error = ToadyError(
            "Custom error",
            error_code=ErrorCode.VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            context=context,
            suggestions=suggestions,
        )
        
        assert error.message == "Custom error"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == context
        assert error.suggestions == suggestions

    def test_to_dict(self):
        """Test ToadyError to_dict method."""
        context = {"field": "value"}
        suggestions = ["Suggestion 1", "Suggestion 2"]
        
        error = ToadyError(
            "Test message",
            error_code=ErrorCode.NETWORK_ERROR,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            suggestions=suggestions,
        )
        
        result = error.to_dict()
        expected = {
            "error": "NETWORK_ERROR",
            "error_code": 1300,
            "message": "Test message",
            "severity": "critical",
            "context": context,
            "suggestions": suggestions,
        }
        assert result == expected

    def test_inheritance_from_exception(self):
        """Test that ToadyError inherits from Exception."""
        error = ToadyError("Test")
        assert isinstance(error, Exception)
        
        # Test that it can be raised and caught
        with pytest.raises(ToadyError) as excinfo:
            raise error
        assert str(excinfo.value) == "[UNKNOWN_ERROR] Test"


class TestValidationError:
    """Test ValidationError class."""

    def test_basic_creation(self):
        """Test basic ValidationError creation."""
        error = ValidationError("Invalid input")
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.field_name is None
        assert error.invalid_value is None
        assert error.expected_format is None

    def test_creation_with_field_details(self):
        """Test ValidationError creation with field details."""
        error = ValidationError(
            "Invalid comment ID",
            field_name="comment_id",
            invalid_value="abc123",
            expected_format="numeric or IC_ prefixed string",
        )
        
        assert error.field_name == "comment_id"
        assert error.invalid_value == "abc123"
        assert error.expected_format == "numeric or IC_ prefixed string"
        assert error.context["field_name"] == "comment_id"
        assert error.context["invalid_value"] == "abc123"
        assert error.context["expected_format"] == "numeric or IC_ prefixed string"

    def test_inheritance(self):
        """Test ValidationError inheritance."""
        error = ValidationError("Test")
        assert isinstance(error, ToadyError)
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_basic_creation(self):
        """Test basic ConfigurationError creation."""
        error = ConfigurationError("Config not found")
        assert error.error_code == ErrorCode.CONFIGURATION_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.config_key is None

    def test_creation_with_config_key(self):
        """Test ConfigurationError creation with config key."""
        error = ConfigurationError("Invalid timeout", config_key="api_timeout")
        assert error.config_key == "api_timeout"
        assert error.context["config_key"] == "api_timeout"


class TestFileOperationError:
    """Test FileOperationError class."""

    def test_basic_creation(self):
        """Test basic FileOperationError creation."""
        error = FileOperationError("File operation failed")
        assert error.error_code == ErrorCode.FILE_NOT_FOUND
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.file_path is None
        assert error.operation is None

    def test_creation_with_details(self):
        """Test FileOperationError creation with details."""
        error = FileOperationError(
            "Cannot read file",
            file_path="/path/to/file.txt",
            operation="read",
        )
        
        assert error.file_path == "/path/to/file.txt"
        assert error.operation == "read"
        assert error.context["file_path"] == "/path/to/file.txt"
        assert error.context["operation"] == "read"


class TestNetworkError:
    """Test NetworkError class."""

    def test_basic_creation(self):
        """Test basic NetworkError creation."""
        error = NetworkError("Network failed")
        assert error.error_code == ErrorCode.NETWORK_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.url is None
        assert error.status_code is None

    def test_creation_with_details(self):
        """Test NetworkError creation with details."""
        error = NetworkError(
            "HTTP error",
            url="https://api.github.com",
            status_code=404,
        )
        
        assert error.url == "https://api.github.com"
        assert error.status_code == 404
        assert error.context["url"] == "https://api.github.com"
        assert error.context["status_code"] == 404


class TestGitHubServiceError:
    """Test GitHubServiceError class."""

    def test_basic_creation(self):
        """Test basic GitHubServiceError creation."""
        error = GitHubServiceError("GitHub API failed")
        assert error.error_code == ErrorCode.GITHUB_API_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert isinstance(error, ToadyError)

    def test_inheritance_hierarchy(self):
        """Test GitHub error inheritance hierarchy."""
        # Test that all GitHub errors inherit from GitHubServiceError
        auth_error = GitHubAuthenticationError()
        api_error = GitHubAPIError("API failed")
        timeout_error = GitHubTimeoutError()
        rate_limit_error = GitHubRateLimitError()
        not_found_error = GitHubNotFoundError("Not found")
        permission_error = GitHubPermissionError("Permission denied")
        
        for error in [auth_error, api_error, timeout_error, rate_limit_error, 
                     not_found_error, permission_error]:
            assert isinstance(error, GitHubServiceError)
            assert isinstance(error, ToadyError)


class TestGitHubCLINotFoundError:
    """Test GitHubCLINotFoundError class."""

    def test_default_creation(self):
        """Test GitHubCLINotFoundError with default message."""
        error = GitHubCLINotFoundError()
        assert "GitHub CLI (gh) not found" in error.message
        assert error.error_code == ErrorCode.GITHUB_CLI_NOT_FOUND
        assert error.severity == ErrorSeverity.CRITICAL
        assert len(error.suggestions) > 0
        assert any("Install GitHub CLI" in s for s in error.suggestions)

    def test_custom_message(self):
        """Test GitHubCLINotFoundError with custom message."""
        error = GitHubCLINotFoundError("Custom CLI error")
        assert error.message == "Custom CLI error"


class TestGitHubAuthenticationError:
    """Test GitHubAuthenticationError class."""

    def test_default_creation(self):
        """Test GitHubAuthenticationError with default message."""
        error = GitHubAuthenticationError()
        assert "authentication failed" in error.message.lower()
        assert error.error_code == ErrorCode.GITHUB_AUTHENTICATION_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert len(error.suggestions) > 0
        assert any("gh auth login" in s for s in error.suggestions)


class TestGitHubAPIError:
    """Test GitHubAPIError class."""

    def test_basic_creation(self):
        """Test basic GitHubAPIError creation."""
        error = GitHubAPIError("API request failed")
        assert error.message == "API request failed"
        assert error.error_code == ErrorCode.GITHUB_API_ERROR
        assert error.status_code is None
        assert error.api_endpoint is None

    def test_creation_with_details(self):
        """Test GitHubAPIError creation with details."""
        error = GitHubAPIError(
            "Repository not found",
            status_code=404,
            api_endpoint="/repos/owner/repo",
        )
        
        assert error.status_code == 404
        assert error.api_endpoint == "/repos/owner/repo"
        assert error.context["status_code"] == 404
        assert error.context["api_endpoint"] == "/repos/owner/repo"


class TestGitHubTimeoutError:
    """Test GitHubTimeoutError class."""

    def test_default_creation(self):
        """Test GitHubTimeoutError with default message."""
        error = GitHubTimeoutError()
        assert "timed out" in error.message.lower()
        assert error.error_code == ErrorCode.GITHUB_TIMEOUT_ERROR
        assert error.timeout_duration is None
        assert len(error.suggestions) > 0

    def test_creation_with_timeout(self):
        """Test GitHubTimeoutError creation with timeout duration."""
        error = GitHubTimeoutError("Command timed out", timeout_duration=30)
        assert error.timeout_duration == 30
        assert error.context["timeout_duration"] == 30


class TestGitHubRateLimitError:
    """Test GitHubRateLimitError class."""

    def test_default_creation(self):
        """Test GitHubRateLimitError with default message."""
        error = GitHubRateLimitError()
        assert "rate limit" in error.message.lower()
        assert error.error_code == ErrorCode.GITHUB_RATE_LIMIT_ERROR
        assert error.reset_time is None
        assert len(error.suggestions) > 0

    def test_creation_with_reset_time(self):
        """Test GitHubRateLimitError creation with reset time."""
        error = GitHubRateLimitError("Rate limit exceeded", reset_time="2024-01-01T00:00:00Z")
        assert error.reset_time == "2024-01-01T00:00:00Z"
        assert error.context["reset_time"] == "2024-01-01T00:00:00Z"


class TestGitHubNotFoundError:
    """Test GitHubNotFoundError class."""

    def test_basic_creation(self):
        """Test basic GitHubNotFoundError creation."""
        error = GitHubNotFoundError("Resource not found")
        assert error.message == "Resource not found"
        assert error.error_code == ErrorCode.GITHUB_NOT_FOUND_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.resource_type is None
        assert error.resource_id is None

    def test_creation_with_resource_details(self):
        """Test GitHubNotFoundError creation with resource details."""
        error = GitHubNotFoundError(
            "Pull request not found",
            resource_type="pull_request",
            resource_id="123",
        )
        
        assert error.resource_type == "pull_request"
        assert error.resource_id == "123"
        assert error.context["resource_type"] == "pull_request"
        assert error.context["resource_id"] == "123"


class TestGitHubPermissionError:
    """Test GitHubPermissionError class."""

    def test_basic_creation(self):
        """Test basic GitHubPermissionError creation."""
        error = GitHubPermissionError("Permission denied")
        assert error.message == "Permission denied"
        assert error.error_code == ErrorCode.GITHUB_PERMISSION_ERROR
        assert error.required_permission is None
        assert error.resource is None
        assert len(error.suggestions) > 0

    def test_creation_with_permission_details(self):
        """Test GitHubPermissionError creation with permission details."""
        error = GitHubPermissionError(
            "Write access required",
            required_permission="write",
            resource="repository",
        )
        
        assert error.required_permission == "write"
        assert error.resource == "repository"
        assert error.context["required_permission"] == "write"
        assert error.context["resource"] == "repository"


class TestCommandExecutionError:
    """Test CommandExecutionError class."""

    def test_basic_creation(self):
        """Test basic CommandExecutionError creation."""
        error = CommandExecutionError("Command failed")
        assert error.error_code == ErrorCode.COMMAND_EXECUTION_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.command is None
        assert error.exit_code is None
        assert error.stderr is None

    def test_creation_with_command_details(self):
        """Test CommandExecutionError creation with command details."""
        error = CommandExecutionError(
            "Git command failed",
            command="git status",
            exit_code=128,
            stderr="fatal: not a git repository",
        )
        
        assert error.command == "git status"
        assert error.exit_code == 128
        assert error.stderr == "fatal: not a git repository"
        assert error.context["command"] == "git status"
        assert error.context["exit_code"] == 128
        assert error.context["stderr"] == "fatal: not a git repository"


class TestServiceSpecificErrors:
    """Test service-specific error classes."""

    def test_fetch_service_error(self):
        """Test FetchServiceError class."""
        error = FetchServiceError("Fetch failed")
        assert error.error_code == ErrorCode.FETCH_SERVICE_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert isinstance(error, ToadyError)

    def test_reply_service_error(self):
        """Test ReplyServiceError class."""
        error = ReplyServiceError("Reply failed")
        assert error.error_code == ErrorCode.REPLY_SERVICE_ERROR
        assert isinstance(error, GitHubServiceError)

    def test_comment_not_found_error(self):
        """Test CommentNotFoundError class."""
        error = CommentNotFoundError("Comment not found", comment_id="123")
        assert error.error_code == ErrorCode.COMMENT_NOT_FOUND
        assert error.comment_id == "123"
        assert error.context["comment_id"] == "123"
        assert len(error.suggestions) > 0
        assert isinstance(error, ReplyServiceError)

    def test_resolve_service_error(self):
        """Test ResolveServiceError class."""
        error = ResolveServiceError("Resolve failed")
        assert error.error_code == ErrorCode.RESOLVE_SERVICE_ERROR
        assert isinstance(error, GitHubServiceError)

    def test_thread_not_found_error(self):
        """Test ThreadNotFoundError class."""
        error = ThreadNotFoundError("Thread not found", thread_id="456")
        assert error.error_code == ErrorCode.THREAD_NOT_FOUND
        assert error.thread_id == "456"
        assert error.context["thread_id"] == "456"
        assert len(error.suggestions) > 0
        assert isinstance(error, ResolveServiceError)

    def test_thread_permission_error(self):
        """Test ThreadPermissionError class."""
        error = ThreadPermissionError("Cannot resolve thread", thread_id="789")
        assert error.error_code == ErrorCode.GITHUB_PERMISSION_ERROR
        assert error.thread_id == "789"
        assert error.context["thread_id"] == "789"
        assert len(error.suggestions) > 0
        assert isinstance(error, ResolveServiceError)


class TestHelperFunctions:
    """Test helper functions for creating errors."""

    def test_create_validation_error(self):
        """Test create_validation_error helper function."""
        error = create_validation_error(
            field_name="comment_id",
            invalid_value="invalid",
            expected_format="numeric or IC_ prefixed",
        )
        
        assert isinstance(error, ValidationError)
        assert error.field_name == "comment_id"
        assert error.invalid_value == "invalid"
        assert error.expected_format == "numeric or IC_ prefixed"
        assert "Invalid comment_id" in error.message
        assert "Expected numeric or IC_ prefixed" in error.message

    def test_create_validation_error_custom_message(self):
        """Test create_validation_error with custom message."""
        error = create_validation_error(
            field_name="test_field",
            invalid_value="test_value",
            expected_format="test_format",
            message="Custom validation message",
        )
        
        assert error.message == "Custom validation message"
        assert error.field_name == "test_field"

    def test_create_github_error(self):
        """Test create_github_error helper function."""
        error = create_github_error(
            message="API call failed",
            status_code=404,
            api_endpoint="/repos/test/repo",
        )
        
        assert isinstance(error, GitHubAPIError)
        assert error.message == "API call failed"
        assert error.status_code == 404
        assert error.api_endpoint == "/repos/test/repo"

    def test_create_github_error_minimal(self):
        """Test create_github_error with minimal parameters."""
        error = create_github_error("Simple error")
        
        assert isinstance(error, GitHubAPIError)
        assert error.message == "Simple error"
        assert error.status_code is None
        assert error.api_endpoint is None


class TestExceptionChaining:
    """Test exception inheritance and type checking."""

    def test_exception_hierarchy(self):
        """Test that all custom exceptions inherit properly."""
        # All toady errors should inherit from ToadyError
        toady_errors = [
            ValidationError("test"),
            ConfigurationError("test"),
            FileOperationError("test"),
            NetworkError("test"),
            GitHubServiceError("test"),
            FetchServiceError("test"),
        ]
        
        for error in toady_errors:
            assert isinstance(error, ToadyError)
            assert isinstance(error, Exception)

        # GitHub-specific errors should inherit from GitHubServiceError
        github_errors = [
            GitHubCLINotFoundError(),
            GitHubAuthenticationError(),
            GitHubAPIError("test"),
            GitHubTimeoutError(),
            GitHubRateLimitError(),
            GitHubNotFoundError("test"),
            GitHubPermissionError("test"),
            ReplyServiceError("test"),
            ResolveServiceError("test"),
        ]
        
        for error in github_errors:
            assert isinstance(error, GitHubServiceError)
            assert isinstance(error, ToadyError)

    def test_catch_by_base_class(self):
        """Test that errors can be caught by their base classes."""
        # Test catching by ToadyError
        with pytest.raises(ToadyError):
            raise ValidationError("test")

        # Test catching by GitHubServiceError
        with pytest.raises(GitHubServiceError):
            raise GitHubAuthenticationError()

        # Test catching specific error types
        with pytest.raises(GitHubAPIError):
            raise GitHubAPIError("test")

    def test_error_context_preservation(self):
        """Test that error context is preserved through inheritance."""
        # Create an error with context
        context = {"original_error": "something went wrong"}
        error = ValidationError("test", context=context)
        
        # The context should be accessible
        assert error.context == context
        assert error.to_dict()["context"] == context

        # Additional context should be merged
        error = ValidationError("test", field_name="test_field", context=context)
        expected_context = context.copy()
        expected_context["field_name"] = "test_field"
        assert error.context == expected_context


class TestBackwardCompatibility:
    """Test backward compatibility features."""

    def test_backward_compatibility_aliases(self):
        """Test that backward compatibility aliases work."""
        # Test importing the alias
        from toady.exceptions import GitHubCLINotFound
        
        # Should be the same class
        assert GitHubCLINotFound is GitHubCLINotFoundError
        
        # Should work the same way
        error = GitHubCLINotFound("test")
        assert isinstance(error, GitHubCLINotFoundError)
        assert isinstance(error, GitHubServiceError)