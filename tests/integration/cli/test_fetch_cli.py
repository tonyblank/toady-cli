"""Integration tests for the fetch CLI command."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from toady.cli import cli


class TestFetchCLI:
    """Test the fetch command CLI integration."""

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_pr_selection_no_prs(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection when no PRs are available."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], None)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        mock_service.fetch_review_threads_with_pr_selection.assert_called_once_with(
            pr_number=None, include_resolved=False, threads_limit=100
        )

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_pr_number(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with valid PR number."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 0
        assert "[]" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_pretty_flag(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with pretty output format."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "🔍 Fetching unresolved threads for PR #123" in result.output
        assert "📝 Found 0 unresolved threads" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_resolved_flag(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with resolved threads included."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123", "--resolved"])
        assert result.exit_code == 0
        assert "[]" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_custom_limit(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with custom limit."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123", "--limit", "50"])
        assert result.exit_code == 0
        assert "[]" in result.output

    def test_fetch_invalid_pr_number_negative(self, runner: CliRunner) -> None:
        """Test fetch with negative PR number."""
        result = runner.invoke(cli, ["fetch", "--pr", "-1"])
        assert result.exit_code != 0
        assert "PR number must be positive" in result.output

    def test_fetch_invalid_pr_number_zero(self, runner: CliRunner) -> None:
        """Test fetch with zero PR number."""
        result = runner.invoke(cli, ["fetch", "--pr", "0"])
        assert result.exit_code != 0
        assert "PR number must be positive" in result.output

    def test_fetch_invalid_limit_negative(self, runner: CliRunner) -> None:
        """Test fetch with negative limit."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--limit", "-1"])
        assert result.exit_code != 0
        assert "Limit must be positive" in result.output

    def test_fetch_invalid_limit_zero(self, runner: CliRunner) -> None:
        """Test fetch with zero limit."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--limit", "0"])
        assert result.exit_code != 0
        assert "Limit must be positive" in result.output

    def test_fetch_invalid_limit_too_large(self, runner: CliRunner) -> None:
        """Test fetch with limit exceeding maximum."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--limit", "1001"])
        assert result.exit_code != 0
        assert "Limit cannot exceed 1000" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_all_options_combined(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with all options combined."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["fetch", "--pr", "123", "--pretty", "--resolved", "--limit", "50"]
        )
        assert result.exit_code == 0
        assert "🔍 Fetching all threads for PR #123 (limit: 50)" in result.output

    def test_fetch_help(self, runner: CliRunner) -> None:
        """Test fetch command help."""
        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "Fetch review threads from a GitHub pull request" in result.output
        assert "Examples:" in result.output

    def test_fetch_pr_parameter_type_validation(self, runner: CliRunner) -> None:
        """Test that --pr parameter only accepts integers."""
        result = runner.invoke(cli, ["fetch", "--pr", "abc"])
        assert result.exit_code != 0
        assert "Invalid value for '--pr'" in result.output

    def test_fetch_limit_parameter_type_validation(self, runner: CliRunner) -> None:
        """Test that --limit parameter only accepts integers."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--limit", "abc"])
        assert result.exit_code != 0
        assert "Invalid value for '--limit'" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_default_limit(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test that fetch uses default limit when not specified."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "(limit: 100)" in result.output

    def test_fetch_enhanced_pr_validation_too_large(self, runner: CliRunner) -> None:
        """Test fetch with unreasonably large PR number."""
        result = runner.invoke(cli, ["fetch", "--pr", "1000000"])
        assert result.exit_code != 0
        assert "PR number appears unreasonably large" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_valid_large_pr_number(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with valid large PR number."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "999999"])
        assert result.exit_code == 0

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_authentication_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with authentication error in pretty mode."""
        from toady.exceptions import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubAuthenticationError("Authentication failed")
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 41  # GITHUB_AUTH_ERROR
        assert "❌ GitHub authentication failed" in result.output
        assert "Run 'gh auth login' to authenticate" in result.output
        assert "🔧 To fix this issue:" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_authentication_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with authentication error in JSON mode."""
        from toady.exceptions import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubAuthenticationError("Authentication failed")
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "authentication_failed"
        assert "Authentication failed" in output["error_message"]

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_timeout_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch timeout error handling."""
        from toady.exceptions import GitHubTimeoutError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubTimeoutError("Request timed out")
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 46  # GITHUB_TIMEOUT
        assert "❌ Request timed out" in result.output
        assert "Try again with a longer timeout" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "timeout"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_rate_limit_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch rate limit error handling."""
        from toady.exceptions import GitHubRateLimitError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubRateLimitError("Rate limit exceeded")
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 42  # GITHUB_RATE_LIMIT
        assert "❌ GitHub API rate limit exceeded" in result.output
        assert "Wait for the rate limit to reset" in result.output
        assert "gh api rate_limit" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "rate_limit_exceeded"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_pr_not_found_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch PR not found error handling."""
        from toady.exceptions import GitHubAPIError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubAPIError("404 Not Found - PR not found")
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "999999", "--pretty"])
        assert result.exit_code == 40  # GITHUB_ERROR
        assert "❌ 404 Not Found - PR not found" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "999999"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "pr_not_found"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_permission_denied_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch permission denied error handling."""
        from toady.exceptions import GitHubAPIError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubAPIError("403 Forbidden - permission denied")
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 40  # GITHUB_ERROR
        assert "❌ 403 Forbidden - permission denied" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "permission_denied"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_general_api_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch general API error handling."""
        from toady.exceptions import GitHubAPIError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            GitHubAPIError("500 Internal Server Error")
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 40  # GITHUB_ERROR
        assert "❌ 500 Internal Server Error" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "api_error"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_service_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch service error handling."""
        from toady.exceptions import FetchServiceError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            FetchServiceError("Service error")
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 70  # FETCH_ERROR
        assert "❌ Service error" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "service_error"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_unexpected_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch unexpected error handling."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = ValueError(
            "Unexpected internal error"
        )
        mock_service_class.return_value = mock_service

        # Test pretty mode
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 1
        assert "❌ An unexpected error occurred" in result.output
        assert "internal error" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["error"] == "internal_error"

    def test_fetch_error_json_output_structure(self, runner: CliRunner) -> None:
        """Test that error JSON output has correct structure."""
        # Test with invalid PR to trigger validation error
        result = runner.invoke(cli, ["fetch", "--pr", "1000000"])
        assert result.exit_code == 2  # Click validation error exit code
        # Validation errors from Click don't produce JSON, they go to stderr

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_comprehensive_parameter_validation(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test comprehensive parameter validation edge cases."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 123)
        mock_service_class.return_value = mock_service

        test_cases = [
            (["fetch", "--pr", "999999"], 0),  # Valid large PR
            (["fetch", "--pr", "1000000"], 2),  # Invalid too large PR
            (["fetch", "--pr", "123", "--limit", "1000"], 0),  # Valid max limit
            (["fetch", "--pr", "123", "--limit", "1001"], 2),  # Invalid too large limit
        ]

        for args, expected_exit_code in test_cases:
            result = runner.invoke(cli, args)
            assert result.exit_code == expected_exit_code, f"Failed for args: {args}"

    # New tests for interactive PR selection scenarios
    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_single_pr_auto_select(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection when single PR is auto-selected."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 456)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        mock_service.fetch_review_threads_with_pr_selection.assert_called_once_with(
            pr_number=None, include_resolved=False, threads_limit=100
        )

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_with_pretty_flag(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection and pretty output."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 789)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pretty"])
        assert result.exit_code == 0
        assert "🔍 Fetching unresolved threads for PR #789" in result.output
        assert "📝 Found 0 unresolved threads" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_with_resolved_flag(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection and resolved threads."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 111)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--resolved"])
        assert result.exit_code == 0
        mock_service.fetch_review_threads_with_pr_selection.assert_called_once_with(
            pr_number=None, include_resolved=True, threads_limit=100
        )

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_with_custom_limit(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection and custom limit."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 222)
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--limit", "50"])
        assert result.exit_code == 0
        mock_service.fetch_review_threads_with_pr_selection.assert_called_once_with(
            pr_number=None, include_resolved=False, threads_limit=50
        )

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_all_options_combined(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection and all options combined."""
        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.return_value = ([], 333)
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["fetch", "--pretty", "--resolved", "--limit", "25"]
        )
        assert result.exit_code == 0
        assert "🔍 Fetching all threads for PR #333 (limit: 25)" in result.output
        mock_service.fetch_review_threads_with_pr_selection.assert_called_once_with(
            pr_number=None, include_resolved=True, threads_limit=25
        )

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_interactive_error_handling(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test fetch with interactive PR selection error handling."""
        from toady.exceptions import FetchServiceError

        mock_service = Mock()
        mock_service.fetch_review_threads_with_pr_selection.side_effect = (
            FetchServiceError("Failed to fetch PRs")
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["fetch", "--pretty"])
        assert result.exit_code == 70  # FETCH_ERROR
        assert "❌ Failed to fetch PRs" in result.output
