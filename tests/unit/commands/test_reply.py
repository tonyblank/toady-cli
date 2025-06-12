"""Unit tests for the reply command module.

This module tests the core reply command logic, including parameter validation,
error handling, format resolution, and service integration. It focuses on unit
testing the command implementation without testing the CLI interface directly.
"""

import json
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner

from toady.cli import cli
from toady.commands.reply import (
    _build_json_reply,
    _handle_reply_error,
    _print_pretty_reply,
    _show_id_help,
    _show_progress,
    _show_warnings,
    _validate_reply_args,
    reply,
    validate_reply_target_id,
)
from toady.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from toady.services.reply_service import (
    CommentNotFoundError,
    ReplyRequest,
    ReplyServiceError,
)


class TestReplyCommandCore:
    """Test the core reply command functionality."""

    def test_reply_command_exists(self):
        """Test that the reply command is properly defined."""
        assert reply is not None
        assert callable(reply)
        assert hasattr(reply, "params")

    def test_reply_command_parameters(self):
        """Test that reply command has expected parameters."""
        param_names = [param.name for param in reply.params]
        expected_params = ["id", "body", "format", "pretty", "verbose", "help_ids"]

        for expected_param in expected_params:
            assert expected_param in param_names, f"Missing parameter: {expected_param}"

    def test_reply_command_defaults(self):
        """Test reply command parameter defaults."""
        param_defaults = {param.name: param.default for param in reply.params}

        assert param_defaults["id"] is None
        assert param_defaults["body"] is None
        assert param_defaults["format"] is None
        assert param_defaults["pretty"] is False
        assert param_defaults["verbose"] is False
        assert param_defaults["help_ids"] is False


class TestValidateReplyTargetId:
    """Test the validate_reply_target_id function."""

    @patch("toady.commands.reply.create_universal_validator")
    def test_valid_numeric_id(self, mock_create_validator):
        """Test validation of valid numeric ID."""
        mock_validator = Mock()
        mock_validator.validate_id.return_value = Mock(value="numeric")
        mock_create_validator.return_value = mock_validator

        result = validate_reply_target_id("123456789")
        assert result == "123456789"
        mock_validator.validate_id.assert_called_once_with(
            "123456789", "Reply target ID"
        )

    @patch("toady.commands.reply.create_universal_validator")
    def test_valid_node_id(self, mock_create_validator):
        """Test validation of valid node ID."""
        mock_validator = Mock()
        mock_validator.validate_id.return_value = Mock(value="IC_")
        mock_create_validator.return_value = mock_validator

        result = validate_reply_target_id("IC_kwDOABcD12MAAAABcDE3fg")
        assert result == "IC_kwDOABcD12MAAAABcDE3fg"

    @patch("toady.commands.reply.create_universal_validator")
    def test_valid_thread_id(self, mock_create_validator):
        """Test validation of valid thread ID."""
        mock_validator = Mock()
        mock_validator.validate_id.return_value = Mock(value="RT_")
        mock_create_validator.return_value = mock_validator

        result = validate_reply_target_id("RT_kwDOABcD12MAAAABcDE3fg")
        assert result == "RT_kwDOABcD12MAAAABcDE3fg"

    def test_empty_id_error(self):
        """Test validation error for empty ID."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_reply_target_id("")
        assert "Reply target ID cannot be empty" in str(exc_info.value)

    def test_whitespace_id_error(self):
        """Test validation error for whitespace-only ID."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_reply_target_id("   ")
        assert "Reply target ID cannot be empty" in str(exc_info.value)

    @patch("toady.commands.reply.create_universal_validator")
    def test_prrc_id_error(self, mock_create_validator):
        """Test special error handling for PRRC_ IDs."""
        mock_validator = Mock()
        mock_validator.validate_id.return_value = Mock(value="PRRC_")
        mock_create_validator.return_value = mock_validator

        with pytest.raises(click.BadParameter) as exc_info:
            validate_reply_target_id("PRRC_kwDOABcD12MAAAABcDE3fg")

        error_msg = str(exc_info.value)
        assert "Individual comment IDs from submitted reviews (PRRC_)" in error_msg
        assert "Use the thread ID instead" in error_msg
        assert "toady reply --help-ids" in error_msg

    @patch("toady.commands.reply.create_universal_validator")
    def test_invalid_format_error_enhancement(self, mock_create_validator):
        """Test error message enhancement for invalid format."""
        mock_validator = Mock()
        mock_validator.validate_id.side_effect = ValueError("must start with one of")
        mock_create_validator.return_value = mock_validator

        with pytest.raises(click.BadParameter) as exc_info:
            validate_reply_target_id("invalid123")

        error_msg = str(exc_info.value)
        assert "must start with one of" in error_msg
        assert "Common ID types for replies" in error_msg
        assert "Thread IDs: PRRT_, PRT_, RT_" in error_msg
        assert "toady reply --help-ids" in error_msg

    @patch("toady.commands.reply.create_universal_validator")
    def test_other_validation_error_enhancement(self, mock_create_validator):
        """Test error message enhancement for other validation errors."""
        mock_validator = Mock()
        mock_validator.validate_id.side_effect = ValueError("appears too short")
        mock_create_validator.return_value = mock_validator

        with pytest.raises(click.BadParameter) as exc_info:
            validate_reply_target_id("IC_abc")

        error_msg = str(exc_info.value)
        assert "appears too short" in error_msg
        assert "toady reply --help-ids" in error_msg


class TestValidateReplyArgs:
    """Test the _validate_reply_args function."""

    @patch("toady.commands.reply.validate_reply_target_id")
    def test_valid_args(self, mock_validate_id):
        """Test validation of valid arguments."""
        mock_validate_id.return_value = "123456789"

        reply_id, body = _validate_reply_args("123456789", "Valid reply message")

        assert reply_id == "123456789"
        assert body == "Valid reply message"
        mock_validate_id.assert_called_once_with("123456789")

    @patch("toady.commands.reply.validate_reply_target_id")
    def test_body_whitespace_trimming(self, mock_validate_id):
        """Test that body whitespace is trimmed."""
        mock_validate_id.return_value = "123456789"

        reply_id, body = _validate_reply_args("123456789", "  Valid reply message  ")

        assert body == "Valid reply message"

    def test_empty_body_error(self):
        """Test validation error for empty body."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_reply_args("123456789", "")
        assert "Reply body cannot be empty" in str(exc_info.value)

    def test_whitespace_only_body_error(self):
        """Test validation error for whitespace-only body."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_reply_args("123456789", "   ")
        assert "Reply body cannot be empty" in str(exc_info.value)

    def test_body_too_long_error(self):
        """Test validation error for body exceeding maximum length."""
        long_body = "x" * 65537
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_reply_args("123456789", long_body)
        assert "Reply body cannot exceed 65,536 characters" in str(exc_info.value)

    def test_body_at_maximum_length(self):
        """Test validation of body at maximum length."""
        max_body = "x" * 65536
        with patch("toady.commands.reply.validate_reply_target_id") as mock_validate_id:
            mock_validate_id.return_value = "123456789"
            reply_id, body = _validate_reply_args("123456789", max_body)
            assert len(body) == 65536

    def test_body_too_short_error(self):
        """Test validation error for body too short."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_reply_args("123456789", "ab")
        assert "Reply body must be at least 3 characters long" in str(exc_info.value)

    def test_short_placeholder_text_error(self):
        """Test validation error for short placeholder text.

        Hits length check first.
        """
        # These hit the length check before the placeholder check
        short_placeholders = [".", "..", "!!", "!?"]

        for placeholder in short_placeholders:
            with pytest.raises(click.BadParameter) as exc_info:
                _validate_reply_args("123456789", placeholder)
            assert "Reply body must be at least 3 characters long" in str(
                exc_info.value
            )

    def test_placeholder_text_error(self):
        """Test validation error for placeholder text."""
        # Only test placeholder texts that are 3+ characters
        # (length check comes first)
        # From the actual implementation:
        # [".", "..", "...", "????", "???", "!!", "!?", "???"]
        placeholder_texts = ["...", "????", "???"]  # The 3+ character ones

        for placeholder in placeholder_texts:
            with pytest.raises(click.BadParameter) as exc_info:
                _validate_reply_args("123456789", placeholder)
            assert "Reply body appears to be placeholder text" in str(exc_info.value)

    def test_insufficient_non_whitespace_error(self):
        """Test validation error for insufficient non-whitespace characters."""
        with pytest.raises(click.BadParameter) as exc_info:
            _validate_reply_args("123456789", "a  \n\t  b")
        assert "Reply body must contain at least 3 non-whitespace characters" in str(
            exc_info.value
        )


class TestPrintPrettyReply:
    """Test the _print_pretty_reply function."""

    def test_basic_reply_info(self, capsys):
        """Test printing basic reply information."""
        reply_info = {
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "reply_id": "987654321",
        }

        _print_pretty_reply(reply_info, verbose=False)

        captured = capsys.readouterr()
        assert "✅ Reply posted successfully" in captured.out
        assert "🔗 View reply at: https://github.com/owner/repo/pull/1" in captured.out
        assert "📝 Reply ID: 987654321" in captured.out

    def test_reply_url_fragment_stripping(self, capsys):
        """Test that URL fragments are stripped for display."""
        reply_info = {
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321"
        }

        _print_pretty_reply(reply_info, verbose=False)

        captured = capsys.readouterr()
        assert "🔗 View reply at: https://github.com/owner/repo/pull/1" in captured.out
        assert "#discussion_r" not in captured.out

    def test_verbose_reply_info(self, capsys):
        """Test printing verbose reply information."""
        reply_info = {
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "reply_id": "987654321",
            "pr_number": "42",
            "pr_title": "Add awesome feature",
            "parent_comment_author": "reviewer123",
            "body_preview": "This is a test reply...",
            "thread_url": "https://github.com/owner/repo/pull/42#pullrequestreview-123456",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }

        _print_pretty_reply(reply_info, verbose=True)

        captured = capsys.readouterr()
        assert "📋 Reply Details:" in captured.out
        assert "Pull Request: #42 - Add awesome feature" in captured.out
        assert "Replying to: @reviewer123" in captured.out
        assert "Your reply: This is a test reply..." in captured.out
        assert (
            "Thread URL: https://github.com/owner/repo/pull/42#pullrequestreview-123456"
            in captured.out
        )
        assert "Posted at: 2023-01-01T12:00:00Z" in captured.out
        assert "Posted by: @testuser" in captured.out

    def test_minimal_reply_info(self, capsys):
        """Test printing with minimal reply information."""
        reply_info = {}

        _print_pretty_reply(reply_info, verbose=False)

        captured = capsys.readouterr()
        assert "✅ Reply posted successfully" in captured.out
        # Should not show empty fields
        assert "🔗 View reply at:" not in captured.out
        assert "📝 Reply ID:" not in captured.out


class TestBuildJsonReply:
    """Test the _build_json_reply function."""

    def test_basic_json_reply(self):
        """Test building basic JSON reply."""
        reply_info = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }

        result = _build_json_reply("123456789", reply_info, verbose=False)

        assert result["id"] == "123456789"
        assert result["success"] is True
        assert result["reply_posted"] is True
        assert result["reply_id"] == "987654321"
        assert (
            result["reply_url"]
            == "https://github.com/owner/repo/pull/1#discussion_r987654321"
        )
        assert result["created_at"] == "2023-01-01T12:00:00Z"
        assert result["author"] == "testuser"

    def test_verbose_json_reply(self):
        """Test building verbose JSON reply."""
        reply_info = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
            "pr_number": "42",
            "pr_title": "Add awesome feature",
            "parent_comment_author": "reviewer123",
            "body_preview": "Test reply",
            "thread_url": "https://github.com/owner/repo/pull/42#pullrequestreview-123456",
            "review_id": "123456",
        }

        result = _build_json_reply(
            "IC_kwDOABcD12MAAAABcDE3fg", reply_info, verbose=True
        )

        assert result["verbose"] is True
        assert result["pr_number"] == "42"
        assert result["pr_title"] == "Add awesome feature"
        assert result["parent_comment_author"] == "reviewer123"
        assert result["body_preview"] == "Test reply"
        assert (
            result["thread_url"]
            == "https://github.com/owner/repo/pull/42#pullrequestreview-123456"
        )
        assert result["review_id"] == "123456"

    def test_optional_fields_handling(self):
        """Test handling of optional fields in JSON reply."""
        reply_info = {
            "reply_id": "987654321",
            "pr_number": "",  # Empty field should not be included
            "pr_title": None,  # None field should not be included
            "parent_comment_author": "reviewer",  # Non-empty field should be included
        }

        result = _build_json_reply("123456789", reply_info, verbose=False)

        assert "pr_number" not in result
        assert "pr_title" not in result
        assert result["parent_comment_author"] == "reviewer"

    def test_minimal_json_reply(self):
        """Test building JSON reply with minimal information."""
        reply_info = {}

        result = _build_json_reply("123456789", reply_info, verbose=False)

        assert result["id"] == "123456789"
        assert result["success"] is True
        assert result["reply_posted"] is True
        assert result["reply_id"] == ""
        assert result["reply_url"] == ""
        assert result["created_at"] == ""
        assert result["author"] == ""


class TestShowWarnings:
    """Test the _show_warnings function."""

    def test_mention_warning_pretty_mode(self, capsys):
        """Test warning for replies starting with mention in pretty mode."""
        _show_warnings("@user thanks for the review!", pretty=True)

        captured = capsys.readouterr()
        assert (
            "⚠️  Note: Reply starts with '@' - this will mention users" in captured.err
        )

    def test_mention_warning_json_mode(self, capsys):
        """Test no warning for mentions in JSON mode."""
        _show_warnings("@user thanks for the review!", pretty=False)

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_repetitive_content_warning(self, capsys):
        """Test warning for repetitive content."""
        _show_warnings("aaaaaaaaaaaaa", pretty=True)

        captured = capsys.readouterr()
        assert "⚠️  Note: Reply contains very repetitive content" in captured.err

    def test_no_warnings_for_normal_content(self, capsys):
        """Test no warnings for normal content."""
        _show_warnings("This is a normal reply with good content", pretty=True)

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_repetitive_content_short_text(self, capsys):
        """Test no warning for short repetitive text."""
        _show_warnings("aaa", pretty=True)

        captured = capsys.readouterr()
        assert "repetitive content" not in captured.err


class TestShowProgress:
    """Test the _show_progress function."""

    def test_progress_pretty_mode(self, capsys):
        """Test progress messages in pretty mode."""
        _show_progress("123456789", "This is a test reply", pretty=True)

        captured = capsys.readouterr()
        assert "💬 Posting reply to 123456789" in captured.out
        assert "📝 Reply: This is a test reply" in captured.out

    def test_progress_json_mode(self, capsys):
        """Test no progress messages in JSON mode."""
        _show_progress("123456789", "This is a test reply", pretty=False)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_progress_long_body_truncation(self, capsys):
        """Test progress message with long body truncation."""
        long_body = "x" * 150
        _show_progress("123456789", long_body, pretty=True)

        captured = capsys.readouterr()
        assert "💬 Posting reply to 123456789" in captured.out
        assert "📝 Reply: " + "x" * 100 + "..." in captured.out

    def test_progress_short_body_no_truncation(self, capsys):
        """Test progress message with short body (no truncation)."""
        short_body = "Short reply"
        _show_progress("123456789", short_body, pretty=True)

        captured = capsys.readouterr()
        assert "📝 Reply: Short reply" in captured.out
        assert "..." not in captured.out


class TestShowIdHelp:
    """Test the _show_id_help function."""

    def test_id_help_content(self, capsys):
        """Test that ID help shows comprehensive content."""
        ctx = Mock()

        _show_id_help(ctx)

        captured = capsys.readouterr()
        assert "🎯 GitHub ID Types for Reply Command" in captured.out
        assert "SUPPORTED ID TYPES:" in captured.out
        assert "PRRT_kwDOABcD12MAAAABcDE3fg" in captured.out
        assert "NOT SUPPORTED:" in captured.out
        assert "PRRC_kwDOABcD12MAAAABcDE3fg" in captured.out
        assert "HOW TO FIND THE RIGHT ID:" in captured.out
        assert "toady fetch --pr <PR_NUMBER> --pretty" in captured.out
        assert "BEST PRACTICES:" in captured.out
        assert "EXAMPLES:" in captured.out
        assert "TROUBLESHOOTING:" in captured.out
        ctx.exit.assert_called_once_with(0)


class TestHandleReplyError:
    """Test the _handle_reply_error function."""

    def test_comment_not_found_error_pretty(self, capsys):
        """Test CommentNotFoundError handling in pretty mode."""
        ctx = Mock()
        error = CommentNotFoundError("Comment 999 not found in PR #1")

        _handle_reply_error(ctx, error, "999", pretty=True)

        captured = capsys.readouterr()
        assert "❌ Comment not found: Comment 999 not found in PR #1" in captured.err
        assert "💡 Possible causes:" in captured.err
        ctx.exit.assert_called_with(1)

    def test_comment_not_found_error_json(self, capsys):
        """Test CommentNotFoundError handling in JSON mode."""
        ctx = Mock()
        error = CommentNotFoundError("Comment 999 not found in PR #1")

        _handle_reply_error(ctx, error, "999", pretty=False)

        captured = capsys.readouterr()
        # Split by lines and take the first line which should be JSON
        lines = captured.err.strip().split("\n")
        output = json.loads(lines[0])
        assert output["success"] is False
        assert output["reply_posted"] is False
        assert output["error"] == "comment_not_found"
        assert "Comment 999 not found" in output["error_message"]
        # Note: ctx.exit is called multiple times due to implementation behavior
        assert ctx.exit.call_count >= 1

    def test_authentication_error_pretty(self, capsys):
        """Test GitHubAuthenticationError handling in pretty mode."""
        ctx = Mock()
        error = GitHubAuthenticationError("Authentication failed")

        _handle_reply_error(ctx, error, "123456789", pretty=True)

        captured = capsys.readouterr()
        assert "❌ Authentication failed: [GITHUB_AUTHENTICATION_ERROR]" in captured.err
        assert "💡 Try running: gh auth login" in captured.err
        ctx.exit.assert_called_with(1)

    def test_authentication_error_json(self, capsys):
        """Test GitHubAuthenticationError handling in JSON mode."""
        ctx = Mock()
        error = GitHubAuthenticationError("Authentication failed")

        _handle_reply_error(ctx, error, "123456789", pretty=False)

        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        output = json.loads(lines[0])
        assert output["error"] == "authentication_failed"
        assert "[GITHUB_AUTHENTICATION_ERROR]" in output["error_message"]
        assert ctx.exit.call_count >= 1

    def test_timeout_error_pretty(self, capsys):
        """Test GitHubTimeoutError handling in pretty mode."""
        ctx = Mock()
        error = GitHubTimeoutError("Request timed out")

        _handle_reply_error(ctx, error, "123456789", pretty=True)

        captured = capsys.readouterr()
        assert "❌ Request timed out: [GITHUB_TIMEOUT_ERROR]" in captured.err
        assert "💡 Try again in a moment" in captured.err
        ctx.exit.assert_called_with(1)

    def test_rate_limit_error_pretty(self, capsys):
        """Test GitHubRateLimitError handling in pretty mode."""
        ctx = Mock()
        error = GitHubRateLimitError("Rate limit exceeded")

        _handle_reply_error(ctx, error, "123456789", pretty=True)

        captured = capsys.readouterr()
        assert "❌ Rate limit exceeded: [GITHUB_RATE_LIMIT_ERROR]" in captured.err
        assert "💡 You've made too many requests" in captured.err
        ctx.exit.assert_called_with(1)

    def test_github_api_error_403_pretty(self, capsys):
        """Test GitHubAPIError 403 handling in pretty mode."""
        ctx = Mock()
        error = GitHubAPIError("403 Forbidden")

        _handle_reply_error(ctx, error, "123456789", pretty=True)

        captured = capsys.readouterr()
        assert "❌ Permission denied: [GITHUB_API_ERROR]" in captured.err
        assert "💡 Possible causes:" in captured.err
        ctx.exit.assert_called_with(1)

    def test_github_api_error_403_json(self, capsys):
        """Test GitHubAPIError 403 handling in JSON mode."""
        ctx = Mock()
        error = GitHubAPIError("403 Forbidden")

        _handle_reply_error(ctx, error, "123456789", pretty=False)

        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        output = json.loads(lines[0])
        assert output["error"] == "permission_denied"
        ctx.exit.assert_called_with(1)

    def test_github_api_error_general_pretty(self, capsys):
        """Test general GitHubAPIError handling in pretty mode."""
        ctx = Mock()
        error = GitHubAPIError("500 Internal Server Error")

        _handle_reply_error(ctx, error, "123456789", pretty=True)

        captured = capsys.readouterr()
        assert "❌ GitHub API error: [GITHUB_API_ERROR]" in captured.err
        assert "💡 This may be a temporary issue" in captured.err
        ctx.exit.assert_called_with(1)

    def test_reply_service_error_pretty(self, capsys):
        """Test ReplyServiceError handling in pretty mode."""
        ctx = Mock()
        error = ReplyServiceError("Service error")

        _handle_reply_error(ctx, error, "123456789", pretty=True)

        captured = capsys.readouterr()
        assert "❌ Failed to post reply: Service error" in captured.err
        assert "💡 This is likely a service error" in captured.err
        ctx.exit.assert_called_once_with(1)

    def test_reply_service_error_json(self, capsys):
        """Test ReplyServiceError handling in JSON mode."""
        ctx = Mock()
        error = ReplyServiceError("Service error")

        _handle_reply_error(ctx, error, "123456789", pretty=False)

        captured = capsys.readouterr()
        output = json.loads(captured.err)
        assert output["error"] == "api_error"
        assert output["error_message"] == "Service error"
        ctx.exit.assert_called_once_with(1)

    def test_unexpected_error_handling(self, capsys):
        """Test handling of unexpected errors."""
        ctx = Mock()
        error = ValueError("Unexpected error")

        _handle_reply_error(ctx, error, "123456789", pretty=False)

        captured = capsys.readouterr()
        output = json.loads(captured.err)
        assert output["error"] == "api_error"
        assert output["error_message"] == "Unexpected error"
        ctx.exit.assert_called_once_with(1)


class TestReplyCommandIntegration:
    """Test integration of reply command components."""

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_successful_reply_json_format(
        self, mock_resolve_format, mock_service_class, runner
    ):
        """Test successful reply with JSON format."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "json"

        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "Test reply"]
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["reply_posted"] is True
        assert output["reply_id"] == "987654321"

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_successful_reply_pretty_format(
        self, mock_resolve_format, mock_service_class, runner, capsys
    ):
        """Test successful reply with pretty format."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
        }
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "pretty"

        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "Test reply", "--pretty"]
        )

        assert result.exit_code == 0
        assert "✅ Reply posted successfully" in result.output

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_verbose_mode_integration(
        self, mock_resolve_format, mock_service_class, runner
    ):
        """Test verbose mode integration."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "pr_number": "42",
            "pr_title": "Test PR",
        }
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "json"

        runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "Test", "--verbose"]
        )

        # Verify that fetch_context=True was passed to the service
        fetch_context = mock_service.post_reply.call_args[1]["fetch_context"]
        assert fetch_context is True

    def test_missing_required_options(self, runner):
        """Test error handling for missing required options."""
        # Missing both options
        result = runner.invoke(cli, ["reply"])
        assert result.exit_code != 0
        assert "Missing option '--id'" in result.output

        # Missing body
        result = runner.invoke(cli, ["reply", "--id", "123"])
        assert result.exit_code != 0
        assert "Missing option '--body'" in result.output

        # Missing id
        result = runner.invoke(cli, ["reply", "--body", "test"])
        assert result.exit_code != 0
        assert "Missing option '--id'" in result.output

    def test_help_ids_flag(self, runner, capsys):
        """Test --help-ids flag integration."""
        result = runner.invoke(cli, ["reply", "--help-ids"])

        assert result.exit_code == 0
        assert "🎯 GitHub ID Types for Reply Command" in result.output

    @patch("toady.commands.reply.resolve_format_from_options")
    def test_format_resolution_error_handling(self, mock_resolve_format, runner):
        """Test format resolution error handling."""
        mock_resolve_format.side_effect = Exception("Format error")

        result = runner.invoke(cli, ["reply", "--id", "123", "--body", "test"])

        assert result.exit_code == 1
        assert "Error: Format error" in result.output

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_service_request_creation(
        self, mock_resolve_format, mock_service_class, runner
    ):
        """Test that ReplyRequest is created correctly."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {"reply_id": "123"}
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "json"

        runner.invoke(cli, ["reply", "--id", "123456789", "--body", "Test reply"])

        # Verify ReplyRequest was created with correct parameters
        request = mock_service.post_reply.call_args[0][0]
        assert isinstance(request, ReplyRequest)
        assert request.comment_id == "123456789"
        assert request.reply_body == "Test reply"

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_warning_display_integration(
        self, mock_resolve_format, mock_service_class, runner
    ):
        """Test warning display integration in pretty mode."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {"reply_id": "123"}
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "pretty"

        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "@user thanks", "--pretty"]
        )

        assert "⚠️  Note: Reply starts with '@'" in result.output

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_progress_display_integration(
        self, mock_resolve_format, mock_service_class, runner
    ):
        """Test progress display integration in pretty mode."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {"reply_id": "123"}
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "pretty"

        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "Test reply", "--pretty"]
        )

        assert "💬 Posting reply to 123456789" in result.output
        assert "📝 Reply: Test reply" in result.output


class TestReplyCommandEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_body_at_exact_limits(self, runner):
        """Test body validation at exact character limits."""
        # Test minimum valid length (3 characters)
        with patch("toady.commands.reply.ReplyService") as mock_service_class:
            mock_service = Mock()
            mock_service.post_reply.return_value = {"reply_id": "123"}
            mock_service_class.return_value = mock_service

            result = runner.invoke(cli, ["reply", "--id", "123456789", "--body", "abc"])
            assert result.exit_code == 0

        # Test maximum valid length (65536 characters)
        with patch("toady.commands.reply.ReplyService") as mock_service_class:
            mock_service = Mock()
            mock_service.post_reply.return_value = {"reply_id": "123"}
            mock_service_class.return_value = mock_service

            max_body = "x" * 65536
            result = runner.invoke(
                cli, ["reply", "--id", "123456789", "--body", max_body]
            )
            assert result.exit_code == 0

    def test_various_id_formats(self, runner):
        """Test various ID format validations."""
        test_cases = [
            ("0", False),  # Invalid: zero
            ("123456789012345678901", False),  # Invalid: too many digits
            ("IC_abc", False),  # Invalid: too short
            ("IC_" + "a" * 101, False),  # Invalid: too long
            ("IC_kwDO@#$%", False),  # Invalid: bad characters
            ("PRRC_kwDOABcD12MAAAABcDE3fg", False),  # Invalid: PRRC not allowed
            ("RT_kwDOABcD12MAAAABcDE3fg", True),  # Valid: thread ID
            ("123456789", True),  # Valid: numeric ID
        ]

        for test_id, should_succeed in test_cases:
            if should_succeed:
                with patch("toady.commands.reply.ReplyService") as mock_service_class:
                    mock_service = Mock()
                    mock_service.post_reply.return_value = {"reply_id": "123"}
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(
                        cli, ["reply", "--id", test_id, "--body", "test"]
                    )
                    assert result.exit_code == 0, f"Should succeed for ID: {test_id}"
            else:
                result = runner.invoke(
                    cli, ["reply", "--id", test_id, "--body", "test"]
                )
                assert result.exit_code != 0, f"Should fail for ID: {test_id}"

    def test_format_output_edge_cases(self):
        """Test format output with edge case data."""
        # Test with empty reply info
        result = _build_json_reply("123", {}, False)
        assert result["id"] == "123"
        assert result["reply_id"] == ""

        # Test with None values - the function uses .get() which returns None
        # when key exists with None
        reply_info = {"reply_id": None, "author": None}
        result = _build_json_reply("123", reply_info, False)
        # The function uses .get() which returns None if the key exists with None value
        assert result["reply_id"] is None
        assert result["author"] is None

    @patch("toady.commands.reply.ReplyService")
    @patch("toady.commands.reply.resolve_format_from_options")
    def test_unicode_body_handling(
        self, mock_resolve_format, mock_service_class, runner
    ):
        """Test handling of Unicode characters in reply body."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {"reply_id": "123"}
        mock_service_class.return_value = mock_service
        mock_resolve_format.return_value = "json"

        unicode_body = "Test with émojis 🎉 and spëcial characters"
        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", unicode_body]
        )

        assert result.exit_code == 0
        # Verify the Unicode body was passed correctly
        request = mock_service.post_reply.call_args[0][0]
        assert request.reply_body == unicode_body


@pytest.fixture(scope="module")
def runner():
    """Create a Click CLI test runner for the module."""
    return CliRunner()
