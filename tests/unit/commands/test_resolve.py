"""Unit tests for the resolve command module.

This module tests the core resolve command logic, including parameter validation,
error handling, format resolution, and service integration. It focuses on unit
testing the command implementation without testing the CLI interface directly.
"""

import json
from unittest.mock import Mock, patch

import click
from click.testing import CliRunner
import pytest

from toady.cli import cli
from toady.commands.resolve import (
    _display_summary,
    _fetch_and_filter_threads,
    _get_action_labels,
    _handle_bulk_resolve,
    _handle_bulk_resolve_error,
    _handle_confirmation_prompt,
    _handle_empty_threads,
    _handle_single_resolve,
    _handle_single_resolve_error,
    _handle_single_resolve_success,
    _process_threads,
    _show_single_resolve_progress,
    _validate_and_prepare_thread_id,
    _validate_resolve_parameters,
    resolve,
)
from toady.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    ResolveServiceError,
    ThreadNotFoundError,
    ThreadPermissionError,
)
from toady.services.fetch_service import FetchServiceError


class TestResolveCommandCore:
    """Test the core resolve command functionality."""

    def test_resolve_command_exists(self):
        """Test that the resolve command is properly defined."""
        assert resolve is not None
        assert callable(resolve)
        assert hasattr(resolve, "params")

    def test_resolve_command_parameters(self):
        """Test that resolve command has expected parameters."""
        param_names = [param.name for param in resolve.params]
        expected_params = [
            "thread_id",
            "bulk_resolve",
            "pr_number",
            "undo",
            "yes",
            "format",
            "pretty",
            "limit",
        ]

        for expected_param in expected_params:
            assert expected_param in param_names, f"Missing parameter: {expected_param}"

    def test_resolve_command_defaults(self):
        """Test resolve command parameter defaults."""
        param_defaults = {param.name: param.default for param in resolve.params}

        assert param_defaults["thread_id"] is None
        assert param_defaults["bulk_resolve"] is False
        assert param_defaults["pr_number"] is None
        assert param_defaults["undo"] is False
        assert param_defaults["yes"] is False
        assert param_defaults["format"] is None
        assert param_defaults["pretty"] is False
        assert param_defaults["limit"] == 100


class TestValidateResolveParameters:
    """Test parameter validation in the resolve command."""

    def test_validate_mutually_exclusive_bulk_and_thread_id(self):
        """Test that bulk_resolve and thread_id are mutually exclusive."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_resolve_parameters(True, "thread123", 456, 100)
        assert "Cannot use --all and --thread-id together" in str(exc_info.value)

    def test_validate_requires_thread_id_or_bulk(self):
        """Test that either thread_id or bulk_resolve must be specified."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_resolve_parameters(False, None, None, 100)
        assert "Must specify either --thread-id or --all" in str(exc_info.value)

    @patch("toady.commands.resolve.validate_pr_number")
    def test_validate_pr_number_called_when_provided(self, mock_validate_pr):
        """Test that PR number validation is called when provided."""
        _validate_resolve_parameters(True, None, 123, 100)
        mock_validate_pr.assert_called_once_with(123)

    @patch("toady.commands.resolve.validate_pr_number")
    def test_validate_pr_number_not_called_when_none(self, mock_validate_pr):
        """Test that PR number validation is not called when None."""
        _validate_resolve_parameters(False, "thread123", None, 100)
        mock_validate_pr.assert_not_called()

    def test_validate_bulk_requires_pr_number(self):
        """Test that bulk resolve requires PR number."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_resolve_parameters(True, None, None, 100)
        assert "--pr is required when using --all" in str(exc_info.value)

    @patch("toady.command_utils.validate_limit")
    def test_validate_limit_called(self, mock_validate_limit):
        """Test that limit validation is called."""
        _validate_resolve_parameters(False, "thread123", None, 150)
        mock_validate_limit.assert_called_once_with(150, max_limit=1000)


class TestValidateAndPrepareThreadId:
    """Test thread ID validation and preparation."""

    def test_valid_thread_id_stripped_and_returned(self):
        """Test that valid thread ID is stripped and returned."""
        with patch("toady.commands.resolve.validate_thread_id") as mock_validate:
            result = _validate_and_prepare_thread_id("  thread123  ")
            assert result == "thread123"
            mock_validate.assert_called_once_with("thread123")

    def test_empty_thread_id_raises_error(self):
        """Test that empty thread ID raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_and_prepare_thread_id("")
        assert "Thread ID cannot be empty" in str(exc_info.value)

    def test_whitespace_thread_id_raises_error(self):
        """Test that whitespace-only thread ID raises error."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_and_prepare_thread_id("   ")
        assert "Thread ID cannot be empty" in str(exc_info.value)

    def test_validation_error_converted_to_bad_parameter(self):
        """Test that validation errors are converted to BadParameter."""
        with patch("toady.commands.resolve.validate_thread_id") as mock_validate:
            mock_validate.side_effect = ValueError("Invalid format")
            with pytest.raises(click.BadParameter) as exc_info:
                _validate_and_prepare_thread_id("invalid")
            assert "Invalid format" in str(exc_info.value)


class TestFetchAndFilterThreads:
    """Test thread fetching and filtering logic."""

    @patch("toady.commands.resolve.FetchService")
    @patch("toady.commands.resolve.click.echo")
    def test_fetch_unresolved_threads_pretty(self, mock_echo, mock_service_class):
        """Test fetching unresolved threads with pretty output."""
        mock_service = Mock()
        mock_threads = [Mock(is_resolved=False), Mock(is_resolved=True)]
        mock_service.fetch_review_threads_from_current_repo.return_value = mock_threads
        mock_service_class.return_value = mock_service

        result = _fetch_and_filter_threads(123, False, True, 50)

        mock_echo.assert_called_once_with(
            "🔍 Fetching threads from PR #123 (limit: 50)..."
        )
        mock_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=123, include_resolved=False, limit=50
        )
        assert len(result) == 1  # Only unresolved thread

    @patch("toady.commands.resolve.FetchService")
    def test_fetch_resolved_threads_for_undo(self, mock_service_class):
        """Test fetching resolved threads for undo operation."""
        mock_service = Mock()
        mock_threads = [Mock(is_resolved=False), Mock(is_resolved=True)]
        mock_service.fetch_review_threads_from_current_repo.return_value = mock_threads
        mock_service_class.return_value = mock_service

        result = _fetch_and_filter_threads(123, True, False, 100)

        mock_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=123, include_resolved=True, limit=100
        )
        assert len(result) == 1  # Only resolved thread

    @patch("toady.commands.resolve.FetchService")
    def test_fetch_threads_no_pretty(self, mock_service_class):
        """Test fetching threads without pretty output."""
        mock_service = Mock()
        mock_threads = [Mock(is_resolved=False)]
        mock_service.fetch_review_threads_from_current_repo.return_value = mock_threads
        mock_service_class.return_value = mock_service

        with patch("toady.commands.resolve.click.echo") as mock_echo:
            _fetch_and_filter_threads(123, False, False, 100)
            mock_echo.assert_not_called()


class TestHandleConfirmationPrompt:
    """Test confirmation prompt handling."""

    def test_confirmation_skipped_with_yes_flag(self):
        """Test that confirmation is skipped when yes flag is used."""
        ctx = Mock()
        threads = [Mock(thread_id="t1", title="Title 1")]

        # Should not exit when yes=True
        _handle_confirmation_prompt(ctx, threads, "resolve", "🔒", 123, True, True)
        ctx.exit.assert_not_called()

    @patch("toady.commands.resolve.click.confirm")
    @patch("toady.commands.resolve.click.echo")
    def test_confirmation_accepted_pretty(self, mock_echo, mock_confirm):
        """Test confirmation accepted in pretty mode."""
        mock_confirm.return_value = True
        ctx = Mock()
        threads = [Mock(thread_id="t1", title="Title 1")]

        _handle_confirmation_prompt(ctx, threads, "resolve", "🔒", 123, False, True)

        mock_confirm.assert_called_once_with("Do you want to resolve these threads?")
        ctx.exit.assert_not_called()

    @patch("toady.commands.resolve.click.confirm")
    @patch("toady.commands.resolve.click.echo")
    def test_confirmation_declined_pretty(self, mock_echo, mock_confirm):
        """Test confirmation declined in pretty mode."""
        mock_confirm.return_value = False
        ctx = Mock()
        threads = [Mock(thread_id="t1", title="Title 1")]

        _handle_confirmation_prompt(ctx, threads, "resolve", "🔒", 123, False, True)

        mock_confirm.assert_called_once_with("Do you want to resolve these threads?")
        ctx.exit.assert_called_once_with(0)

    @patch("toady.commands.resolve.click.echo")
    def test_confirmation_required_json_mode(self, mock_echo):
        """Test that confirmation is required in JSON mode without yes flag."""
        ctx = Mock()
        threads = [Mock(thread_id="t1", title="Title 1")]

        _handle_confirmation_prompt(ctx, threads, "resolve", "🔒", 123, False, False)

        ctx.exit.assert_called_once_with(1)
        mock_echo.assert_called_once()

    @patch("toady.commands.resolve.click.confirm")
    @patch("toady.commands.resolve.click.echo")
    def test_confirmation_shows_first_five_threads(self, mock_echo, mock_confirm):
        """Test that confirmation shows first 5 threads and indicates more."""
        mock_confirm.return_value = True
        ctx = Mock()
        threads = [Mock(thread_id=f"t{i}", title=f"Title {i}") for i in range(10)]

        _handle_confirmation_prompt(ctx, threads, "resolve", "🔒", 123, False, True)

        # Check that it shows first 5 and indicates more
        echo_calls = [
            str(call.args[0]) if call.args else str(call)
            for call in mock_echo.call_args_list
        ]
        assert any("1. t0 - Title 0" in call for call in echo_calls)
        assert any("5. t4 - Title 4" in call for call in echo_calls)
        assert any("... and 5 more" in call for call in echo_calls)


class TestProcessThreads:
    """Test thread processing logic."""

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.time.sleep")
    @patch("toady.commands.resolve.click.echo")
    def test_process_threads_resolve_success(
        self, mock_echo, mock_sleep, mock_service_class
    ):
        """Test successful thread resolution processing."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        threads = [Mock(thread_id="t1"), Mock(thread_id="t2")]
        succeeded, failed, failed_threads = _process_threads(
            threads, False, "Resolving", "🔒", True
        )

        assert succeeded == 2
        assert failed == 0
        assert failed_threads == []
        assert mock_service.resolve_thread.call_count == 2
        mock_service.resolve_thread.assert_any_call("t1")
        mock_service.resolve_thread.assert_any_call("t2")

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.time.sleep")
    @patch("toady.commands.resolve.click.echo")
    def test_process_threads_unresolve_success(
        self, mock_echo, mock_sleep, mock_service_class
    ):
        """Test successful thread unresolve processing."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        threads = [Mock(thread_id="t1")]
        succeeded, failed, failed_threads = _process_threads(
            threads, True, "Unresolving", "🔓", False
        )

        assert succeeded == 1
        assert failed == 0
        mock_service.unresolve_thread.assert_called_once_with("t1")

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.time.sleep")
    @patch("toady.commands.resolve.click.echo")
    def test_process_threads_rate_limit_error(
        self, mock_echo, mock_sleep, mock_service_class
    ):
        """Test handling of rate limit errors during processing."""
        mock_service = Mock()
        mock_service.resolve_thread.side_effect = [
            None,  # First call succeeds
            GitHubRateLimitError("Rate limit exceeded"),  # Second call fails
        ]
        mock_service_class.return_value = mock_service

        threads = [Mock(thread_id="t1"), Mock(thread_id="t2")]
        succeeded, failed, failed_threads = _process_threads(
            threads, False, "Resolving", "🔒", True
        )

        assert succeeded == 1
        assert failed == 1
        assert len(failed_threads) == 1
        assert failed_threads[0]["thread_id"] == "t2"
        assert "Rate limit exceeded" in failed_threads[0]["error"]

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.time.sleep")
    @patch("toady.commands.resolve.click.echo")
    def test_process_threads_api_error(self, mock_echo, mock_sleep, mock_service_class):
        """Test handling of API errors during processing."""
        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ResolveServiceError("API error")
        mock_service_class.return_value = mock_service

        threads = [Mock(thread_id="t1")]
        succeeded, failed, failed_threads = _process_threads(
            threads, False, "Resolving", "🔒", False
        )

        assert succeeded == 0
        assert failed == 1
        assert failed_threads[0]["thread_id"] == "t1"

    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve.time.sleep")
    def test_process_threads_no_sleep_after_last(self, mock_sleep, mock_service_class):
        """Test that no sleep occurs after the last thread."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        threads = [Mock(thread_id="t1")]
        _process_threads(threads, False, "Resolving", "🔒", False)

        # Should not sleep after processing the last (only) thread
        mock_sleep.assert_not_called()


class TestDisplaySummary:
    """Test summary display logic."""

    @patch("toady.commands.resolve.click.echo")
    def test_display_summary_pretty_success(self, mock_echo):
        """Test summary display in pretty mode with success."""
        threads = [Mock(), Mock()]
        _display_summary(threads, 2, 0, [], "resolve", "resolved", 123, True)

        echo_calls = [call[0][0] for call in mock_echo.call_args_list]
        assert any("✅ Bulk resolve completed:" in call for call in echo_calls)
        assert any("📊 Total threads processed: 2" in call for call in echo_calls)
        assert any("✅ Successfully resolved: 2" in call for call in echo_calls)

    @patch("toady.commands.resolve.click.echo")
    def test_display_summary_pretty_with_failures(self, mock_echo):
        """Test summary display in pretty mode with failures."""
        threads = [Mock(), Mock()]
        failed_threads = [{"thread_id": "t1", "error": "Failed"}]
        _display_summary(
            threads, 1, 1, failed_threads, "resolve", "resolved", 123, True
        )

        echo_calls = [call[0][0] for call in mock_echo.call_args_list]
        assert any("❌ Failed: 1" in call for call in echo_calls)
        assert any("❌ Failed threads:" in call for call in echo_calls)
        assert any("• t1: Failed" in call for call in echo_calls)

    @patch("toady.commands.resolve.click.echo")
    def test_display_summary_json_success(self, mock_echo):
        """Test summary display in JSON mode with success."""
        threads = [Mock(), Mock()]
        _display_summary(threads, 2, 0, [], "resolve", "resolved", 123, False)

        # Should output JSON
        mock_echo.assert_called_once()
        output = json.loads(mock_echo.call_args[0][0])
        assert output["pr_number"] == 123
        assert output["action"] == "resolve"
        assert output["threads_processed"] == 2
        assert output["threads_succeeded"] == 2
        assert output["threads_failed"] == 0
        assert output["success"] is True

    @patch("toady.commands.resolve.click.echo")
    def test_display_summary_json_with_failures(self, mock_echo):
        """Test summary display in JSON mode with failures."""
        threads = [Mock()]
        failed_threads = [{"thread_id": "t1", "error": "Failed"}]
        _display_summary(
            threads, 0, 1, failed_threads, "unresolve", "unresolved", 456, False
        )

        output = json.loads(mock_echo.call_args[0][0])
        assert output["success"] is False
        assert output["failed_threads"] == failed_threads


class TestGetActionLabels:
    """Test action label generation."""

    def test_get_action_labels_resolve(self):
        """Test action labels for resolve operation."""
        action, action_past, action_present, action_symbol = _get_action_labels(False)
        assert action == "resolve"
        assert action_past == "resolved"
        assert action_present == "Resolving"
        assert action_symbol == "🔒"

    def test_get_action_labels_unresolve(self):
        """Test action labels for unresolve operation."""
        action, action_past, action_present, action_symbol = _get_action_labels(True)
        assert action == "unresolve"
        assert action_past == "unresolved"
        assert action_present == "Unresolving"
        assert action_symbol == "🔓"


class TestHandleEmptyThreads:
    """Test empty threads handling."""

    @patch("toady.commands.resolve.click.echo")
    def test_handle_empty_threads_pretty_resolve(self, mock_echo):
        """Test empty threads handling in pretty mode for resolve."""
        _handle_empty_threads(123, "resolve", False, True)
        mock_echo.assert_called_once_with("✅ No unresolved threads found in PR #123")

    @patch("toady.commands.resolve.click.echo")
    def test_handle_empty_threads_pretty_unresolve(self, mock_echo):
        """Test empty threads handling in pretty mode for unresolve."""
        _handle_empty_threads(456, "unresolve", True, True)
        mock_echo.assert_called_once_with("✅ No resolved threads found in PR #456")

    @patch("toady.commands.resolve.click.echo")
    def test_handle_empty_threads_json_resolve(self, mock_echo):
        """Test empty threads handling in JSON mode for resolve."""
        _handle_empty_threads(123, "resolve", False, False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output["pr_number"] == 123
        assert output["action"] == "resolve"
        assert output["threads_processed"] == 0
        assert output["success"] is True
        assert output["message"] == "No unresolved threads found"

    @patch("toady.commands.resolve.click.echo")
    def test_handle_empty_threads_json_unresolve(self, mock_echo):
        """Test empty threads handling in JSON mode for unresolve."""
        _handle_empty_threads(456, "unresolve", True, False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output["message"] == "No resolved threads found"


class TestHandleBulkResolveError:
    """Test bulk resolve error handling."""

    @patch("toady.commands.resolve.click.echo")
    def test_handle_fetch_service_error_pretty(self, mock_echo):
        """Test FetchServiceError handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = FetchServiceError("Fetch failed")

        with pytest.raises(SystemExit):
            _handle_bulk_resolve_error(ctx, error, 123, "resolve", True)

        mock_echo.assert_called_with(
            "❌ Failed to fetch threads: Fetch failed", err=True
        )
        ctx.exit.assert_called_once_with(1)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_fetch_service_error_json(self, mock_echo):
        """Test FetchServiceError handling in JSON mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = FetchServiceError("Fetch failed")

        with pytest.raises(SystemExit):
            _handle_bulk_resolve_error(ctx, error, 123, "resolve", False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output["error"] == "fetch_failed"
        assert output["error_message"] == "Fetch failed"

    @patch("toady.commands.resolve.click.echo")
    def test_handle_authentication_error_pretty(self, mock_echo):
        """Test GitHubAuthenticationError handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = GitHubAuthenticationError("Auth failed")

        with pytest.raises(SystemExit):
            _handle_bulk_resolve_error(ctx, error, 123, "resolve", True)

        calls = [
            str(call.args[0]) if call.args else str(call)
            for call in mock_echo.call_args_list
        ]
        assert any(
            "❌ Authentication failed: [GITHUB_AUTHENTICATION_ERROR] Auth failed"
            in call
            for call in calls
        )
        assert any("💡 Try running: gh auth login" in call for call in calls)

    def test_handle_click_exit_exception(self):
        """Test that Click Exit exceptions are re-raised."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = click.exceptions.Exit(5)

        with pytest.raises(SystemExit):
            _handle_bulk_resolve_error(ctx, error, 123, "resolve", True)

        # The function should call ctx.exit(5) to re-raise the exit
        ctx.exit.assert_called_once_with(5)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_unexpected_error_pretty(self, mock_echo):
        """Test unexpected error handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = ValueError("Unexpected error")

        with pytest.raises(SystemExit):
            _handle_bulk_resolve_error(ctx, error, 123, "resolve", True)

        mock_echo.assert_called_with(
            "❌ Unexpected error during bulk resolve: Unexpected error", err=True
        )
        ctx.exit.assert_called_once_with(1)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_unexpected_error_json(self, mock_echo):
        """Test unexpected error handling in JSON mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = ValueError("Unexpected error")

        with pytest.raises(SystemExit):
            _handle_bulk_resolve_error(ctx, error, 123, "resolve", False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output["error"] == "internal_error"
        assert output["error_message"] == "Unexpected error"


class TestShowSingleResolveProgress:
    """Test single resolve progress display."""

    @patch("toady.commands.resolve.click.echo")
    def test_show_progress_resolve_pretty(self, mock_echo):
        """Test progress display for resolve in pretty mode."""
        _show_single_resolve_progress("thread123", False, True)
        mock_echo.assert_called_once_with("🔒 Resolving thread thread123")

    @patch("toady.commands.resolve.click.echo")
    def test_show_progress_unresolve_pretty(self, mock_echo):
        """Test progress display for unresolve in pretty mode."""
        _show_single_resolve_progress("thread123", True, True)
        mock_echo.assert_called_once_with("🔓 Unresolving thread thread123")

    @patch("toady.commands.resolve.click.echo")
    def test_show_progress_no_pretty(self, mock_echo):
        """Test no progress display when pretty=False."""
        _show_single_resolve_progress("thread123", False, False)
        mock_echo.assert_not_called()


class TestHandleSingleResolveSuccess:
    """Test single resolve success handling."""

    @patch("toady.commands.resolve.click.echo")
    def test_handle_success_resolve_pretty(self, mock_echo):
        """Test success handling for resolve in pretty mode."""
        result = {
            "thread_id": "thread123",
            "action": "resolve",
            "success": True,
            "thread_url": "https://github.com/test/repo/pull/1#discussion_r123",
        }
        _handle_single_resolve_success(result, False, True)

        calls = [call[0][0] for call in mock_echo.call_args_list]
        assert any("✅ Thread resolved successfully" in call for call in calls)
        assert any("🔗 View thread at:" in call for call in calls)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_success_unresolve_pretty(self, mock_echo):
        """Test success handling for unresolve in pretty mode."""
        result = {"thread_id": "thread123", "action": "unresolve", "success": True}
        _handle_single_resolve_success(result, True, True)

        mock_echo.assert_called_once_with("✅ Thread unresolved successfully")

    @patch("toady.commands.resolve.click.echo")
    def test_handle_success_json_mode(self, mock_echo):
        """Test success handling in JSON mode."""
        result = {"thread_id": "thread123", "action": "resolve", "success": True}
        _handle_single_resolve_success(result, False, False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output == result


class TestHandleSingleResolveError:
    """Test single resolve error handling."""

    @patch("toady.commands.resolve.click.echo")
    def test_handle_thread_not_found_error_pretty(self, mock_echo):
        """Test ThreadNotFoundError handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = ThreadNotFoundError("Thread not found")

        with pytest.raises(SystemExit):
            _handle_single_resolve_error(ctx, error, "thread123", False, True)

        mock_echo.assert_called_with(
            "❌ Thread not found: [THREAD_NOT_FOUND] Thread not found", err=True
        )
        ctx.exit.assert_called_once_with(1)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_thread_not_found_error_json(self, mock_echo):
        """Test ThreadNotFoundError handling in JSON mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = ThreadNotFoundError("Thread not found")

        with pytest.raises(SystemExit):
            _handle_single_resolve_error(ctx, error, "thread123", False, False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output["error"] == "thread_not_found"
        assert output["thread_id"] == "thread123"
        assert output["action"] == "resolve"

    @patch("toady.commands.resolve.click.echo")
    def test_handle_permission_error_pretty(self, mock_echo):
        """Test ThreadPermissionError handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = ThreadPermissionError("Permission denied")

        with pytest.raises(SystemExit):
            _handle_single_resolve_error(ctx, error, "thread123", False, True)

        calls = [
            str(call.args[0]) if call.args else str(call)
            for call in mock_echo.call_args_list
        ]
        assert any(
            "❌ Permission denied: [GITHUB_PERMISSION_ERROR] Permission denied" in call
            for call in calls
        )
        assert any("💡 Ensure you have write access" in call for call in calls)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_authentication_error_pretty(self, mock_echo):
        """Test GitHubAuthenticationError handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = GitHubAuthenticationError("Auth failed")

        with pytest.raises(SystemExit):
            _handle_single_resolve_error(ctx, error, "thread123", False, True)

        calls = [
            str(call.args[0]) if call.args else str(call)
            for call in mock_echo.call_args_list
        ]
        assert any(
            "❌ Authentication failed: [GITHUB_AUTHENTICATION_ERROR] Auth failed"
            in call
            for call in calls
        )
        assert any("💡 Try running: gh auth login" in call for call in calls)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_resolve_service_error_pretty(self, mock_echo):
        """Test ResolveServiceError handling in pretty mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = ResolveServiceError("Service error")

        with pytest.raises(SystemExit):
            _handle_single_resolve_error(ctx, error, "thread123", False, True)

        mock_echo.assert_called_with(
            "❌ Failed to resolve thread: [RESOLVE_SERVICE_ERROR] Service error",
            err=True,
        )
        ctx.exit.assert_called_once_with(1)

    @patch("toady.commands.resolve.click.echo")
    def test_handle_github_api_error_json(self, mock_echo):
        """Test GitHubAPIError handling in JSON mode."""
        ctx = Mock()
        ctx.exit.side_effect = SystemExit
        error = GitHubAPIError("API error")

        with pytest.raises(SystemExit):
            _handle_single_resolve_error(ctx, error, "thread123", True, False)

        output = json.loads(mock_echo.call_args[0][0])
        assert output["error"] == "api_error"
        assert output["action"] == "unresolve"


class TestHandleSingleResolve:
    """Test single resolve handling integration."""

    @patch("toady.commands.resolve._validate_and_prepare_thread_id")
    @patch("toady.commands.resolve._show_single_resolve_progress")
    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve._handle_single_resolve_success")
    def test_handle_single_resolve_success_flow(
        self,
        mock_handle_success,
        mock_service_class,
        mock_show_progress,
        mock_validate_id,
    ):
        """Test successful single resolve flow."""
        ctx = Mock()
        mock_validate_id.return_value = "clean_thread_id"
        mock_service = Mock()
        mock_result = {"thread_id": "clean_thread_id", "success": True}
        mock_service.resolve_thread.return_value = mock_result
        mock_service_class.return_value = mock_service

        _handle_single_resolve(ctx, "  thread_id  ", False, True)

        mock_validate_id.assert_called_once_with("  thread_id  ")
        mock_show_progress.assert_called_once_with("clean_thread_id", False, True)
        mock_service.resolve_thread.assert_called_once_with("clean_thread_id")
        mock_handle_success.assert_called_once_with(mock_result, False, True)

    @patch("toady.commands.resolve._validate_and_prepare_thread_id")
    @patch("toady.commands.resolve._show_single_resolve_progress")
    @patch("toady.commands.resolve.ResolveService")
    @patch("toady.commands.resolve._handle_single_resolve_error")
    def test_handle_single_resolve_error_flow(
        self,
        mock_handle_error,
        mock_service_class,
        mock_show_progress,
        mock_validate_id,
    ):
        """Test error handling in single resolve flow."""
        ctx = Mock()
        mock_validate_id.return_value = "clean_thread_id"
        mock_service = Mock()
        mock_error = ResolveServiceError("Service error")
        mock_service.unresolve_thread.side_effect = mock_error
        mock_service_class.return_value = mock_service

        _handle_single_resolve(ctx, "thread_id", True, False)

        mock_service.unresolve_thread.assert_called_once_with("clean_thread_id")
        mock_handle_error.assert_called_once_with(
            ctx, mock_error, "clean_thread_id", True, False
        )


class TestHandleBulkResolve:
    """Test bulk resolve handling integration."""

    @patch("toady.commands.resolve._fetch_and_filter_threads")
    @patch("toady.commands.resolve._handle_empty_threads")
    def test_handle_bulk_resolve_empty_threads(self, mock_handle_empty, mock_fetch):
        """Test bulk resolve with no threads found."""
        ctx = Mock()
        mock_fetch.return_value = []

        _handle_bulk_resolve(ctx, 123, False, False, True, 100)

        mock_fetch.assert_called_once_with(123, False, True, 100)
        mock_handle_empty.assert_called_once_with(123, "resolve", False, True)

    @patch("toady.commands.resolve._fetch_and_filter_threads")
    @patch("toady.commands.resolve._handle_confirmation_prompt")
    @patch("toady.commands.resolve._process_threads")
    @patch("toady.commands.resolve._display_summary")
    def test_handle_bulk_resolve_success_flow(
        self, mock_display, mock_process, mock_confirm, mock_fetch
    ):
        """Test successful bulk resolve flow."""
        ctx = Mock()
        mock_threads = [Mock(thread_id="t1"), Mock(thread_id="t2")]
        mock_fetch.return_value = mock_threads
        mock_process.return_value = (2, 0, [])  # succeeded, failed, failed_threads

        _handle_bulk_resolve(ctx, 123, False, True, False, 100)

        mock_fetch.assert_called_once_with(123, False, False, 100)
        mock_confirm.assert_called_once_with(
            ctx, mock_threads, "resolve", "🔒", 123, True, False
        )
        mock_process.assert_called_once_with(
            mock_threads, False, "Resolving", "🔒", False
        )
        mock_display.assert_called_once_with(
            mock_threads, 2, 0, [], "resolve", "resolved", 123, False
        )

    @patch("toady.commands.resolve._fetch_and_filter_threads")
    @patch("toady.commands.resolve._handle_confirmation_prompt")
    @patch("toady.commands.resolve._process_threads")
    @patch("toady.commands.resolve._display_summary")
    def test_handle_bulk_resolve_with_failures(
        self, mock_display, mock_process, mock_confirm, mock_fetch
    ):
        """Test bulk resolve with some failures."""
        ctx = Mock()
        mock_threads = [Mock(thread_id="t1")]
        mock_fetch.return_value = mock_threads
        mock_process.return_value = (0, 1, [{"thread_id": "t1", "error": "Failed"}])

        _handle_bulk_resolve(ctx, 123, False, False, False, 100)

        # Should exit with error code when there are failures
        ctx.exit.assert_called_once_with(1)

    @patch("toady.commands.resolve._fetch_and_filter_threads")
    @patch("toady.commands.resolve._handle_bulk_resolve_error")
    def test_handle_bulk_resolve_exception_handling(
        self, mock_handle_error, mock_fetch
    ):
        """Test bulk resolve exception handling."""
        ctx = Mock()
        mock_error = FetchServiceError("Fetch failed")
        mock_fetch.side_effect = mock_error

        _handle_bulk_resolve(ctx, 123, False, False, False, 100)

        mock_handle_error.assert_called_once_with(
            ctx, mock_error, 123, "resolve", False
        )


class TestResolveCommandIntegration:
    """Test resolve command integration with CLI."""

    @patch("toady.commands.resolve.resolve_format_from_options")
    @patch("toady.commands.resolve._validate_resolve_parameters")
    @patch("toady.commands.resolve._handle_single_resolve")
    def test_resolve_command_single_thread_flow(
        self, mock_handle_single, mock_validate, mock_resolve_format, runner
    ):
        """Test resolve command single thread flow."""
        mock_resolve_format.return_value = "json"

        runner.invoke(cli, ["resolve", "--thread-id", "thread123"])

        mock_resolve_format.assert_called_once_with(None, False)
        mock_validate.assert_called_once_with(False, "thread123", None, 100)
        mock_handle_single.assert_called_once()

    @patch("toady.commands.resolve.resolve_format_from_options")
    @patch("toady.commands.resolve._validate_resolve_parameters")
    @patch("toady.commands.resolve._handle_bulk_resolve")
    def test_resolve_command_bulk_flow(
        self, mock_handle_bulk, mock_validate, mock_resolve_format, runner
    ):
        """Test resolve command bulk flow."""
        mock_resolve_format.return_value = "pretty"

        runner.invoke(cli, ["resolve", "--all", "--pr", "123", "--pretty"])

        mock_resolve_format.assert_called_once_with(None, True)
        mock_validate.assert_called_once_with(True, None, 123, 100)
        mock_handle_bulk.assert_called_once()

    def test_resolve_command_validation_error(self, runner):
        """Test resolve command validation error handling."""
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert "Must specify either --thread-id or --all" in result.output

    @patch("toady.commands.resolve.resolve_format_from_options")
    def test_resolve_command_format_error(self, mock_resolve_format, runner):
        """Test resolve command format resolution error."""
        mock_resolve_format.side_effect = ValueError("Format error")

        result = runner.invoke(cli, ["resolve", "--thread-id", "thread123"])
        assert result.exit_code == 1
        assert "Error: Format error" in result.output


class TestResolveCommandParameterCombinations:
    """Test various parameter combinations in the resolve command."""

    @patch("toady.commands.resolve.resolve_format_from_options")
    @patch("toady.commands.resolve._validate_resolve_parameters")
    @patch("toady.commands.resolve._handle_single_resolve")
    def test_all_single_parameters_combination(
        self, mock_handle_single, mock_validate, mock_resolve_format, runner
    ):
        """Test resolve command with all single thread parameters."""
        mock_resolve_format.return_value = "pretty"

        runner.invoke(
            cli,
            [
                "resolve",
                "--thread-id",
                "thread123",
                "--undo",
                "--format",
                "pretty",
                "--pretty",
            ],
        )

        mock_resolve_format.assert_called_once_with("pretty", True)
        mock_validate.assert_called_once_with(False, "thread123", None, 100)

    @patch("toady.commands.resolve.resolve_format_from_options")
    @patch("toady.commands.resolve._validate_resolve_parameters")
    @patch("toady.commands.resolve._handle_bulk_resolve")
    def test_all_bulk_parameters_combination(
        self, mock_handle_bulk, mock_validate, mock_resolve_format, runner
    ):
        """Test resolve command with all bulk parameters."""
        mock_resolve_format.return_value = "json"

        runner.invoke(
            cli,
            [
                "resolve",
                "--all",
                "--pr",
                "456",
                "--undo",
                "--yes",
                "--limit",
                "200",
            ],
        )

        mock_resolve_format.assert_called_once_with(None, False)
        mock_validate.assert_called_once_with(True, None, 456, 200)

    def test_boundary_limit_values(self, runner):
        """Test resolve command with boundary limit values."""
        # Test with limit 1
        result = runner.invoke(cli, ["resolve", "--all", "--pr", "123", "--limit", "1"])
        # Should not fail on limit validation

        # Test with limit 1000 (max)
        result = runner.invoke(
            cli, ["resolve", "--all", "--pr", "123", "--limit", "1000"]
        )
        # Should not fail on limit validation

        # Test with limit over 1000
        result = runner.invoke(
            cli, ["resolve", "--all", "--pr", "123", "--limit", "1001"]
        )
        assert result.exit_code != 0
        assert "Limit cannot exceed 1000" in result.output


@pytest.fixture(scope="module")
def runner():
    """Create a Click CLI test runner for the module."""
    return CliRunner()
