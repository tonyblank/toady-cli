"""Parsers for transforming GitHub API responses to model objects."""

from typing import Any, Dict, List, Optional, Tuple, Union, cast

from .models import Comment, ReviewThread
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
            ValueError: If the response structure is invalid
            KeyError: If required fields are missing from the response
        """
        try:
            # Navigate to the review threads data
            pull_request = response["data"]["repository"]["pullRequest"]
            review_threads_data = pull_request["reviewThreads"]["nodes"]

            threads = []
            for thread_data in review_threads_data:
                thread = self._parse_single_review_thread(thread_data)
                threads.append(thread)

            return threads

        except KeyError as e:
            raise ValueError(f"Invalid response structure: missing key {e}") from e

    def _parse_single_review_thread(self, thread_data: Dict[str, Any]) -> ReviewThread:
        """Parse a single review thread from GraphQL response data.

        Args:
            thread_data: Dictionary containing thread data from GraphQL response

        Returns:
            ReviewThread object

        Raises:
            ValueError: If thread data is invalid or incomplete
        """
        # Extract basic thread information
        thread_id = thread_data["id"]
        is_resolved = thread_data.get("isResolved", False)

        # Parse comments to get thread metadata
        comments_data = thread_data.get("comments", {}).get("nodes", [])
        if not comments_data:
            raise ValueError(f"Review thread {thread_id} has no comments")

        # Parse comments
        comments = []
        for comment_data in comments_data:
            comment = self._parse_single_comment(comment_data, thread_id)
            comments.append(comment)

        # Use first comment to determine thread metadata
        first_comment = comments[0]
        title = self._extract_title_from_comment(first_comment.content)
        created_at = first_comment.created_at
        updated_at = max(comment.updated_at for comment in comments)
        author = first_comment.author
        status = "RESOLVED" if is_resolved else "UNRESOLVED"

        return ReviewThread(
            thread_id=thread_id,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            author=author,
            comments=cast(List[Union[str, Any]], comments),
        )

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
            ValueError: If comment data is invalid
        """
        comment_id = comment_data["id"]
        content = comment_data["body"]
        created_at = parse_datetime(comment_data["createdAt"])
        updated_at = parse_datetime(comment_data["updatedAt"])

        # Extract author information
        author_data = comment_data.get("author", {})
        author = author_data.get("login", "unknown")

        # Handle parent comment (replies)
        parent_id = None
        reply_to = comment_data.get("replyTo")
        if reply_to:
            parent_id = reply_to["id"]

        return Comment(
            comment_id=comment_id,
            content=content,
            author=author,
            created_at=created_at,
            updated_at=updated_at,
            parent_id=parent_id,
            thread_id=thread_id,
        )

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
            ValueError: If the response structure is invalid
        """
        threads = self.parse_review_threads_response(response)

        # Extract pagination info
        try:
            review_threads_data = response["data"]["repository"]["pullRequest"][
                "reviewThreads"
            ]
            page_info = review_threads_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            next_cursor = page_info.get("endCursor") if has_next_page else None

            return threads, next_cursor

        except KeyError as e:
            raise ValueError(f"Invalid pagination structure: missing key {e}") from e


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
            ValueError: If the response is invalid
        """
        if not isinstance(response, dict):
            raise ValueError("Response must be a dictionary")

        if "data" not in response:
            if "errors" in response:
                errors = response["errors"]
                if errors:  # Only raise GraphQL errors if there are actual errors
                    error_messages = [
                        error.get("message", str(error)) for error in errors
                    ]
                    raise ValueError(f"GraphQL errors: {'; '.join(error_messages)}")
                else:
                    raise ValueError("Response missing 'data' field")
            raise ValueError("Response missing 'data' field")

        data = response["data"]
        if not isinstance(data, dict):
            raise ValueError("Response 'data' field must be a dictionary")

        # Check for required nested structure
        if "repository" not in data:
            raise ValueError("Missing 'repository' in response data")

        repository = data["repository"]
        if repository is None:
            raise ValueError("Repository not found (null value)")

        if "pullRequest" not in repository:
            raise ValueError("Missing 'pullRequest' in repository data")

        pull_request = repository["pullRequest"]
        if pull_request is None:
            raise ValueError("Pull request not found (null value)")

        if "reviewThreads" not in pull_request:
            raise ValueError("Missing 'reviewThreads' in pull request data")

        return True

    @staticmethod
    def validate_review_thread_data(thread_data: Dict[str, Any]) -> bool:
        """Validate that review thread data has required fields.

        Args:
            thread_data: Thread data dictionary to validate

        Returns:
            True if valid

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["id"]
        for field in required_fields:
            if field not in thread_data:
                raise ValueError(f"Missing required field '{field}' in thread data")

        # Validate comments structure if present
        if "comments" in thread_data:
            comments_data = thread_data["comments"]
            if "nodes" not in comments_data:
                raise ValueError("Missing 'nodes' in comments data")

        return True

    @staticmethod
    def validate_comment_data(comment_data: Dict[str, Any]) -> bool:
        """Validate that comment data has required fields.

        Args:
            comment_data: Comment data dictionary to validate

        Returns:
            True if valid

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["id", "body", "createdAt", "updatedAt"]
        for field in required_fields:
            if field not in comment_data:
                raise ValueError(f"Missing required field '{field}' in comment data")

        return True
