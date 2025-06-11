"""Pull request selection logic for automatic detection and user selection."""

from typing import List, NoReturn, Optional, Union

import click

from ..exceptions import create_validation_error
from ..models.models import PullRequest


class PRSelectionError(Exception):
    """Exception raised when PR selection fails."""

    pass


class PRSelector:
    """Handles pull request selection logic for different scenarios."""

    def __init__(self) -> None:
        """Initialize the PR selector."""
        pass

    def select_pull_request(
        self, pull_requests: List[PullRequest], allow_multiple: bool = True
    ) -> Union[int, None]:
        """Select a pull request from the available options.

        Args:
            pull_requests: List of available pull requests
            allow_multiple: Whether to allow interactive selection when
                multiple PRs exist

        Returns:
            PR number if selection successful, None if no PRs or user cancelled

        Raises:
            PRSelectionError: If PR selection fails due to validation or user error
            ValidationError: If input validation fails
        """
        if not isinstance(pull_requests, list):
            raise create_validation_error(
                field_name="pull_requests",
                invalid_value=type(pull_requests).__name__,
                expected_format="list of PullRequest objects",
                message="pull_requests must be a list",
            )

        # Scenario 1: No open PRs
        if not pull_requests:
            return self._handle_no_prs()

        # Scenario 2: Single open PR
        if len(pull_requests) == 1:
            return self._handle_single_pr(pull_requests[0])

        # Scenario 3: Multiple open PRs
        if allow_multiple:
            return self._handle_multiple_prs(pull_requests)
        else:
            # If not allowing multiple selection, treat as error
            raise PRSelectionError(
                f"Found {len(pull_requests)} open pull requests, but multiple "
                "selection is not allowed in this context"
            )

    def _handle_no_prs(self) -> NoReturn:
        """Handle the case when no open PRs are found.

        Raises:
            PRSelectionError: Always, as this is an error condition
        """
        raise PRSelectionError(
            "No open pull requests found in this repository. "
            "Please specify a PR number with --pr or create a pull request first."
        )

    def _handle_single_pr(self, pull_request: PullRequest) -> int:
        """Handle the case when exactly one open PR is found.

        Args:
            pull_request: The single open pull request

        Returns:
            The PR number (auto-selected)
        """
        # Auto-select the single PR
        click.echo(
            f"Auto-selecting PR #{pull_request.number}: {pull_request.title}",
            err=True,
        )
        return pull_request.number

    def _handle_multiple_prs(self, pull_requests: List[PullRequest]) -> Optional[int]:
        """Handle the case when multiple open PRs are found.

        Args:
            pull_requests: List of open pull requests

        Returns:
            Selected PR number, or None if user cancelled

        Raises:
            PRSelectionError: If user input is invalid or selection fails
        """
        # Sort PRs by update time (most recent first) for better UX
        sorted_prs = sorted(pull_requests, key=lambda pr: pr.updated_at, reverse=True)

        # Display the list of available PRs
        click.echo(f"Found {len(sorted_prs)} open pull requests:", err=True)
        click.echo("", err=True)

        for i, pr in enumerate(sorted_prs, 1):
            # Format draft indicator
            draft_indicator = " (draft)" if pr.is_draft else ""

            # Format thread count
            thread_info = ""
            if pr.review_thread_count > 0:
                thread_info = f" [{pr.review_thread_count} threads]"

            # Display the PR option
            click.echo(
                f"  {i}. PR #{pr.number}: {pr.title}{draft_indicator}{thread_info}",
                err=True,
            )
            click.echo(
                f"     by {pr.author} ({pr.head_ref} → {pr.base_ref})",
                err=True,
            )

        click.echo("", err=True)

        # Prompt for selection
        try:
            selection = click.prompt(
                f"Select a pull request (number 1-{len(sorted_prs)}, or 'q' to quit)",
                type=str,
                err=True,
            )

            # Handle quit option
            if selection.lower() in ("q", "quit", "exit"):
                raise PRSelectionError("Selection cancelled by user")

            # Validate and convert selection
            try:
                selection_num = int(selection)
            except ValueError as e:
                raise PRSelectionError(
                    f"Invalid selection '{selection}'. Please enter a number "
                    f"between 1 and {len(sorted_prs)}, or 'q' to quit."
                ) from e

            # Validate range
            if not (1 <= selection_num <= len(sorted_prs)):
                raise PRSelectionError(
                    f"Selection {selection_num} is out of range. Please enter a "
                    f"number between 1 and {len(sorted_prs)}."
                )

            # Return the selected PR number
            selected_pr = sorted_prs[selection_num - 1]
            click.echo(
                f"Selected PR #{selected_pr.number}: {selected_pr.title}",
                err=True,
            )
            return selected_pr.number

        except click.Abort:
            # User pressed Ctrl+C
            raise PRSelectionError("Selection cancelled by user") from None
        except Exception as e:
            if isinstance(e, PRSelectionError):
                raise
            raise PRSelectionError(f"Selection failed: {str(e)}") from e

    def validate_pr_exists(
        self, pr_number: int, pull_requests: List[PullRequest]
    ) -> bool:
        """Validate that a specific PR number exists in the list.

        Args:
            pr_number: PR number to validate
            pull_requests: List of available pull requests

        Returns:
            True if PR exists in the list

        Raises:
            ValidationError: If PR number is not found
        """
        if not isinstance(pr_number, int):
            raise create_validation_error(
                field_name="pr_number",
                invalid_value=type(pr_number).__name__,
                expected_format="integer",
                message="PR number must be an integer",
            )

        if pr_number <= 0:
            raise create_validation_error(
                field_name="pr_number",
                invalid_value=str(pr_number),
                expected_format="positive integer",
                message="PR number must be positive",
            )

        # Check if PR exists in the list
        pr_numbers = [pr.number for pr in pull_requests]
        if pr_number not in pr_numbers:
            raise create_validation_error(
                field_name="pr_number",
                invalid_value=str(pr_number),
                expected_format=f"one of: {', '.join(map(str, sorted(pr_numbers)))}",
                message=(
                    f"PR #{pr_number} not found in open pull requests. "
                    f"Available: {', '.join(map(str, sorted(pr_numbers)))}"
                ),
            )

        return True
