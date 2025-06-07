"""Reply service for posting comments to GitHub pull request reviews."""

import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .github_service import GitHubAPIError, GitHubService, GitHubServiceError


class ReplyServiceError(GitHubServiceError):
    """Base exception for reply service errors."""

    pass


class CommentNotFoundError(ReplyServiceError):
    """Raised when the specified comment cannot be found."""

    pass


@dataclass
class ReplyRequest:
    """Data class for encapsulating reply request parameters."""

    comment_id: str
    reply_body: str
    owner: Optional[str] = None
    repo: Optional[str] = None


class ReplyService:
    """Service for posting replies to GitHub pull request review comments."""

    def __init__(self, github_service: Optional[GitHubService] = None) -> None:
        """Initialize the reply service.

        Args:
            github_service: Optional GitHubService instance. If None, creates a new one.
        """
        self.github_service = github_service or GitHubService()

    def post_reply(self, request: ReplyRequest) -> Dict[str, str]:
        """Post a reply to a pull request review comment.

        Args:
            request: ReplyRequest object containing all necessary parameters.

        Returns:
            Dictionary containing reply information including URL and ID.

        Raises:
            ReplyServiceError: If the reply fails to post.
            CommentNotFoundError: If the comment cannot be found.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        # Get repository info if not provided
        if not request.owner or not request.repo:
            repo_info = self._get_repository_info()
            owner = request.owner or repo_info[0]
            repo = request.repo or repo_info[1]
        else:
            owner = request.owner
            repo = request.repo

        # Construct the API endpoint
        endpoint = f"repos/{owner}/{repo}/pulls/comments/{request.comment_id}/replies"

        # Prepare the request payload (for reference)
        # payload = {"body": request.reply_body}

        # Execute the API call using gh CLI
        try:
            args = [
                "api",
                endpoint,
                "--method",
                "POST",
                "--field",
                f"body={request.reply_body}",
                "--header",
                "Accept: application/vnd.github+json",
            ]

            result = self.github_service.run_gh_command(args)
            response_data = json.loads(result.stdout)

            # Extract relevant information from the response
            reply_info = {
                "reply_id": str(response_data.get("id", "")),
                "reply_url": response_data.get("html_url", ""),
                "comment_id": request.comment_id,
                "created_at": response_data.get("created_at", ""),
                "author": response_data.get("user", {}).get("login", ""),
            }

            return reply_info

        except json.JSONDecodeError as e:
            raise ReplyServiceError(f"Failed to parse API response: {e}") from e
        except GitHubAPIError as e:
            # Check if it's a "not found" error for the comment
            if "404" in str(e) or "not found" in str(e).lower():
                raise CommentNotFoundError(
                    f"Comment {request.comment_id} not found"
                ) from e
            raise ReplyServiceError(f"Failed to post reply: {e}") from e

    def _get_repository_info(self) -> Tuple[str, str]:
        """Get the current repository owner and name.

        Returns:
            Tuple of (owner, repo_name).

        Raises:
            ReplyServiceError: If repository info cannot be determined.
        """
        repo_info = self.github_service.get_current_repo()
        if not repo_info:
            raise ReplyServiceError(
                "Could not determine repository information. "
                "Make sure you're in a git repository with GitHub remote."
            )

        parts = repo_info.split("/")
        if len(parts) != 2:
            raise ReplyServiceError(f"Invalid repository format: {repo_info}")

        return parts[0], parts[1]

    def validate_comment_exists(
        self, owner: str, repo: str, pull_number: int, comment_id: str
    ) -> bool:
        """Validate that a comment exists in the specified pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull request number.
            comment_id: Comment ID to validate.

        Returns:
            True if the comment exists, False otherwise.
        """
        try:
            # Query the specific comment to see if it exists
            endpoint = f"repos/{owner}/{repo}/pulls/comments/{comment_id}"
            args = ["api", endpoint, "--header", "Accept: application/vnd.github+json"]

            result = self.github_service.run_gh_command(args)
            data = json.loads(result.stdout)

            # Check if the comment belongs to the specified PR
            comment_pr_number = data.get("pull_request_number")
            return comment_pr_number == pull_number  # type: ignore[no-any-return]

        except (GitHubAPIError, json.JSONDecodeError, KeyError):
            return False
