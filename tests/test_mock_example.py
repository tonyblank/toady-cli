"""Example tests demonstrating mock_gh_command fixture usage."""

import subprocess


def test_mock_gh_command_default_behavior(mock_gh_command):
    """Test that mock_gh_command provides realistic default behavior."""
    # Test default successful behavior
    result = subprocess.run(["gh", "api", "user"], capture_output=True, text=True)

    assert result.returncode == 0
    assert result.stdout == '{"data": "mock_response"}'
    assert result.stderr == ""
    assert mock_gh_command.called


def test_mock_gh_command_success_configuration(mock_gh_command):
    """Test configuring mock for successful gh command."""
    # Configure mock for successful response
    mock_gh_command.configure_success(
        stdout='{"login": "testuser", "id": 12345}', stderr=""
    )

    result = subprocess.run(["gh", "api", "user"], capture_output=True, text=True)

    assert result.returncode == 0
    assert '"login": "testuser"' in result.stdout
    assert result.stderr == ""


def test_mock_gh_command_failure_configuration(mock_gh_command):
    """Test configuring mock for failed gh command."""
    # Configure mock for authentication error
    mock_gh_command.configure_gh_auth_error()

    result = subprocess.run(["gh", "api", "user"], capture_output=True, text=True)

    assert result.returncode == 1
    assert "Not logged into any GitHub hosts" in result.stderr
    assert result.stdout == ""


def test_mock_gh_command_not_found(mock_gh_command):
    """Test configuring mock for gh command not found."""
    # Configure mock for command not found
    mock_gh_command.configure_gh_not_found()

    result = subprocess.run(["gh", "api", "user"], capture_output=True, text=True)

    assert result.returncode == 127
    assert "command not found" in result.stderr
