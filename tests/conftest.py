"""Shared pytest fixtures and configuration."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_gh_command(mocker):
    """Mock the subprocess calls to gh CLI with realistic return values."""
"""Shared pytest fixtures and configuration."""

import pytest
from unittest.mock import MagicMock
from click.testing import CliRunner

# ...rest of your fixtures...

    # Create a mock CompletedProcess instance with default successful behavior
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '{"data": "mock_response"}'
    mock_result.stderr = ""
    mock_result.check_returncode.return_value = None

    # Patch subprocess.run to return our mock result
    mock = mocker.patch("subprocess.run", return_value=mock_result)

    # Add helper methods to easily configure different scenarios
    mock.configure_success = (
        lambda stdout="", stderr="": setattr(mock_result, "stdout", stdout)
        or setattr(mock_result, "stderr", stderr)
        or setattr(mock_result, "returncode", 0)
    )
    mock.configure_failure = (
        lambda returncode=1, stderr="Command failed": setattr(
            mock_result, "returncode", returncode
        )
        or setattr(mock_result, "stderr", stderr)
        or setattr(mock_result, "stdout", "")
    )
    mock.configure_gh_auth_error = lambda: mock.configure_failure(
        returncode=1, stderr="gh: Not logged into any GitHub hosts"
    )
    mock.configure_gh_not_found = lambda: mock.configure_failure(
        returncode=127, stderr="gh: command not found"
    )

    return mock
