"""Tests for the reply service module."""

import json
from unittest.mock import Mock, patch

import pytest

from toady.services.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubService,
)
from toady.services.reply_service import (
    CommentNotFoundError,
    ReplyRequest,
    ReplyService,
    ReplyServiceError,
)


class TestReplyService:
    """Test the ReplyService class."""

    def test_init_default(self) -> None:
        """Test ReplyService initialization with default GitHubService."""
        service = ReplyService()
        assert service.github_service is not None
        assert isinstance(service.github_service, GitHubService)

    def test_init_custom_service(self) -> None:
        """Test ReplyService initialization with custom GitHubService."""
        mock_github_service = Mock(spec=GitHubService)
        service = ReplyService(mock_github_service)
        assert service.github_service is mock_github_service

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_success(self, mock_get_repo_info: Mock) -> None:
        """Test successful reply posting."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps(
            {
                "id": 123456789,
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r123456789",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {"login": "testuser"},
            }
        )

        # Set up the responses: first for posting reply, then parent info fails
        mock_github_service.run_gh_command.side_effect = [
            mock_response,  # post_reply call
            GitHubAPIError("404 Not Found"),  # _get_parent_comment_info fails
        ]

        mock_get_repo_info.return_value = ("owner", "repo")

        service = ReplyService(mock_github_service)
        request = ReplyRequest(comment_id="123456789", reply_body="Test reply")
        result = service.post_reply(request)

        assert result["reply_id"] == "123456789"
        assert "https://github.com/owner/repo/pull/1" in result["reply_url"]
        assert result["comment_id"] == "123456789"
        assert result["created_at"] == "2023-01-01T12:00:00Z"
        assert result["author"] == "testuser"

        # Verify the API call was made correctly
        expected_args = [
            "api",
            "repos/owner/repo/pulls/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            "body=Test reply",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        assert (
            mock_github_service.run_gh_command.call_args_list[0][0][0] == expected_args
        )

    def test_post_reply_with_explicit_params(self) -> None:
        """Test reply posting with explicitly provided parameters."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps(
            {
                "id": 987654321,
                "html_url": "https://github.com/owner/repo/pull/5#discussion_r987654321",
                "created_at": "2023-01-02T15:30:00Z",
                "user": {"login": "reviewer"},
            }
        )

        # Set up the responses: first for posting reply, then parent info fails
        mock_github_service.run_gh_command.side_effect = [
            mock_response,  # post_reply call
            GitHubAPIError("404 Not Found"),  # _get_parent_comment_info fails
        ]

        service = ReplyService(mock_github_service)
        request = ReplyRequest(
            comment_id="123456789",
            reply_body="Thanks for the feedback!",
            owner="testowner",
            repo="testrepo",
        )
        result = service.post_reply(request)

        assert result["reply_id"] == "987654321"
        assert result["author"] == "reviewer"

        # Verify the API call with explicit parameters
        expected_args = [
            "api",
            "repos/testowner/testrepo/pulls/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            "body=Thanks for the feedback!",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        assert (
            mock_github_service.run_gh_command.call_args_list[0][0][0] == expected_args
        )

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_comment_not_found(self, mock_get_repo_info: Mock) -> None:
        """Test reply posting when comment is not found."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.run_gh_command.side_effect = GitHubAPIError("404 Not Found")

        mock_get_repo_info.return_value = ("owner", "repo")

        service = ReplyService(mock_github_service)
        request = ReplyRequest(comment_id="999999999", reply_body="Test reply")
        with pytest.raises(CommentNotFoundError) as exc_info:
            service.post_reply(request)

        assert "Comment 999999999 not found" in str(exc_info.value)

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_authentication_error(self, mock_get_repo_info: Mock) -> None:
        """Test reply posting with authentication error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.run_gh_command.side_effect = GitHubAuthenticationError(
            "Auth failed"
        )

        mock_get_repo_info.return_value = ("owner", "repo")

        service = ReplyService(mock_github_service)
        request = ReplyRequest(comment_id="123456789", reply_body="Test reply")
        with pytest.raises(GitHubAuthenticationError):
            service.post_reply(request)

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_invalid_json_response(self, mock_get_repo_info: Mock) -> None:
        """Test reply posting with invalid JSON response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = "invalid json"
        mock_github_service.run_gh_command.return_value = mock_response

        mock_get_repo_info.return_value = ("owner", "repo")

        service = ReplyService(mock_github_service)
        request = ReplyRequest(comment_id="123456789", reply_body="Test reply")
        with pytest.raises(ReplyServiceError) as exc_info:
            service.post_reply(request)

        assert "Failed to parse API response" in str(exc_info.value)

    def test_get_repository_info_success(self) -> None:
        """Test successful repository info retrieval."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.get_current_repo.return_value = "owner/repo"

        service = ReplyService(mock_github_service)
        owner, repo = service._get_repository_info()

        assert owner == "owner"
        assert repo == "repo"

    def test_get_repository_info_no_repo(self) -> None:
        """Test repository info retrieval when not in a repo."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.get_current_repo.return_value = None

        service = ReplyService(mock_github_service)
        with pytest.raises(ReplyServiceError) as exc_info:
            service._get_repository_info()

        assert "Could not determine repository information" in str(exc_info.value)

    def test_get_repository_info_invalid_format(self) -> None:
        """Test repository info retrieval with invalid format."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.get_current_repo.return_value = "invalid-format"

        service = ReplyService(mock_github_service)
        with pytest.raises(ReplyServiceError) as exc_info:
            service._get_repository_info()

        assert "Invalid repository format" in str(exc_info.value)

    def test_validate_comment_exists_success(self) -> None:
        """Test successful comment validation."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps({"pull_request_number": 42})
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        exists = service.validate_comment_exists("owner", "repo", 42, "123456789")

        assert exists is True
        expected_args = [
            "api",
            "repos/owner/repo/pulls/comments/123456789",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        mock_github_service.run_gh_command.assert_called_once_with(expected_args)

    def test_validate_comment_exists_wrong_pr(self) -> None:
        """Test comment validation when comment belongs to different PR."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps({"pull_request_number": 999})
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        exists = service.validate_comment_exists("owner", "repo", 42, "123456789")

        assert exists is False

    def test_validate_comment_exists_not_found(self) -> None:
        """Test comment validation when comment doesn't exist."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.run_gh_command.side_effect = GitHubAPIError("404 Not Found")

        service = ReplyService(mock_github_service)
        exists = service.validate_comment_exists("owner", "repo", 42, "123456789")

        assert exists is False

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_node_id_success(self, mock_get_repo_info: Mock) -> None:
        """Test successful reply posting with node ID."""
        mock_get_repo_info.return_value = ("owner", "repo")

        mock_github_service = Mock(spec=GitHubService)
        mock_response = {
            "data": {
                "addPullRequestReviewThreadReply": {
                    "comment": {
                        "id": "MDEyOklzc3VlQ29tbWVudDEyMzQ1Njc4OQ==",
                        "body": "Test reply body",
                        "author": {"login": "testuser"},
                        "createdAt": "2023-01-01T12:00:00Z",
                        "url": "https://github.com/owner/repo/pull/1#discussion_r123456789",
                    }
                }
            }
        }
        mock_github_service.post_reply.return_value = mock_response

        service = ReplyService(mock_github_service)
        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        result = service.post_reply(request)

        assert result is not None
        mock_github_service.post_reply.assert_called_once()

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_numeric_id_fallback(self, mock_get_repo_info: Mock) -> None:
        """Test reply posting with numeric ID falls back to REST."""
        mock_get_repo_info.return_value = ("owner", "repo")

        mock_github_service = Mock(spec=GitHubService)
        service = ReplyService(mock_github_service)

        # Mock the fallback method
        service._post_reply_fallback_rest = Mock(return_value={"id": "123456789"})

        request = ReplyRequest("123456789", "Test reply body")
        result = service.post_reply(request)

        service._post_reply_fallback_rest.assert_called_once()
        assert result == {"id": "123456789"}

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_graphql_errors(self, mock_get_repo_info: Mock) -> None:
        """Test GraphQL error handling in post_reply."""
        mock_get_repo_info.return_value = ("owner", "repo")

        mock_github_service = Mock(spec=GitHubService)
        mock_response = {"errors": [{"message": "Comment not found"}]}
        mock_github_service.post_reply.return_value = mock_response

        service = ReplyService(mock_github_service)
        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        with pytest.raises(CommentNotFoundError):
            service.post_reply(request)

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_no_comment_data(self, mock_get_repo_info: Mock) -> None:
        """Test post_reply when no comment data is returned."""
        mock_get_repo_info.return_value = ("owner", "repo")

        mock_github_service = Mock(spec=GitHubService)
        mock_response = {"data": {"addPullRequestReviewThreadReply": {}}}
        mock_github_service.post_reply.return_value = mock_response

        service = ReplyService(mock_github_service)
        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        with pytest.raises(ReplyServiceError) as exc_info:
            service.post_reply(request)

        assert "No comment data returned" in str(exc_info.value)

    def test_post_reply_invalid_comment_id(self) -> None:
        """Test post_reply with invalid comment ID raises ValueError."""
        mock_github_service = Mock(spec=GitHubService)
        service = ReplyService(mock_github_service)

        # Mock _get_repository_info to succeed, but make github_service.post_reply fail
        with patch.object(
            service, "_get_repository_info", return_value=("owner", "repo")
        ):
            # Mock post_reply to raise ValueError for invalid format
            mock_github_service.post_reply.side_effect = ValueError("Invalid format")

            request = ReplyRequest("invalid_node_id", "Test reply body")

            with pytest.raises(ReplyServiceError) as exc_info:
                service.post_reply(request)

            assert "Invalid comment ID" in str(exc_info.value)

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_github_api_error(self, mock_get_repo_info: Mock) -> None:
        """Test post_reply with GitHubAPIError."""
        mock_get_repo_info.return_value = ("owner", "repo")

        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.post_reply.side_effect = GitHubAPIError("API error")

        service = ReplyService(mock_github_service)
        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        with pytest.raises(ReplyServiceError) as exc_info:
            service.post_reply(request)

        assert "Failed to post reply" in str(exc_info.value)

    @patch.object(ReplyService, "_get_repository_info")
    def test_post_reply_github_api_not_found_error(
        self, mock_get_repo_info: Mock
    ) -> None:
        """Test post_reply with GitHubAPIError for not found."""
        mock_get_repo_info.return_value = ("owner", "repo")

        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.post_reply.side_effect = GitHubAPIError("Comment not found")

        service = ReplyService(mock_github_service)
        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        with pytest.raises(CommentNotFoundError):
            service.post_reply(request)

    def test_handle_graphql_errors_not_found(self) -> None:
        """Test _handle_graphql_errors with not found error."""
        service = ReplyService()
        errors = [{"message": "Comment not found"}]

        with pytest.raises(CommentNotFoundError):
            service._handle_graphql_errors(errors, "123")

    def test_handle_graphql_errors_does_not_exist(self) -> None:
        """Test _handle_graphql_errors with does not exist error."""
        service = ReplyService()
        errors = [{"message": "Resource does not exist"}]

        with pytest.raises(CommentNotFoundError):
            service._handle_graphql_errors(errors, "123")

    def test_handle_graphql_errors_generic(self) -> None:
        """Test _handle_graphql_errors with generic error."""
        service = ReplyService()
        errors = [{"message": "Generic error"}, {"message": "Another error"}]

        with pytest.raises(ReplyServiceError) as exc_info:
            service._handle_graphql_errors(errors, "123")

        assert "Generic error; Another error" in str(exc_info.value)

    def test_handle_graphql_errors_no_message(self) -> None:
        """Test _handle_graphql_errors with error without message."""
        service = ReplyService()
        errors = [{"type": "UNKNOWN", "path": ["field"]}]

        with pytest.raises(ReplyServiceError) as exc_info:
            service._handle_graphql_errors(errors, "123")

        # Should use str representation of error dict
        assert "type" in str(exc_info.value)

    def test_build_reply_info_from_graphql_with_context(self) -> None:
        """Test _build_reply_info_from_graphql with fetch_context=True."""
        mock_github_service = Mock(spec=GitHubService)
        service = ReplyService(mock_github_service)

        # Mock the context fetching method
        service._get_parent_comment_info = Mock(return_value={"parent": "context"})

        comment_data = {
            "id": "MDEyOklzc3VlQ29tbWVudDEyMzQ1Njc4OQ==",
            "body": "Test reply",
            "author": {"login": "testuser"},
            "createdAt": "2023-01-01T12:00:00Z",
            "url": "https://github.com/owner/repo/pull/1#discussion_r123456789",
        }

        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        result = service._build_reply_info_from_graphql(
            comment_data, request, fetch_context=True, owner="owner", repo="repo"
        )

        service._get_parent_comment_info.assert_called_once()
        assert "parent" in result
        assert result["parent"] == "context"

    def test_build_reply_info_from_graphql_without_context(self) -> None:
        """Test _build_reply_info_from_graphql with fetch_context=False."""
        mock_github_service = Mock(spec=GitHubService)
        service = ReplyService(mock_github_service)

        comment_data = {
            "id": "MDEyOklzc3VlQ29tbWVudDEyMzQ1Njc4OQ==",
            "body": "Test reply",
            "author": {"login": "testuser"},
            "createdAt": "2023-01-01T12:00:00Z",
            "url": "https://github.com/owner/repo/pull/1#discussion_r123456789",
        }

        request = ReplyRequest("RC_kwDOABCDEF4AaAaA", "Test reply body")

        result = service._build_reply_info_from_graphql(
            comment_data, request, fetch_context=False, owner="owner", repo="repo"
        )

        # Check the actual keys returned by the method
        assert "reply_id" in result
        assert "reply_url" in result
        assert "comment_id" in result
        assert "created_at" in result
        assert "author" in result
        assert "body_preview" in result
        assert result["comment_id"] == "RC_kwDOABCDEF4AaAaA"
        assert result["author"] == "testuser"

    def test_validate_comment_exists_invalid_response(self) -> None:
        """Test comment validation with invalid JSON response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = "invalid json"
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        exists = service.validate_comment_exists("owner", "repo", 42, "123456789")

        assert exists is False

    def test_post_reply_with_parent_info(self) -> None:
        """Test posting reply with parent comment information."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock main reply response
        reply_response = Mock()
        reply_response.stdout = json.dumps(
            {
                "id": 987654321,
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {"login": "testuser"},
                "pull_request_review_id": 111222333,
            }
        )

        # Mock parent comment response
        parent_response = Mock()
        parent_response.stdout = json.dumps(
            {
                "id": 123456789,
                "user": {"login": "reviewer123"},
                "pull_request_url": "https://api.github.com/repos/owner/repo/pulls/42",
                "pull_request_review_id": 111222333,
                "html_url": "https://github.com/owner/repo/pull/42#discussion_r123456789",
            }
        )

        # Mock PR info response
        pr_response = Mock()
        pr_response.stdout = json.dumps(
            {
                "number": 42,
                "title": "Add awesome feature",
                "html_url": "https://github.com/owner/repo/pull/42",
                "state": "open",
            }
        )

        # Set up responses in order
        mock_github_service.run_gh_command.side_effect = [
            reply_response,  # post_reply call
            parent_response,  # _get_parent_comment_info call
            pr_response,  # _get_pr_info call
        ]
        mock_github_service.get_current_repo.return_value = "owner/repo"

        service = ReplyService(mock_github_service)
        request = ReplyRequest(
            comment_id="123456789", reply_body="Test reply with context"
        )
        result = service.post_reply(request, fetch_context=True)

        assert result["reply_id"] == "987654321"
        assert result["pr_number"] == "42"
        assert result["pr_title"] == "Add awesome feature"
        assert result["parent_comment_author"] == "reviewer123"
        assert (
            result["thread_url"]
            == "https://github.com/owner/repo/pull/42#pullrequestreview-111222333"
        )
        assert result["body_preview"] == "Test reply with context"

    def test_post_reply_parent_info_failure(self) -> None:
        """Test posting reply when parent info fetch fails."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock main reply response
        reply_response = Mock()
        reply_response.stdout = json.dumps(
            {
                "id": 987654321,
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {"login": "testuser"},
            }
        )

        # Mock parent comment failure
        mock_github_service.run_gh_command.side_effect = [
            reply_response,  # post_reply succeeds
            GitHubAPIError("404 Not Found"),  # parent info fails
        ]
        mock_github_service.get_current_repo.return_value = "owner/repo"

        service = ReplyService(mock_github_service)
        request = ReplyRequest(comment_id="123456789", reply_body="Test reply")
        result = service.post_reply(request)

        # Should still succeed, just without parent info
        assert result["reply_id"] == "987654321"
        assert "pr_number" not in result
        assert "parent_comment_author" not in result

    def test_get_parent_comment_info_success(self) -> None:
        """Test getting parent comment information."""
        mock_github_service = Mock(spec=GitHubService)

        # Mock comment response
        comment_response = Mock()
        comment_response.stdout = json.dumps(
            {
                "id": 123456789,
                "user": {"login": "reviewer123"},
                "pull_request_url": "https://api.github.com/repos/owner/repo/pulls/42",
                "pull_request_review_id": 111222333,
                "html_url": "https://github.com/owner/repo/pull/42#discussion_r123456789",
            }
        )

        # Mock PR response
        pr_response = Mock()
        pr_response.stdout = json.dumps(
            {
                "number": 42,
                "title": "Test PR",
                "html_url": "https://github.com/owner/repo/pull/42",
                "state": "open",
            }
        )

        mock_github_service.run_gh_command.side_effect = [comment_response, pr_response]

        service = ReplyService(mock_github_service)
        result = service._get_parent_comment_info("owner", "repo", "123456789")

        assert result is not None
        assert result["pr_number"] == "42"
        assert result["pr_title"] == "Test PR"
        assert result["parent_comment_author"] == "reviewer123"
        assert "thread_url" in result

    def test_get_pr_info_success(self) -> None:
        """Test getting PR information."""
        mock_github_service = Mock(spec=GitHubService)

        pr_response = Mock()
        pr_response.stdout = json.dumps(
            {
                "number": 42,
                "title": "Amazing feature",
                "html_url": "https://github.com/owner/repo/pull/42",
                "state": "open",
            }
        )

        mock_github_service.run_gh_command.return_value = pr_response

        service = ReplyService(mock_github_service)
        result = service._get_pr_info("owner", "repo", "42")

        assert result is not None
        assert result["title"] == "Amazing feature"
        assert result["html_url"] == "https://github.com/owner/repo/pull/42"
        assert result["state"] == "open"

    def test_post_reply_long_body_preview(self) -> None:
        """Test that body preview is truncated for long replies."""
        mock_github_service = Mock(spec=GitHubService)

        reply_response = Mock()
        reply_response.stdout = json.dumps(
            {
                "id": 987654321,
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {"login": "testuser"},
            }
        )

        mock_github_service.run_gh_command.return_value = reply_response
        mock_github_service.get_current_repo.return_value = "owner/repo"

        service = ReplyService(mock_github_service)
        long_body = "x" * 150  # Body longer than 100 chars
        request = ReplyRequest(comment_id="123456789", reply_body=long_body)
        result = service.post_reply(request)

        assert result["body_preview"] == "x" * 100 + "..."


class TestReplyServiceExceptions:
    """Test reply service exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """Test that all exceptions inherit from ReplyServiceError."""
        assert issubclass(CommentNotFoundError, ReplyServiceError)

    def test_exception_messages(self) -> None:
        """Test exception message handling."""
        with pytest.raises(ReplyServiceError) as exc_info:
            raise ReplyServiceError("Test error")
        assert str(exc_info.value) == "Test error"

        with pytest.raises(CommentNotFoundError) as exc_info:
            raise CommentNotFoundError("Comment not found")
        assert str(exc_info.value) == "Comment not found"


class TestReplyServiceIntegration:
    """Integration tests for reply service with edge cases."""

    def test_post_reply_with_special_characters(self) -> None:
        """Test reply posting with special characters in body."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps(
            {
                "id": 123456789,
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r123456789",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {"login": "testuser"},
            }
        )

        # Set up the responses: first for posting reply, then parent info fails
        mock_github_service.run_gh_command.side_effect = [
            mock_response,  # post_reply call
            GitHubAPIError("404 Not Found"),  # _get_parent_comment_info fails
        ]

        service = ReplyService(mock_github_service)
        special_body = (
            "Thanks for the feedback! 🎉 Here's some code: `console.log('hello');`"
        )

        request = ReplyRequest(
            comment_id="123456789",
            reply_body=special_body,
            owner="owner",
            repo="repo",
        )
        result = service.post_reply(request)

        assert result["reply_id"] == "123456789"

        # Verify the special characters were properly passed
        expected_args = [
            "api",
            "repos/owner/repo/pulls/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            f"body={special_body}",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        assert (
            mock_github_service.run_gh_command.call_args_list[0][0][0] == expected_args
        )

    def test_post_reply_large_body(self) -> None:
        """Test reply posting with large body content."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps(
            {
                "id": 123456789,
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r123456789",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {"login": "testuser"},
            }
        )

        # Set up the responses: first for posting reply, then parent info fails
        mock_github_service.run_gh_command.side_effect = [
            mock_response,  # post_reply call
            GitHubAPIError("404 Not Found"),  # _get_parent_comment_info fails
        ]

        service = ReplyService(mock_github_service)
        large_body = "A" * 5000  # Large but reasonable reply

        request = ReplyRequest(
            comment_id="123456789",
            reply_body=large_body,
            owner="owner",
            repo="repo",
        )
        result = service.post_reply(request)

        assert result["reply_id"] == "123456789"

        # Verify the large body was properly handled
        expected_args = [
            "api",
            "repos/owner/repo/pulls/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            f"body={large_body}",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        assert (
            mock_github_service.run_gh_command.call_args_list[0][0][0] == expected_args
        )
