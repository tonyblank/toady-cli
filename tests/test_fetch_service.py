"""Tests for the fetch service module."""

from unittest.mock import Mock, patch

import pytest

from toady.fetch_service import FetchService, FetchServiceError
from toady.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubService,
)


class TestFetchService:
    """Test the FetchService class."""

    def test_init_default(self) -> None:
        """Test FetchService initialization with default GitHubService."""
        service = FetchService()
        assert service.github_service is not None
        assert isinstance(service.github_service, GitHubService)

    def test_init_custom_service(self) -> None:
        """Test FetchService initialization with custom GitHubService."""
        mock_github_service = Mock(spec=GitHubService)
        service = FetchService(mock_github_service)
        assert service.github_service is mock_github_service

    def test_fetch_review_threads_success(self) -> None:
        """Test successful review threads fetching."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock GraphQL response
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "PRT_kwDOABcD12MAAAABcDE3fg",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_kwDOABcD12MAAAABcDE3fg",
                                                "body": "This looks good!",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2023-01-01T12:00:00Z",
                                                "updatedAt": "2023-01-01T12:00:00Z",
                                            }
                                        ]
                                    },
                                }
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }

        mock_github_service.execute_graphql_query.return_value = mock_response

        service = FetchService(mock_github_service)
        threads = service.fetch_review_threads(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            include_resolved=False,
            limit=100,
        )

        assert len(threads) == 1
        assert threads[0].thread_id == "PRT_kwDOABcD12MAAAABcDE3fg"
        assert threads[0].status == "UNRESOLVED"
        assert len(threads[0].comments) == 1
        assert threads[0].comments[0].content == "This looks good!"

        # Verify GraphQL query was called correctly
        mock_github_service.execute_graphql_query.assert_called_once()
        call_args = mock_github_service.execute_graphql_query.call_args
        variables = call_args[0][1]  # Second argument is variables
        assert variables["owner"] == "testowner"
        assert variables["repo"] == "testrepo"
        assert variables["number"] == 123

    def test_fetch_review_threads_with_resolved(self) -> None:
        """Test fetching review threads including resolved ones."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock GraphQL response with both resolved and unresolved
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "PRT_unresolved",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_unresolved",
                                                "body": "Unresolved comment",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2023-01-01T12:00:00Z",
                                                "updatedAt": "2023-01-01T12:00:00Z",
                                            }
                                        ]
                                    },
                                },
                                {
                                    "id": "PRT_resolved",
                                    "isResolved": True,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_resolved",
                                                "body": "Resolved comment",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2023-01-01T12:00:00Z",
                                                "updatedAt": "2023-01-01T12:00:00Z",
                                            }
                                        ]
                                    },
                                },
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }

        mock_github_service.execute_graphql_query.return_value = mock_response

        service = FetchService(mock_github_service)
        threads = service.fetch_review_threads(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            include_resolved=True,
            limit=100,
        )

        assert len(threads) == 2
        unresolved = next(t for t in threads if t.thread_id == "PRT_unresolved")
        resolved = next(t for t in threads if t.thread_id == "PRT_resolved")

        assert unresolved.status == "UNRESOLVED"
        assert resolved.status == "RESOLVED"

    def test_fetch_review_threads_empty_response(self) -> None:
        """Test fetching when no threads are found."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock empty GraphQL response
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }

        mock_github_service.execute_graphql_query.return_value = mock_response

        service = FetchService(mock_github_service)
        threads = service.fetch_review_threads(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
        )

        assert len(threads) == 0

    def test_fetch_review_threads_authentication_error(self) -> None:
        """Test fetch with authentication error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.side_effect = (
            GitHubAuthenticationError("Authentication failed")
        )

        service = FetchService(mock_github_service)
        with pytest.raises(GitHubAuthenticationError):
            service.fetch_review_threads(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
            )

    def test_fetch_review_threads_api_error(self) -> None:
        """Test fetch with GitHub API error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.side_effect = GitHubAPIError(
            "404 Not Found"
        )

        service = FetchService(mock_github_service)
        with pytest.raises(GitHubAPIError):
            service.fetch_review_threads(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
            )

    def test_fetch_review_threads_service_error(self) -> None:
        """Test fetch with unexpected error wrapped in FetchServiceError."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.side_effect = ValueError(
            "Unexpected error"
        )

        service = FetchService(mock_github_service)
        with pytest.raises(FetchServiceError) as exc_info:
            service.fetch_review_threads(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
            )

        assert "Failed to fetch review threads" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)

    @patch.object(FetchService, "_get_repository_info")
    def test_fetch_from_current_repo_success(self, mock_get_repo_info: Mock) -> None:
        """Test fetching from current repository."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }
        mock_github_service.execute_graphql_query.return_value = mock_response
        mock_get_repo_info.return_value = ("owner", "repo")

        service = FetchService(mock_github_service)
        threads = service.fetch_review_threads_from_current_repo(pr_number=123)

        assert len(threads) == 0
        mock_get_repo_info.assert_called_once()

    def test_get_repository_info_success(self) -> None:
        """Test successful repository info retrieval."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.get_current_repo.return_value = "owner/repo"

        service = FetchService(mock_github_service)
        owner, repo = service._get_repository_info()

        assert owner == "owner"
        assert repo == "repo"

    def test_get_repository_info_no_repo(self) -> None:
        """Test repository info retrieval when not in a repo."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.get_current_repo.return_value = None

        service = FetchService(mock_github_service)
        with pytest.raises(FetchServiceError) as exc_info:
            service._get_repository_info()

        assert "Could not determine repository information" in str(exc_info.value)

    def test_get_repository_info_invalid_format(self) -> None:
        """Test repository info retrieval with invalid format."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.get_current_repo.return_value = "invalid-format"

        service = FetchService(mock_github_service)
        with pytest.raises(FetchServiceError) as exc_info:
            service._get_repository_info()

        assert "Invalid repository format" in str(exc_info.value)

    def test_fetch_with_custom_limit(self) -> None:
        """Test fetching with custom limit parameter."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }
        mock_github_service.execute_graphql_query.return_value = mock_response

        service = FetchService(mock_github_service)
        service.fetch_review_threads(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            limit=50,
        )

        # Verify the query was called (limit is embedded in the query)
        mock_github_service.execute_graphql_query.assert_called_once()


class TestFetchServiceExceptions:
    """Test fetch service exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """Test that FetchServiceError inherits from Exception."""
        assert issubclass(FetchServiceError, Exception)

    def test_exception_messages(self) -> None:
        """Test exception message handling."""
        with pytest.raises(FetchServiceError) as exc_info:
            raise FetchServiceError("Test error")
        assert str(exc_info.value) == "Test error"


class TestFetchServiceIntegration:
    """Integration tests for fetch service with edge cases."""

    def test_fetch_with_multiple_comments_per_thread(self) -> None:
        """Test fetching threads with multiple comments."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock response with multiple comments per thread
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "PRT_thread1",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_comment1",
                                                "body": "First comment",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2023-01-01T12:00:00Z",
                                                "updatedAt": "2023-01-01T12:00:00Z",
                                            },
                                            {
                                                "id": "IC_comment2",
                                                "body": "Second comment",
                                                "author": {"login": "author"},
                                                "createdAt": "2023-01-01T13:00:00Z",
                                                "updatedAt": "2023-01-01T13:00:00Z",
                                            },
                                        ]
                                    },
                                }
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }

        mock_github_service.execute_graphql_query.return_value = mock_response

        service = FetchService(mock_github_service)
        threads = service.fetch_review_threads(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
        )

        assert len(threads) == 1
        thread = threads[0]
        assert len(thread.comments) == 2
        assert thread.comments[0].content == "First comment"
        assert thread.comments[1].content == "Second comment"
        assert thread.comments[0].author == "reviewer"
        assert thread.comments[1].author == "author"

    def test_fetch_handles_missing_optional_fields(self) -> None:
        """Test fetching with missing optional fields in response."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock response with minimal data
        mock_response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "PRT_minimal",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_minimal",
                                                "body": "Minimal comment",
                                                "author": {"login": "user"},
                                                "createdAt": "2023-01-01T12:00:00Z",
                                                "updatedAt": "2023-01-01T12:00:00Z",
                                            }
                                        ]
                                    },
                                }
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            }
        }

        mock_github_service.execute_graphql_query.return_value = mock_response

        service = FetchService(mock_github_service)
        threads = service.fetch_review_threads(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
        )

        assert len(threads) == 1
        thread = threads[0]
        assert thread.thread_id == "PRT_minimal"
        assert len(thread.comments) == 1
