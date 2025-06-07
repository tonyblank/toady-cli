"""Tests for the CLI interface."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from toady import __version__
from toady.cli import cli


class TestCLI:
    """Test the main CLI interface."""

    def test_version(self, runner: CliRunner) -> None:
        """Test version display."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self, runner: CliRunner) -> None:
        """Test help display."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Toady - GitHub PR review management tool" in result.output
        assert "Commands:" in result.output


class TestFetchCommand:
    """Test the fetch command."""

    def test_fetch_requires_pr_option(self, runner: CliRunner) -> None:
        """Test that fetch requires --pr option."""
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code != 0
        assert "Missing option '--pr'" in result.output

    def test_fetch_with_pr_number(self, runner: CliRunner) -> None:
        """Test fetch with valid PR number."""
        result = runner.invoke(cli, ["fetch", "--pr", "123"])
        assert result.exit_code == 0
        assert "[]" in result.output

    def test_fetch_with_pretty_flag(self, runner: CliRunner) -> None:
        """Test fetch with pretty output format."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "🔍 Fetching unresolved threads for PR #123" in result.output
        assert "📝 Found 0 review threads" in result.output

    def test_fetch_with_resolved_flag(self, runner: CliRunner) -> None:
        """Test fetch with resolved threads included."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--resolved"])
        assert result.exit_code == 0
        assert "[]" in result.output

    def test_fetch_with_custom_limit(self, runner: CliRunner) -> None:
        """Test fetch with custom limit."""
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

    def test_fetch_all_options_combined(self, runner: CliRunner) -> None:
        """Test fetch with all options combined."""
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

    def test_fetch_default_limit(self, runner: CliRunner) -> None:
        """Test that fetch uses default limit when not specified."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "(limit: 100)" in result.output


class TestReplyCommand:
    """Test the reply command."""

    def test_reply_requires_options(self, runner: CliRunner) -> None:
        """Test that reply requires both comment-id and body options."""
        result = runner.invoke(cli, ["reply"])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_reply_requires_body(self, runner: CliRunner) -> None:
        """Test that reply requires --body option."""
        result = runner.invoke(cli, ["reply", "--comment-id", "123"])
        assert result.exit_code != 0
        assert "Missing option '--body'" in result.output

    def test_reply_requires_comment_id(self, runner: CliRunner) -> None:
        """Test that reply requires --comment-id option."""
        result = runner.invoke(cli, ["reply", "--body", "test"])
        assert result.exit_code != 0
        assert "Missing option '--comment-id'" in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_with_valid_numeric_id(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with valid numeric comment ID."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 0
        assert '"comment_id": "123456789"' in result.output
        assert '"reply_posted": true' in result.output
        assert '"reply_id": "987654321"' in result.output

        from toady.reply_service import ReplyRequest

        expected_request = ReplyRequest(comment_id="123456789", reply_body="Test reply")
        mock_service.post_reply.assert_called_once_with(expected_request)

    @patch("toady.cli.ReplyService")
    def test_reply_with_valid_node_id(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with valid GitHub node ID."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "IC_kwDOABcD12MAAAABcDE3fg",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            [
                "reply",
                "--comment-id",
                "IC_kwDOABcD12MAAAABcDE3fg",
                "--body",
                "Test reply",
            ],
        )
        assert result.exit_code == 0
        assert '"comment_id": "IC_kwDOABcD12MAAAABcDE3fg"' in result.output

        from toady.reply_service import ReplyRequest

        expected_request = ReplyRequest(
            comment_id="IC_kwDOABcD12MAAAABcDE3fg", reply_body="Test reply"
        )
        mock_service.post_reply.assert_called_once_with(expected_request)

    @patch("toady.cli.ReplyService")
    def test_reply_with_pretty_output(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with pretty output format."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            [
                "reply",
                "--comment-id",
                "123456789",
                "--body",
                "Test reply",
                "--pretty",
            ],
        )
        assert result.exit_code == 0
        assert "💬 Posting reply to comment 123456789" in result.output
        assert "✅ Reply posted successfully" in result.output
        assert "🔗 View reply at: https://github.com/owner/repo/pull/1" in result.output

    def test_reply_empty_comment_id(self, runner: CliRunner) -> None:
        """Test reply with empty comment ID."""
        result = runner.invoke(cli, ["reply", "--comment-id", "", "--body", "test"])
        assert result.exit_code != 0
        assert "Comment ID cannot be empty" in result.output

    def test_reply_whitespace_comment_id(self, runner: CliRunner) -> None:
        """Test reply with whitespace-only comment ID."""
        result = runner.invoke(cli, ["reply", "--comment-id", "   ", "--body", "test"])
        assert result.exit_code != 0
        assert "Comment ID cannot be empty" in result.output

    def test_reply_invalid_comment_id_format(self, runner: CliRunner) -> None:
        """Test reply with invalid comment ID format."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "invalid123", "--body", "test"]
        )
        assert result.exit_code != 0
        assert "Comment ID must be numeric" in result.output

    def test_reply_invalid_node_id_too_short(self, runner: CliRunner) -> None:
        """Test reply with too short node ID."""
        result = runner.invoke(cli, ["reply", "--comment-id", "IC_abc", "--body", "test"])
        assert result.exit_code != 0
        assert "GitHub node ID appears too short to be valid" in result.output

    def test_reply_empty_body(self, runner: CliRunner) -> None:
        """Test reply with empty body."""
        result = runner.invoke(cli, ["reply", "--comment-id", "123456789", "--body", ""])
        assert result.exit_code != 0
        assert "Reply body cannot be empty" in result.output

    def test_reply_whitespace_only_body(self, runner: CliRunner) -> None:
        """Test reply with whitespace-only body."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "   "]
        )
        assert result.exit_code != 0
        assert "Reply body cannot be empty" in result.output

    def test_reply_body_too_long(self, runner: CliRunner) -> None:
        """Test reply with body exceeding maximum length."""
        long_body = "x" * 65537  # One character over the limit
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", long_body]
        )
        assert result.exit_code != 0
        assert "Reply body cannot exceed 65,536 characters" in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_body_at_maximum_length(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with body at maximum length."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        max_body = "x" * 65536  # Exactly at the limit
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", max_body]
        )
        assert result.exit_code == 0

    @patch("toady.cli.ReplyService")
    def test_reply_body_with_mention_warning(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with body starting with @ shows warning."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service
        result = runner.invoke(
            cli,
            [
                "reply",
                "--comment-id",
                "123456789",
                "--body",
                "@user thanks!",
                "--pretty",
            ],
        )
        assert result.exit_code == 0
        assert "⚠️  Note: Reply starts with '@' - this will mention users" in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_body_with_mention_no_warning_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with @ mention doesn't show warning in JSON mode."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "@user thanks!"]
        )
        assert result.exit_code == 0
        assert "⚠️" not in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_long_body_truncation_in_pretty_mode(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test that long reply body is truncated in pretty output."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        long_body = "x" * 150  # Longer than 100 characters
        result = runner.invoke(
            cli,
            [
                "reply",
                "--comment-id",
                "123456789",
                "--body",
                long_body,
                "--pretty",
            ],
        )
        assert result.exit_code == 0
        assert "📝 Reply: " + "x" * 100 + "..." in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_various_comment_id_formats(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with various valid comment ID formats."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "test_id",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        test_cases = [
            "1",
            "123",
            "123456789",
            "IC_kwDOABcD12M",
            "IC_kwDOABcD12MAAAABcDE3fg",
        ]

        for comment_id in test_cases:
            result = runner.invoke(
                cli, ["reply", "--comment-id", comment_id, "--body", "test"]
            )
            assert result.exit_code == 0, f"Failed for comment ID: {comment_id}"

    def test_reply_invalid_comment_id_formats(self, runner: CliRunner) -> None:
        """Test reply with various invalid comment ID formats."""
        test_cases = [
            "abc123",  # Invalid: starts with letters
            "123abc",  # Invalid: ends with letters
            "PRT_123",  # Invalid: wrong prefix
            "IC_a",  # Invalid: too short node ID
            "12.34",  # Invalid: contains decimal
            "-123",  # Invalid: negative number
            "123 456",  # Invalid: contains space
        ]

        for comment_id in test_cases:
            result = runner.invoke(
                cli, ["reply", "--comment-id", comment_id, "--body", "test"]
            )
            assert (
                result.exit_code != 0
            ), f"Should have failed for comment ID: {comment_id}"

    @patch("toady.cli.ReplyService")
    def test_reply_json_output_structure(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test that JSON output has correct structure."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert "comment_id" in output
        assert "reply_posted" in output
        assert "reply_url" in output
        assert "reply_id" in output
        assert "created_at" in output
        assert "author" in output
        assert output["comment_id"] == "123456789"
        assert output["reply_posted"] is True
        assert output["reply_id"] == "987654321"
        assert output["author"] == "testuser"
        assert "https://github.com/" in output["reply_url"]

    def test_reply_help_content(self, runner: CliRunner) -> None:
        """Test reply command help content."""
        result = runner.invoke(cli, ["reply", "--help"])
        assert result.exit_code == 0
        assert "Post a reply to a specific review comment" in result.output
        assert "Examples:" in result.output
        assert "--comment-id" in result.output
        assert "--body" in result.output

    def test_reply_parameter_metavars(self, runner: CliRunner) -> None:
        """Test that parameter metavars are displayed correctly."""
        result = runner.invoke(cli, ["reply", "--help"])
        assert result.exit_code == 0
        assert "ID" in result.output  # metavar for comment-id
        assert "TEXT" in result.output  # metavar for body

    @patch("toady.cli.ReplyService")
    def test_reply_comment_not_found_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with comment not found error in pretty mode."""
        from toady.reply_service import CommentNotFoundError

        mock_service = Mock()
        mock_service.post_reply.side_effect = CommentNotFoundError(
            "Comment 999 not found in PR #1"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--comment-id", "999", "--body", "Test reply", "--pretty"]
        )
        assert result.exit_code == 1
        assert "❌ Comment not found: Comment 999 not found in PR #1" in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_comment_not_found_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with comment not found error in JSON mode."""
        from toady.reply_service import CommentNotFoundError

        mock_service = Mock()
        mock_service.post_reply.side_effect = CommentNotFoundError(
            "Comment 999 not found in PR #1"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--comment-id", "999", "--body", "Test reply"]
        )
        assert result.exit_code == 1

        import json

        output = json.loads(result.output)
        assert output["reply_posted"] is False
        assert output["error"] == "comment_not_found"
        assert "Comment 999 not found" in output["error_message"]

    @patch("toady.cli.ReplyService")
    def test_reply_authentication_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with authentication error in pretty mode."""
        from toady.github_service import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.post_reply.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            ["reply", "--comment-id", "123456789", "--body", "Test reply", "--pretty"],
        )
        assert result.exit_code == 1
        assert "❌ Authentication failed: Authentication failed" in result.output
        assert "💡 Try running: gh auth login" in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_authentication_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with authentication error in JSON mode."""
        from toady.github_service import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.post_reply.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 1

        import json

        output = json.loads(result.output)
        assert output["reply_posted"] is False
        assert output["error"] == "authentication_failed"
        assert "Authentication failed" in output["error_message"]

    @patch("toady.cli.ReplyService")
    def test_reply_api_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with API error in pretty mode."""
        from toady.reply_service import ReplyServiceError

        mock_service = Mock()
        mock_service.post_reply.side_effect = ReplyServiceError("API request failed")
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            ["reply", "--comment-id", "123456789", "--body", "Test reply", "--pretty"],
        )
        assert result.exit_code == 1
        assert "❌ Failed to post reply: API request failed" in result.output

    @patch("toady.cli.ReplyService")
    def test_reply_api_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with API error in JSON mode."""
        from toady.reply_service import ReplyServiceError

        mock_service = Mock()
        mock_service.post_reply.side_effect = ReplyServiceError("API request failed")
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 1

        import json

        output = json.loads(result.output)
        assert output["reply_posted"] is False
        assert output["error"] == "api_error"
        assert "API request failed" in output["error_message"]


class TestResolveCommand:
    """Test the resolve command."""

    def test_resolve_requires_thread_id(self, runner: CliRunner) -> None:
        """Test that resolve requires --thread-id option."""
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert "Missing option '--thread-id'" in result.output

    @patch("toady.cli.ResolveService")
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

    @patch("toady.cli.ResolveService")
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

    @patch("toady.cli.ResolveService")
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

    @patch("toady.cli.ResolveService")
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

    @patch("toady.cli.ResolveService")
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
        assert "Thread ID must be numeric" in result.output

    def test_resolve_invalid_node_id_too_short(self, runner: CliRunner) -> None:
        """Test resolve with too short node ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "PRT_abc"])
        assert result.exit_code != 0
        assert "GitHub node ID appears too short to be valid" in result.output

    def test_resolve_various_thread_id_formats(self, runner: CliRunner) -> None:
        """Test resolve with various valid thread ID formats."""
        with patch("toady.cli.ResolveService") as mock_service_class:
            mock_service = Mock()
            mock_service.resolve_thread.return_value = {
                "thread_id": "test_id",
                "action": "resolve",
                "success": True,
                "is_resolved": "true",
                "thread_url": "https://github.com/owner/repo/pull/123#discussion_r123",
            }
            mock_service_class.return_value = mock_service

            test_cases = [
                "1",
                "123",
                "123456789",
                "PRT_kwDOABcD12M",
                "PRT_kwDOABcD12MAAAABcDE3fg",
            ]

            for thread_id in test_cases:
                result = runner.invoke(cli, ["resolve", "--thread-id", thread_id])
                assert result.exit_code == 0, f"Failed for thread ID: {thread_id}"

    def test_resolve_invalid_thread_id_formats(self, runner: CliRunner) -> None:
        """Test resolve with various invalid thread ID formats."""
        test_cases = [
            "abc123",  # Invalid: starts with letters
            "123abc",  # Invalid: ends with letters
            "IC_123",  # Invalid: wrong prefix
            "PRT_a",  # Invalid: too short node ID
            "12.34",  # Invalid: contains decimal
            "-123",  # Invalid: negative number
            "123 456",  # Invalid: contains space
        ]

        for thread_id in test_cases:
            result = runner.invoke(cli, ["resolve", "--thread-id", thread_id])
            assert (
                result.exit_code != 0
            ), f"Should have failed for thread ID: {thread_id}"

    @patch("toady.cli.ResolveService")
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

    @patch("toady.cli.ResolveService")
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

    @patch("toady.cli.ResolveService")
    def test_resolve_thread_not_found_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with thread not found error in pretty mode."""
        from toady.resolve_service import ThreadNotFoundError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ThreadNotFoundError(
            "Thread 999 not found"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "999", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Thread not found: Thread 999 not found" in result.output

    @patch("toady.cli.ResolveService")
    def test_resolve_thread_not_found_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with thread not found error in JSON mode."""
        from toady.resolve_service import ThreadNotFoundError

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

    @patch("toady.cli.ResolveService")
    def test_resolve_permission_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with permission error in pretty mode."""
        from toady.resolve_service import ThreadPermissionError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ThreadPermissionError(
            "Permission denied"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Permission denied: Permission denied" in result.output
        assert "💡 Ensure you have write access to the repository" in result.output

    @patch("toady.cli.ResolveService")
    def test_resolve_permission_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with permission error in JSON mode."""
        from toady.resolve_service import ThreadPermissionError

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

    @patch("toady.cli.ResolveService")
    def test_resolve_authentication_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with authentication error in pretty mode."""
        from toady.github_service import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Authentication failed: Authentication failed" in result.output
        assert "💡 Try running: gh auth login" in result.output

    @patch("toady.cli.ResolveService")
    def test_resolve_authentication_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with authentication error in JSON mode."""
        from toady.github_service import GitHubAuthenticationError

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

    @patch("toady.cli.ResolveService")
    def test_resolve_api_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with API error in pretty mode."""
        from toady.resolve_service import ResolveServiceError

        mock_service = Mock()
        mock_service.resolve_thread.side_effect = ResolveServiceError(
            "API request failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 1
        assert "❌ Failed to resolve thread: API request failed" in result.output

    @patch("toady.cli.ResolveService")
    def test_resolve_api_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test resolve with API error in JSON mode."""
        from toady.resolve_service import ResolveServiceError

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
        assert "Mark a review thread as resolved or unresolved" in result.output
        assert "Examples:" in result.output
        assert "--thread-id" in result.output
        assert "--undo" in result.output

    def test_resolve_parameter_metavars(self, runner: CliRunner) -> None:
        """Test that parameter metavars are displayed correctly."""
        result = runner.invoke(cli, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "ID" in result.output  # metavar for thread-id

    def test_resolve_all_options_combined(self, runner: CliRunner) -> None:
        """Test resolve with all options combined."""
        with patch("toady.cli.ResolveService") as mock_service_class:
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

    def test_resolve_thread_id_parameter_type_validation(
        self, runner: CliRunner
    ) -> None:
        """Test that thread-id parameter accepts string values correctly."""
        # This tests that string validation works, not Click type validation
        result = runner.invoke(cli, ["resolve", "--thread-id", "thread-123"])
        assert (
            result.exit_code != 0
        )  # Should fail format validation, not type validation