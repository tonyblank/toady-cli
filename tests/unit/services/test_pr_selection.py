"""Unit tests for PR selection logic."""

from datetime import datetime
from unittest.mock import patch

import click
import pytest

from toady.exceptions import ValidationError
from toady.models import PullRequest
from toady.pr_selection import PRSelectionError, PRSelector


class TestPRSelector:
    """Test cases for PRSelector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.selector = PRSelector()

        # Create test PRs
        self.pr1 = PullRequest(
            number=1,
            title="First PR",
            author="user1",
            head_ref="feature-1",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            updated_at=datetime(2023, 1, 1, 11, 0, 0),
            url="https://github.com/owner/repo/pull/1",
            review_thread_count=2,
        )

        self.pr2 = PullRequest(
            number=2,
            title="Second PR (Draft)",
            author="user2",
            head_ref="feature-2",
            base_ref="main",
            is_draft=True,
            created_at=datetime(2023, 1, 2, 10, 0, 0),
            updated_at=datetime(2023, 1, 2, 12, 0, 0),
            url="https://github.com/owner/repo/pull/2",
            review_thread_count=0,
        )

        self.pr3 = PullRequest(
            number=3,
            title="Third PR with very long title that should be displayed properly",
            author="user3",
            head_ref="feature-3",
            base_ref="develop",
            is_draft=False,
            created_at=datetime(2023, 1, 3, 10, 0, 0),
            updated_at=datetime(2023, 1, 3, 13, 0, 0),
            url="https://github.com/owner/repo/pull/3",
            review_thread_count=5,
        )

    def test_init(self):
        """Test PRSelector initialization."""
        selector = PRSelector()
        assert selector is not None

    def test_select_pull_request_invalid_input(self):
        """Test select_pull_request with invalid input types."""
        with pytest.raises(ValidationError) as exc_info:
            self.selector.select_pull_request("not a list")

        assert "pull_requests must be a list" in str(exc_info.value)

    def test_select_pull_request_no_prs(self):
        """Test select_pull_request with no open PRs."""
        with pytest.raises(PRSelectionError) as exc_info:
            self.selector.select_pull_request([])

        error_msg = str(exc_info.value)
        assert "No open pull requests found" in error_msg
        assert "specify a PR number with --pr" in error_msg

    @patch("click.echo")
    def test_select_pull_request_single_pr(self, mock_echo):
        """Test select_pull_request with single PR (auto-selection)."""
        result = self.selector.select_pull_request([self.pr1])

        assert result == 1
        mock_echo.assert_called_once_with("Auto-selecting PR #1: First PR", err=True)

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pull_request_multiple_prs_valid_selection(
        self, mock_prompt, mock_echo
    ):
        """Test select_pull_request with multiple PRs and valid user selection."""
        mock_prompt.return_value = "2"

        result = self.selector.select_pull_request([self.pr1, self.pr2, self.pr3])

        assert result == 2  # Should select pr2 (which is index 1 in the sorted list)

        # Verify that PRs are displayed (echo called multiple times)
        assert (
            mock_echo.call_count >= 5
        )  # Header + PRs + blank lines + selection confirmation

        # Verify prompt was called
        mock_prompt.assert_called_once()

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pull_request_multiple_prs_quit(self, mock_prompt, mock_echo):
        """Test select_pull_request with multiple PRs and user quits."""
        mock_prompt.return_value = "q"

        with pytest.raises(PRSelectionError) as exc_info:
            self.selector.select_pull_request([self.pr1, self.pr2])

        assert "Selection cancelled by user" in str(exc_info.value)

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pull_request_multiple_prs_invalid_number(
        self, mock_prompt, mock_echo
    ):
        """Test select_pull_request with multiple PRs and invalid number."""
        mock_prompt.return_value = "invalid"

        with pytest.raises(PRSelectionError) as exc_info:
            self.selector.select_pull_request([self.pr1, self.pr2])

        error_msg = str(exc_info.value)
        assert "Invalid selection 'invalid'" in error_msg

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pull_request_multiple_prs_out_of_range(
        self, mock_prompt, mock_echo
    ):
        """Test select_pull_request with multiple PRs and out-of-range selection."""
        mock_prompt.return_value = "5"  # Only 2 PRs available

        with pytest.raises(PRSelectionError) as exc_info:
            self.selector.select_pull_request([self.pr1, self.pr2])

        error_msg = str(exc_info.value)
        assert "Selection 5 is out of range" in error_msg

    @patch("click.echo")
    @patch("click.prompt")
    def test_select_pull_request_multiple_prs_ctrl_c(self, mock_prompt, mock_echo):
        """Test select_pull_request with multiple PRs and user presses Ctrl+C."""
        mock_prompt.side_effect = click.Abort()

        with pytest.raises(PRSelectionError) as exc_info:
            self.selector.select_pull_request([self.pr1, self.pr2])

        assert "Selection cancelled by user" in str(exc_info.value)

    def test_select_pull_request_multiple_prs_not_allowed(self):
        """Test select_pull_request with multiple PRs when not allowed."""
        with pytest.raises(PRSelectionError) as exc_info:
            self.selector.select_pull_request(
                [self.pr1, self.pr2], allow_multiple=False
            )

        error_msg = str(exc_info.value)
        assert "Found 2 open pull requests" in error_msg
        assert "multiple selection is not allowed" in error_msg

    @patch("click.echo")
    def test_pr_sorting_by_update_time(self, mock_echo):
        """Test that PRs are sorted by update time (most recent first)."""
        # Create PRs with different update times
        older_pr = PullRequest(
            number=10,
            title="Older PR",
            author="user",
            head_ref="old",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            updated_at=datetime(2023, 1, 1, 10, 0, 0),  # Earlier
            url="https://github.com/owner/repo/pull/10",
            review_thread_count=0,
        )

        newer_pr = PullRequest(
            number=5,
            title="Newer PR",
            author="user",
            head_ref="new",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2023, 1, 2, 10, 0, 0),
            updated_at=datetime(2023, 1, 2, 10, 0, 0),  # Later
            url="https://github.com/owner/repo/pull/5",
            review_thread_count=0,
        )

        with patch("click.prompt", return_value="1"):
            result = self.selector.select_pull_request([older_pr, newer_pr])

        # Should select the newer PR (which will be first after sorting)
        assert result == 5

    @patch("click.echo")
    def test_pr_display_formatting(self, mock_echo):
        """Test that PR display formatting includes all expected information."""
        with patch("click.prompt", return_value="1"):
            self.selector.select_pull_request([self.pr1, self.pr2])

        # Check that echo was called with PR information
        echo_calls = [call.args[0] for call in mock_echo.call_args_list]

        # Find the call that contains PR #1 info
        pr1_call = next((call for call in echo_calls if "PR #1:" in call), None)
        assert pr1_call is not None
        assert "First PR" in pr1_call
        assert "[2 threads]" in pr1_call

        # Find the call that contains PR #2 info
        pr2_call = next((call for call in echo_calls if "PR #2:" in call), None)
        assert pr2_call is not None
        assert "Second PR (Draft)" in pr2_call
        assert "(draft)" in pr2_call

    def test_handle_no_prs(self):
        """Test _handle_no_prs method directly."""
        with pytest.raises(PRSelectionError) as exc_info:
            self.selector._handle_no_prs()

        error_msg = str(exc_info.value)
        assert "No open pull requests found" in error_msg

    @patch("click.echo")
    def test_handle_single_pr(self, mock_echo):
        """Test _handle_single_pr method directly."""
        result = self.selector._handle_single_pr(self.pr1)

        assert result == 1
        mock_echo.assert_called_once_with("Auto-selecting PR #1: First PR", err=True)

    def test_validate_pr_exists_invalid_input_type(self):
        """Test validate_pr_exists with invalid input type."""
        with pytest.raises(ValidationError) as exc_info:
            self.selector.validate_pr_exists("not_an_int", [self.pr1])

        assert "PR number must be an integer" in str(exc_info.value)

    def test_validate_pr_exists_negative_number(self):
        """Test validate_pr_exists with negative PR number."""
        with pytest.raises(ValidationError) as exc_info:
            self.selector.validate_pr_exists(-1, [self.pr1])

        assert "PR number must be positive" in str(exc_info.value)

    def test_validate_pr_exists_zero(self):
        """Test validate_pr_exists with zero PR number."""
        with pytest.raises(ValidationError) as exc_info:
            self.selector.validate_pr_exists(0, [self.pr1])

        assert "PR number must be positive" in str(exc_info.value)

    def test_validate_pr_exists_not_found(self):
        """Test validate_pr_exists with PR not in list."""
        with pytest.raises(ValidationError) as exc_info:
            self.selector.validate_pr_exists(999, [self.pr1, self.pr2])

        error_msg = str(exc_info.value)
        assert "PR #999 not found" in error_msg
        assert "Available: 1, 2" in error_msg

    def test_validate_pr_exists_success(self):
        """Test validate_pr_exists with valid PR."""
        result = self.selector.validate_pr_exists(1, [self.pr1, self.pr2])
        assert result is True

    def test_validate_pr_exists_success_multiple(self):
        """Test validate_pr_exists with valid PR from multiple options."""
        result = self.selector.validate_pr_exists(2, [self.pr1, self.pr2, self.pr3])
        assert result is True


class TestPRSelectionIntegration:
    """Integration tests for PR selection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.selector = PRSelector()

    @patch("click.echo")
    @patch("click.prompt")
    def test_full_selection_workflow(self, mock_prompt, mock_echo):
        """Test the complete selection workflow."""
        # Create test PRs
        prs = [
            PullRequest(
                number=i,
                title=f"Test PR {i}",
                author=f"user{i}",
                head_ref=f"feature-{i}",
                base_ref="main",
                is_draft=False,
                created_at=datetime(2023, 1, i, 10, 0, 0),
                updated_at=datetime(2023, 1, i, 12, 0, 0),
                url=f"https://github.com/owner/repo/pull/{i}",
                review_thread_count=i,
            )
            for i in range(1, 4)
        ]

        mock_prompt.return_value = "2"

        result = self.selector.select_pull_request(prs)

        # Should select PR #2 (middle one chronologically, but may be sorted)
        assert isinstance(result, int)
        assert result in [1, 2, 3]  # Should be one of the valid PR numbers

        # Verify interaction occurred
        assert mock_echo.call_count > 0
        mock_prompt.assert_called_once()

    def test_edge_case_empty_title(self):
        """Test handling of PR with empty title fails validation."""
        # This should fail during PR creation due to validation
        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                number=1,
                title="",  # Edge case: empty title - should fail validation
                author="user",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime(2023, 1, 1, 10, 0, 0),
                updated_at=datetime(2023, 1, 1, 11, 0, 0),
                url="https://github.com/owner/repo/pull/1",
                review_thread_count=0,
            )

        assert "title cannot be empty" in str(exc_info.value)
