"""Interactive pull request selection interface."""

from typing import List, Optional

import click

from ..formatters.formatters import PrettyFormatter
from ..models.models import PullRequest


class PRSelector:
    """Interactive pull request selection interface.

    Provides user-friendly interface for selecting from multiple PRs
    with formatted display and navigation controls.
    """

    def __init__(self, output_format: str = "pretty") -> None:
        """Initialize the PR selector.

        Args:
            output_format: Output format ("json" or "pretty"). Controls whether
                           interactive messages are displayed or suppressed.
        """
        self.formatter = PrettyFormatter()
        self.output_format = output_format
        self.is_json_mode = output_format == "json"

    def select_pr(self, pull_requests: List[PullRequest]) -> Optional[int]:
        """Select a PR from the given list through interactive interface.

        Args:
            pull_requests: List of available pull requests

        Returns:
            Selected PR number, or None if user cancels

        Raises:
            ValidationError: If input validation fails
        """
        if not pull_requests:
            return None

        if len(pull_requests) == 1:
            # Auto-select single PR
            return pull_requests[0].number

        # Multiple PRs
        if self.is_json_mode:
            # In JSON mode, we can't do interactive selection
            # Send error message to stderr and return None
            click.echo(
                "Error: Multiple PRs found but interactive selection not available "
                "in JSON mode. Please specify --pr option.",
                err=True,
            )
            return None

        # Show interactive selection (pretty mode only)
        return self._show_pr_selection_menu(pull_requests)

    def _show_pr_selection_menu(
        self, pull_requests: List[PullRequest]
    ) -> Optional[int]:
        """Display interactive PR selection menu.

        Args:
            pull_requests: List of pull requests to choose from

        Returns:
            Selected PR number, or None if cancelled
        """
        # Display header
        # In JSON mode, send to stderr to avoid polluting JSON output
        click.echo(err=self.is_json_mode)
        plural = "s" if len(pull_requests) != 1 else ""
        header = f"📋 Found {len(pull_requests)} open pull request{plural}"
        click.echo(click.style(header, bold=True, fg="cyan"), err=self.is_json_mode)
        click.echo(err=self.is_json_mode)

        # Display PR list with formatting
        self._display_pr_list(pull_requests)

        # Get user selection
        return self._prompt_for_selection(pull_requests)

    def _display_pr_list(self, pull_requests: List[PullRequest]) -> None:
        """Display formatted list of pull requests.

        Args:
            pull_requests: List of pull requests to display
        """
        for i, pr in enumerate(pull_requests, 1):
            # Format PR entry with consistent styling
            number_style = click.style(f"[{i}]", bold=True, fg="yellow")
            pr_number = click.style(f"#{pr.number}", bold=True, fg="green")
            title = click.style(pr.title, fg="white")

            # Format author and branch info
            author_info = click.style(f"by {pr.author}", fg="blue")
            branch_info = click.style(f"{pr.head_ref} → {pr.base_ref}", fg="magenta")

            # Add draft indicator if applicable
            draft_indicator = ""
            if pr.is_draft:
                draft_indicator = click.style(" [DRAFT]", fg="yellow", dim=True)

            # Add review thread count if any
            thread_info = ""
            if pr.review_thread_count > 0:
                plural = "s" if pr.review_thread_count != 1 else ""
                thread_count = click.style(
                    f" ({pr.review_thread_count} thread{plural})",
                    fg="red",
                    dim=True,
                )
                thread_info = thread_count

            # Combine all components
            # In JSON mode, send to stderr to avoid polluting JSON output
            click.echo(
                f"  {number_style} {pr_number} {title}{draft_indicator}",
                err=self.is_json_mode,
            )
            click.echo(
                f"      {author_info} • {branch_info}{thread_info}",
                err=self.is_json_mode,
            )
            click.echo(err=self.is_json_mode)

    def _prompt_for_selection(self, pull_requests: List[PullRequest]) -> Optional[int]:
        """Prompt user for PR selection with validation.

        Args:
            pull_requests: List of available pull requests

        Returns:
            Selected PR number, or None if cancelled
        """
        while True:
            try:
                # Create choice prompt
                max_num = len(pull_requests)
                prompt_text = click.style(
                    f"Select a pull request [1-{max_num}] (or 'q' to quit): ",
                    fg="cyan",
                )

                choice = click.prompt(prompt_text, type=str, show_default=False)

                # Handle quit
                if choice.lower() in ("q", "quit", "exit"):
                    click.echo(click.style("Operation cancelled.", fg="yellow"))
                    return None

                # Validate numeric input
                try:
                    selection = int(choice)
                except ValueError:
                    max_num = len(pull_requests)
                    error_msg = (
                        f"Error: Please enter a number between 1 and {max_num}, "
                        "or 'q' to quit."
                    )
                    click.echo(
                        click.style(
                            error_msg,
                            fg="red",
                        )
                    )
                    continue

                # Validate range
                if not 1 <= selection <= len(pull_requests):
                    max_num = len(pull_requests)
                    error_msg = f"Error: Please enter a number between 1 and {max_num}."
                    click.echo(
                        click.style(
                            error_msg,
                            fg="red",
                        )
                    )
                    continue

                # Get selected PR
                selected_pr = pull_requests[selection - 1]

                # Show confirmation
                confirm_text = click.style(
                    f"Selected PR #{selected_pr.number}: {selected_pr.title}",
                    fg="green",
                    bold=True,
                )
                click.echo(f"✅ {confirm_text}")
                click.echo()

                return selected_pr.number

            except (KeyboardInterrupt, click.Abort):
                click.echo()
                click.echo(click.style("Operation cancelled.", fg="yellow"))
                return None

    def display_no_prs_message(self) -> None:
        """Display message when no open PRs are found."""
        # In JSON mode, completely suppress output to avoid compatibility issues
        if self.is_json_mode:
            return

        # Pretty mode - show the message
        click.echo()
        message = "📝 No open pull requests found in this repository."
        click.echo(click.style(message, fg="yellow", bold=True))

        suggestion = (
            "To fetch review threads, please specify a PR number using --pr option."
        )
        click.echo(click.style(suggestion, fg="cyan"))
        click.echo()

    def display_auto_selected_pr(self, pr: PullRequest) -> None:
        """Display message when automatically selecting single PR.

        Args:
            pr: The automatically selected pull request
        """
        # In JSON mode, completely suppress output to avoid compatibility issues
        if self.is_json_mode:
            return

        # Pretty mode - show the selection message
        click.echo()
        header = "🎯 Auto-selected the only open pull request:"
        click.echo(click.style(header, fg="green", bold=True))

        pr_info = f"#{pr.number}: {pr.title}"
        click.echo(click.style(pr_info, fg="white", bold=True))

        author_branch = f"by {pr.author} • {pr.head_ref} → {pr.base_ref}"
        click.echo(click.style(author_branch, fg="blue"))
        click.echo()


class PRSelectionResult:
    """Result of PR selection process."""

    def __init__(self, pr_number: Optional[int], cancelled: bool = False) -> None:
        """Initialize selection result.

        Args:
            pr_number: Selected PR number, None if no selection
            cancelled: True if user cancelled the operation
        """
        self.pr_number = pr_number
        self.cancelled = cancelled

    @property
    def has_selection(self) -> bool:
        """Check if a PR was selected."""
        return self.pr_number is not None

    @property
    def should_continue(self) -> bool:
        """Check if operation should continue."""
        return self.has_selection and not self.cancelled


def create_pr_selector() -> PRSelector:
    """Factory function to create PR selector instance.

    Returns:
        Configured PRSelector instance
    """
    return PRSelector()
