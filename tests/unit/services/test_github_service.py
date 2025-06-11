"""Tests for the GitHub service module."""

from unittest.mock import Mock, patch

import pytest

from toady.services.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubCLINotFoundError,
    GitHubRateLimitError,
    GitHubService,
    GitHubServiceError,
    GitHubTimeoutError,
)


class TestGitHubService:
    """Test the GitHubService class."""

    def test_init(self) -> None:
        """Test GitHubService initialization."""
        service = GitHubService()
        assert service.gh_command == "gh"
        assert service.timeout == 30

    def test_init_custom_timeout(self) -> None:
        """Test GitHubService initialization with custom timeout."""
        service = GitHubService(timeout=60)
        assert service.timeout == 60

    def test_init_invalid_timeout_zero(self) -> None:
        """Test GitHubService initialization with zero timeout."""
        with pytest.raises(ValueError) as exc_info:
            GitHubService(timeout=0)
        assert "Timeout must be a positive integer" in str(exc_info.value)

    def test_init_invalid_timeout_negative(self) -> None:
        """Test GitHubService initialization with negative timeout."""
        with pytest.raises(ValueError) as exc_info:
            GitHubService(timeout=-5)
        assert "Timeout must be a positive integer" in str(exc_info.value)

    def test_init_invalid_timeout_non_integer(self) -> None:
        """Test GitHubService initialization with non-integer timeout."""
        with pytest.raises(ValueError) as exc_info:
            GitHubService(timeout=30.5)  # type: ignore[arg-type]
        assert "Timeout must be a positive integer" in str(exc_info.value)

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
            ["gh", "api", "user"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
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
        """Test gh command with generic API error."""
        mock_check.return_value = True
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Resource not found"
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

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_timeout_error(
        self, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Test gh command with timeout error."""
        import subprocess

        mock_check.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(["gh", "api", "user"], 30)

        service = GitHubService()
        with pytest.raises(GitHubTimeoutError):
            service.run_gh_command(["api", "user"])

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_rate_limit_error(
        self, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Test gh command with rate limit error."""
        mock_check.return_value = True
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="API rate limit exceeded"
        )

        service = GitHubService()
        with pytest.raises(GitHubRateLimitError):
            service.run_gh_command(["api", "user"])

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_rate_limit_error_success_exit_code(
        self, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Test gh command detects rate limit error even with exit code 0."""
        mock_check.return_value = True
        mock_run.return_value = Mock(
            returncode=0, stdout='{"data": null}', stderr="rate limited"
        )

        service = GitHubService()
        with pytest.raises(GitHubRateLimitError) as exc_info:
            service.run_gh_command(["api", "user"])
        assert "rate limited" in str(exc_info.value)

    @patch.object(GitHubService, "check_gh_installation")
    @patch("subprocess.run")
    def test_run_gh_command_custom_timeout(
        self, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Test gh command with custom timeout."""
        mock_check.return_value = True
        mock_result = Mock(returncode=0, stdout="success", stderr="")
        mock_run.return_value = mock_result

        service = GitHubService()
        result = service.run_gh_command(["api", "user"], timeout=60)

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["gh", "api", "user"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    @patch.object(GitHubService, "run_gh_command")
    def test_execute_graphql_query_success(self, mock_run: Mock) -> None:
        """Test successful GraphQL query execution."""
        mock_result = Mock(stdout='{"data": {"viewer": {"login": "testuser"}}}')
        mock_run.return_value = mock_result

        service = GitHubService()
        response = service.execute_graphql_query("query { viewer { login } }")

        expected_args = ["api", "graphql", "-f", "query=query { viewer { login } }"]
        mock_run.assert_called_once_with(expected_args)
        assert response == {"data": {"viewer": {"login": "testuser"}}}

    @patch.object(GitHubService, "run_gh_command")
    def test_execute_graphql_query_with_variables(self, mock_run: Mock) -> None:
        """Test GraphQL query execution with variables."""
        mock_result = Mock(stdout='{"data": {"repository": {"name": "test"}}}')
        mock_run.return_value = mock_result

        service = GitHubService()
        variables = {"owner": "testowner", "repo": "testrepo", "number": 123}
        response = service.execute_graphql_query(
            "query($owner: String!) { }", variables
        )

        expected_args = [
            "api",
            "graphql",
            "-f",
            "query=query($owner: String!) { }",
            "-F",
            "owner=testowner",
            "-F",
            "repo=testrepo",
            "-F",
            "number=123",
        ]
        mock_run.assert_called_once_with(expected_args)
        assert response == {"data": {"repository": {"name": "test"}}}

    @patch.object(GitHubService, "run_gh_command")
    def test_execute_graphql_query_with_errors(self, mock_run: Mock) -> None:
        """Test GraphQL query execution with GraphQL errors."""
        mock_result = Mock(stdout='{"errors": [{"message": "Field not found"}]}')
        mock_run.return_value = mock_result

        service = GitHubService()
        with pytest.raises(GitHubAPIError) as exc_info:
            service.execute_graphql_query("query { invalid }")

        assert "GraphQL query failed: Field not found" in str(exc_info.value)

    @patch.object(GitHubService, "run_gh_command")
    def test_execute_graphql_query_invalid_json(self, mock_run: Mock) -> None:
        """Test GraphQL query execution with invalid JSON response."""
        mock_result = Mock(stdout="invalid json")
        mock_run.return_value = mock_result

        service = GitHubService()
        with pytest.raises(GitHubAPIError) as exc_info:
            service.execute_graphql_query("query { viewer { login } }")

        assert "Failed to parse GraphQL response" in str(exc_info.value)

    def test_get_repo_info_from_url_https(self) -> None:
        """Test extracting repo info from HTTPS URL."""
        service = GitHubService()
        owner, repo = service.get_repo_info_from_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_get_repo_info_from_url_ssh(self) -> None:
        """Test extracting repo info from SSH URL."""
        service = GitHubService()
        owner, repo = service.get_repo_info_from_url("git@github.com:owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_get_repo_info_from_url_owner_repo_format(self) -> None:
        """Test extracting repo info from owner/repo format."""
        service = GitHubService()
        owner, repo = service.get_repo_info_from_url("owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_get_repo_info_from_url_invalid(self) -> None:
        """Test extracting repo info from invalid URL."""
        service = GitHubService()
        with pytest.raises(ValueError) as exc_info:
            service.get_repo_info_from_url("invalid-url")

        assert "Invalid GitHub repository URL or format" in str(exc_info.value)

    @patch.object(GitHubService, "run_gh_command")
    def test_validate_repository_access_success(self, mock_run: Mock) -> None:
        """Test successful repository access validation."""
        mock_result = Mock(stdout='{"name": "repo"}')
        mock_run.return_value = mock_result

        service = GitHubService()
        assert service.validate_repository_access("owner", "repo") is True

        mock_run.assert_called_once_with(
            ["repo", "view", "owner/repo", "--json", "name"]
        )

    @patch.object(GitHubService, "run_gh_command")
    def test_validate_repository_access_failure(self, mock_run: Mock) -> None:
        """Test failed repository access validation."""
        mock_run.side_effect = GitHubAPIError("Repository not found")

        service = GitHubService()
        assert service.validate_repository_access("owner", "repo") is False

    @patch.object(GitHubService, "run_gh_command")
    def test_validate_repository_access_rate_limit_error(self, mock_run: Mock) -> None:
        """Test repository access validation re-raises rate limit errors."""
        mock_run.side_effect = GitHubRateLimitError("Rate limit exceeded")

        service = GitHubService()
        with pytest.raises(GitHubRateLimitError) as exc_info:
            service.validate_repository_access("owner", "repo")
        assert "Rate limit exceeded" in str(exc_info.value)

    @patch.object(GitHubService, "run_gh_command")
    def test_validate_repository_access_timeout_error(self, mock_run: Mock) -> None:
        """Test repository access validation re-raises timeout errors."""
        mock_run.side_effect = GitHubTimeoutError("Command timed out")

        service = GitHubService()
        with pytest.raises(GitHubTimeoutError) as exc_info:
            service.validate_repository_access("owner", "repo")
        assert "Command timed out" in str(exc_info.value)

    @patch.object(GitHubService, "run_gh_command")
    def test_check_pr_exists_success(self, mock_run: Mock) -> None:
        """Test successful PR existence check."""
        mock_result = Mock(stdout='{"number": 123}')
        mock_run.return_value = mock_result

        service = GitHubService()
        assert service.check_pr_exists("owner", "repo", 123) is True

        mock_run.assert_called_once_with(
            ["pr", "view", "123", "--repo", "owner/repo", "--json", "number"]
        )

    @patch.object(GitHubService, "run_gh_command")
    def test_check_pr_exists_failure(self, mock_run: Mock) -> None:
        """Test failed PR existence check."""
        mock_run.side_effect = GitHubAPIError("Pull request not found")

        service = GitHubService()
        assert service.check_pr_exists("owner", "repo", 123) is False


class TestGitHubServiceExceptions:
    """Test GitHub service exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """Test that all exceptions inherit from GitHubServiceError."""
        assert issubclass(GitHubCLINotFoundError, GitHubServiceError)
        assert issubclass(GitHubAuthenticationError, GitHubServiceError)
        assert issubclass(GitHubAPIError, GitHubServiceError)
        assert issubclass(GitHubTimeoutError, GitHubServiceError)
        assert issubclass(GitHubRateLimitError, GitHubServiceError)

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

        with pytest.raises(GitHubTimeoutError) as exc_info:
            raise GitHubTimeoutError("Timeout error")
        assert str(exc_info.value) == "Timeout error"

        with pytest.raises(GitHubRateLimitError) as exc_info:
            raise GitHubRateLimitError("Rate limit error")
        assert str(exc_info.value) == "Rate limit error"
