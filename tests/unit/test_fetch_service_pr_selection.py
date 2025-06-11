"""Tests for FetchService PR selection functionality."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from toady.models.models import PullRequest, ReviewThread
from toady.services.fetch_service import FetchService, FetchServiceError
from toady.services.github_service import GitHubAPIError, GitHubAuthenticationError
from toady.services.pr_selector import PRSelectionResult


class TestFetchServicePRSelection:
    """Test FetchService interactive PR selection functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_github_service = MagicMock()
        self.fetch_service = FetchService(github_service=self.mock_github_service)

    def test_select_pr_interactively_no_prs(self) -> None:
        """Test interactive PR selection when no PRs are found."""
        # Mock fetch_open_pull_requests_from_current_repo to return empty list
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=[]
        )

        # Mock display_no_prs_message
        self.fetch_service.pr_selector.display_no_prs_message = MagicMock()

        result = self.fetch_service.select_pr_interactively()

        assert isinstance(result, PRSelectionResult)
        assert result.pr_number is None
        assert result.cancelled is False
        assert not result.has_selection
        assert not result.should_continue

        # Verify methods were called
        self.fetch_service.fetch_open_pull_requests_from_current_repo.assert_called_once_with(
            include_drafts=False, limit=100
        )
        self.fetch_service.pr_selector.display_no_prs_message.assert_called_once()

    def test_select_pr_interactively_single_pr(self) -> None:
        """Test interactive PR selection with single PR auto-selection."""
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

        # Mock fetch_open_pull_requests_from_current_repo to return single PR
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=[pr]
        )

        # Mock display_auto_selected_pr
        self.fetch_service.pr_selector.display_auto_selected_pr = MagicMock()

        result = self.fetch_service.select_pr_interactively()

        assert isinstance(result, PRSelectionResult)
        assert result.pr_number == 42
        assert result.cancelled is False
        assert result.has_selection
        assert result.should_continue

        # Verify methods were called
        self.fetch_service.pr_selector.display_auto_selected_pr.assert_called_once_with(
            pr
        )

    def test_select_pr_interactively_multiple_prs_selection(self) -> None:
        """Test interactive PR selection with multiple PRs and user selection."""
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

        # Mock fetch_open_pull_requests_from_current_repo to return multiple PRs
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=prs
        )

        # Mock select_pr to return selection
        self.fetch_service.pr_selector.select_pr = MagicMock(return_value=42)

        result = self.fetch_service.select_pr_interactively()

        assert isinstance(result, PRSelectionResult)
        assert result.pr_number == 42
        assert result.cancelled is False
        assert result.has_selection
        assert result.should_continue

        # Verify methods were called
        self.fetch_service.pr_selector.select_pr.assert_called_once_with(prs)

    def test_select_pr_interactively_multiple_prs_cancelled(self) -> None:
        """Test interactive PR selection with user cancellation."""
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

        # Mock fetch_open_pull_requests_from_current_repo to return PRs
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=prs
        )

        # Mock select_pr to return None (cancelled)
        self.fetch_service.pr_selector.select_pr = MagicMock(return_value=None)

        result = self.fetch_service.select_pr_interactively()

        assert isinstance(result, PRSelectionResult)
        assert result.pr_number is None
        assert result.cancelled is True
        assert not result.has_selection
        assert not result.should_continue

    def test_select_pr_interactively_with_drafts(self) -> None:
        """Test interactive PR selection with include_drafts option."""
        # Mock fetch_open_pull_requests_from_current_repo
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=[]
        )
        self.fetch_service.pr_selector.display_no_prs_message = MagicMock()

        self.fetch_service.select_pr_interactively(include_drafts=True, limit=50)

        # Verify correct parameters were passed
        self.fetch_service.fetch_open_pull_requests_from_current_repo.assert_called_once_with(
            include_drafts=True, limit=50
        )

    def test_select_pr_interactively_github_error(self) -> None:
        """Test interactive PR selection with GitHub API error."""
        # Mock fetch_open_pull_requests_from_current_repo to raise GitHubAPIError
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            side_effect=GitHubAPIError("API error")
        )

        # Should re-raise GitHub service errors
        with pytest.raises(GitHubAPIError, match="API error"):
            self.fetch_service.select_pr_interactively()

    def test_select_pr_interactively_other_error(self) -> None:
        """Test interactive PR selection with other errors."""
        # Mock fetch_open_pull_requests_from_current_repo to raise generic error
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            side_effect=ValueError("Some error")
        )

        # Should wrap in FetchServiceError
        with pytest.raises(
            FetchServiceError, match="Failed to select PR interactively"
        ):
            self.fetch_service.select_pr_interactively()

    def test_fetch_review_threads_with_pr_selection_provided_pr(self) -> None:
        """Test fetching threads with provided PR number (no selection needed)."""
        threads = [
            ReviewThread(
                thread_id="RT_123",
                title="Test thread",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="reviewer",
                comments=[],
            )
        ]

        # Mock fetch_review_threads_from_current_repo
        self.fetch_service.fetch_review_threads_from_current_repo = MagicMock(
            return_value=threads
        )

        result_threads, selected_pr = (
            self.fetch_service.fetch_review_threads_with_pr_selection(
                pr_number=42,
                include_resolved=True,
                threads_limit=50,
            )
        )

        assert result_threads == threads
        assert selected_pr == 42

        # Verify fetch was called with correct parameters
        self.fetch_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=42, include_resolved=True, limit=50
        )

    def test_fetch_review_threads_with_pr_selection_interactive_success(self) -> None:
        """Test fetching threads with successful interactive PR selection."""
        threads = [
            ReviewThread(
                thread_id="RT_123",
                title="Test thread",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="reviewer",
                comments=[],
            )
        ]

        # Mock select_pr_interactively to return successful selection
        self.fetch_service.select_pr_interactively = MagicMock(
            return_value=PRSelectionResult(pr_number=42, cancelled=False)
        )

        # Mock fetch_review_threads_from_current_repo
        self.fetch_service.fetch_review_threads_from_current_repo = MagicMock(
            return_value=threads
        )

        result_threads, selected_pr = (
            self.fetch_service.fetch_review_threads_with_pr_selection(
                pr_number=None,
                include_resolved=True,
                include_drafts=True,
                threads_limit=50,
                prs_limit=25,
            )
        )

        assert result_threads == threads
        assert selected_pr == 42

        # Verify interactive selection was called
        self.fetch_service.select_pr_interactively.assert_called_once_with(
            include_drafts=True, limit=25
        )

        # Verify fetch was called with selected PR
        self.fetch_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=42, include_resolved=True, limit=50
        )

    def test_fetch_review_threads_with_pr_selection_interactive_cancelled(self) -> None:
        """Test fetching threads with cancelled interactive PR selection."""
        # Mock select_pr_interactively to return cancelled selection
        self.fetch_service.select_pr_interactively = MagicMock(
            return_value=PRSelectionResult(pr_number=None, cancelled=True)
        )

        result_threads, selected_pr = (
            self.fetch_service.fetch_review_threads_with_pr_selection(pr_number=None)
        )

        assert result_threads == []
        assert selected_pr is None

        # Should not call fetch_review_threads_from_current_repo
        self.fetch_service.fetch_review_threads_from_current_repo = MagicMock()
        assert not self.fetch_service.fetch_review_threads_from_current_repo.called

    def test_fetch_review_threads_with_pr_selection_interactive_no_prs(self) -> None:
        """Test fetching threads when no PRs are available."""
        # Mock select_pr_interactively to return no selection (no PRs)
        self.fetch_service.select_pr_interactively = MagicMock(
            return_value=PRSelectionResult(pr_number=None, cancelled=False)
        )

        result_threads, selected_pr = (
            self.fetch_service.fetch_review_threads_with_pr_selection(pr_number=None)
        )

        assert result_threads == []
        assert selected_pr is None

    def test_fetch_review_threads_with_pr_selection_github_error(self) -> None:
        """Test error handling in fetch_review_threads_with_pr_selection."""
        # Mock select_pr_interactively to raise GitHubAuthenticationError
        self.fetch_service.select_pr_interactively = MagicMock(
            side_effect=GitHubAuthenticationError("Auth failed")
        )

        # Should re-raise GitHub service errors
        with pytest.raises(GitHubAuthenticationError, match="Auth failed"):
            self.fetch_service.fetch_review_threads_with_pr_selection(pr_number=None)

    def test_fetch_review_threads_with_pr_selection_other_error(self) -> None:
        """Test error wrapping in fetch_review_threads_with_pr_selection."""
        # Mock select_pr_interactively to raise generic error
        self.fetch_service.select_pr_interactively = MagicMock(
            side_effect=RuntimeError("Unexpected error")
        )

        # Should wrap in FetchServiceError
        with pytest.raises(
            FetchServiceError, match="Failed to fetch review threads with PR selection"
        ):
            self.fetch_service.fetch_review_threads_with_pr_selection(pr_number=None)


class TestFetchServicePRSelectionIntegration:
    """Integration tests for FetchService PR selection functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_github_service = MagicMock()
        self.fetch_service = FetchService(github_service=self.mock_github_service)

    def test_end_to_end_single_pr_workflow(self) -> None:
        """Test complete workflow with single PR auto-selection."""
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
            review_thread_count=1,
        )

        threads = [
            ReviewThread(
                thread_id="RT_123",
                title="Test thread",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="reviewer",
                comments=[],
            )
        ]

        # Mock the complete workflow
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=[pr]
        )
        self.fetch_service.fetch_review_threads_from_current_repo = MagicMock(
            return_value=threads
        )
        self.fetch_service.pr_selector.display_auto_selected_pr = MagicMock()

        # Test the complete workflow
        result_threads, selected_pr = (
            self.fetch_service.fetch_review_threads_with_pr_selection()
        )

        assert result_threads == threads
        assert selected_pr == 42

        # Verify all steps were executed
        self.fetch_service.fetch_open_pull_requests_from_current_repo.assert_called_once()
        self.fetch_service.pr_selector.display_auto_selected_pr.assert_called_once_with(
            pr
        )
        self.fetch_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=42, include_resolved=False, limit=100
        )

    @patch("toady.pr_selector.click.prompt")
    @patch("toady.pr_selector.click.echo")
    def test_end_to_end_multiple_prs_workflow(self, mock_echo, mock_prompt) -> None:
        """Test complete workflow with multiple PRs and user selection."""
        mock_prompt.return_value = "1"

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
                review_thread_count=2,
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
                review_thread_count=1,
            ),
        ]

        threads = [
            ReviewThread(
                thread_id="RT_123",
                title="Test thread",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="reviewer",
                comments=[],
            )
        ]

        # Mock the complete workflow
        self.fetch_service.fetch_open_pull_requests_from_current_repo = MagicMock(
            return_value=prs
        )
        self.fetch_service.fetch_review_threads_from_current_repo = MagicMock(
            return_value=threads
        )

        # Test the complete workflow
        result_threads, selected_pr = (
            self.fetch_service.fetch_review_threads_with_pr_selection()
        )

        assert result_threads == threads
        assert selected_pr == 41  # User selected first PR

        # Verify all steps were executed
        self.fetch_service.fetch_open_pull_requests_from_current_repo.assert_called_once()
        self.fetch_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=41, include_resolved=False, limit=100
        )

        # Verify user interaction occurred
        mock_prompt.assert_called_once()
        assert mock_echo.call_count > 0
