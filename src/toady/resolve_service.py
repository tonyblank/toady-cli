"""Service for resolving and unresolving review threads via GitHub GraphQL API."""

import logging
from typing import Any, Dict, List, Optional

from .github_service import GitHubAPIError, GitHubService, GitHubServiceError


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
            # Use the new mutation constants from github_service
            from .github_service import RESOLVE_THREAD_MUTATION
            from .node_id_validation import validate_thread_id

            # Validate thread ID
            validate_thread_id(thread_id)

            variables = {"threadId": thread_id}
            result = self.github_service.execute_graphql_query(
                RESOLVE_THREAD_MUTATION, variables
            )

            # Check for GraphQL errors first
            if "errors" in result:
                error_messages = [
                    error.get("message", str(error)) for error in result["errors"]
                ]
                # Handle specific error types
                if any(
                    "not found" in msg.lower() or "does not exist" in msg.lower()
                    for msg in error_messages
                ):
                    raise ThreadNotFoundError(f"Thread {thread_id} not found")
                elif any(
                    keyword in msg.lower()
                    for keyword in [
                        "permission",
                        "forbidden",
                        "not accessible",
                        "unauthorized",
                    ]
                    for msg in error_messages
                ):
                    raise ThreadPermissionError(
                        f"Permission denied - cannot resolve thread {thread_id}: "
                        f"{'; '.join(error_messages)}"
                    )
                else:
                    raise ResolveServiceError(
                        f"Failed to resolve thread: {'; '.join(error_messages)}"
                    )

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
        except GitHubAPIError as e:
            # Handle specific GraphQL errors
            if "not found" in str(e).lower():
                raise ThreadNotFoundError(f"Thread {thread_id} not found") from e
            elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
                raise ThreadPermissionError(
                    f"Permission denied to resolve thread {thread_id}"
                ) from e
            raise ResolveServiceError(f"Failed to resolve thread: {e}") from e

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
            # Use the new mutation constants from github_service
            from .github_service import UNRESOLVE_THREAD_MUTATION
            from .node_id_validation import validate_thread_id

            # Validate thread ID
            validate_thread_id(thread_id)

            variables = {"threadId": thread_id}
            result = self.github_service.execute_graphql_query(
                UNRESOLVE_THREAD_MUTATION, variables
            )

            # Check for GraphQL errors first
            if "errors" in result:
                error_messages = [
                    error.get("message", str(error)) for error in result["errors"]
                ]
                # Handle specific error types
                if any(
                    "not found" in msg.lower() or "does not exist" in msg.lower()
                    for msg in error_messages
                ):
                    raise ThreadNotFoundError(f"Thread {thread_id} not found")
                elif any(
                    keyword in msg.lower()
                    for keyword in [
                        "permission",
                        "forbidden",
                        "not accessible",
                        "unauthorized",
                    ]
                    for msg in error_messages
                ):
                    raise ThreadPermissionError(
                        f"Permission denied - cannot unresolve thread {thread_id}: "
                        f"{'; '.join(error_messages)}"
                    )
                else:
                    raise ResolveServiceError(
                        f"Failed to unresolve thread: {'; '.join(error_messages)}"
                    )

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
        except GitHubAPIError as e:
            # Handle specific GraphQL errors
            if "not found" in str(e).lower():
                raise ThreadNotFoundError(f"Thread {thread_id} not found") from e
            elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
                raise ThreadPermissionError(
                    f"Permission denied to unresolve thread {thread_id}"
                ) from e
            raise ResolveServiceError(f"Failed to unresolve thread: {e}") from e

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

        This method queries the specific thread directly rather than fetching all
        threads, making it more efficient and avoiding pagination issues with large PRs.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull request number.
            thread_id: Thread ID to validate.

        Returns:
            True if the thread exists, False otherwise.

        Raises:
            ResolveServiceError: If there's an API error that prevents validation.
        """
        logger = logging.getLogger(__name__)

        try:
            # Query the specific thread directly using the GitHub GraphQL node interface
            # This is more efficient than fetching all threads and avoids pagination
            query = """
            query ValidateThreadExists(
                $threadId: ID!
                $owner: String!
                $repo: String!
                $number: Int!
            ) {
                node(id: $threadId) {
                    ... on PullRequestReviewThread {
                        id
                        pullRequest {
                            number
                            repository {
                                owner {
                                    login
                                }
                                name
                            }
                        }
                    }
                }
            }
            """

            variables = {
                "threadId": thread_id,
                "owner": owner,
                "repo": repo,
                "number": pull_number,
            }

            result = self.github_service.execute_graphql_query(query, variables)

            # Check for GraphQL errors
            if "errors" in result:
                error_messages = [
                    error.get("message", str(error)) for error in result["errors"]
                ]
                logger.warning(
                    "GraphQL errors during thread validation for thread %s: %s",
                    thread_id,
                    "; ".join(error_messages),
                )
                # For validation, GraphQL errors typically mean the thread doesn't exist
                # or we don't have access to it, so return False
                return False

            # Extract the thread node from response
            thread_node = result.get("data", {}).get("node")

            if not thread_node:
                # Thread doesn't exist or is not a PullRequestReviewThread
                return False

            # Verify the thread belongs to the correct PR and repository
            pull_request = thread_node.get("pullRequest", {})
            if pull_request.get("number") != pull_number:
                logger.warning(
                    "Thread %s exists but belongs to PR #%d, not #%d",
                    thread_id,
                    pull_request.get("number", -1),
                    pull_number,
                )
                return False

            repository = pull_request.get("repository", {})
            repo_owner = repository.get("owner", {}).get("login", "")
            repo_name = repository.get("name", "")

            if repo_owner != owner or repo_name != repo:
                logger.warning(
                    "Thread %s exists but belongs to %s/%s, not %s/%s",
                    thread_id,
                    repo_owner,
                    repo_name,
                    owner,
                    repo,
                )
                return False

            return True

        except GitHubAPIError as e:
            logger.error(
                "GitHub API error during thread validation for thread %s in %s/%s "
                "PR #%d: %s",
                thread_id,
                owner,
                repo,
                pull_number,
                str(e),
            )
            raise ResolveServiceError(
                f"Failed to validate thread existence due to API error: {e}"
            ) from e
        except KeyError as e:
            logger.error(
                "Unexpected response structure during thread validation for thread %s: "
                "missing key %s",
                thread_id,
                str(e),
            )
            raise ResolveServiceError(
                f"Failed to validate thread existence due to unexpected response "
                f"structure: {e}"
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error during thread validation for thread %s in %s/%s "
                "PR #%d: %s",
                thread_id,
                owner,
                repo,
                pull_number,
                str(e),
            )
            raise ResolveServiceError(
                f"Failed to validate thread existence due to unexpected error: {e}"
            ) from e
