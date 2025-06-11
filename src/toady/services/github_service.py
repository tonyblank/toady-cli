"""GitHub CLI integration service for toady."""

import json
import subprocess
from typing import Any, Dict, List, Optional, Tuple

# GraphQL mutation constants
REPLY_THREAD_MUTATION = """
mutation AddPullRequestReviewThreadReply($threadId: ID!, $body: String!) {
    addPullRequestReviewThreadReply(input: {
        pullRequestReviewThreadId: $threadId,
        body: $body
    }) {
        comment {
            id
            body
            createdAt
            updatedAt
            author {
                login
            }
            url
            pullRequestReview {
                id
            }
            replyTo {
                id
            }
        }
    }
}
""".strip()

REPLY_COMMENT_MUTATION = """
mutation AddPullRequestReviewComment(
    $reviewId: ID!, $commentId: ID!, $body: String!
) {
    addPullRequestReviewComment(input: {
        pullRequestReviewId: $reviewId,
        inReplyTo: $commentId,
        body: $body
    }) {
        comment {
            id
            body
            createdAt
            updatedAt
            author {
                login
            }
            url
            pullRequestReview {
                id
            }
            replyTo {
                id
            }
        }
    }
}
""".strip()

RESOLVE_THREAD_MUTATION = """
mutation ResolveReviewThread($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
        thread {
            id
            isResolved
            pullRequest {
                number
                repository {
                    nameWithOwner
                }
            }
        }
    }
}
""".strip()

UNRESOLVE_THREAD_MUTATION = """
mutation UnresolveReviewThread($threadId: ID!) {
    unresolveReviewThread(input: {threadId: $threadId}) {
        thread {
            id
            isResolved
            pullRequest {
                number
                repository {
                    nameWithOwner
                }
            }
        }
    }
}
""".strip()


class GitHubServiceError(Exception):
    """Base exception for GitHub service errors."""

    pass


class GitHubCLINotFoundError(GitHubServiceError):
    """Raised when gh CLI is not found or not installed."""

    pass


class GitHubAuthenticationError(GitHubServiceError):
    """Raised when gh CLI authentication fails."""

    pass


class GitHubAPIError(GitHubServiceError):
    """Raised when GitHub API calls fail."""

    pass


class GitHubTimeoutError(GitHubServiceError):
    """Raised when GitHub CLI commands timeout."""

    pass


class GitHubRateLimitError(GitHubServiceError):
    """Raised when GitHub API rate limit is exceeded."""

    pass


class GitHubService:
    """Service for interacting with GitHub through the gh CLI."""

    def __init__(self, timeout: int = 30) -> None:
        """Initialize the GitHub service.

        Args:
            timeout: Command timeout in seconds (default: 30)

        Raises:
            ValueError: If timeout is not a positive integer.
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("Timeout must be a positive integer")

        self.gh_command = "gh"
        self.timeout = timeout

    def check_gh_installation(self) -> bool:
        """Check if gh CLI is installed and accessible.

        Returns:
            True if gh CLI is installed, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.gh_command, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_gh_version(self) -> Optional[str]:
        """Get the installed gh CLI version.

        Returns:
            Version string if gh CLI is installed, None otherwise.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
        """
        try:
            result = subprocess.run(
                [self.gh_command, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise GitHubCLINotFoundError(
                    "gh CLI is not installed or not accessible"
                )

            # Parse version from output like "gh version 2.40.1 (2023-12-13)"
            for line in result.stdout.split("\n"):
                if line.startswith("gh version"):
                    return line.split()[2]

            return None
        except FileNotFoundError as e:
            raise GitHubCLINotFoundError(
                "gh CLI is not installed or not accessible"
            ) from e

    def check_authentication(self) -> bool:
        """Check if gh CLI is authenticated with GitHub.

        Returns:
            True if authenticated, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.gh_command, "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def validate_version_compatibility(self, min_version: str = "2.0.0") -> bool:
        """Validate that the installed gh CLI version meets minimum requirements.

        Args:
            min_version: Minimum required version (default: 2.0.0).

        Returns:
            True if version is compatible, False otherwise.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
        """
        current_version = self.get_gh_version()
        if not current_version:
            return False

        # Simple version comparison (assumes semantic versioning)
        current_parts = [int(x) for x in current_version.split(".")]
        min_parts = [int(x) for x in min_version.split(".")]

        # Pad with zeros if needed
        max_len = max(len(current_parts), len(min_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        min_parts.extend([0] * (max_len - len(min_parts)))

        return current_parts >= min_parts

    def run_gh_command(self, args: List[str], timeout: Optional[int] = None) -> Any:
        """Run a gh CLI command with error handling and timeout support.

        Args:
            args: List of command arguments (excluding 'gh').
            timeout: Command timeout in seconds (uses instance default if None).

        Returns:
            CompletedProcess result.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubTimeoutError: If the command times out.
            GitHubRateLimitError: If rate limit is exceeded.
        """
        if not self.check_gh_installation():
            raise GitHubCLINotFoundError("gh CLI is not installed or not accessible")

        command_timeout = timeout or self.timeout

        try:
            result = subprocess.run(
                [self.gh_command] + args,
                capture_output=True,
                text=True,
                check=False,
                timeout=command_timeout,
            )

            # Check for timeout (this shouldn't happen as timeout would raise exception)
            if result.returncode == 124:  # Standard timeout exit code
                raise GitHubTimeoutError(
                    f"GitHub CLI command timed out after {command_timeout} seconds"
                )

            # Check for rate limiting (inspect stderr regardless of exit code)
            if any(
                phrase in result.stderr.lower()
                for phrase in ["rate limit", "rate limited", "api rate limit"]
            ):
                raise GitHubRateLimitError(
                    f"GitHub API rate limit exceeded: {result.stderr}"
                )

            # Check for authentication errors
            if result.returncode != 0 and any(
                phrase in result.stderr.lower()
                for phrase in ["authentication", "unauthorized", "forbidden"]
            ):
                raise GitHubAuthenticationError(
                    f"GitHub authentication failed: {result.stderr}"
                )

            # Check for other API errors
            if result.returncode != 0:
                raise GitHubAPIError(f"GitHub API call failed: {result.stderr}")

            return result

        except subprocess.TimeoutExpired as e:
            raise GitHubTimeoutError(
                f"GitHub CLI command timed out after {command_timeout} seconds"
            ) from e
        except FileNotFoundError as e:
            raise GitHubCLINotFoundError(
                "gh CLI is not installed or not accessible"
            ) from e

    def get_json_output(self, args: List[str]) -> Any:
        """Run a gh CLI command and parse JSON output.

        Args:
            args: List of command arguments (excluding 'gh').

        Returns:
            Parsed JSON data.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
            GitHubAPIError: If the GitHub API call fails or JSON parsing fails.
        """
        result = self.run_gh_command(args)

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Failed to parse JSON response: {e}") from e

    def get_current_repo(self) -> Optional[str]:
        """Get the current repository name (owner/repo format).

        Returns:
            Repository name in owner/repo format, or None if not in a repo.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
        """
        try:
            result = self.run_gh_command(["repo", "view", "--json", "nameWithOwner"])
            data = json.loads(result.stdout)
            name_with_owner = data.get("nameWithOwner")
            return name_with_owner if isinstance(name_with_owner, str) else None
        except (GitHubAPIError, json.JSONDecodeError):
            return None

    def execute_graphql_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query using gh CLI.

        Args:
            query: GraphQL query string.
            variables: Optional variables for the query.

        Returns:
            Parsed JSON response from GraphQL API.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
            GitHubAPIError: If the GraphQL query fails.
            GitHubTimeoutError: If the command times out.
            GitHubRateLimitError: If rate limit is exceeded.
        """
        args = ["api", "graphql", "-f", f"query={query}"]

        # Add variables if provided as individual field arguments
        # Use -F for proper type conversion (strings, integers, booleans)
        if variables:
            for key, value in variables.items():
                args.extend(["-F", f"{key}={value}"])

        result = self.run_gh_command(args)

        try:
            response = json.loads(result.stdout)

            # Check for GraphQL errors
            if "errors" in response:
                error_messages = [
                    error.get("message", str(error)) for error in response["errors"]
                ]
                raise GitHubAPIError(
                    f"GraphQL query failed: {'; '.join(error_messages)}"
                )

            return response  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Failed to parse GraphQL response: {e}") from e

    def get_repo_info_from_url(self, repo_url: str) -> Tuple[str, str]:
        """Extract owner and repository name from a GitHub URL.

        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo).

        Returns:
            Tuple of (owner, repo_name).

        Raises:
            ValueError: If the URL format is invalid.
        """
        import re

        # Match various GitHub URL formats
        patterns = [
            r"github\.com[:/]([^/]+)/([^/\.]+)",  # SSH or HTTPS
            r"^([^/]+)/([^/]+)$",  # owner/repo format
        ]

        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                owner, repo = match.groups()
                # Remove .git suffix if present
                repo = repo.rstrip(".git")
                return owner, repo

        raise ValueError(f"Invalid GitHub repository URL or format: {repo_url}")

    def validate_repository_access(self, owner: str, repo: str) -> bool:
        """Validate that the current user has access to the specified repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            True if the repository is accessible, False otherwise.

        Raises:
            GitHubRateLimitError: If rate limit is exceeded.
            GitHubTimeoutError: If the command times out.
        """
        try:
            self.run_gh_command(["repo", "view", f"{owner}/{repo}", "--json", "name"])
            return True
        except GitHubRateLimitError:
            # Re-raise rate limit errors - these are systemic issues
            raise
        except GitHubTimeoutError:
            # Re-raise timeout errors - these are systemic issues
            raise
        except GitHubAPIError:
            # Only suppress general API errors (like 404, permission denied)
            return False

    def check_pr_exists(self, owner: str, repo: str, pr_number: int) -> bool:
        """Check if a pull request exists in the specified repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            True if the PR exists, False otherwise.
        """
        try:
            self.run_gh_command(
                [
                    "pr",
                    "view",
                    str(pr_number),
                    "--repo",
                    f"{owner}/{repo}",
                    "--json",
                    "number",
                ]
            )
            return True
        except GitHubAPIError:
            return False

    def post_reply(
        self, comment_id: str, body: str, review_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a reply to a review comment or thread.

        Args:
            comment_id: The comment or thread ID to reply to.
            body: The reply message body.
            review_id: The review ID (required for comment replies to numeric IDs).

        Returns:
            The GraphQL response containing the new comment data.

        Raises:
            ValueError: If parameters are invalid.
            GitHubAPIError: If the GraphQL mutation fails.
        """
        if not comment_id or not comment_id.strip():
            raise ValueError("Comment ID cannot be empty")
        if not body or not body.strip():
            raise ValueError("Reply body cannot be empty")

        comment_id = comment_id.strip()
        body = body.strip()

        # Determine reply strategy based on comment ID format
        strategy = self._determine_reply_strategy(comment_id)

        if strategy == "thread_reply":
            # Use thread reply mutation for node IDs
            from .node_id_validation import create_thread_validator

            validator = create_thread_validator()
            validator.validate_id(comment_id, "Thread ID")

            variables = {"threadId": comment_id, "body": body}
            return self.execute_graphql_query(REPLY_THREAD_MUTATION, variables)
        else:
            # Use comment reply mutation for numeric/node IDs needing review context
            from .node_id_validation import validate_comment_id

            validate_comment_id(comment_id)

            # If review_id is not provided, try to fetch it for node IDs
            if not review_id and not comment_id.isdigit():
                review_id = self._get_review_id_for_comment(comment_id)

            if not review_id:
                raise ValueError(
                    "Review ID is required for comment replies. "
                    "Could not determine review ID from comment."
                )

            variables = {"reviewId": review_id, "commentId": comment_id, "body": body}
            return self.execute_graphql_query(REPLY_COMMENT_MUTATION, variables)

    def resolve_thread(self, thread_id: str, undo: bool = False) -> Dict[str, Any]:
        """Resolve or unresolve a review thread.

        Args:
            thread_id: The thread ID to resolve/unresolve.
            undo: If True, unresolve the thread; if False, resolve it.

        Returns:
            The GraphQL response containing the thread data.

        Raises:
            ValueError: If thread_id is invalid.
            GitHubAPIError: If the GraphQL mutation fails.
        """
        if not thread_id or not thread_id.strip():
            raise ValueError("Thread ID cannot be empty")

        thread_id = thread_id.strip()

        # Validate thread ID
        from .node_id_validation import validate_thread_id

        validate_thread_id(thread_id)

        variables = {"threadId": thread_id}
        mutation = UNRESOLVE_THREAD_MUTATION if undo else RESOLVE_THREAD_MUTATION
        return self.execute_graphql_query(mutation, variables)

    def _determine_reply_strategy(self, comment_id: str) -> str:
        """Determine the best reply strategy based on the comment ID format.

        Args:
            comment_id: The comment ID to analyze.

        Returns:
            Either "thread_reply" for node IDs or "comment_reply" for numeric IDs.
        """
        # If it's a numeric ID, we need to use the legacy comment reply approach
        if comment_id.isdigit():
            return "comment_reply"

        # For node IDs, we need to determine if it's a thread ID or comment ID
        # Thread IDs start with PRT_, PRRT_, RT_
        # Comment IDs start with IC_, PRRC_, RP_
        if comment_id.startswith(("PRT_", "PRRT_", "RT_")):
            return "thread_reply"
        elif comment_id.startswith(("IC_", "PRRC_", "RP_")):
            return "comment_reply"
        else:
            # Default to comment reply for unknown formats
            return "comment_reply"

    def _get_review_id_for_comment(self, comment_id: str) -> Optional[str]:
        """Get the review ID associated with a comment node ID.

        This method uses GraphQL to query the comment and get its associated review ID.

        Args:
            comment_id: Comment node ID.

        Returns:
            The review ID (node ID) or None if not found.

        Raises:
            GitHubAPIError: If the GraphQL query fails.
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
            result = self.execute_graphql_query(query, variables)

            if "errors" in result:
                error_messages = [
                    error.get("message", str(error)) for error in result["errors"]
                ]
                raise GitHubAPIError(
                    f"Failed to get review ID: {'; '.join(error_messages)}"
                )

            comment_node = result.get("data", {}).get("node")
            if not comment_node:
                return None

            review_data = comment_node.get("pullRequestReview")
            if not review_data or "id" not in review_data:
                return None

            return str(review_data["id"])

        except GitHubAPIError:
            # Re-raise GitHub API errors
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to get review ID: {e}") from e

    def fetch_open_pull_requests(
        self, owner: str, repo: str, include_drafts: bool = False, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch open pull requests from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            include_drafts: Whether to include draft PRs
            limit: Maximum number of PRs to fetch (1-100)

        Returns:
            List of pull request data dictionaries

        Raises:
            ValueError: If parameters are invalid
            GitHubAPIError: If the GraphQL query fails
            GitHubAuthenticationError: If authentication fails
            GitHubTimeoutError: If the command times out
            GitHubRateLimitError: If rate limit is exceeded
        """
        if not owner or not owner.strip():
            raise ValueError("Owner cannot be empty")
        if not repo or not repo.strip():
            raise ValueError("Repository name cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        # Import here to avoid circular imports
        from .graphql_queries import build_open_prs_query

        # Build the query
        query_builder = build_open_prs_query(include_drafts=include_drafts, limit=limit)
        query = query_builder.build_query()
        variables = query_builder.build_variables(owner, repo)

        # Execute the query
        response = self.execute_graphql_query(query, variables)

        # Parse the response
        try:
            repository_data = response.get("data", {}).get("repository")
            if not repository_data:
                raise GitHubAPIError("Repository not found or no access")

            pull_requests_data = repository_data.get("pullRequests", {})
            pr_nodes: List[Dict[str, Any]] = pull_requests_data.get("nodes", [])

            # Filter out drafts if not included
            if query_builder.should_filter_drafts():
                pr_nodes = [pr for pr in pr_nodes if not pr.get("isDraft", False)]

            return pr_nodes

        except KeyError as e:
            raise GitHubAPIError(
                f"Unexpected GraphQL response format: missing {e}"
            ) from e
        except Exception as e:
            raise GitHubAPIError(f"Failed to parse pull requests response: {e}") from e
