"""Enhanced integration test configuration and fixtures for real API testing.

This module provides comprehensive fixtures and utilities for integration tests
that interact with real GitHub APIs, including authentication management,
test data setup/cleanup, and resilience testing infrastructure.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
from click.testing import CliRunner

from toady.services.github_service import GitHubService


@pytest.fixture(scope="session")
def integration_test_config() -> Dict[str, Any]:
    """Load integration test configuration from environment variables.

    Returns:
        Dictionary containing integration test configuration parameters.
    """
    return {
        "test_repo": os.getenv("TOADY_TEST_REPO", "toady-test/integration-testing"),
        "test_org": os.getenv("TOADY_TEST_ORG", "toady-test"),
        "api_timeout": int(os.getenv("TOADY_API_TIMEOUT", "30")),
        "rate_limit_buffer": int(os.getenv("TOADY_RATE_LIMIT_BUFFER", "100")),
        "skip_slow_tests": os.getenv("TOADY_SKIP_SLOW_TESTS", "false").lower()
        == "true",
        "test_pr_number": int(os.getenv("TOADY_TEST_PR_NUMBER", "1")),
        "max_retry_attempts": int(os.getenv("TOADY_MAX_RETRY_ATTEMPTS", "3")),
        "retry_delay": float(os.getenv("TOADY_RETRY_DELAY", "1.0")),
    }


@pytest.fixture(scope="session")
def github_api_health_check(integration_test_config: Dict[str, Any]) -> bool:
    """Verify GitHub API accessibility and authentication before running tests.

    Args:
        integration_test_config: Integration test configuration.

    Returns:
        True if GitHub API is accessible and authenticated.

    Raises:
        pytest.skip: If GitHub API is not accessible or authentication fails.
    """
    try:
        # Check if gh CLI is available
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip("GitHub CLI (gh) not available")

        # Check authentication status
        auth_result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if auth_result.returncode != 0:
            pytest.skip("GitHub CLI not authenticated - run 'gh auth login'")

        # Check rate limit status
        rate_limit_result = subprocess.run(
            ["gh", "api", "rate_limit"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if rate_limit_result.returncode != 0:
            pytest.skip("Unable to check GitHub API rate limits")

        import json

        rate_data = json.loads(rate_limit_result.stdout)
        remaining = rate_data.get("rate", {}).get("remaining", 0)

        if remaining < integration_test_config["rate_limit_buffer"]:
            pytest.skip(f"Insufficient GitHub API rate limit remaining: {remaining}")

        return True

    except subprocess.TimeoutExpired:
        pytest.skip("GitHub CLI commands timed out")
    except FileNotFoundError:
        pytest.skip("GitHub CLI (gh) not found in PATH")
    except json.JSONDecodeError:
        pytest.skip("Invalid JSON response from GitHub API")
    except Exception as e:
        pytest.skip(f"GitHub API health check failed: {e}")


@pytest.fixture
def github_service_real(github_api_health_check: bool) -> GitHubService:
    """Create a real GitHubService instance for integration testing.

    Args:
        github_api_health_check: Ensures GitHub API is accessible.

    Returns:
        Configured GitHubService instance.
    """
    return GitHubService(timeout=30)


@pytest.fixture
def integration_cli_runner() -> CliRunner:
    """Create a CLI runner configured for integration testing.

    Returns:
        CliRunner instance with integration test configuration.
    """
    runner = CliRunner()
    return runner


@pytest.fixture
def temp_cache_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for cache during integration tests.

    Yields:
        Path to temporary cache directory.
    """
    with tempfile.TemporaryDirectory(prefix="toady_integration_cache_") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_repository_info(integration_test_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get information about the test repository.

    Args:
        integration_test_config: Integration test configuration.

    Returns:
        Dictionary containing test repository information.
    """
    repo = integration_test_config["test_repo"]
    parts = repo.split("/")

    if len(parts) != 2:
        pytest.skip(f"Invalid test repository format: {repo}")

    return {
        "owner": parts[0],
        "repo": parts[1],
        "full_name": repo,
        "pr_number": integration_test_config["test_pr_number"],
    }


@pytest.fixture
def verify_test_pr_exists(
    github_service_real: GitHubService, test_repository_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Verify that the test PR exists and is accessible.

    Args:
        github_service_real: Real GitHub service instance.
        test_repository_info: Test repository information.

    Returns:
        PR information if accessible.

    Raises:
        pytest.skip: If test PR is not accessible.
    """
    try:
        # Try to access the test PR to verify it exists and we have permissions
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{test_repository_info['full_name']}/pulls/{test_repository_info['pr_number']}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            pytest.skip(
                f"Test PR {test_repository_info['pr_number']} not accessible "
                f"in {test_repository_info['full_name']}"
            )

        import json

        pr_data = json.loads(result.stdout)

        return {
            "number": pr_data["number"],
            "title": pr_data["title"],
            "state": pr_data["state"],
            "node_id": pr_data["node_id"],
            "html_url": pr_data["html_url"],
        }

    except Exception as e:
        pytest.skip(f"Failed to verify test PR: {e}")


@pytest.fixture
def rate_limit_aware_delay():
    """Add delay between API calls to respect rate limits."""

    def delay(seconds: float = 1.0) -> None:
        """Add a delay between API calls.

        Args:
            seconds: Number of seconds to delay.
        """
        time.sleep(seconds)

    return delay


@pytest.fixture
def api_retry_helper(integration_test_config: Dict[str, Any]):
    """Helper for retrying API calls with exponential backoff."""

    def retry_api_call(func, *args, **kwargs):
        """Retry an API call with exponential backoff.

        Args:
            func: Function to call.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function call.

        Raises:
            Exception: If all retry attempts fail.
        """
        max_attempts = integration_test_config["max_retry_attempts"]
        base_delay = integration_test_config["retry_delay"]

        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception:
                if attempt == max_attempts - 1:
                    raise

                delay = base_delay * (2**attempt)
                time.sleep(delay)

        # This should never be reached, but just in case
        raise RuntimeError("Maximum retry attempts exceeded")

    return retry_api_call


@pytest.fixture
def network_simulation():
    """Utilities for simulating network conditions during testing."""

    class NetworkSimulator:
        """Simulate various network conditions for testing."""

        @staticmethod
        def simulate_timeout(timeout_seconds: float = 5.0):
            """Simulate a network timeout.

            Args:
                timeout_seconds: Timeout duration in seconds.
            """
            time.sleep(timeout_seconds)

        @staticmethod
        def simulate_slow_connection(delay_seconds: float = 2.0):
            """Simulate a slow network connection.

            Args:
                delay_seconds: Delay duration in seconds.
            """
            time.sleep(delay_seconds)

        @staticmethod
        def simulate_intermittent_failure(failure_rate: float = 0.3):
            """Simulate intermittent network failures.

            Args:
                failure_rate: Probability of failure (0.0 to 1.0).

            Returns:
                True if operation should succeed, False if it should fail.
            """
            import random

            return random.random() > failure_rate

    return NetworkSimulator()


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during integration tests."""

    class PerformanceMonitor:
        """Monitor and measure performance during tests."""

        def __init__(self):
            self.start_time = None
            self.metrics = {}

        def start_timing(self, operation: str):
            """Start timing an operation.

            Args:
                operation: Name of the operation being timed.
            """
            self.start_time = time.time()
            self.current_operation = operation

        def stop_timing(self) -> float:
            """Stop timing and record the duration.

            Returns:
                Duration of the operation in seconds.
            """
            if self.start_time is None:
                raise ValueError("No timing operation in progress")

            duration = time.time() - self.start_time
            self.metrics[self.current_operation] = duration
            self.start_time = None
            return duration

        def get_metrics(self) -> Dict[str, float]:
            """Get all recorded performance metrics.

            Returns:
                Dictionary of operation names to durations.
            """
            return self.metrics.copy()

        def assert_performance_threshold(self, operation: str, max_seconds: float):
            """Assert that an operation completed within a time threshold.

            Args:
                operation: Name of the operation to check.
                max_seconds: Maximum allowed duration in seconds.

            Raises:
                AssertionError: If operation exceeded the threshold.
            """
            duration = self.metrics.get(operation)
            if duration is None:
                raise ValueError(f"No metrics recorded for operation: {operation}")

            assert duration <= max_seconds, (
                f"Operation '{operation}' took {duration:.2f}s, "
                f"which exceeds threshold of {max_seconds:.2f}s"
            )

    return PerformanceMonitor()


@pytest.fixture
def integration_test_cleanup():
    """Cleanup helper for integration tests."""
    cleanup_tasks = []

    def add_cleanup(func, *args, **kwargs):
        """Add a cleanup task to be executed after the test.

        Args:
            func: Cleanup function to call.
            *args: Positional arguments for the cleanup function.
            **kwargs: Keyword arguments for the cleanup function.
        """
        cleanup_tasks.append((func, args, kwargs))

    yield add_cleanup

    # Execute cleanup tasks in reverse order
    for func, args, kwargs in reversed(cleanup_tasks):
        try:
            func(*args, **kwargs)
        except Exception as e:
            # Log cleanup errors but don't fail the test
            print(f"Cleanup error: {e}")


@pytest.fixture
def skip_if_slow(integration_test_config: Dict[str, Any]):
    """Skip slow tests based on configuration."""
    if integration_test_config["skip_slow_tests"]:
        pytest.skip("Slow tests are disabled (TOADY_SKIP_SLOW_TESTS=true)")


# Session-level fixtures for expensive setup
@pytest.fixture(scope="session")
def session_github_service(github_api_health_check: bool) -> GitHubService:
    """Create a session-level GitHub service instance."""
    return GitHubService(timeout=30)


@pytest.fixture(scope="session")
def session_test_repository_access(
    session_github_service: GitHubService, integration_test_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Verify session-level access to test repository."""
    repo = integration_test_config["test_repo"]

    try:
        # Test basic repository access
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}"], capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            pytest.skip(f"Cannot access test repository: {repo}")

        import json

        repo_data = json.loads(result.stdout)

        return {
            "name": repo_data["name"],
            "full_name": repo_data["full_name"],
            "private": repo_data["private"],
            "permissions": repo_data.get("permissions", {}),
        }

    except Exception as e:
        pytest.skip(f"Failed to verify repository access: {e}")
