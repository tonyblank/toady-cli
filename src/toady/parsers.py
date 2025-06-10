"""Parsers for transforming GitHub API responses to model objects."""

from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    ValidationError,
    create_github_error,
    create_validation_error,
)
from .models import Comment, PullRequest, ReviewThread
from .utils import parse_datetime


class GraphQLResponseParser:
    """Parser for GitHub GraphQL API responses."""

    def __init__(self) -> None:
        """Initialize the parser."""
        pass

    def parse_review_threads_response(
        self, response: Dict[str, Any]
    ) -> List[ReviewThread]:
        """Parse a GraphQL response containing review threads.

        Args:
            response: The GraphQL response dictionary from GitHub API

        Returns:
            List of ReviewThread objects parsed from the response

        Raises:
            GitHubAPIError: If the response structure indicates API errors
            ValidationError: If the response structure is invalid or malformed
        """
        try:
            # Validate the top-level response structure first
            ResponseValidator.validate_graphql_response(response)

            # Navigate to the review threads data (guaranteed to exist after validation)
            pull_request = response["data"]["repository"]["pullRequest"]
            review_threads_data = pull_request["reviewThreads"]["nodes"]

            if not isinstance(review_threads_data, list):
                raise create_validation_error(
                    field_name="reviewThreads.nodes",
                    invalid_value=type(review_threads_data).__name__,
                    expected_format="list of thread objects",
                    message="reviewThreads.nodes must be a list",
                )

            threads = []
            for i, thread_data in enumerate(review_threads_data):
                try:
                    thread = self._parse_single_review_thread(thread_data)
                    threads.append(thread)
                except ValidationError as e:
                    # Re-raise with context about which thread failed
                    raise create_validation_error(
                        field_name=f"reviewThreads.nodes[{i}]",
                        invalid_value=thread_data.get("id", "unknown"),
                        expected_format="valid thread object",
                        message=f"Failed to parse thread at index {i}: {str(e)}",
                    ) from e

            return threads

        except KeyError as e:
            raise create_validation_error(
                field_name=str(e).strip("'\""),
                invalid_value="missing",
                expected_format="required field in GraphQL response",
                message=f"Invalid response structure: missing key {e}",
            ) from e
        except (TypeError, AttributeError) as e:
            raise create_validation_error(
                field_name="response",
                invalid_value=type(response).__name__,
                expected_format="valid GraphQL response dictionary",
                message=f"Response parsing failed due to type error: {str(e)}",
            ) from e

    def _parse_single_review_thread(self, thread_data: Dict[str, Any]) -> ReviewThread:
        """Parse a single review thread from GraphQL response data.

        Args:
            thread_data: Dictionary containing thread data from GraphQL response

        Returns:
            ReviewThread object

        Raises:
            ValidationError: If thread data is invalid or incomplete
        """
        try:
            # Validate thread data before accessing fields
            ResponseValidator.validate_review_thread_data(thread_data)

            # Thread ID is guaranteed to exist after validation
            thread_id = thread_data["id"]

            is_resolved = thread_data.get("isResolved", False)

            # Parse comments to get thread metadata
            comments_data = thread_data.get("comments", {}).get("nodes", [])
            if not comments_data:
                raise create_validation_error(
                    field_name="thread.comments.nodes",
                    invalid_value="empty list",
                    expected_format="list with at least one comment",
                    message=f"Review thread {thread_id} has no comments",
                )

            # Parse comments with enhanced error handling
            comments = []
            for i, comment_data in enumerate(comments_data):
                try:
                    # Validate comment data before parsing
                    ResponseValidator.validate_comment_data(comment_data)
                    comment = self._parse_single_comment(comment_data, thread_id)
                    comments.append(comment)
                except ValidationError as e:
                    # Re-raise with context about which comment failed
                    raise create_validation_error(
                        field_name=f"thread.comments.nodes[{i}]",
                        invalid_value=comment_data.get("id", "unknown"),
                        expected_format="valid comment object",
                        message=(
                            f"Failed to parse comment at index {i} in thread "
                            f"{thread_id}: {str(e)}"
                        ),
                    ) from e

            # Use first comment to determine thread metadata
            try:
                first_comment = comments[0]
                title = self._extract_title_from_comment(first_comment.content)
                created_at = first_comment.created_at
                updated_at = max(comment.updated_at for comment in comments)
                author = first_comment.author
                status = "RESOLVED" if is_resolved else "UNRESOLVED"
            except (IndexError, AttributeError) as e:
                raise create_validation_error(
                    field_name="thread.comments",
                    invalid_value=f"{len(comments)} comments",
                    expected_format="list with valid comment objects",
                    message=(
                        f"Cannot extract thread metadata from comments in thread "
                        f"{thread_id}: {str(e)}"
                    ),
                ) from e

            return ReviewThread(
                thread_id=thread_id,
                title=title,
                created_at=created_at,
                updated_at=updated_at,
                status=status,
                author=author,
                comments=comments,
            )

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except KeyError as e:
            raise create_validation_error(
                field_name=str(e).strip("'\""),
                invalid_value="missing",
                expected_format="required field in thread data",
                message=f"Missing required field {e} in thread data",
            ) from e
        except (TypeError, AttributeError) as e:
            raise create_validation_error(
                field_name="thread_data",
                invalid_value=type(thread_data).__name__,
                expected_format="valid thread data dictionary",
                message=f"Thread parsing failed due to type error: {str(e)}",
            ) from e

    def _parse_single_comment(
        self, comment_data: Dict[str, Any], thread_id: str
    ) -> Comment:
        """Parse a single comment from GraphQL response data.

        Args:
            comment_data: Dictionary containing comment data from GraphQL response
            thread_id: ID of the thread this comment belongs to

        Returns:
            Comment object

        Raises:
            ValidationError: If comment data is invalid
        """
        try:
            # Extract and validate required fields
            comment_id = comment_data.get("id")
            if not comment_id:
                raise create_validation_error(
                    field_name="comment.id",
                    invalid_value="missing",
                    expected_format="non-empty string",
                    message="Comment ID is required but missing",
                )

            content = comment_data.get("body", "")

            # Parse datetime fields with proper error handling
            try:
                created_at = parse_datetime(comment_data["createdAt"])
            except (KeyError, ValueError) as e:
                raise create_validation_error(
                    field_name="comment.createdAt",
                    invalid_value=comment_data.get("createdAt", "missing"),
                    expected_format="valid ISO datetime string",
                    message=f"Failed to parse comment creation date: {str(e)}",
                ) from e

            try:
                updated_at = parse_datetime(comment_data["updatedAt"])
            except (KeyError, ValueError) as e:
                raise create_validation_error(
                    field_name="comment.updatedAt",
                    invalid_value=comment_data.get("updatedAt", "missing"),
                    expected_format="valid ISO datetime string",
                    message=f"Failed to parse comment update date: {str(e)}",
                ) from e

            # Extract author information with fallback
            author_data = comment_data.get("author", {})
            author = author_data.get("login", "unknown") if author_data else "unknown"

            # Handle parent comment (replies) with error handling
            parent_id = None
            reply_to = comment_data.get("replyTo")
            if reply_to:
                try:
                    parent_id = reply_to.get("id")
                except (TypeError, AttributeError):
                    # Log the issue but don't fail - just skip parent ID
                    parent_id = None

            # Extract review information with error handling
            review_id = None
            review_state = None
            review_data = comment_data.get("pullRequestReview")
            if review_data:
                try:
                    review_id = review_data.get("id")
                    review_state = review_data.get("state")
                except (TypeError, AttributeError):
                    # Log the issue but don't fail - just skip review info
                    review_id = None
                    review_state = None

            return Comment(
                comment_id=comment_id,
                content=content,
                author=author,
                created_at=created_at,
                updated_at=updated_at,
                parent_id=parent_id,
                thread_id=thread_id,
                review_id=review_id,
                review_state=review_state,
            )

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except KeyError as e:
            raise create_validation_error(
                field_name=str(e).strip("'\""),
                invalid_value="missing",
                expected_format="required field in comment data",
                message=(
                    f"Missing required field {e} in comment data for thread "
                    f"{thread_id}"
                ),
            ) from e
        except (TypeError, AttributeError) as e:
            raise create_validation_error(
                field_name="comment_data",
                invalid_value=type(comment_data).__name__,
                expected_format="valid comment data dictionary",
                message=f"Comment parsing failed due to type error: {str(e)}",
            ) from e

    def _extract_title_from_comment(self, content: str) -> str:
        """Extract a title from comment content.

        Args:
            content: The comment content

        Returns:
            A suitable title for the review thread (first line or truncated content)
        """
        if not content:
            return "Empty comment"

        # Use first line as title, or truncate if too long
        first_line = content.split("\n")[0].strip()
        if len(first_line) > 100:
            return first_line[:97] + "..."
        return first_line or "Empty comment"

    def parse_paginated_response(
        self, response: Dict[str, Any]
    ) -> Tuple[List[ReviewThread], Optional[str]]:
        """Parse a paginated GraphQL response for review threads.

        Args:
            response: The GraphQL response dictionary

        Returns:
            Tuple of (review_threads_list, next_cursor)
            next_cursor is None if there are no more pages

        Raises:
            ValidationError: If the response structure is invalid
        """
        try:
            # Parse threads first (this will handle most validation)
            threads = self.parse_review_threads_response(response)

            # Extract pagination info with proper error handling
            review_threads_data = response["data"]["repository"]["pullRequest"][
                "reviewThreads"
            ]
            page_info = review_threads_data.get("pageInfo", {})

            if not isinstance(page_info, dict):
                raise create_validation_error(
                    field_name="reviewThreads.pageInfo",
                    invalid_value=type(page_info).__name__,
                    expected_format="dictionary with pagination information",
                    message="pageInfo must be a dictionary",
                )

            has_next_page = page_info.get("hasNextPage", False)
            next_cursor = page_info.get("endCursor") if has_next_page else None

            return threads, next_cursor

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except KeyError as e:
            raise create_validation_error(
                field_name=str(e).strip("'\""),
                invalid_value="missing",
                expected_format="required field in pagination response",
                message=f"Invalid pagination structure: missing key {e}",
            ) from e
        except (TypeError, AttributeError) as e:
            raise create_validation_error(
                field_name="response",
                invalid_value=type(response).__name__,
                expected_format="valid paginated GraphQL response",
                message=f"Pagination parsing failed due to type error: {str(e)}",
            ) from e

    def parse_pull_requests_response(
        self, response: Dict[str, Any]
    ) -> List[PullRequest]:
        """Parse a GraphQL response containing pull requests.

        Args:
            response: The GraphQL response dictionary from GitHub API

        Returns:
            List of PullRequest objects parsed from the response

        Raises:
            GitHubAPIError: If the response structure indicates API errors
            ValidationError: If the response structure is invalid or malformed
        """
        try:
            # Validate the top-level response structure first
            ResponseValidator.validate_graphql_prs_response(response)

            # Navigate to the pull requests data (guaranteed to exist after validation)
            repository = response["data"]["repository"]
            pull_requests_data = repository["pullRequests"]["nodes"]

            if not isinstance(pull_requests_data, list):
                raise create_validation_error(
                    field_name="pullRequests.nodes",
                    invalid_value=type(pull_requests_data).__name__,
                    expected_format="list of pull request objects",
                    message="pullRequests.nodes must be a list",
                )

            # Parse each pull request
            pull_requests = []
            for i, pr_data in enumerate(pull_requests_data):
                try:
                    # Validate individual PR data
                    ResponseValidator.validate_pull_request_data(pr_data)

                    # Parse the PR data
                    pull_request = self._parse_pull_request_data(pr_data)
                    pull_requests.append(pull_request)

                except ValidationError as e:
                    # Re-raise with context about which PR failed
                    raise create_validation_error(
                        field_name=f"pullRequest[{i}]",
                        invalid_value=e.invalid_value,
                        expected_format=e.expected_format or "valid pull request data",
                        message=f"Failed to parse pull request {i}: {e.message}",
                    ) from e

            return pull_requests

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except KeyError as e:
            raise create_validation_error(
                field_name=str(e).strip("'\""),
                invalid_value="missing",
                expected_format="required field in GraphQL response",
                message=f"Invalid response structure: missing key {e}",
            ) from e
        except (TypeError, AttributeError) as e:
            raise create_validation_error(
                field_name="response",
                invalid_value=type(response).__name__,
                expected_format="valid GraphQL pull requests response",
                message=f"Response parsing failed due to type error: {str(e)}",
            ) from e

    def _parse_pull_request_data(self, pr_data: Dict[str, Any]) -> PullRequest:
        """Parse individual pull request data into a PullRequest object.

        Args:
            pr_data: Pull request data dictionary from GraphQL response

        Returns:
            PullRequest object

        Raises:
            ValidationError: If the data is invalid or cannot be parsed
        """
        try:
            # Extract author information
            author_data = pr_data.get("author", {})
            author_login = (
                author_data.get("login", "unknown") if author_data else "unknown"
            )

            # Extract review thread count
            review_threads_data = pr_data.get("reviewThreads", {})
            review_thread_count = review_threads_data.get("totalCount", 0)

            # Parse dates
            try:
                created_at = parse_datetime(pr_data["createdAt"])
            except Exception as e:
                raise create_validation_error(
                    field_name="createdAt",
                    invalid_value=pr_data.get("createdAt", "missing"),
                    expected_format="ISO datetime string",
                    message=f"Invalid createdAt format: {str(e)}",
                ) from e

            try:
                updated_at = parse_datetime(pr_data["updatedAt"])
            except Exception as e:
                raise create_validation_error(
                    field_name="updatedAt",
                    invalid_value=pr_data.get("updatedAt", "missing"),
                    expected_format="ISO datetime string",
                    message=f"Invalid updatedAt format: {str(e)}",
                ) from e

            # Create PullRequest object
            return PullRequest(
                number=pr_data["number"],
                title=pr_data["title"],
                author=author_login,
                head_ref=pr_data["headRefName"],
                base_ref=pr_data["baseRefName"],
                is_draft=pr_data.get("isDraft", False),
                created_at=created_at,
                updated_at=updated_at,
                url=pr_data["url"],
                review_thread_count=review_thread_count,
                node_id=pr_data.get("id"),
            )

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except KeyError as e:
            raise create_validation_error(
                field_name=str(e).strip("'\""),
                invalid_value="missing",
                expected_format="required field in pull request data",
                message=f"Missing required field in pull request data: {e}",
            ) from e
        except (TypeError, AttributeError) as e:
            raise create_validation_error(
                field_name="pr_data",
                invalid_value=type(pr_data).__name__,
                expected_format="valid pull request data dictionary",
                message=f"Pull request parsing failed due to type error: {str(e)}",
            ) from e


class ResponseValidator:
    """Validator for GitHub API response structures."""

    @staticmethod
    def validate_graphql_response(response: Dict[str, Any]) -> bool:
        """Validate that a GraphQL response has the expected structure.

        Args:
            response: The response dictionary to validate

        Returns:
            True if the response is valid

        Raises:
            ValidationError: If the response is invalid
            GitHubAPIError: If there are GraphQL errors from the API
        """
        if not isinstance(response, dict):
            raise create_validation_error(
                field_name="response",
                invalid_value=type(response).__name__,
                expected_format="dictionary",
                message="GraphQL response must be a dictionary",
            )

        if "data" not in response:
            if "errors" in response:
                errors = response["errors"]
                if errors:  # Only raise GraphQL errors if there are actual errors
                    error_messages = [
                        error.get("message", str(error)) for error in errors
                    ]
                    # Use GitHubAPIError for GraphQL API errors
                    raise create_github_error(
                        message=f"GraphQL API errors: {'; '.join(error_messages)}",
                        api_endpoint="GraphQL",
                    )
                else:
                    raise create_validation_error(
                        field_name="data",
                        invalid_value="missing",
                        expected_format="data field in GraphQL response",
                        message="Response missing 'data' field",
                    )
            raise create_validation_error(
                field_name="data",
                invalid_value="missing",
                expected_format="data field in GraphQL response",
                message="Response missing 'data' field",
            )

        data = response["data"]
        if not isinstance(data, dict):
            raise create_validation_error(
                field_name="data",
                invalid_value=type(data).__name__,
                expected_format="dictionary",
                message="Response 'data' field must be a dictionary",
            )

        # Check for required nested structure
        if "repository" not in data:
            raise create_validation_error(
                field_name="repository",
                invalid_value="missing",
                expected_format="repository object in response data",
                message="Missing 'repository' in response data",
            )

        repository = data["repository"]
        if repository is None:
            raise create_validation_error(
                field_name="repository",
                invalid_value="null",
                expected_format="valid repository object",
                message="Repository not found (null value)",
            )

        if "pullRequest" not in repository:
            raise create_validation_error(
                field_name="pullRequest",
                invalid_value="missing",
                expected_format="pull request object in repository data",
                message="Missing 'pullRequest' in repository data",
            )

        pull_request = repository["pullRequest"]
        if pull_request is None:
            raise create_validation_error(
                field_name="pullRequest",
                invalid_value="null",
                expected_format="valid pull request object",
                message="Pull request not found (null value)",
            )

        if "reviewThreads" not in pull_request:
            raise create_validation_error(
                field_name="reviewThreads",
                invalid_value="missing",
                expected_format="review threads object in pull request data",
                message="Missing 'reviewThreads' in pull request data",
            )

        return True

    @staticmethod
    def validate_graphql_prs_response(response: Dict[str, Any]) -> bool:
        """Validate GraphQL response for pull requests has expected structure.

        Args:
            response: The response dictionary to validate

        Returns:
            True if the response is valid

        Raises:
            ValidationError: If the response is invalid
            GitHubAPIError: If there are GraphQL errors from the API
        """
        if not isinstance(response, dict):
            raise create_validation_error(
                field_name="response",
                invalid_value=type(response).__name__,
                expected_format="dictionary",
                message="GraphQL response must be a dictionary",
            )

        if "data" not in response:
            if "errors" in response:
                errors = response["errors"]
                if errors:  # Only raise GraphQL errors if there are actual errors
                    error_messages = [
                        error.get("message", str(error)) for error in errors
                    ]
                    # Use GitHubAPIError for GraphQL API errors
                    raise create_github_error(
                        message=f"GraphQL API errors: {'; '.join(error_messages)}",
                        api_endpoint="GraphQL",
                    )
                else:
                    raise create_validation_error(
                        field_name="data",
                        invalid_value="missing",
                        expected_format="data field in GraphQL response",
                        message="Response missing 'data' field",
                    )
            raise create_validation_error(
                field_name="data",
                invalid_value="missing",
                expected_format="data field in GraphQL response",
                message="Response missing 'data' field",
            )

        data = response["data"]
        if not isinstance(data, dict):
            raise create_validation_error(
                field_name="data",
                invalid_value=type(data).__name__,
                expected_format="dictionary",
                message="Response 'data' field must be a dictionary",
            )

        # Check for required nested structure
        if "repository" not in data:
            raise create_validation_error(
                field_name="repository",
                invalid_value="missing",
                expected_format="repository object in response data",
                message="Missing 'repository' in response data",
            )

        repository = data["repository"]
        if repository is None:
            raise create_validation_error(
                field_name="repository",
                invalid_value="null",
                expected_format="valid repository object",
                message="Repository not found (null value)",
            )

        if "pullRequests" not in repository:
            raise create_validation_error(
                field_name="pullRequests",
                invalid_value="missing",
                expected_format="pull requests object in repository data",
                message="Missing 'pullRequests' in repository data",
            )

        return True

    @staticmethod
    def validate_pull_request_data(pr_data: Dict[str, Any]) -> bool:
        """Validate that pull request data has required fields.

        Args:
            pr_data: Pull request data dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If required fields are missing
        """
        if not isinstance(pr_data, dict):
            raise create_validation_error(
                field_name="pr_data",
                invalid_value=type(pr_data).__name__,
                expected_format="dictionary",
                message="Pull request data must be a dictionary",
            )

        required_fields = [
            "number",
            "title",
            "headRefName",
            "baseRefName",
            "createdAt",
            "updatedAt",
            "url",
        ]
        for field in required_fields:
            if field not in pr_data:
                raise create_validation_error(
                    field_name=f"pr.{field}",
                    invalid_value="missing",
                    expected_format=f"required field '{field}' in PR data",
                    message=f"Missing required field '{field}' in pull request data",
                )

        return True

    @staticmethod
    def validate_review_thread_data(thread_data: Dict[str, Any]) -> bool:
        """Validate that review thread data has required fields.

        Args:
            thread_data: Thread data dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If required fields are missing
        """
        if not isinstance(thread_data, dict):
            raise create_validation_error(
                field_name="thread_data",
                invalid_value=type(thread_data).__name__,
                expected_format="dictionary",
                message="Thread data must be a dictionary",
            )

        required_fields = ["id"]
        for field in required_fields:
            if field not in thread_data:
                raise create_validation_error(
                    field_name=f"thread.{field}",
                    invalid_value="missing",
                    expected_format=f"required field '{field}' in thread data",
                    message=f"Missing required field '{field}' in thread data",
                )

        # Validate comments structure if present
        if "comments" in thread_data:
            comments_data = thread_data["comments"]
            if not isinstance(comments_data, dict):
                raise create_validation_error(
                    field_name="thread.comments",
                    invalid_value=type(comments_data).__name__,
                    expected_format="dictionary with comments data",
                    message="Comments data must be a dictionary",
                )
            if "nodes" not in comments_data:
                raise create_validation_error(
                    field_name="thread.comments.nodes",
                    invalid_value="missing",
                    expected_format="list of comment nodes",
                    message="Missing 'nodes' in comments data",
                )

        return True

    @staticmethod
    def validate_comment_data(comment_data: Dict[str, Any]) -> bool:
        """Validate that comment data has required fields.

        Args:
            comment_data: Comment data dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If required fields are missing
        """
        if not isinstance(comment_data, dict):
            raise create_validation_error(
                field_name="comment_data",
                invalid_value=type(comment_data).__name__,
                expected_format="dictionary",
                message="Comment data must be a dictionary",
            )

        required_fields = ["id", "body", "createdAt", "updatedAt"]
        for field in required_fields:
            if field not in comment_data:
                raise create_validation_error(
                    field_name=f"comment.{field}",
                    invalid_value="missing",
                    expected_format=f"required field '{field}' in comment data",
                    message=f"Missing required field '{field}' in comment data",
                )

        return True

    @staticmethod
    def validate_pull_requests_response(response: Dict[str, Any]) -> bool:
        """Validate a GraphQL response has expected structure for pull requests.

        Args:
            response: The response dictionary to validate

        Returns:
            True if the response is valid

        Raises:
            ValidationError: If the response is invalid
            GitHubAPIError: If there are GraphQL errors from the API
        """
        if not isinstance(response, dict):
            raise create_validation_error(
                field_name="response",
                invalid_value=type(response).__name__,
                expected_format="dictionary",
                message="GraphQL response must be a dictionary",
            )

        if "data" not in response:
            if "errors" in response:
                errors = response["errors"]
                if errors:  # Only raise GraphQL errors if there are actual errors
                    error_messages = [
                        error.get("message", str(error)) for error in errors
                    ]
                    # Use GitHubAPIError for GraphQL API errors
                    raise create_github_error(
                        message=f"GraphQL API errors: {'; '.join(error_messages)}",
                        api_endpoint="GraphQL",
                    )
            raise create_validation_error(
                field_name="data",
                invalid_value="missing",
                expected_format="data field in GraphQL response",
                message="Response missing 'data' field",
            )

        data = response["data"]
        if not isinstance(data, dict):
            raise create_validation_error(
                field_name="data",
                invalid_value=type(data).__name__,
                expected_format="dictionary",
                message="Response 'data' field must be a dictionary",
            )

        # Check for required nested structure
        if "repository" not in data:
            raise create_validation_error(
                field_name="repository",
                invalid_value="missing",
                expected_format="repository object in response data",
                message="Missing 'repository' in response data",
            )

        repository = data["repository"]
        if repository is None:
            raise create_validation_error(
                field_name="repository",
                invalid_value="null",
                expected_format="valid repository object",
                message="Repository not found (null value)",
            )

        if "pullRequests" not in repository:
            raise create_validation_error(
                field_name="pullRequests",
                invalid_value="missing",
                expected_format="pull requests object in repository data",
                message="Missing 'pullRequests' in repository data",
            )

        return True

    @staticmethod
    def validate_pull_request_data(pr_data: Dict[str, Any]) -> bool:
        """Validate that pull request data has required fields.

        Args:
            pr_data: Pull request data dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If required fields are missing
        """
        if not isinstance(pr_data, dict):
            raise create_validation_error(
                field_name="pr_data",
                invalid_value=type(pr_data).__name__,
                expected_format="dictionary",
                message="Pull request data must be a dictionary",
            )

        required_fields = [
            "id",
            "number",
            "title",
            "headRefName",
            "baseRefName",
            "createdAt",
            "updatedAt",
            "url",
        ]
        for field in required_fields:
            if field not in pr_data:
                raise create_validation_error(
                    field_name=f"pullRequest.{field}",
                    invalid_value="missing",
                    expected_format=f"required field '{field}' in pull request data",
                    message=f"Missing required field '{field}' in pull request data",
                )

        return True
