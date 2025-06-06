"""Tests for the GitHub service module."""

from unittest.mock import Mock, patch

import pytest

from toady.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubCLINotFoundError,
    GitHubService,
    GitHubServiceError,
)


class TestGitHubService:
    """Test the GitHubService class."""

    def test_init(self) -> None:
        """Test GitHubService initialization."""
        service = GitHubService()
        assert service.gh_command == "gh"

    @patch("subprocess.run")
    def test_check_gh_installation_success(self, mock_run: Mock) -> None:
        """Test successful gh CLI installation check."""
        mock_run.return_value = Mock(returncode=0)

        service = GitHubService()
        assert service.check_gh_installation() is True

        mock_run.assert_called_once_with(
            ["gh", "--version"], capture_output=True, text=True, check=False
        )

    @patch("subprocess.run")
    def test_check_gh_installation_failure(self, mock_run: Mock) -> None:
        """Test failed gh CLI installation check."""
        mock_run.return_value = Mock(returncode=1)

        service = GitHubService()
        assert service.check_gh_installation() is False

    @patch("subprocess.run")
    def test_check_gh_installation_not_found(self, mock_run: Mock) -> None:
        """Test gh CLI not found."""
        mock_run.side_effect = FileNotFoundError()

        service = GitHubService()
        assert service.check_gh_installation() is False

    @patch("subprocess.run")
    def test_get_gh_version_success(self, mock_run: Mock) -> None:
        """Test successful version retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="gh version 2.40.1 (2023-12-13)\nhttps://github.com/cli/cli/releases/tag/v2.40.1\n",
        )

        service = GitHubService()
        version = service.get_gh_version()
        assert version == "2.40.1"

    @patch("subprocess.run")
    def test_get_gh_version_not_found(self, mock_run: Mock) -> None:
        """Test version retrieval when gh CLI not found."""
        mock_run.side_effect = FileNotFoundError()

        service = GitHubService()
        with pytest.raises(GitHubCLINotFoundError):
            service.get_gh_version()

    @patch("subprocess.run")
    def test_get_gh_version_failure(self, mock_run: Mock) -> None:
        """Test version retrieval failure."""
        mock_run.return_value = Mock(returncode=1)

        service = GitHubService()
        with pytest.raises(GitHubCLINotFoundError):
            service.get_gh_version()

    @patch("subprocess.run")
    def test_check_authentication_success(self, mock_run: Mock) -> None:
        """Test successful authentication check."""
        mock_run.return_value = Mock(returncode=0)

        service = GitHubService()
        assert service.check_authentication() is True

        mock_run.assert_called_once_with(
            ["gh", "auth", "status"], capture_output=True, text=True, check=False
        )

    @patch("subprocess.run")
    def test_check_authentication_failure(self, mock_run: Mock) -> None:
        """Test failed authentication check."""
        mock_run.return_value = Mock(returncode=1)

        service = GitHubService()
        assert service.check_authentication() is False

    @patch("subprocess.run")
    def test_check_authentication_not_found(self, mock_run: Mock) -> None:
        """Test authentication check when gh CLI not found."""
        mock_run.side_effect = FileNotFoundError()

        service = GitHubService()
        assert service.check_authentication() is False

    @patch.object(GitHubService, "get_gh_version")
    def test_validate_version_compatibility_success(
        self, mock_get_version: Mock
    ) -> None:
        """Test successful version compatibility check."""
        mock_get_version.return_value = "2.40.1"

        service = GitHubService()
        assert service.validate_version_compatibility("2.0.0") is True
        assert service.validate_version_compatibility("2.40.0") is True
        assert service.validate_version_compatibility("2.40.1") is True

    @patch.object(GitHubService, "get_gh_version")
    def test_validate_version_compatibility_failure(
        self, mock_get_version: Mock
    ) -> None:
        """Test failed version compatibility check."""
        mock_get_version.return_value = "1.9.0"

        service = GitHubService()
        assert service.validate_version_compatibility("2.0.0") is False

    @patch.object(GitHubService, "get_gh_version")
    def test_validate_version_compatibility_no_version(
        self, mock_get_version: Mock
    ) -> None:
        """Test version compatibility check with no version."""
        mock_get_version.return_value = None

        service = GitHubService()
        assert service.validate_version_compatibility("2.0.0") is False

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_success(self, mock_run: Mock, mock_check: Mock) -> None:
        """Test successful gh command execution."""
        mock_check.return_value = True
        mock_result = Mock(returncode=0, stdout="success", stderr="")
        mock_run.return_value = mock_result

        service = GitHubService()
        result = service.run_gh_command(["api", "user"])

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["gh", "api", "user"], capture_output=True, text=True, check=False
        )

    @patch.object(GitHubService, "check_gh_installation")
    def test_run_gh_command_not_installed(self, mock_check: Mock) -> None:
        """Test gh command when CLI not installed."""
        mock_check.return_value = False

        service = GitHubService()
        with pytest.raises(GitHubCLINotFoundError):
            service.run_gh_command(["api", "user"])

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_authentication_error(
        self, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Test gh command with authentication error."""
        mock_check.return_value = True
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="authentication required"
        )

        service = GitHubService()
        with pytest.raises(GitHubAuthenticationError):
            service.run_gh_command(["api", "user"])

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_api_error(self, mock_run: Mock, mock_check: Mock) -> None:
        """Test gh command with API error."""
        mock_check.return_value = True
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="API rate limit exceeded"
        )

        service = GitHubService()
        with pytest.raises(GitHubAPIError):
            service.run_gh_command(["api", "user"])

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_file_not_found(
        self, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Test gh command when file not found during execution."""
        mock_check.return_value = True
        mock_run.side_effect = FileNotFoundError()

        service = GitHubService()
        with pytest.raises(GitHubCLINotFoundError):
            service.run_gh_command(["api", "user"])

    @patch.object(GitHubService, "run_gh_command")
    def test_get_json_output_success(self, mock_run: Mock) -> None:
        """Test successful JSON output parsing."""
        mock_result = Mock(stdout='{"login": "testuser"}')
        mock_run.return_value = mock_result

        service = GitHubService()
        data = service.get_json_output(["api", "user"])

        assert data == {"login": "testuser"}
        mock_run.assert_called_once_with(["api", "user"])

    @patch.object(GitHubService, "run_gh_command")
    def test_get_json_output_invalid_json(self, mock_run: Mock) -> None:
        """Test JSON output parsing with invalid JSON."""
        mock_result = Mock(stdout="invalid json")
        mock_run.return_value = mock_result

        service = GitHubService()
        with pytest.raises(GitHubAPIError):
            service.get_json_output(["api", "user"])

    @patch.object(GitHubService, "run_gh_command")
    def test_get_current_repo_success(self, mock_run: Mock) -> None:
        """Test successful current repository retrieval."""
        mock_result = Mock(stdout='{"nameWithOwner": "owner/repo"}')
        mock_run.return_value = mock_result

        service = GitHubService()
        repo = service.get_current_repo()

        assert repo == "owner/repo"
        mock_run.assert_called_once_with(["repo", "view", "--json", "nameWithOwner"])

    @patch.object(GitHubService, "run_gh_command")
    def test_get_current_repo_api_error(self, mock_run: Mock) -> None:
        """Test current repository retrieval with API error."""
        mock_run.side_effect = GitHubAPIError("Not in a repository")

        service = GitHubService()
        repo = service.get_current_repo()

        assert repo is None

    @patch.object(GitHubService, "run_gh_command")
    def test_get_current_repo_invalid_json(self, mock_run: Mock) -> None:
        """Test current repository retrieval with invalid JSON."""
        mock_result = Mock(stdout="invalid json")
        mock_run.return_value = mock_result

        service = GitHubService()
        repo = service.get_current_repo()

        assert repo is None


class TestGitHubServiceExceptions:
    """Test GitHub service exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """Test that all exceptions inherit from GitHubServiceError."""
        assert issubclass(GitHubCLINotFoundError, GitHubServiceError)
        assert issubclass(GitHubAuthenticationError, GitHubServiceError)
        assert issubclass(GitHubAPIError, GitHubServiceError)

    def test_exception_messages(self) -> None:
        """Test exception message handling."""
        with pytest.raises(GitHubCLINotFoundError) as exc_info:
            raise GitHubCLINotFoundError("Test message")
        assert str(exc_info.value) == "Test message"

        with pytest.raises(GitHubAuthenticationError) as exc_info:
            raise GitHubAuthenticationError("Auth failed")
        assert str(exc_info.value) == "Auth failed"

        with pytest.raises(GitHubAPIError) as exc_info:
            raise GitHubAPIError("API error")
        assert str(exc_info.value) == "API error"
