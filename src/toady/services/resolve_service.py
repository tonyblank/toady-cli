"""Service for resolving and unresolving review threads via GitHub GraphQL API."""

import logging
from typing import Any, Optional

from ..exceptions import (
    GitHubAPIError,
    ResolveServiceError,
    ThreadNotFoundError,
    ThreadPermissionError,
    ValidationError,
    create_github_error,
    create_validation_error,
)
from ..validators.node_id_validation import validate_thread_id
from .github_service import (
    RESOLVE_THREAD_MUTATION,
    UNRESOLVE_THREAD_MUTATION,
    GitHubService,
)


class ResolveService:
    """Service for resolving and unresolving GitHub pull request review threads."""

    def __init__(self, github_service: Optional[GitHubService] = None) -> None:
        """Initialize the resolve service.

        Args:
            github_service: Optional GitHubService instance. If None, creates a new one.
        """
        self.github_service = github_service or GitHubService()

    def resolve_thread(self, thread_id: str) -> dict[str, Any]:
        """Resolve a review thread.

        Args:
            thread_id: GitHub thread ID (numeric or node ID starting with PRT_).

        Returns:
            Dictionary containing resolution result information.

        Raises:
            ResolveServiceError: If the resolve operation fails.
            ThreadNotFoundError: If the thread cannot be found.
            ThreadPermissionError: If user lacks permission to resolve.
            ValidationError: If the thread ID is invalid.
            GitHubAPIError: If the GitHub API call fails.
        """
        try:
            # Validate thread ID with enhanced error handling
            try:
                validate_thread_id(thread_id)
            except ValueError as e:
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value=thread_id,
                    expected_format="valid GitHub thread ID",
                    message=f"Invalid thread ID format: {e!s}",
                ) from e

            # Execute GraphQL mutation with error handling
            variables = {"threadId": thread_id}
            try:
                result = self.github_service.execute_graphql_query(
                    RESOLVE_THREAD_MUTATION, variables
                )
            except GitHubAPIError:
                raise
            except Exception as e:
                raise create_github_error(
                    message=f"Failed to execute resolve mutation: {e!s}",
                    api_endpoint="GraphQL resolve mutation",
                ) from e

            # Check for GraphQL errors first
            if "errors" in result:
                self._handle_graphql_errors(result["errors"], thread_id, "resolve")

            # Extract thread data from response with validation
            try:
                thread_data = (
                    result.get("data", {})
                    .get("resolveReviewThread", {})
                    .get("thread", {})
                )

                if not thread_data:
                    raise ResolveServiceError(
                        message="No thread data returned from GraphQL mutation",
                        context={"thread_id": thread_id, "action": "resolve"},
                    )

                # Extract URL with intelligent fallback
                thread_url = self._get_thread_url(thread_data, thread_id)

                return {
                    "thread_id": thread_id,
                    "action": "resolve",
                    "success": True,
                    "is_resolved": str(thread_data.get("isResolved", True)).lower(),
                    "thread_url": thread_url,
                }
            except (KeyError, TypeError, AttributeError) as e:
                raise ResolveServiceError(
                    message=(
                        "Invalid response structure from resolve mutation: " f"{e!s}"
                    ),
                    context={
                        "thread_id": thread_id,
                        "action": "resolve",
                        "response_keys": (
                            list(result.keys())
                            if isinstance(result, dict)
                            else "not_dict"
                        ),
                    },
                ) from e

        except (
            ValidationError,
            ResolveServiceError,
            ThreadNotFoundError,
            ThreadPermissionError,
            GitHubAPIError,
        ):
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            # Wrap any unexpected errors
            raise ResolveServiceError(
                message=f"Unexpected error during thread resolution: {e!s}",
                context={"thread_id": thread_id, "action": "resolve"},
            ) from e

    def unresolve_thread(self, thread_id: str) -> dict[str, Any]:
        """Unresolve a review thread.

        Args:
            thread_id: GitHub thread ID (numeric or node ID starting with PRT_).

        Returns:
            Dictionary containing unresolve result information.

        Raises:
            ResolveServiceError: If the unresolve operation fails.
            ThreadNotFoundError: If the thread cannot be found.
            ThreadPermissionError: If user lacks permission to unresolve.
            ValidationError: If the thread ID is invalid.
            GitHubAPIError: If the GitHub API call fails.
        """
        try:
            # Validate thread ID with enhanced error handling
            try:
                validate_thread_id(thread_id)
            except ValueError as e:
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value=thread_id,
                    expected_format="valid GitHub thread ID",
                    message=f"Invalid thread ID format: {e!s}",
                ) from e

            # Execute GraphQL mutation with error handling
            variables = {"threadId": thread_id}
            try:
                result = self.github_service.execute_graphql_query(
                    UNRESOLVE_THREAD_MUTATION, variables
                )
            except GitHubAPIError:
                raise
            except Exception as e:
                raise create_github_error(
                    message=f"Failed to execute unresolve mutation: {e!s}",
                    api_endpoint="GraphQL unresolve mutation",
                ) from e

            # Check for GraphQL errors first
            if "errors" in result:
                self._handle_graphql_errors(result["errors"], thread_id, "unresolve")

            # Extract thread data from response with validation
            try:
                thread_data = (
                    result.get("data", {})
                    .get("unresolveReviewThread", {})
                    .get("thread", {})
                )

                if not thread_data:
                    raise ResolveServiceError(
                        message="No thread data returned from GraphQL mutation",
                        context={"thread_id": thread_id, "action": "unresolve"},
                    )

                # Extract URL with intelligent fallback
                thread_url = self._get_thread_url(thread_data, thread_id)

                return {
                    "thread_id": thread_id,
                    "action": "unresolve",
                    "success": True,
                    "is_resolved": str(thread_data.get("isResolved", False)).lower(),
                    "thread_url": thread_url,
                }
            except (KeyError, TypeError, AttributeError) as e:
                raise ResolveServiceError(
                    message=(
                        "Invalid response structure from unresolve mutation: " f"{e!s}"
                    ),
                    context={
                        "thread_id": thread_id,
                        "action": "unresolve",
                        "response_keys": (
                            list(result.keys())
                            if isinstance(result, dict)
                            else "not_dict"
                        ),
                    },
                ) from e

        except (
            ValidationError,
            ResolveServiceError,
            ThreadNotFoundError,
            ThreadPermissionError,
            GitHubAPIError,
        ):
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            # Wrap any unexpected errors
            raise ResolveServiceError(
                message=f"Unexpected error during thread unresolution: {e!s}",
                context={"thread_id": thread_id, "action": "unresolve"},
            ) from e

    def _handle_graphql_errors(
        self, errors: list[dict[str, Any]], thread_id: str, action: str
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
        try:
            if not isinstance(errors, list):
                raise ResolveServiceError(
                    message=(
                        f"Invalid GraphQL errors format: expected list, "
                        f"got {type(errors).__name__}"
                    ),
                    context={"thread_id": thread_id, "action": action},
                )

            error_messages = []
            for i, error in enumerate(errors):
                try:
                    if not isinstance(error, dict):
                        # mypy: disable-error-code=unreachable
                        error_messages.append(
                            f"Invalid error format at index {i}: {error!s}"
                        )
                        continue

                    message = error.get("message", str(error))

                    # Check for specific error types and handle them
                    message_lower = message.lower()

                    if (
                        "not found" in message_lower
                        or "does not exist" in message_lower
                    ):
                        raise ThreadNotFoundError(
                            message=f"Thread {thread_id} not found",
                            thread_id=thread_id,
                        )
                    if (
                        "permission" in message_lower
                        or "forbidden" in message_lower
                        or "not accessible" in message_lower
                    ):
                        raise ThreadPermissionError(
                            message=(
                                f"Permission denied: cannot {action} thread "
                                f"{thread_id}. Ensure you have write access to the "
                                "repository."
                            ),
                            thread_id=thread_id,
                        )
                    # If we get here, it's a generic error message
                    error_messages.append(message)
                except (ThreadNotFoundError, ThreadPermissionError):
                    # Re-raise these immediately
                    raise
                except Exception as e:
                    # Continue processing other errors
                    error_messages.append(f"Error processing GraphQL error {i}: {e!s}")

            # If we get here, it's a generic GraphQL error
            combined_message = (
                "; ".join(error_messages) if error_messages else "Unknown GraphQL error"
            )
            raise ResolveServiceError(
                message=f"Failed to {action} thread {thread_id}: {combined_message}",
                context={
                    "thread_id": thread_id,
                    "action": action,
                    "error_count": len(errors),
                },
            )

        except (ThreadNotFoundError, ThreadPermissionError, ResolveServiceError):
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            # Wrap any unexpected errors in error handling
            raise ResolveServiceError(
                message=f"Error processing GraphQL errors during {action}: {e!s}",
                context={"thread_id": thread_id, "action": action},
            ) from e

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
            ValidationError: If input parameters are invalid.
            ResolveServiceError: If there's an API error that prevents validation.
        """
        logger = logging.getLogger(__name__)

        try:
            # Validate input parameters
            if not isinstance(owner, str) or not owner.strip():
                raise create_validation_error(
                    field_name="owner",
                    invalid_value=owner,
                    expected_format="non-empty string",
                    message="Repository owner must be a non-empty string",
                )
            if not isinstance(repo, str) or not repo.strip():
                raise create_validation_error(
                    field_name="repo",
                    invalid_value=repo,
                    expected_format="non-empty string",
                    message="Repository name must be a non-empty string",
                )
            if not isinstance(pull_number, int) or pull_number <= 0:
                raise create_validation_error(
                    field_name="pull_number",
                    invalid_value=pull_number,
                    expected_format="positive integer",
                    message="Pull request number must be a positive integer",
                )
            if not isinstance(thread_id, str) or not thread_id.strip():
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value=thread_id,
                    expected_format="non-empty string",
                    message="Thread ID must be a non-empty string",
                )

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

            try:
                result = self.github_service.execute_graphql_query(query, variables)
            except GitHubAPIError:
                raise
            except Exception as e:
                raise create_github_error(
                    message=f"Failed to execute thread validation query: {e!s}",
                    api_endpoint="GraphQL node validation",
                ) from e

            # Check for GraphQL errors with enhanced handling
            if "errors" in result:
                try:
                    error_messages = []
                    for error in result["errors"]:
                        if isinstance(error, dict):
                            error_messages.append(error.get("message", str(error)))
                        else:
                            error_messages.append(str(error))

                    logger.warning(
                        "GraphQL errors during thread validation for thread %s: %s",
                        thread_id,
                        "; ".join(error_messages),
                    )
                    # For validation, GraphQL errors typically mean the thread
                    # doesn't exist
                    # or we don't have access to it, so return False
                    return False
                except Exception as e:
                    logger.warning(
                        "Error processing GraphQL errors during thread validation: %s",
                        str(e),
                    )
                    return False

            # Extract the thread node from response with error handling
            try:
                thread_node = result.get("data", {}).get("node")

                if not thread_node:
                    # Thread doesn't exist or is not a PullRequestReviewThread
                    return False

                # Verify the thread belongs to the correct PR and repository
                pull_request = thread_node.get("pullRequest", {})
                if not isinstance(pull_request, dict):
                    logger.warning(
                        "Invalid pullRequest structure for thread %s",
                        thread_id,
                    )
                    return False

                if pull_request.get("number") != pull_number:
                    logger.warning(
                        "Thread %s exists but belongs to PR #%d, not #%d",
                        thread_id,
                        pull_request.get("number", -1),
                        pull_number,
                    )
                    return False

                repository = pull_request.get("repository", {})
                if not isinstance(repository, dict):
                    logger.warning(
                        "Invalid repository structure for thread %s",
                        thread_id,
                    )
                    return False

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

            except (KeyError, TypeError, AttributeError) as e:
                logger.error(
                    (
                        "Unexpected response structure during thread validation "
                        "for thread %s: %s"
                    ),
                    thread_id,
                    str(e),
                )
                raise ResolveServiceError(
                    message=(
                        "Failed to validate thread existence due to unexpected "
                        f"response structure: {e!s}"
                    ),
                    context={
                        "thread_id": thread_id,
                        "owner": owner,
                        "repo": repo,
                        "pull_number": pull_number,
                    },
                ) from e

        except (ValidationError, ResolveServiceError, GitHubAPIError):
            # Re-raise our custom exceptions as-is
            raise
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
                message=(
                    "Failed to validate thread existence due to unexpected "
                    f"error: {e!s}"
                ),
                context={
                    "thread_id": thread_id,
                    "owner": owner,
                    "repo": repo,
                    "pull_number": pull_number,
                },
            ) from e

    def _get_thread_url(self, thread_data: dict[str, Any], thread_id: str) -> str:
        """Extract thread URL from GraphQL response with intelligent fallback.

        Args:
            thread_data: Thread data from GraphQL response
            thread_id: Thread ID for fallback URL construction

        Returns:
            Thread URL (from API or constructed fallback)
        """
        try:
            # First, try to get the URL directly from the API response
            # Note: PullRequestReviewThread doesn't have a url field in GitHub's
            # GraphQL schema, so this will typically be None, but we check anyway
            # for future compatibility
            url = thread_data.get("url")
            if url and isinstance(url, str) and url.strip():
                return str(url.strip())

            # If no URL from API, construct one using PR information from the response
            pull_request_data = thread_data.get("pullRequest", {})
            if isinstance(pull_request_data, dict):
                pr_number = pull_request_data.get("number")
                repository_data = pull_request_data.get("repository", {})

                if isinstance(repository_data, dict):
                    name_with_owner = repository_data.get("nameWithOwner")

                    if (
                        isinstance(pr_number, int)
                        and isinstance(name_with_owner, str)
                        and name_with_owner.strip()
                    ):
                        # Extract numeric ID from thread_id for URL fragment
                        url_fragment = self._extract_thread_url_fragment(thread_id)
                        return (
                            f"https://github.com/{name_with_owner.strip()}/pull/"
                            f"{pr_number}#discussion_r{url_fragment}"
                        )

            # Final fallback: use current repository context
            return self._build_fallback_url(thread_id)

        except Exception:
            # If anything goes wrong, use the safe fallback
            return self._build_fallback_url(thread_id)

    def _extract_thread_url_fragment(self, thread_id: str) -> str:
        """Extract the numeric portion of thread ID for URL construction.

        Args:
            thread_id: Thread ID (numeric or node ID)

        Returns:
            Numeric string suitable for URL fragment
        """
        try:
            # If it's already numeric, use it directly
            if thread_id.isdigit():
                return thread_id

            # For node IDs, we'll use the thread_id as-is since GitHub can handle it
            # The URL will work even with node IDs in modern GitHub
            return thread_id
        except Exception:
            # Fallback to the thread_id itself
            return thread_id

    def _build_fallback_url(self, thread_id: str) -> str:
        """Build a fallback URL using current repository context.

        Args:
            thread_id: Thread ID for URL construction

        Returns:
            Fallback URL
        """
        try:
            # Try to get current repository
            current_repo = self.github_service.get_current_repo()
            if current_repo and "/" in current_repo:
                url_fragment = self._extract_thread_url_fragment(thread_id)
                # Use a generic PR reference since we don't know the specific PR
                return (
                    f"https://github.com/{current_repo}/pull/"
                    f"{{pr_number}}#discussion_r{url_fragment}"
                )
        except Exception:
            pass

        # Ultimate fallback when all else fails
        url_fragment = self._extract_thread_url_fragment(thread_id)
        return f"https://github.com/{{owner}}/{{repo}}/pull/{{pr_number}}#discussion_r{url_fragment}"
