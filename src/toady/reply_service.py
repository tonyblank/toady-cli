"""Reply service for posting comments to GitHub pull request reviews."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .github_service import GitHubAPIError, GitHubService, GitHubServiceError
from .reply_mutations import (
    create_comment_reply_mutation,
    create_thread_reply_mutation,
    determine_reply_strategy,
)


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

    def post_reply(
        self, request: ReplyRequest, fetch_context: bool = False
    ) -> Dict[str, Any]:
        """Post a reply to a pull request review comment using GraphQL mutations.

        This method now uses GraphQL mutations instead of REST API calls for better
        integration with GitHub's modern API. It supports both numeric comment IDs
        (legacy) and GitHub node IDs for backward compatibility.

        Args:
            request: ReplyRequest object containing all necessary parameters.
            fetch_context: Whether to fetch additional context (PR info, parent
                          comment, etc.). Set to True when verbose output is
                          needed. Default: False.

        Returns:
            Dictionary containing comprehensive reply information including:
            - reply_id: The unique ID of the posted reply
            - reply_url: Direct URL to view the reply on GitHub
            - comment_id: The ID of the comment being replied to
            - created_at: Timestamp when the reply was created
            - author: Username of the reply author
            - pr_number: Pull request number the comment belongs to
            - pr_title: Title of the pull request
            - thread_url: URL to the entire review thread
            - body_preview: First 100 characters of the reply body
            - parent_comment_author: Author of the comment being replied to

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

        try:
            # Determine the best strategy based on comment ID format
            strategy = determine_reply_strategy(request.comment_id)

            if strategy == "thread_reply":
                # Use addPullRequestReviewThreadReply for thread node IDs
                return self._post_thread_reply(request, fetch_context, owner, repo)
            elif strategy == "comment_reply" and not request.comment_id.isdigit():
                # Use addPullRequestReviewComment with inReplyTo for comment node IDs
                return self._post_comment_reply(request, fetch_context, owner, repo)
            else:
                # Use REST API for numeric IDs to maintain backward compatibility
                return self._post_reply_fallback_rest(
                    request, fetch_context, owner, repo
                )

        except ValueError as e:
            raise ReplyServiceError(f"Invalid comment ID: {e}") from e

    def _post_thread_reply(
        self, request: ReplyRequest, fetch_context: bool, owner: str, repo: str
    ) -> Dict[str, Any]:
        """Post a reply using the addPullRequestReviewThreadReply mutation.

        Args:
            request: ReplyRequest object.
            fetch_context: Whether to fetch additional context.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary with reply information.
        """
        try:
            mutation, variables = create_thread_reply_mutation(
                request.comment_id, request.reply_body
            )
            result = self.github_service.execute_graphql_query(mutation, variables)

            # Check for GraphQL errors
            if "errors" in result:
                self._handle_graphql_errors(result["errors"], request.comment_id)

            # Extract comment data from response
            comment_data = (
                result.get("data", {})
                .get("addPullRequestReviewThreadReply", {})
                .get("comment", {})
            )

            if not comment_data:
                raise ReplyServiceError(
                    "No comment data returned from GraphQL mutation"
                )

            return self._build_reply_info_from_graphql(
                comment_data, request, fetch_context, owner, repo
            )

        except GitHubAPIError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise CommentNotFoundError(
                    f"Thread {request.comment_id} not found"
                ) from e
            raise ReplyServiceError(f"Failed to post reply: {e}") from e

    def _post_comment_reply(
        self, request: ReplyRequest, fetch_context: bool, owner: str, repo: str
    ) -> Dict[str, Any]:
        """Post a reply using the addPullRequestReviewComment mutation with inReplyTo.

        This method first needs to get the review ID associated with the comment.

        Args:
            request: ReplyRequest object.
            fetch_context: Whether to fetch additional context.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary with reply information.
        """
        try:
            # First, get the review ID from the comment
            review_id = self._get_review_id_for_comment(owner, repo, request.comment_id)

            mutation, variables = create_comment_reply_mutation(
                review_id, request.comment_id, request.reply_body
            )
            result = self.github_service.execute_graphql_query(mutation, variables)

            # Check for GraphQL errors
            if "errors" in result:
                self._handle_graphql_errors(result["errors"], request.comment_id)

            # Extract comment data from response
            comment_data = (
                result.get("data", {})
                .get("addPullRequestReviewComment", {})
                .get("comment", {})
            )

            if not comment_data:
                raise ReplyServiceError(
                    "No comment data returned from GraphQL mutation"
                )

            return self._build_reply_info_from_graphql(
                comment_data, request, fetch_context, owner, repo
            )

        except GitHubAPIError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise CommentNotFoundError(
                    f"Comment {request.comment_id} not found"
                ) from e
            raise ReplyServiceError(f"Failed to post reply: {e}") from e

    def _handle_graphql_errors(
        self, errors: List[Dict[str, Any]], comment_id: str
    ) -> None:
        """Handle GraphQL errors and raise appropriate exceptions.

        Args:
            errors: List of GraphQL errors.
            comment_id: The comment ID that caused the error.

        Raises:
            CommentNotFoundError: If comment is not found.
            ReplyServiceError: For other GraphQL errors.
        """
        error_messages = []
        for error in errors:
            message = error.get("message", str(error))

            # Check for specific error types
            if "not found" in message.lower() or "does not exist" in message.lower():
                raise CommentNotFoundError(f"Comment {comment_id} not found")

            error_messages.append(message)

        # If we get here, it's a generic GraphQL error
        combined_message = "; ".join(error_messages)
        raise ReplyServiceError(f"Failed to post reply: {combined_message}")

    def _build_reply_info_from_graphql(
        self,
        comment_data: Dict[str, Any],
        request: ReplyRequest,
        fetch_context: bool,
        owner: str,
        repo: str,
    ) -> Dict[str, Any]:
        """Build reply information dictionary from GraphQL response data.

        Args:
            comment_data: GraphQL comment data.
            request: Original reply request.
            fetch_context: Whether to fetch additional context.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary with comprehensive reply information.
        """
        reply_info = {
            "reply_id": str(comment_data.get("id", "")),
            "reply_url": comment_data.get("url", ""),
            "comment_id": request.comment_id,
            "created_at": comment_data.get("createdAt", ""),
            "author": comment_data.get("author", {}).get("login", ""),
            "body_preview": request.reply_body[:100]
            + ("..." if len(request.reply_body) > 100 else ""),
        }

        # Extract review ID if available
        if "pullRequestReview" in comment_data:
            review_data = comment_data["pullRequestReview"]
            if "id" in review_data:
                reply_info["review_id"] = str(review_data["id"])

        # Try to get parent comment info for context only if requested
        if fetch_context:
            parent_info = self._get_parent_comment_info(owner, repo, request.comment_id)
            if parent_info:
                reply_info.update(parent_info)

        return reply_info

    def _post_reply_fallback_rest(
        self, request: ReplyRequest, fetch_context: bool, owner: str, repo: str
    ) -> Dict[str, Any]:
        """Fallback to REST API for posting replies.

        This method uses the original REST API approach for backward compatibility.

        Args:
            request: ReplyRequest object.
            fetch_context: Whether to fetch additional context.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary with reply information.
        """
        # Construct the API endpoint
        endpoint = f"repos/{owner}/{repo}/pulls/comments/{request.comment_id}/replies"

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

            # Extract comprehensive information from the response
            reply_info = {
                "reply_id": str(response_data.get("id", "")),
                "reply_url": response_data.get("html_url", ""),
                "comment_id": request.comment_id,
                "created_at": response_data.get("created_at", ""),
                "author": response_data.get("user", {}).get("login", ""),
                "body_preview": request.reply_body[:100]
                + ("..." if len(request.reply_body) > 100 else ""),
            }

            # Extract additional context if available
            if "pull_request_review_id" in response_data:
                reply_info["review_id"] = str(response_data["pull_request_review_id"])

            # Try to get parent comment info for context only if requested
            if fetch_context:
                parent_info = self._get_parent_comment_info(
                    owner, repo, request.comment_id
                )
                if parent_info:
                    reply_info.update(parent_info)

            return reply_info

        except json.JSONDecodeError as e:
            raise ReplyServiceError(f"Failed to parse API response: {e}") from e
        except GitHubAPIError as e:
            # Check if it's a "not found" error for the comment
            if "404" in str(e) or "not found" in str(e).lower():
                raise CommentNotFoundError(
                    f"Comment {request.comment_id} not found"
                ) from e
            # Check if it's a "review already submitted" error
            elif "review has already been submitted" in str(e).lower():
                raise ReplyServiceError(
                    f"Cannot reply to comment {request.comment_id} because the review "
                    f"has already been submitted. Try using the thread ID instead, or "
                    f"resolve the thread to acknowledge the comment."
                ) from e
            raise ReplyServiceError(f"Failed to post reply: {e}") from e

    def _get_review_id_for_comment(
        self, _owner: str, _repo: str, comment_id: str
    ) -> str:
        """Get the review ID associated with a node ID comment.

        This method uses GraphQL to query the comment and get its associated review ID.

        Args:
            owner: Repository owner.
            repo: Repository name.
            comment_id: Comment node ID.

        Returns:
            The review ID (node ID).

        Raises:
            ReplyServiceError: If the review ID cannot be determined.
            CommentNotFoundError: If the comment is not found.
        """
        try:
            query = """
            query GetCommentReview($commentId: ID!) {
                node(id: $commentId) {
                    ... on PullRequestReviewComment {
                        pullRequestReview {
                            id
                        }
                    }
                }
            }
            """

            variables = {"commentId": comment_id}
            result = self.github_service.execute_graphql_query(query, variables)

            if "errors" in result:
                error_messages = [
                    error.get("message", str(error)) for error in result["errors"]
                ]
                if any("not found" in msg.lower() for msg in error_messages):
                    raise CommentNotFoundError(f"Comment {comment_id} not found")
                raise ReplyServiceError(
                    f"Failed to get review ID: {'; '.join(error_messages)}"
                )

            comment_node = result.get("data", {}).get("node")
            if not comment_node:
                raise CommentNotFoundError(f"Comment {comment_id} not found")

            review_data = comment_node.get("pullRequestReview")
            if not review_data or "id" not in review_data:
                raise ReplyServiceError(f"Comment {comment_id} is not part of a review")

            return str(review_data["id"])

        except GitHubAPIError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise CommentNotFoundError(f"Comment {comment_id} not found") from e
            raise ReplyServiceError(f"Failed to get review ID: {e}") from e

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

    def _get_parent_comment_info(
        self, owner: str, repo: str, comment_id: str
    ) -> Optional[Dict[str, str]]:
        """Get information about the parent comment for additional context.

        Args:
            owner: Repository owner.
            repo: Repository name.
            comment_id: Comment ID to get info for.

        Returns:
            Dictionary with parent comment info or None if not available.
        """
        try:
            # Query the specific comment to get context
            endpoint = f"repos/{owner}/{repo}/pulls/comments/{comment_id}"
            args = ["api", endpoint, "--header", "Accept: application/vnd.github+json"]

            result = self.github_service.run_gh_command(args)
            data = json.loads(result.stdout)

            parent_info = {}

            # Get PR information from the comment
            if "pull_request_url" in data:
                pr_url = data["pull_request_url"]
                pr_number = pr_url.split("/")[-1]
                parent_info["pr_number"] = pr_number

                # Try to get PR title
                pr_info = self._get_pr_info(owner, repo, pr_number)
                if pr_info:
                    parent_info["pr_title"] = pr_info.get("title", "")
                    parent_info["pr_url"] = pr_info.get("html_url", "")

            # Get parent comment author
            if "user" in data and "login" in data["user"]:
                parent_info["parent_comment_author"] = data["user"]["login"]

            # Get thread URL if available
            if "html_url" in data:
                # Convert comment URL to thread URL
                comment_url = data["html_url"]
                thread_url = (
                    comment_url.split("#")[0]
                    + "#pullrequestreview-"
                    + str(data.get("pull_request_review_id", ""))
                )
                if data.get("pull_request_review_id"):
                    parent_info["thread_url"] = thread_url

            return parent_info if parent_info else None

        except (GitHubAPIError, json.JSONDecodeError, KeyError):
            # Don't fail the whole operation if we can't get parent info
            return None

    def _get_pr_info(
        self, owner: str, repo: str, pr_number: str
    ) -> Optional[Dict[str, str]]:
        """Get basic PR information.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            Dictionary with PR info or None if not available.
        """
        try:
            endpoint = f"repos/{owner}/{repo}/pulls/{pr_number}"
            args = ["api", endpoint, "--header", "Accept: application/vnd.github+json"]

            result = self.github_service.run_gh_command(args)
            data = json.loads(result.stdout)

            return {
                "title": data.get("title", ""),
                "html_url": data.get("html_url", ""),
                "state": data.get("state", ""),
            }

        except (GitHubAPIError, json.JSONDecodeError, KeyError):
            return None
