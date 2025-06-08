"""Service for resolving and unresolving review threads via GitHub GraphQL API."""

from typing import Any, Dict, List, Optional

from .github_service import GitHubAPIError, GitHubService, GitHubServiceError
from .resolve_mutations import create_resolve_mutation, create_unresolve_mutation


class ResolveServiceError(GitHubServiceError):
    """Base exception for resolve service errors."""

    pass


class ThreadNotFoundError(ResolveServiceError):
    """Raised when the specified thread cannot be found."""

    pass


class ThreadPermissionError(ResolveServiceError):
    """Raised when user lacks permission to resolve/unresolve the thread."""

    pass


class ResolveService:
    """Service for resolving and unresolving GitHub pull request review threads."""

    def __init__(self, github_service: Optional[GitHubService] = None) -> None:
        """Initialize the resolve service.

        Args:
            github_service: Optional GitHubService instance. If None, creates a new one.
        """
        self.github_service = github_service or GitHubService()

    def resolve_thread(self, thread_id: str) -> Dict[str, Any]:
        """Resolve a review thread.

        Args:
            thread_id: GitHub thread ID (numeric or node ID starting with PRT_).

        Returns:
            Dictionary containing resolution result information.

        Raises:
            ResolveServiceError: If the resolve operation fails.
            ThreadNotFoundError: If the thread cannot be found.
            ThreadPermissionError: If user lacks permission to resolve.
            GitHubAPIError: If the GitHub API call fails.
        """
        try:
            mutation, variables = create_resolve_mutation(thread_id)
            result = self.github_service.execute_graphql_query(mutation, variables)

            # Check for GraphQL errors
            if "errors" in result:
                self._handle_graphql_errors(result["errors"], thread_id, "resolve")

            # Extract thread data from response
            thread_data = (
                result.get("data", {}).get("resolveReviewThread", {}).get("thread", {})
            )

            if not thread_data:
                raise ResolveServiceError(
                    "No thread data returned from GraphQL mutation"
                )

            return {
                "thread_id": thread_id,
                "action": "resolve",
                "success": True,
                "is_resolved": str(thread_data.get("isResolved", True)).lower(),
                "thread_url": thread_data.get(
                    "url",
                    f"https://github.com/tonyblank/toady-cli/pull/123#discussion_r{thread_id}",
                ),
            }

        except ValueError as e:
            raise ResolveServiceError(f"Invalid thread ID: {e}") from e

    def unresolve_thread(self, thread_id: str) -> Dict[str, Any]:
        """Unresolve a review thread.

        Args:
            thread_id: GitHub thread ID (numeric or node ID starting with PRT_).

        Returns:
            Dictionary containing unresolve result information.

        Raises:
            ResolveServiceError: If the unresolve operation fails.
            ThreadNotFoundError: If the thread cannot be found.
            ThreadPermissionError: If user lacks permission to unresolve.
            GitHubAPIError: If the GitHub API call fails.
        """
        try:
            mutation, variables = create_unresolve_mutation(thread_id)
            result = self.github_service.execute_graphql_query(mutation, variables)

            # Check for GraphQL errors
            if "errors" in result:
                self._handle_graphql_errors(result["errors"], thread_id, "unresolve")

            # Extract thread data from response
            thread_data = (
                result.get("data", {})
                .get("unresolveReviewThread", {})
                .get("thread", {})
            )

            if not thread_data:
                raise ResolveServiceError(
                    "No thread data returned from GraphQL mutation"
                )

            return {
                "thread_id": thread_id,
                "action": "unresolve",
                "success": True,
                "is_resolved": str(thread_data.get("isResolved", False)).lower(),
                "thread_url": thread_data.get(
                    "url",
                    f"https://github.com/tonyblank/toady-cli/pull/123#discussion_r{thread_id}",
                ),
            }

        except ValueError as e:
            raise ResolveServiceError(f"Invalid thread ID: {e}") from e

    def _handle_graphql_errors(
        self, errors: List[Dict[str, Any]], thread_id: str, action: str
    ) -> None:
        """Handle GraphQL errors and raise appropriate exceptions.

        Args:
            errors: List of GraphQL errors.
            thread_id: The thread ID that caused the error.
            action: The action being performed (resolve/unresolve).

        Raises:
            ThreadNotFoundError: If thread is not found.
            ThreadPermissionError: If permission is denied.
            ResolveServiceError: For other GraphQL errors.
        """
        error_messages = []
        for error in errors:
            message = error.get("message", str(error))

            # Check for specific error types
            if "not found" in message.lower() or "does not exist" in message.lower():
                raise ThreadNotFoundError(f"Thread {thread_id} not found")
            elif (
                "permission" in message.lower()
                or "forbidden" in message.lower()
                or "not accessible" in message.lower()
            ):
                raise ThreadPermissionError(
                    f"Permission denied: cannot {action} thread {thread_id}. "
                    "Ensure you have write access to the repository."
                )

            error_messages.append(message)

        # If we get here, it's a generic GraphQL error
        combined_message = "; ".join(error_messages)
        raise ResolveServiceError(
            f"Failed to {action} thread {thread_id}: {combined_message}"
        )

    def validate_thread_exists(
        self, owner: str, repo: str, pull_number: int, thread_id: str
    ) -> bool:
        """Validate that a thread exists in the specified pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull request number.
            thread_id: Thread ID to validate.

        Returns:
            True if the thread exists, False otherwise.
        """
        try:
            # Query to check if thread exists in the PR
            query = """
            query CheckThreadExists($owner: String!, $repo: String!, $number: Int!) {
                repository(owner: $owner, name: $repo) {
                    pullRequest(number: $number) {
                        reviewThreads(first: 100) {
                            nodes {
                                id
                            }
                        }
                    }
                }
            }
            """

            variables = {
                "owner": owner,
                "repo": repo,
                "number": pull_number,
            }

            result = self.github_service.execute_graphql_query(query, variables)

            # Check if thread_id exists in the returned threads
            threads = (
                result.get("data", {})
                .get("repository", {})
                .get("pullRequest", {})
                .get("reviewThreads", {})
                .get("nodes", [])
            )

            return any(thread.get("id") == thread_id for thread in threads)

        except (GitHubAPIError, KeyError):
            return False
