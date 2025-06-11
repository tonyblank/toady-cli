"""Tests for the PR selector module."""

from datetime import datetime
from unittest.mock import patch

from toady.models.models import PullRequest
from toady.services.pr_selector import PRSelectionResult, PRSelector, create_pr_selector


class TestPRSelector:
    """Test the PRSelector class."""

    def test_init(self) -> None:
        """Test PRSelector initialization."""
        selector = PRSelector()
        assert selector is not None
        assert selector.formatter is not None

    def test_select_pr_empty_list(self) -> None:
        """Test selecting from empty PR list returns None."""
        selector = PRSelector()
        result = selector.select_pr([])
        assert result is None

    def test_select_pr_single_pr(self) -> None:
        """Test selecting from single PR auto-selects it."""
        selector = PRSelector()
        pr = PullRequest(
            number=42,
            title="Test PR",
            author="testuser",
            head_ref="feature",
            base_ref="main",
            is_draft=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/pull/42",
            review_thread_count=0,
        )

        result = selector.select_pr([pr])
        assert result == 42

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pr_multiple_prs_valid_selection(
        self, mock_prompt, mock_echo
    ) -> None:
        """Test selecting from multiple PRs with valid user input."""
        mock_prompt.return_value = "2"

        selector = PRSelector()
        prs = [
            PullRequest(
                number=41,
                title="First PR",
                author="user1",
                head_ref="feature1",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/41",
                review_thread_count=1,
            ),
            PullRequest(
                number=42,
                title="Second PR",
                author="user2",
                head_ref="feature2",
                base_ref="main",
                is_draft=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            ),
        ]

        result = selector.select_pr(prs)
        assert result == 42

        # Verify user interaction
        mock_prompt.assert_called_once()
        # Should show header, PR list, and confirmation
        assert mock_echo.call_count >= 5

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pr_multiple_prs_quit(self, mock_prompt, mock_echo) -> None:
        """Test quitting from PR selection."""
        mock_prompt.return_value = "q"

        selector = PRSelector()
        prs = [
            PullRequest(
                number=41,
                title="First PR",
                author="user1",
                head_ref="feature1",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/41",
                review_thread_count=1,
            ),
            PullRequest(
                number=42,
                title="Second PR",
                author="user2",
                head_ref="feature2",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            ),
        ]

        result = selector.select_pr(prs)
        assert result is None

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pr_invalid_then_valid_selection(
        self, mock_prompt, mock_echo
    ) -> None:
        """Test invalid input followed by valid selection."""
        mock_prompt.side_effect = ["invalid", "0", "3", "1"]

        selector = PRSelector()
        prs = [
            PullRequest(
                number=41,
                title="First PR",
                author="user1",
                head_ref="feature1",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/41",
                review_thread_count=1,
            ),
            PullRequest(
                number=42,
                title="Second PR",
                author="user2",
                head_ref="feature2",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            ),
        ]

        result = selector.select_pr(prs)
        assert result == 41

        # Should have been called 4 times due to invalid inputs
        assert mock_prompt.call_count == 4

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pr_keyboard_interrupt(self, mock_prompt, mock_echo) -> None:
        """Test handling keyboard interrupt during selection."""
        mock_prompt.side_effect = KeyboardInterrupt()

        selector = PRSelector()
        prs = [
            PullRequest(
                number=41,
                title="First PR",
                author="user1",
                head_ref="feature1",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/41",
                review_thread_count=1,
            ),
            PullRequest(
                number=42,
                title="Second PR",
                author="user2",
                head_ref="feature2",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            ),
        ]

        result = selector.select_pr(prs)
        assert result is None

    @patch("click.echo")
    def test_display_no_prs_message(self, mock_echo) -> None:
        """Test displaying no PRs message."""
        selector = PRSelector()
        selector.display_no_prs_message()

        # Should display message and suggestion
        assert mock_echo.call_count >= 2

        # Check that appropriate messages were called
        calls = [str(call_arg) for call_arg in mock_echo.call_args_list]
        assert any("No open pull requests" in call_str for call_str in calls)
        assert any("specify a PR number" in call_str for call_str in calls)

    @patch("click.echo")
    def test_display_auto_selected_pr(self, mock_echo) -> None:
        """Test displaying auto-selected PR message."""
        selector = PRSelector()
        pr = PullRequest(
            number=42,
            title="Auto-selected PR",
            author="testuser",
            head_ref="feature",
            base_ref="main",
            is_draft=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/pull/42",
            review_thread_count=2,
        )

        selector.display_auto_selected_pr(pr)

        # Should display header, PR info, and author/branch info
        assert mock_echo.call_count >= 3

        # Check that PR information was included
        calls = [str(call_arg) for call_arg in mock_echo.call_args_list]
        assert any(
            "#42" in call_str and "Auto-selected PR" in call_str for call_str in calls
        )
        assert any(
            "testuser" in call_str and "feature" in call_str for call_str in calls
        )

    @patch("click.echo")
    def test_display_pr_list_formatting(self, mock_echo) -> None:
        """Test PR list display formatting with various PR types."""
        selector = PRSelector()
        prs = [
            PullRequest(
                number=41,
                title="Regular PR with threads",
                author="user1",
                head_ref="feature1",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/41",
                review_thread_count=3,
            ),
            PullRequest(
                number=42,
                title="Draft PR without threads",
                author="user2",
                head_ref="feature2",
                base_ref="develop",
                is_draft=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            ),
        ]

        selector._display_pr_list(prs)

        # Should display each PR with proper formatting
        calls = [str(call_arg) for call_arg in mock_echo.call_args_list]

        # Check for PR numbers, titles, authors, and branch info
        assert any(
            "#41" in call_str and "Regular PR with threads" in call_str
            for call_str in calls
        )
        assert any(
            "#42" in call_str and "Draft PR without threads" in call_str
            for call_str in calls
        )
        assert any("user1" in call_str and "feature1" in call_str for call_str in calls)
        assert any("user2" in call_str and "feature2" in call_str for call_str in calls)
        assert any("develop" in call_str for call_str in calls)


class TestPRSelectionResult:
    """Test the PRSelectionResult class."""

    def test_init_with_selection(self) -> None:
        """Test initialization with a selected PR."""
        result = PRSelectionResult(pr_number=42, cancelled=False)
        assert result.pr_number == 42
        assert result.cancelled is False
        assert result.has_selection is True
        assert result.should_continue is True

    def test_init_cancelled(self) -> None:
        """Test initialization with cancelled selection."""
        result = PRSelectionResult(pr_number=None, cancelled=True)
        assert result.pr_number is None
        assert result.cancelled is True
        assert result.has_selection is False
        assert result.should_continue is False

    def test_init_no_selection(self) -> None:
        """Test initialization with no selection (no PRs available)."""
        result = PRSelectionResult(pr_number=None, cancelled=False)
        assert result.pr_number is None
        assert result.cancelled is False
        assert result.has_selection is False
        assert result.should_continue is False

    def test_has_selection_property(self) -> None:
        """Test has_selection property."""
        result_with_selection = PRSelectionResult(pr_number=42)
        result_without_selection = PRSelectionResult(pr_number=None)

        assert result_with_selection.has_selection is True
        assert result_without_selection.has_selection is False

    def test_should_continue_property(self) -> None:
        """Test should_continue property."""
        # Should continue with valid selection
        result_continue = PRSelectionResult(pr_number=42, cancelled=False)
        assert result_continue.should_continue is True

        # Should not continue if cancelled
        result_cancelled = PRSelectionResult(pr_number=42, cancelled=True)
        assert result_cancelled.should_continue is False

        # Should not continue if no selection
        result_no_selection = PRSelectionResult(pr_number=None, cancelled=False)
        assert result_no_selection.should_continue is False


class TestCreatePRSelector:
    """Test the create_pr_selector factory function."""

    def test_create_pr_selector(self) -> None:
        """Test factory function creates valid PRSelector instance."""
        selector = create_pr_selector()
        assert isinstance(selector, PRSelector)
        assert selector.formatter is not None


class TestPRSelectorIntegration:
    """Integration tests for PR selector workflows."""

    @patch("click.echo")
    @patch("click.prompt")
    def test_complete_selection_workflow(self, mock_prompt, mock_echo) -> None:
        """Test complete PR selection workflow from display to selection."""
        mock_prompt.return_value = "1"

        selector = PRSelector()
        prs = [
            PullRequest(
                number=42,
                title="Test PR for selection",
                author="testuser",
                head_ref="feature-branch",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=2,
            ),
            PullRequest(
                number=43,
                title="Second PR for selection",
                author="testuser2",
                head_ref="feature-branch-2",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/43",
                review_thread_count=1,
            ),
        ]

        result = selector.select_pr(prs)

        # Should return the selected PR number
        assert result == 42

        # Should have displayed the menu and gotten user input
        mock_prompt.assert_called_once()

        # Should have displayed header, PR list, and confirmation
        calls = [str(call_arg) for call_arg in mock_echo.call_args_list]
        assert any("Found 2 open pull request" in call_str for call_str in calls)
        assert any(
            "#42" in call_str and "Test PR for selection" in call_str
            for call_str in calls
        )
        assert any("Selected PR #42" in call_str for call_str in calls)

    @patch("click.echo")
    def test_edge_case_very_long_title(self, mock_echo) -> None:
        """Test handling of very long PR titles in display."""
        selector = PRSelector()
        long_title = "A" * 200  # Very long title

        pr = PullRequest(
            number=42,
            title=long_title,
            author="testuser",
            head_ref="feature",
            base_ref="main",
            is_draft=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/pull/42",
            review_thread_count=0,
        )

        selector._display_pr_list([pr])

        # Should handle long titles gracefully (not crash)
        assert mock_echo.call_count > 0
        calls = [str(call_arg) for call_arg in mock_echo.call_args_list]
        assert any("#42" in call_str for call_str in calls)

    @patch("click.echo")
    def test_edge_case_special_characters_in_title(self, mock_echo) -> None:
        """Test handling of special characters in PR titles."""
        selector = PRSelector()

        pr = PullRequest(
            number=42,
            title="PR with émojis 🚀 and spëcial chars & symbols!",
            author="user-name_123",
            head_ref="feature/special-chars",
            base_ref="main",
            is_draft=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/pull/42",
            review_thread_count=0,
        )

        selector._display_pr_list([pr])

        # Should handle special characters gracefully
        assert mock_echo.call_count > 0
        calls = [str(call_arg) for call_arg in mock_echo.call_args_list]
        assert any("#42" in call_str for call_str in calls)
        assert any("émojis" in call_str for call_str in calls)
