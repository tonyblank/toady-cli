"""Integration tests for the resolve CLI command."""

from datetime import datetime
import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from toady.cli import cli


class TestResolveCLI:
    """Test the resolve command CLI integration."""

    def test_resolve_requires_thread_id(self, runner: CliRunner) -> None:
        """Test that resolve requires either --thread-id or --all option."""
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert "Must specify either --thread-id or --all" in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_valid_numeric_id(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with valid numeric thread ID."""
        mock_service = Mock()
        mock_service.resolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 0
        assert '"thread_id": "123456789"' in result.output
        assert '"action": "resolve"' in result.output
        assert '"success": true' in result.output

        mock_service.resolve_thread.assert_called_once_with("123456789")

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_valid_node_id(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with valid GitHub node ID."""
        mock_service = Mock()
        mock_service.resolve_thread.return_value = {
            "thread_id": "PRT_kwDOABcD12MAAAABcDE3fg",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["resolve", "--thread-id", "PRT_kwDOABcD12MAAAABcDE3fg"]
        )
        assert result.exit_code == 0
        assert '"thread_id": "PRT_kwDOABcD12MAAAABcDE3fg"' in result.output

        mock_service.resolve_thread.assert_called_once_with(
            "PRT_kwDOABcD12MAAAABcDE3fg"
        )

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_undo_flag(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with undo flag."""
        mock_service = Mock()
        mock_service.unresolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "unresolve",
            "success": True,
            "is_resolved": "false",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--undo"])
        assert result.exit_code == 0
        assert '"action": "unresolve"' in result.output
        assert '"success": true' in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_pretty_output(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with pretty output format."""
        mock_service = Mock()
        mock_service.resolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 0
        assert "🔒 Resolving thread 123456789" in result.output
        assert "✅ Thread resolved successfully" in result.output
        assert (
            "🔗 View thread at: https://github.com/owner/repo/pull/123" in result.output
        )

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_undo_pretty_output(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test unresolve with pretty output format."""
        mock_service = Mock()
        mock_service.unresolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "unresolve",
            "success": True,
            "is_resolved": "false",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["resolve", "--thread-id", "123456789", "--undo", "--pretty"]
        )
        assert result.exit_code == 0
        assert "🔓 Unresolving thread 123456789" in result.output
        assert "✅ Thread unresolved successfully" in result.output

    def test_resolve_empty_thread_id(self, runner: CliRunner) -> None:
        """Test resolve with empty thread ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", ""])
        assert result.exit_code != 0
        assert "Thread ID cannot be empty" in result.output

    def test_resolve_whitespace_thread_id(self, runner: CliRunner) -> None:
        """Test resolve with whitespace-only thread ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "   "])
        assert result.exit_code != 0
        assert "Thread ID cannot be empty" in result.output

    def test_resolve_invalid_thread_id_format(self, runner: CliRunner) -> None:
        """Test resolve with invalid thread ID format."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "invalid123"])
        assert result.exit_code != 0
        assert "Thread ID must start with one of" in result.output

    def test_resolve_invalid_node_id_too_short(self, runner: CliRunner) -> None:
        """Test resolve with too short node ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "PRT_abc"])
        assert result.exit_code != 0
        assert "appears too short to be valid" in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_json_output_structure(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test that JSON output has correct structure."""
        mock_service = Mock()
        mock_service.resolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert "thread_id" in output
        assert "action" in output
        assert "success" in output
        assert "thread_url" in output
        assert output["thread_id"] == "123456789"
        assert output["action"] == "resolve"
        assert output["success"] is True
        assert "https://github.com/" in output["thread_url"]

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_json_output_with_undo(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test that JSON output has correct structure with undo flag."""
        mock_service = Mock()
        mock_service.unresolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "unresolve",
            "success": True,
            "is_resolved": "false",
            "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123456789",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--undo"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["action"] == "unresolve"

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_thread_not_found_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with thread not found error in pretty mode."""
        from toady.exceptions import ThreadNotFoundError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ThreadNotFoundError(
            "Thread 999 not found"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "999", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Thread not found:" in result.output
        assert "Thread 999 not found" in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_thread_not_found_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with thread not found error in JSON mode."""
        from toady.exceptions import ThreadNotFoundError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ThreadNotFoundError(
            "Thread 999 not found"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "999"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "thread_not_found"
        assert "Thread 999 not found" in output["error_message"]

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_permission_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with permission error in pretty mode."""
        from toady.exceptions import ThreadPermissionError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ThreadPermissionError(
            "Permission denied"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Permission denied:" in result.output
        assert "Permission denied" in result.output
        assert "💡 Ensure you have write access to the repository" in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_permission_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with permission error in JSON mode."""
        from toady.exceptions import ThreadPermissionError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ThreadPermissionError(
            "Permission denied"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "permission_denied"
        assert "Permission denied" in output["error_message"]

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_authentication_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with authentication error in pretty mode."""
        from toady.exceptions import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 1
        assert (
            "❌ Authentication failed: [GITHUB_AUTHENTICATION_ERROR]" in result.output
        )
        assert "💡 Try running: gh auth login" in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_authentication_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with authentication error in JSON mode."""
        from toady.exceptions import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "authentication_failed"
        assert "Authentication failed" in output["error_message"]

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_api_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with API error in pretty mode."""
        from toady.exceptions import ResolveServiceError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ResolveServiceError(
            "API request failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Failed to resolve thread:" in result.output
        assert "API request failed" in result.output

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_api_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with API error in JSON mode."""
        from toady.exceptions import ResolveServiceError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ResolveServiceError(
            "API request failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "api_error"
        assert "API request failed" in output["error_message"]

    def test_resolve_help_content(self, runner: CliRunner) -> None:
        """Test resolve command help content."""
        result = runner.invoke(cli, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "Mark review threads as resolved or unresolved" in result.output
        assert "Examples:" in result.output
        assert "--thread-id" in result.output
        assert "--undo" in result.output

    def test_resolve_parameter_metavars(self, runner: CliRunner) -> None:
        """Test that parameter metavars are displayed correctly."""
        result = runner.invoke(cli, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "ID" in result.output  # metavar for thread-id

    # Tests for --all flag functionality
    def test_resolve_all_requires_pr_option(self, runner: CliRunner) -> None:
        """Test that --all requires --pr option."""
        result = runner.invoke(cli, ["resolve", "--all"])
        assert result.exit_code != 0
        assert "--pr is required when using --all" in result.output

    def test_resolve_all_and_thread_id_mutually_exclusive(
        self, runner: CliRunner
    ) -> None:
        """Test that --all and --thread-id cannot be used together."""
        result = runner.invoke(
            cli, ["resolve", "--all", "--thread-id", "123", "--pr", "456"]
        )
        assert result.exit_code != 0
        assert "Cannot use --all and --thread-id together" in result.output

    def test_resolve_requires_either_all_or_thread_id(self, runner: CliRunner) -> None:
        """Test that either --all or --thread-id must be specified."""
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert "Must specify either --thread-id or --all" in result.output

    def test_resolve_all_validates_pr_number(self, runner: CliRunner) -> None:
        """Test that --all validates PR number ranges."""
        # Test negative PR number
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "-1"])
        assert result.exit_code != 0
        assert "PR number must be positive" in result.output

        # Test zero PR number
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "0"])
        assert result.exit_code != 0
        assert "PR number must be positive" in result.output

        # Test excessively large PR number
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "1000000"])
        assert result.exit_code != 0
        assert "PR number appears unreasonably large" in result.output

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.FetchService")
    def test_resolve_all_no_threads_found(
        self,
        mock_fetch_service_class: Mock,
        mock_resolve_service_class: Mock,
        runner: CliRunner,
    ) -> None:
        """Test --all when no unresolved threads are found."""
        mock_fetch_service = Mock()
        mock_fetch_service.fetch_review_threads_from_current_repo.return_value = []
        mock_fetch_service_class.return_value = mock_fetch_service

        # Test pretty mode
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "No unresolved threads found in PR #123" in result.output

        # Test JSON mode
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "123"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["threads_processed"] == 0
        assert output["message"] == "No unresolved threads found"

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.FetchService")
    def test_resolve_all_successful_bulk_operation(
        self,
        mock_fetch_service_class: Mock,
        mock_resolve_service_class: Mock,
        runner: CliRunner,
    ) -> None:
        """Test successful bulk resolution with --all flag."""
        from toady.models import ReviewThread

        mock_fetch_service = Mock()
        mock_threads = [
            ReviewThread(
                thread_id="thread1",
                title="Test thread 1",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="UNRESOLVED",
                author="testuser",
                comments=[],
            ),
            ReviewThread(
                thread_id="thread2",
                title="Test thread 2",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="UNRESOLVED",
                author="testuser",
                comments=[],
            ),
        ]
        mock_fetch_service.fetch_review_threads_from_current_repo.return_value = (
            mock_threads
        )
        mock_fetch_service_class.return_value = mock_fetch_service

        mock_resolve_service = Mock()
        mock_resolve_service.resolve_thread.return_value = {"success": True}
        mock_resolve_service_class.return_value = mock_resolve_service

        # Test JSON mode with --yes flag
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "123", "--yes"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["success"] is True
        assert output["threads_processed"] == 2
        assert output["threads_succeeded"] == 2
        assert output["threads_failed"] == 0

        # Verify both threads were resolved
        assert mock_resolve_service.resolve_thread.call_count == 2
        mock_resolve_service.resolve_thread.assert_any_call("thread1")
        mock_resolve_service.resolve_thread.assert_any_call("thread2")

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.FetchService")
    def test_resolve_all_successful_bulk_operation_pretty(
        self,
        mock_fetch_service_class: Mock,
        mock_resolve_service_class: Mock,
        runner: CliRunner,
    ) -> None:
        """Test successful bulk resolution with --all flag in pretty mode."""
        from toady.models import ReviewThread

        mock_fetch_service = Mock()
        mock_threads = [
            ReviewThread(
                thread_id="thread1",
                title="Test thread 1",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="UNRESOLVED",
                author="testuser",
                comments=[],
            ),
            ReviewThread(
                thread_id="thread2",
                title="Test thread 2",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="UNRESOLVED",
                author="testuser",
                comments=[],
            ),
        ]
        mock_fetch_service.fetch_review_threads_from_current_repo.return_value = (
            mock_threads
        )
        mock_fetch_service_class.return_value = mock_fetch_service

        mock_resolve_service = Mock()
        mock_resolve_service.resolve_thread.return_value = {"success": True}
        mock_resolve_service_class.return_value = mock_resolve_service

        result = runner.invoke(
            cli, ["resolve", "--all", "--pr", "123", "--yes", "--pretty"]
        )
        assert result.exit_code == 0
        assert "Fetching threads from PR #123" in result.output
        assert "Resolving 2 thread(s)" in result.output
        assert "Bulk resolve completed" in result.output
        assert "Total threads processed: 2" in result.output
        assert "Successfully resolved: 2" in result.output
