"""Fetch service for retrieving review threads from GitHub pull requests."""

from typing import List, Optional, Tuple

from ..models.models import PullRequest, ReviewThread
from ..parsers.graphql_queries import (
    build_open_prs_query,
    build_review_threads_query,
)
from ..parsers.parsers import GraphQLResponseParser
from .github_service import GitHubService, GitHubServiceError
from .pr_selector import PRSelectionResult, PRSelector


class FetchServiceError(Exception):
    """Base exception for fetch service errors."""

    pass


class FetchService:
    """Service for fetching review threads from GitHub pull requests."""

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        output_format: str = "pretty",
    ) -> None:
        """Initialize the fetch service.

        Args:
            github_service: Optional GitHubService instance. If None, creates a new one.
            output_format: Output format for PR selection messages ("json" or "pretty").
        """
        self.github_service = github_service or GitHubService()
        self.parser = GraphQLResponseParser()
        self.pr_selector = PRSelector(output_format=output_format)

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
            query_builder = build_open_prs_query(
                include_drafts=include_drafts, limit=limit
            )
            query = query_builder.build_query()
            variables = query_builder.build_variables(owner, repo)

            # Execute the GraphQL query
            response = self.github_service.execute_graphql_query(query, variables)

            # Parse the response and apply filtering
            prs = self.parser.parse_pull_requests_response(response)

            # Filter drafts if needed (safety net in case query builder doesn't filter)
            if not include_drafts:
                prs = [pr for pr in prs if not pr.is_draft]

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

    def select_pr_interactively(
        self,
        include_drafts: bool = False,
        limit: int = 100,
    ) -> PRSelectionResult:
        """Interactively select a PR from the current repository.

        Fetches open PRs from the current repository and presents an interactive
        selection interface to the user. Handles different scenarios:
        - No PRs: Shows appropriate message and returns no selection
        - Single PR: Auto-selects and returns it
        - Multiple PRs: Shows interactive menu for user selection

        Args:
            include_drafts: Whether to include draft PRs (default: False).
            limit: Maximum number of PRs to fetch (default: 100).

        Returns:
            PRSelectionResult with selected PR number or cancellation status.

        Raises:
            FetchServiceError: If the fetch operation fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        try:
            # Fetch open PRs from current repository
            pull_requests = self.fetch_open_pull_requests_from_current_repo(
                include_drafts=include_drafts,
                limit=limit,
            )

            # Handle different scenarios
            if not pull_requests:
                # No PRs found - show message and return no selection
                self.pr_selector.display_no_prs_message()
                return PRSelectionResult(pr_number=None, cancelled=False)

            elif len(pull_requests) == 1:
                # Single PR - auto-select it
                selected_pr = pull_requests[0]
                self.pr_selector.display_auto_selected_pr(selected_pr)
                return PRSelectionResult(pr_number=selected_pr.number, cancelled=False)

            else:
                # Multiple PRs - show interactive selection
                selected_pr_number = self.pr_selector.select_pr(pull_requests)
                if selected_pr_number is None:
                    return PRSelectionResult(pr_number=None, cancelled=True)
                return PRSelectionResult(pr_number=selected_pr_number, cancelled=False)

        except Exception as e:
            # Re-raise GitHub service exceptions as-is
            if isinstance(e, GitHubServiceError):
                raise
            # Wrap other exceptions in FetchServiceError
            raise FetchServiceError(f"Failed to select PR interactively: {e}") from e

    def fetch_review_threads_with_pr_selection(
        self,
        pr_number: Optional[int] = None,
        include_resolved: bool = False,
        include_drafts: bool = False,
        threads_limit: int = 100,
        prs_limit: int = 100,
    ) -> Tuple[List[ReviewThread], Optional[int]]:
        """Fetch review threads with optional interactive PR selection.

        If pr_number is provided, fetches threads from that PR directly.
        If pr_number is None, performs interactive PR selection first.

        Args:
            pr_number: Optional PR number. If None, triggers interactive selection.
            include_resolved: Whether to include resolved threads (default: False).
            include_drafts: Whether to include draft PRs in selection (default: False).
            threads_limit: Maximum number of threads to fetch (default: 100).
            prs_limit: Maximum number of PRs to fetch for selection (default: 100).

        Returns:
            Tuple of (review_threads_list, selected_pr_number).
            If interactive selection was cancelled, returns ([], None).

        Raises:
            FetchServiceError: If the fetch operation fails.
            GitHubAPIError: If the GitHub API call fails.
            GitHubAuthenticationError: If authentication fails.
        """
        try:
            # Determine PR number
            if pr_number is not None:
                # Use provided PR number directly
                selected_pr_number = pr_number
            else:
                # Perform interactive PR selection
                selection_result = self.select_pr_interactively(
                    include_drafts=include_drafts,
                    limit=prs_limit,
                )

                if not selection_result.should_continue:
                    # User cancelled or no PR available
                    return [], None

                # At this point, should_continue is True, so pr_number must be set
                if selection_result.pr_number is None:
                    raise FetchServiceError("Unexpected empty selection result")
                selected_pr_number = selection_result.pr_number

            # Fetch review threads from the selected PR
            threads = self.fetch_review_threads_from_current_repo(
                pr_number=selected_pr_number,
                include_resolved=include_resolved,
                limit=threads_limit,
            )

            return threads, selected_pr_number

        except Exception as e:
            # Re-raise GitHub service exceptions as-is
            if isinstance(e, GitHubServiceError):
                raise
            # Wrap other exceptions in FetchServiceError
            raise FetchServiceError(
                f"Failed to fetch review threads with PR selection: {e}"
            ) from e
