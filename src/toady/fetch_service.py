"""Fetch service for retrieving review threads from GitHub pull requests."""

from typing import List, Optional, Tuple

from .github_service import GitHubService, GitHubServiceError
from .graphql_queries import (
    build_open_prs_query,
    build_review_threads_query,
    create_open_prs_query_variables,
)
from .models import PullRequest, ReviewThread
from .parsers import GraphQLResponseParser


class FetchServiceError(Exception):
    """Base exception for fetch service errors."""

    pass


class FetchService:
    """Service for fetching review threads from GitHub pull requests."""

    def __init__(self, github_service: Optional[GitHubService] = None) -> None:
        """Initialize the fetch service.

        Args:
            github_service: Optional GitHubService instance. If None, creates a new one.
        """
        self.github_service = github_service or GitHubService()
        self.parser = GraphQLResponseParser()

    def fetch_review_threads(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        include_resolved: bool = False,
        limit: int = 100,
    ) -> List[ReviewThread]:
        """Fetch review threads from a GitHub pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            include_resolved: Whether to include resolved threads (default: False).
            limit: Maximum number of threads to fetch (default: 100).

        Returns:
            List of ReviewThread objects.

        Raises:
            FetchServiceError: If the fetch operation fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        try:
            # Build the GraphQL query
            query_builder = build_review_threads_query(
                include_resolved=include_resolved, limit=limit
            )

            # Build query and variables
            query = query_builder.build_query()
            variables = query_builder.build_variables(owner, repo, pr_number)

            # Execute the GraphQL query
            response = self.github_service.execute_graphql_query(query, variables)

            # Parse the response and filter if needed
            threads = self.parser.parse_review_threads_response(response)

            # Filter resolved threads if not including them
            if query_builder.should_filter_resolved():
                threads = [t for t in threads if not t.is_resolved]

            # Return the threads
            return threads

        except Exception as e:
            # Re-raise GitHub service exceptions as-is
            if isinstance(e, GitHubServiceError):
                raise
            # Wrap other exceptions in FetchServiceError
            raise FetchServiceError(f"Failed to fetch review threads: {e}") from e

    def _get_repository_info(self) -> Tuple[str, str]:
        """Get the current repository owner and name.

        Returns:
            Tuple of (owner, repo_name).

        Raises:
            FetchServiceError: If repository info cannot be determined.
        """
        repo_info = self.github_service.get_current_repo()
        if not repo_info:
            raise FetchServiceError(
                "Could not determine repository information. "
                "Make sure you're in a git repository with GitHub remote."
            )

        parts = repo_info.split("/")
        if len(parts) != 2:
            raise FetchServiceError(f"Invalid repository format: {repo_info}")

        return parts[0], parts[1]

    def fetch_review_threads_from_current_repo(
        self,
        pr_number: int,
        include_resolved: bool = False,
        limit: int = 100,
    ) -> List[ReviewThread]:
        """Fetch review threads from a PR in the current repository.

        Args:
            pr_number: Pull request number.
            include_resolved: Whether to include resolved threads (default: False).
            limit: Maximum number of threads to fetch (default: 100).

        Returns:
            List of ReviewThread objects.

        Raises:
            FetchServiceError: If the fetch operation fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        # Get repository info from current directory
        owner, repo = self._get_repository_info()

        # Fetch threads
        return self.fetch_review_threads(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            include_resolved=include_resolved,
            limit=limit,
        )

    def fetch_open_pull_requests(
        self,
        owner: str,
        repo: str,
        include_drafts: bool = False,
        limit: int = 100,
    ) -> List[PullRequest]:
        """Fetch open pull requests from a GitHub repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            include_drafts: Whether to include draft PRs (default: False).
            limit: Maximum number of PRs to fetch (default: 100).

        Returns:
            List of PullRequest objects.

        Raises:
            FetchServiceError: If the fetch operation fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        try:
            # Build the GraphQL query
            query = build_open_prs_query(include_drafts=include_drafts, limit=limit)
            variables = create_open_prs_query_variables(owner, repo)

            # Execute the GraphQL query
            response = self.github_service.execute_graphql_query(query, variables)

            # Parse the response and apply filtering
            prs = self.parser.parse_pull_requests_response(
                response, include_drafts=include_drafts
            )

            # Return the PRs
            return prs

        except Exception as e:
            # Re-raise GitHub service exceptions as-is
            if isinstance(e, GitHubServiceError):
                raise
            # Wrap other exceptions in FetchServiceError
            raise FetchServiceError(f"Failed to fetch open pull requests: {e}") from e

    def fetch_open_pull_requests_from_current_repo(
        self,
        include_drafts: bool = False,
        limit: int = 100,
    ) -> List[PullRequest]:
        """Fetch open pull requests from the current repository.

        Args:
            include_drafts: Whether to include draft PRs (default: False).
            limit: Maximum number of PRs to fetch (default: 100).

        Returns:
            List of PullRequest objects.

        Raises:
            FetchServiceError: If the fetch operation fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        # Get repository info from current directory
        owner, repo = self._get_repository_info()

        # Fetch PRs
        return self.fetch_open_pull_requests(
            owner=owner,
            repo=repo,
            include_drafts=include_drafts,
            limit=limit,
        )
