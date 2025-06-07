"""Tests for the reply service module."""

import json
from unittest.mock import Mock, patch

import pytest

from toady.github_service import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubService,
)
from toady.reply_service import (
    CommentNotFoundError,
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
    @patch.object(ReplyService, "_get_pull_number_from_comment")
    def test_post_reply_success(
        self, mock_get_pr_number: Mock, mock_get_repo_info: Mock
    ) -> None:
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
        mock_github_service.run_gh_command.return_value = mock_response

        mock_get_repo_info.return_value = ("owner", "repo")
        mock_get_pr_number.return_value = 1

        service = ReplyService(mock_github_service)
        result = service.post_reply("123456789", "Test reply")

        assert result["reply_id"] == "123456789"
        assert "https://github.com/owner/repo/pull/1" in result["reply_url"]
        assert result["comment_id"] == "123456789"
        assert result["created_at"] == "2023-01-01T12:00:00Z"
        assert result["author"] == "testuser"

        # Verify the API call was made correctly
        expected_args = [
            "api",
            "repos/owner/repo/pulls/1/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            "body=Test reply",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        mock_github_service.run_gh_command.assert_called_once_with(expected_args)

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
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        result = service.post_reply(
            comment_id="IC_kwDOABcD12MAAAABcDE3fg",
            reply_body="Thanks for the feedback!",
            owner="testowner",
            repo="testrepo",
            pull_number=5,
        )

        assert result["reply_id"] == "987654321"
        assert result["author"] == "reviewer"

        # Verify the API call with explicit parameters
        expected_args = [
            "api",
            "repos/testowner/testrepo/pulls/5/comments/IC_kwDOABcD12MAAAABcDE3fg/replies",
            "--method",
            "POST",
            "--field",
            "body=Thanks for the feedback!",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        mock_github_service.run_gh_command.assert_called_once_with(expected_args)

    @patch.object(ReplyService, "_get_repository_info")
    @patch.object(ReplyService, "_get_pull_number_from_comment")
    def test_post_reply_comment_not_found(
        self, mock_get_pr_number: Mock, mock_get_repo_info: Mock
    ) -> None:
        """Test reply posting when comment is not found."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.run_gh_command.side_effect = GitHubAPIError("404 Not Found")

        mock_get_repo_info.return_value = ("owner", "repo")
        mock_get_pr_number.return_value = 1

        service = ReplyService(mock_github_service)
        with pytest.raises(CommentNotFoundError) as exc_info:
            service.post_reply("nonexistent", "Test reply")

        assert "Comment nonexistent not found in PR #1" in str(exc_info.value)

    @patch.object(ReplyService, "_get_repository_info")
    @patch.object(ReplyService, "_get_pull_number_from_comment")
    def test_post_reply_authentication_error(
        self, mock_get_pr_number: Mock, mock_get_repo_info: Mock
    ) -> None:
        """Test reply posting with authentication error."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.run_gh_command.side_effect = GitHubAuthenticationError(
            "Auth failed"
        )

        mock_get_repo_info.return_value = ("owner", "repo")
        mock_get_pr_number.return_value = 1

        service = ReplyService(mock_github_service)
        with pytest.raises(GitHubAuthenticationError):
            service.post_reply("123456789", "Test reply")

    @patch.object(ReplyService, "_get_repository_info")
    @patch.object(ReplyService, "_get_pull_number_from_comment")
    def test_post_reply_invalid_json_response(
        self, mock_get_pr_number: Mock, mock_get_repo_info: Mock
    ) -> None:
        """Test reply posting with invalid JSON response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = "invalid json"
        mock_github_service.run_gh_command.return_value = mock_response

        mock_get_repo_info.return_value = ("owner", "repo")
        mock_get_pr_number.return_value = 1

        service = ReplyService(mock_github_service)
        with pytest.raises(ReplyServiceError) as exc_info:
            service.post_reply("123456789", "Test reply")

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

    def test_get_pull_number_from_comment_success(self) -> None:
        """Test successful PR number retrieval from current branch."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps({"number": 42})
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        pr_number = service._get_pull_number_from_comment("owner", "repo", "123456789")

        assert pr_number == 42
        mock_github_service.run_gh_command.assert_called_once_with(
            ["pr", "view", "--json", "number"]
        )

    def test_get_pull_number_from_comment_no_pr(self) -> None:
        """Test PR number retrieval when not on a PR branch."""
        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.run_gh_command.side_effect = GitHubAPIError("No PR found")

        service = ReplyService(mock_github_service)
        with pytest.raises(ReplyServiceError) as exc_info:
            service._get_pull_number_from_comment("owner", "repo", "123456789")

        assert "Could not determine pull request number" in str(exc_info.value)

    def test_get_pull_number_from_comment_invalid_response(self) -> None:
        """Test PR number retrieval with invalid response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = json.dumps({"number": "not-a-number"})
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        with pytest.raises(ReplyServiceError) as exc_info:
            service._get_pull_number_from_comment("owner", "repo", "123456789")

        assert "Could not determine pull request number" in str(exc_info.value)

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

    def test_validate_comment_exists_invalid_response(self) -> None:
        """Test comment validation with invalid JSON response."""
        mock_github_service = Mock(spec=GitHubService)
        mock_response = Mock()
        mock_response.stdout = "invalid json"
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        exists = service.validate_comment_exists("owner", "repo", 42, "123456789")

        assert exists is False


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
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        special_body = (
            "Thanks for the feedback! 🎉 Here's some code: `console.log('hello');`"
        )

        result = service.post_reply(
            comment_id="123456789",
            reply_body=special_body,
            owner="owner",
            repo="repo",
            pull_number=1,
        )

        assert result["reply_id"] == "123456789"

        # Verify the special characters were properly passed
        expected_args = [
            "api",
            "repos/owner/repo/pulls/1/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            f"body={special_body}",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        mock_github_service.run_gh_command.assert_called_once_with(expected_args)

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
        mock_github_service.run_gh_command.return_value = mock_response

        service = ReplyService(mock_github_service)
        large_body = "A" * 5000  # Large but reasonable reply

        result = service.post_reply(
            comment_id="123456789",
            reply_body=large_body,
            owner="owner",
            repo="repo",
            pull_number=1,
        )

        assert result["reply_id"] == "123456789"

        # Verify the large body was properly handled
        expected_args = [
            "api",
            "repos/owner/repo/pulls/1/comments/123456789/replies",
            "--method",
            "POST",
            "--field",
            f"body={large_body}",
            "--header",
            "Accept: application/vnd.github+json",
        ]
        mock_github_service.run_gh_command.assert_called_once_with(expected_args)
