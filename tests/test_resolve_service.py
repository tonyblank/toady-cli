"""Tests for the resolve service module."""

import json
from unittest.mock import Mock, patch

import pytest

from toady.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubService,
)
from toady.resolve_service import (
    ResolveService,
    ResolveServiceError,
    ThreadNotFoundError,
    ThreadPermissionError,
)


class TestResolveService:
    """Test the ResolveService class."""

    def test_init_default(self) -> None:
        """Test ResolveService initialization with default GitHubService."""
        service = ResolveService()
        assert service.github_service is not None
        assert isinstance(service.github_service, GitHubService)

    def test_init_custom_service(self) -> None:
        """Test ResolveService initialization with custom GitHubService."""
        mock_github_service = Mock(spec=GitHubService)
        service = ResolveService(mock_github_service)
        assert service.github_service is mock_github_service

    def test_resolve_thread_success(self) -> None:
        """Test successful thread resolution."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": {
                        "id": "PRT_kwDOABcD12MAAAABcDE3fg",
                        "isResolved": True,
                    }
                }
            }
        }

        service = ResolveService(mock_github_service)
        result = service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")

        assert result["thread_id"] == "PRT_kwDOABcD12MAAAABcDE3fg"
        assert result["action"] == "resolve"
        assert result["success"] is True
        assert result["is_resolved"] == "true"
        assert "thread_url" in result

        # Verify the GraphQL mutation was called
        mock_github_service.execute_graphql_query.assert_called_once()
        call_args = mock_github_service.execute_graphql_query.call_args
        mutation, variables = call_args[0]
        assert "resolveReviewThread" in mutation
        assert variables == {"threadId": "PRT_kwDOABcD12MAAAABcDE3fg"}

    def test_unresolve_thread_success(self) -> None:
        """Test successful thread unresolving."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "unresolveReviewThread": {
                    "thread": {
                        "id": "PRT_kwDOABcD12MAAAABcDE3fg",
                        "isResolved": False,
                    }
                }
            }
        }

        service = ResolveService(mock_github_service)
        result = service.unresolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")

        assert result["thread_id"] == "PRT_kwDOABcD12MAAAABcDE3fg"
        assert result["action"] == "unresolve"
        assert result["success"] is True
        assert result["is_resolved"] == "false"
        assert "thread_url" in result

        # Verify the GraphQL mutation was called
        mock_github_service.execute_graphql_query.assert_called_once()
        call_args = mock_github_service.execute_graphql_query.call_args
        mutation, variables = call_args[0]
        assert "unresolveReviewThread" in mutation
        assert variables == {"threadId": "PRT_kwDOABcD12MAAAABcDE3fg"}

    def test_resolve_thread_with_numeric_id(self) -> None:
        """Test resolving thread with numeric ID."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": {
                        "id": "123456789",
                        "isResolved": True,
                    }
                }
            }
        }

        service = ResolveService(mock_github_service)
        result = service.resolve_thread("123456789")

        assert result["thread_id"] == "123456789"
        assert result["action"] == "resolve"
        assert result["success"] is True

    def test_resolve_thread_invalid_id(self) -> None:
        """Test resolving thread with invalid ID."""
        mock_github_service = Mock(spec=GitHubService)
        service = ResolveService(mock_github_service)

        with pytest.raises(ResolveServiceError) as exc_info:
            service.resolve_thread("invalid-id")
        assert "Invalid thread ID" in str(exc_info.value)

    def test_resolve_thread_not_found_error(self) -> None:
        """Test resolving thread when thread is not found."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "errors": [
                {
                    "message": "Thread not found",
                    "type": "NOT_FOUND",
                }
            ]
        }

        service = ResolveService(mock_github_service)

        with pytest.raises(ThreadNotFoundError) as exc_info:
            service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")
        assert "Thread PRT_kwDOABcD12MAAAABcDE3fg not found" in str(exc_info.value)

    def test_resolve_thread_permission_error(self) -> None:
        """Test resolving thread with permission error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "errors": [
                {
                    "message": "Resource not accessible by integration",
                    "type": "FORBIDDEN",
                }
            ]
        }

        service = ResolveService(mock_github_service)

        with pytest.raises(ThreadPermissionError) as exc_info:
            service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")
        assert "Permission denied" in str(exc_info.value)
        assert "cannot resolve thread" in str(exc_info.value)

    def test_resolve_thread_generic_error(self) -> None:
        """Test resolving thread with generic GraphQL error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "errors": [
                {
                    "message": "Something went wrong",
                    "type": "INTERNAL_ERROR",
                }
            ]
        }

        service = ResolveService(mock_github_service)

        with pytest.raises(ResolveServiceError) as exc_info:
            service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")
        assert "Failed to resolve thread" in str(exc_info.value)
        assert "Something went wrong" in str(exc_info.value)

    def test_resolve_thread_no_data_error(self) -> None:
        """Test resolving thread when no thread data is returned."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "resolveReviewThread": {}
            }
        }

        service = ResolveService(mock_github_service)

        with pytest.raises(ResolveServiceError) as exc_info:
            service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")
        assert "No thread data returned from GraphQL mutation" in str(exc_info.value)

    def test_unresolve_thread_permission_error(self) -> None:
        """Test unresolving thread with permission error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "errors": [
                {
                    "message": "Permission denied",
                    "type": "FORBIDDEN",
                }
            ]
        }

        service = ResolveService(mock_github_service)

        with pytest.raises(ThreadPermissionError) as exc_info:
            service.unresolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")
        assert "Permission denied" in str(exc_info.value)
        assert "cannot unresolve thread" in str(exc_info.value)


class TestResolveServiceExceptions:
    """Test resolve service exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """Test that all exceptions inherit from ResolveServiceError."""
        assert issubclass(ThreadNotFoundError, ResolveServiceError)
        assert issubclass(ThreadPermissionError, ResolveServiceError)

    def test_exception_messages(self) -> None:
        """Test exception message handling."""
        with pytest.raises(ResolveServiceError) as exc_info:
            raise ResolveServiceError("Test error")
        assert str(exc_info.value) == "Test error"

        with pytest.raises(ThreadNotFoundError) as exc_info:
            raise ThreadNotFoundError("Thread not found")
        assert str(exc_info.value) == "Thread not found"

        with pytest.raises(ThreadPermissionError) as exc_info:
            raise ThreadPermissionError("Permission denied")
        assert str(exc_info.value) == "Permission denied"


class TestResolveServiceErrorHandling:
    """Test error handling in resolve service."""

    def test_handle_multiple_graphql_errors(self) -> None:
        """Test handling multiple GraphQL errors."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "errors": [
                {"message": "First error"},
                {"message": "Second error"},
            ]
        }

        service = ResolveService(mock_github_service)

        with pytest.raises(ResolveServiceError) as exc_info:
            service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")
        assert "First error; Second error" in str(exc_info.value)

    def test_handle_error_with_different_not_found_messages(self) -> None:
        """Test handling different 'not found' error message formats."""
        test_cases = [
            "Thread not found",
            "Resource does not exist", 
            "Object not found in repository",
        ]

        for error_message in test_cases:
            mock_github_service = Mock(spec=GitHubService)
            mock_github_service.execute_graphql_query.return_value = {
                "errors": [{"message": error_message}]
            }

            service = ResolveService(mock_github_service)

            with pytest.raises(ThreadNotFoundError):
                service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")

    def test_handle_error_with_different_permission_messages(self) -> None:
        """Test handling different permission error message formats."""
        test_cases = [
            "Permission denied",
            "Forbidden access",
            "Resource not accessible by integration",
        ]

        for error_message in test_cases:
            mock_github_service = Mock(spec=GitHubService)
            mock_github_service.execute_graphql_query.return_value = {
                "errors": [{"message": error_message}]
            }

            service = ResolveService(mock_github_service)

            with pytest.raises(ThreadPermissionError):
                service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")


class TestResolveServiceIntegration:
    """Integration tests for resolve service with edge cases."""

    def test_resolve_thread_with_all_response_fields(self) -> None:
        """Test resolving thread with complete API response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": {
                        "id": "PRT_kwDOABcD12MAAAABcDE3fg",
                        "isResolved": True,
                        "url": "https://github.com/owner/repo/pull/123#discussion_r123",
                    }
                }
            }
        }

        service = ResolveService(mock_github_service)
        result = service.resolve_thread("PRT_kwDOABcD12MAAAABcDE3fg")

        assert result["thread_id"] == "PRT_kwDOABcD12MAAAABcDE3fg"
        assert result["action"] == "resolve"
        assert result["success"] is True
        assert result["is_resolved"] == "true"
        assert "github.com" in result["thread_url"]

    def test_unresolve_thread_with_minimal_response(self) -> None:
        """Test unresolving thread with minimal API response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "unresolveReviewThread": {
                    "thread": {
                        "id": "123456789",
                        "isResolved": False,
                    }
                }
            }
        }

        service = ResolveService(mock_github_service)
        result = service.unresolve_thread("123456789")

        assert result["thread_id"] == "123456789"
        assert result["action"] == "unresolve"
        assert result["success"] is True
        assert result["is_resolved"] == "false"

    def test_resolve_thread_boundary_thread_ids(self) -> None:
        """Test resolving threads with boundary thread ID values."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.execute_graphql_query.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": {
                        "id": "1",
                        "isResolved": True,
                    }
                }
            }
        }

        service = ResolveService(mock_github_service)

        # Test single digit ID
        result = service.resolve_thread("1")
        assert result["thread_id"] == "1"

        # Test minimum valid node ID
        mock_github_service.execute_graphql_query.return_value["data"]["resolveReviewThread"]["thread"]["id"] = "PRT_kwDOABcD"
        result = service.resolve_thread("PRT_kwDOABcD")
        assert result["thread_id"] == "PRT_kwDOABcD"