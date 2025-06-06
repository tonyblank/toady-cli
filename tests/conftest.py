"""Shared pytest fixtures and configuration."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_gh_command(mocker):
    """Mock the subprocess calls to gh CLI."""
    return mocker.patch("subprocess.run")
