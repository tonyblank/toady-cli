"""Shared pytest fixtures and configuration."""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_gh_command(mocker):
    """Mock the subprocess calls to gh CLI with realistic return values."""
    # Create a mock CompletedProcess instance with default successful behavior
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '{"data": "mock_response"}'
    mock_result.stderr = ""
    mock_result.check_returncode.return_value = None

    # Patch subprocess.run to return our mock result
    mock = mocker.patch("subprocess.run", return_value=mock_result)

    # Add helper methods to easily configure different scenarios
    def configure_success(stdout="", stderr=""):
        """Configure mock for successful command execution."""
        mock_result.stdout = stdout
        mock_result.stderr = stderr
        mock_result.returncode = 0

    def configure_failure(returncode=1, stderr="Command failed"):
        """Configure mock for failed command execution."""
        mock_result.returncode = returncode
        mock_result.stderr = stderr
        mock_result.stdout = ""

    def configure_gh_auth_error():
        """Configure mock for GitHub authentication error."""
        configure_failure(returncode=1, stderr="gh: Not logged into any GitHub hosts")

    def configure_gh_not_found():
        """Configure mock for GitHub CLI not found error."""
        configure_failure(returncode=127, stderr="gh: command not found")

    mock.configure_success = configure_success
    mock.configure_failure = configure_failure
    mock.configure_gh_auth_error = configure_gh_auth_error
    mock.configure_gh_not_found = configure_gh_not_found

    return mock
