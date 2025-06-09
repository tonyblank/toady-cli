"""GraphQL query builders for GitHub API interactions."""

import base64
import re
from typing import Any, Dict, Optional


def _validate_cursor(cursor: str) -> bool:
    """Validate that a cursor is safe for use in GraphQL queries.

    GitHub cursors are typically Base64-encoded strings. This function validates
    that the cursor matches expected patterns to prevent injection attacks.

    Args:
        cursor: The cursor string to validate

    Returns:
        True if the cursor is valid and safe to use

    Raises:
        ValueError: If the cursor is invalid or potentially unsafe
    """
    if not cursor:
        return False

    # Additional length check to prevent excessively long cursors (check first)
    if len(cursor) > 1000:
        raise ValueError("Cursor exceeds maximum length of 1000 characters")

    # GitHub cursors are typically Base64-encoded strings
    # They should only contain alphanumeric characters, +, /, and = for padding
    if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", cursor):
        raise ValueError(
            "Invalid cursor format: cursors must be Base64-encoded strings"
        )

    # Verify it's valid Base64 by attempting to decode
    try:
        base64.b64decode(cursor, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid Base64 cursor: {str(e)}") from e

    return True


class ReviewThreadQueryBuilder:
    """Builder for GraphQL queries to fetch review threads from GitHub."""

    def __init__(self) -> None:
        """Initialize the query builder."""
        self._include_resolved = False
        self._limit = 100
        self._comment_limit = 10

    def include_resolved(self, include: bool = True) -> "ReviewThreadQueryBuilder":
        """Include resolved threads in the query results.

        Args:
            include: Whether to include resolved threads

        Returns:
            Self for method chaining
        """
        self._include_resolved = include
        return self

    def limit(self, count: int) -> "ReviewThreadQueryBuilder":
        """Set the maximum number of threads to fetch.

        Args:
            count: Maximum number of threads (1-100)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If count is not between 1 and 100
        """
        if not 1 <= count <= 100:
            raise ValueError("Limit must be between 1 and 100")
        self._limit = count
        return self

    def comment_limit(self, count: int) -> "ReviewThreadQueryBuilder":
        """Set the maximum number of comments per thread to fetch.

        Args:
            count: Maximum number of comments per thread (1-50)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If count is not between 1 and 50
        """
        if not 1 <= count <= 50:
            raise ValueError("Comment limit must be between 1 and 50")
        self._comment_limit = count
        return self

    def build_query(self) -> str:
        """Build the GraphQL query string.

        Returns:
            Complete GraphQL query string
        """
        # Base query structure
        query = f"""
        query($owner: String!, $repo: String!, $number: Int!) {{
          repository(owner: $owner, name: $repo) {{
            pullRequest(number: $number) {{
              id
              number
              title
              url
              reviewThreads(first: {self._limit}) {{
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
                nodes {{
                  id
                  isResolved
                  isOutdated
                  line
                  originalLine
                  path
                  diffSide
                  startLine
                  originalStartLine
                  comments(first: {self._comment_limit}) {{
                    pageInfo {{
                      hasNextPage
                      endCursor
                    }}
                    nodes {{
                      id
                      body
                      createdAt
                      updatedAt
                      author {{
                        login
                        ... on User {{
                          name
                        }}
                      }}
                      url
                      replyTo {{
                        id
                      }}
                      pullRequestReview {{
                        id
                        state
                      }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        return query.strip()

    def build_variables(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Build the GraphQL query variables.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Dictionary of query variables
        """
        return {"owner": owner, "repo": repo, "number": pr_number}

    def should_filter_resolved(self) -> bool:
        """Check if resolved threads should be filtered out.

        Returns:
            True if resolved threads should be filtered from results
        """
        return not self._include_resolved


def build_review_threads_query(
    include_resolved: bool = False, limit: int = 100, comment_limit: int = 10
) -> ReviewThreadQueryBuilder:
    """Create a configured ReviewThreadQueryBuilder.

    Args:
        include_resolved: Whether to include resolved threads
        limit: Maximum number of threads to fetch
        comment_limit: Maximum number of comments per thread

    Returns:
        Configured query builder
    """
    builder = ReviewThreadQueryBuilder()
    builder.include_resolved(include_resolved)
    builder.limit(limit)
    builder.comment_limit(comment_limit)
    return builder


def create_paginated_query(limit: int = 100, after_cursor: Optional[str] = None) -> str:
    """Create a paginated GraphQL query for review threads.

    Args:
        limit: Maximum number of threads to fetch
        after_cursor: Cursor for pagination (optional)

    Returns:
        GraphQL query string with pagination support

    Raises:
        ValueError: If after_cursor is provided but invalid
    """
    # Validate cursor if provided
    if after_cursor is not None:
        _validate_cursor(after_cursor)

    # Use GraphQL variables for safe cursor handling
    cursor_variable = ", $after: String" if after_cursor is not None else ""
    cursor_arg = ", after: $after" if after_cursor is not None else ""

    query = f"""
    query($owner: String!, $repo: String!, $number: Int!{cursor_variable}) {{
      repository(owner: $owner, name: $repo) {{
        pullRequest(number: $number) {{
          id
          reviewThreads(first: {limit}{cursor_arg}) {{
            pageInfo {{
              hasNextPage
              endCursor
            }}
            totalCount
            nodes {{
              id
              isResolved
              isOutdated
              line
              originalLine
              path
              diffSide
              startLine
              originalStartLine
              comments(first: 10) {{
                nodes {{
                  id
                  body
                  createdAt
                  updatedAt
                  author {{
                    login
                  }}
                  url
                  replyTo {{
                    id
                  }}
                  pullRequestReview {{
                    id
                    state
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """

    return query.strip()


def create_paginated_query_variables(
    owner: str, repo: str, pr_number: int, after_cursor: Optional[str] = None
) -> Dict[str, Any]:
    """Create variables for the paginated GraphQL query.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        after_cursor: Cursor for pagination (optional)

    Returns:
        Dictionary of GraphQL variables

    Raises:
        ValueError: If after_cursor is provided but invalid
    """
    # Validate cursor if provided
    if after_cursor is not None:
        _validate_cursor(after_cursor)

    variables = {"owner": owner, "repo": repo, "number": pr_number}

    if after_cursor is not None:
        variables["after"] = after_cursor

    return variables
