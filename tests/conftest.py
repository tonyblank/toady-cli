"""Shared pytest fixtures and configuration."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from click.testing import CliRunner

from toady.models.models import Comment, ReviewThread


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (may require authentication)",
    )


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


# Session-scoped fixtures for maximum performance
@pytest.fixture(scope="session")
def sample_datetime():
    """Shared datetime for consistent test data."""
    return datetime(2024, 1, 15, 10, 0, 0)


@pytest.fixture(scope="session")
def sample_comment(sample_datetime):
    """Reusable Comment instance for all tests."""
    return Comment(
        comment_id="IC_kwDOABcD12MAAAABcDE3fg",
        content="This is a sample comment for testing purposes",
        author="testuser",
        created_at=sample_datetime,
        updated_at=sample_datetime,
        parent_id=None,
        thread_id="RT_kwDOABcD12MAAAABcDE3fg",
    )


@pytest.fixture(scope="session")
def sample_comment_with_parent(sample_datetime):
    """Reusable Comment instance with parent for all tests."""
    return Comment(
        comment_id="IC_kwDOABcD12MAAAABcDE3fh",
        content="This is a reply comment for testing",
        author="reviewer",
        created_at=sample_datetime,
        updated_at=sample_datetime,
        parent_id="IC_kwDOABcD12MAAAABcDE3fg",
        thread_id="RT_kwDOABcD12MAAAABcDE3fg",
    )


@pytest.fixture(scope="session")
def sample_review_thread(sample_datetime, sample_comment):
    """Reusable ReviewThread instance for all tests."""
    return ReviewThread(
        thread_id="RT_kwDOABcD12MAAAABcDE3fg",
        title="Sample review thread for testing",
        created_at=sample_datetime,
        updated_at=sample_datetime,
        status="UNRESOLVED",
        author="reviewer",
        comments=[sample_comment],
    )


@pytest.fixture(scope="session")
def sample_resolved_thread(sample_datetime, sample_comment):
    """Reusable resolved ReviewThread instance for all tests."""
    return ReviewThread(
        thread_id="RT_kwDOABcD12MAAAABcDE3fh",
        title="Resolved review thread for testing",
        created_at=sample_datetime,
        updated_at=sample_datetime,
        status="RESOLVED",
        author="reviewer",
        comments=[sample_comment],
    )


@pytest.fixture(scope="session")
def mock_github_responses():
    """Pre-built mock GitHub API responses for consistent testing."""
    return {
        "review_threads_response": {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "RT_kwDOABcD12MAAAABcDE3fg",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_kwDOABcD12MAAAABcDE3fg",
                                                "body": "Sample comment",
                                                "author": {"login": "testuser"},
                                                "createdAt": "2024-01-15T10:00:00Z",
                                                "updatedAt": "2024-01-15T10:00:00Z",
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    }
                }
            }
        },
        "empty_threads_response": {
            "data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": []}}}}
        },
        "comment_reply_response": {
            "data": {
                "addPullRequestReviewComment": {
                    "comment": {
                        "id": "987654321",
                        "url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
                        "createdAt": "2023-01-01T12:00:00Z",
                        "author": {"login": "testuser"},
                    }
                }
            }
        },
        "resolve_thread_response": {
            "data": {
                "resolveReviewThread": {
                    "thread": {"id": "RT_kwDOABcD12MAAAABcDE3fg", "isResolved": True}
                }
            }
        },
        "error_responses": {
            "authentication_error": {
                "errors": [
                    {
                        "type": "FORBIDDEN",
                        "message": "Resource not accessible by integration",
                    }
                ]
            },
            "not_found_error": {
                "errors": [
                    {
                        "type": "NOT_FOUND",
                        "message": "Could not resolve to a PullRequestReviewThread with the id of RT_invalid",  # noqa: E501
                    }
                ]
            },
        },
    }


@pytest.fixture(scope="session")
def common_test_dates():
    """Common datetime objects used across tests."""
    base_date = datetime(2024, 1, 15, 10, 0, 0)
    return {
        "created_at": base_date,
        "updated_at": base_date,
        "old_date": datetime(2023, 12, 1, 10, 0, 0),
        "future_date": datetime(2024, 6, 1, 10, 0, 0),
    }


# Module-scoped fixtures for expensive operations
@pytest.fixture(scope="module")
def temp_directory():
    """Shared temporary directory for file operations and caching."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


# Factory fixtures for dynamic test data
@pytest.fixture
def comment_factory(sample_datetime):
    """Factory for creating Comment instances with custom data."""

    def _create_comment(**overrides):
        defaults = {
            "comment_id": "IC_factory_default",
            "content": "Factory-generated comment",
            "author": "factory_user",
            "created_at": sample_datetime,
            "updated_at": sample_datetime,
            "parent_id": None,
            "thread_id": "RT_factory_default",
        }
        defaults.update(overrides)
        return Comment(**defaults)

    return _create_comment


@pytest.fixture
def thread_factory(sample_datetime):
    """Factory for creating ReviewThread instances with custom data."""

    def _create_thread(**overrides):
        defaults = {
            "thread_id": "RT_factory_default",
            "title": "Factory-generated thread",
            "created_at": sample_datetime,
            "updated_at": sample_datetime,
            "status": "UNRESOLVED",
            "author": "factory_user",
            "comments": [],
        }
        defaults.update(overrides)
        return ReviewThread(**defaults)

    return _create_thread


@pytest.fixture
def graphql_response_factory():
    """Factory for creating mock GraphQL responses."""

    def _create_response(threads_data=None, **kwargs):
        if threads_data is None:
            threads_data = []

        response = {
            "data": {
                "repository": {
                    "pullRequest": {"reviewThreads": {"nodes": threads_data}}
                }
            }
        }

        if kwargs.get("include_errors"):
            response["errors"] = kwargs.get("errors", [])

        return response

    return _create_response


# Service mock fixtures
@pytest.fixture
def mock_github_service():
    """Pre-configured GitHub service mock."""
    from toady.github_service import GitHubService

    service = Mock(spec=GitHubService)
    service.is_authenticated.return_value = True
    service.execute_graphql_query.return_value = {"data": {"test": "success"}}
    service.post_reply.return_value = {
        "reply_id": "123456789",
        "reply_url": "https://github.com/test/repo/pull/1#discussion_r123456789",
        "created_at": "2024-01-15T10:00:00Z",
        "author": "testuser",
    }

    return service


@pytest.fixture
def mock_fetch_service(mock_github_responses):
    """Pre-configured fetch service mock."""
    from toady.fetch_service import FetchService

    service = Mock(spec=FetchService)
    service.fetch_review_threads_from_current_repo.return_value = []

    return service


@pytest.fixture
def mock_reply_service():
    """Pre-configured reply service mock."""
    from toady.reply_service import ReplyService

    service = Mock(spec=ReplyService)
    service.post_reply.return_value = {
        "reply_id": "987654321",
        "reply_url": "https://github.com/test/repo/pull/1#discussion_r987654321",
        "comment_id": "123456789",
        "created_at": "2024-01-15T10:00:00Z",
        "author": "testuser",
    }

    return service


@pytest.fixture
def mock_resolve_service():
    """Pre-configured resolve service mock."""
    from toady.resolve_service import ResolveService

    service = Mock(spec=ResolveService)
    service.resolve_thread.return_value = {
        "thread_id": "RT_kwDOABcD12MAAAABcDE3fg",
        "action": "resolve",
        "success": True,
        "is_resolved": "true",
        "thread_url": "https://github.com/test/repo/pull/1#discussion_rRT_kwDOABcD12MAAAABcDE3fg",
    }
    service.unresolve_thread.return_value = {
        "thread_id": "RT_kwDOABcD12MAAAABcDE3fg",
        "action": "unresolve",
        "success": True,
        "is_resolved": "false",
        "thread_url": "https://github.com/test/repo/pull/1#discussion_rRT_kwDOABcD12MAAAABcDE3fg",
    }

    return service
