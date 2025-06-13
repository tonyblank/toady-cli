"""Integration tests for the reply CLI command."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from toady.cli import cli


class TestReplyCLI:
    """Test the reply command CLI integration."""

    def test_reply_requires_options(self, runner: CliRunner) -> None:
        """Test that reply requires both reply-to-id and body options."""
        result = runner.invoke(cli, ["reply"])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_reply_requires_body(self, runner: CliRunner) -> None:
        """Test that reply requires --body option."""
        result = runner.invoke(cli, ["reply", "--id", "123"])
        assert result.exit_code != 0
        assert "Missing option '--body'" in result.output

    def test_reply_requires_id(self, runner: CliRunner) -> None:
        """Test that reply requires --id option."""
        result = runner.invoke(cli, ["reply", "--body", "test"])
        assert result.exit_code != 0
        assert "Missing option '--id'" in result.output

    @patch("toady.commands.reply.ReplyService")
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
            cli, ["reply", "--id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 0
        assert '"id": "123456789"' in result.output
        assert '"reply_posted": true' in result.output
        assert '"reply_id": "987654321"' in result.output

        from toady.services.reply_service import ReplyRequest

        expected_request = ReplyRequest(comment_id="123456789", reply_body="Test reply")
        mock_service.post_reply.assert_called_once_with(
            expected_request, fetch_context=False
        )

    @patch("toady.commands.reply.ReplyService")
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
                "--id",
                "IC_kwDOABcD12MAAAABcDE3fg",
                "--body",
                "Test reply",
            ],
        )
        assert result.exit_code == 0
        assert '"id": "IC_kwDOABcD12MAAAABcDE3fg"' in result.output

        from toady.services.reply_service import ReplyRequest

        expected_request = ReplyRequest(
            comment_id="IC_kwDOABcD12MAAAABcDE3fg", reply_body="Test reply"
        )
        mock_service.post_reply.assert_called_once_with(
            expected_request, fetch_context=False
        )

    @patch("toady.commands.reply.ReplyService")
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
                "--id",
                "123456789",
                "--body",
                "Test reply",
                "--pretty",
            ],
        )
        assert result.exit_code == 0
        assert "💬 Posting reply to 123456789" in result.output
        assert "✅ Reply posted successfully" in result.output
        assert "🔗 View reply at: https://github.com/owner/repo/pull/1" in result.output

    def test_reply_empty_id(self, runner: CliRunner) -> None:
        """Test reply with empty id."""
        result = runner.invoke(cli, ["reply", "--id", " ", "--body", "test"])
        assert result.exit_code != 0
        assert "Reply target ID cannot be empty" in result.output

    def test_reply_whitespace_id(self, runner: CliRunner) -> None:
        """Test reply with whitespace-only id."""
        result = runner.invoke(cli, ["reply", "--id", "   ", "--body", "test"])
        assert result.exit_code != 0
        assert "Reply target ID cannot be empty" in result.output

    def test_reply_invalid_id_format(self, runner: CliRunner) -> None:
        """Test reply with invalid id format."""
        result = runner.invoke(cli, ["reply", "--id", "invalid123", "--body", "test"])
        assert result.exit_code != 0
        assert "Reply target ID must start with one of" in result.output

    def test_reply_invalid_node_id_too_short(self, runner: CliRunner) -> None:
        """Test reply with too short node ID."""
        result = runner.invoke(cli, ["reply", "--id", "IC_abc", "--body", "test"])
        assert result.exit_code != 0
        assert "appears too short to be valid" in result.output

    def test_reply_empty_body(self, runner: CliRunner) -> None:
        """Test reply with empty body."""
        result = runner.invoke(cli, ["reply", "--id", "123456789", "--body", " "])
        assert result.exit_code != 0
        assert "Reply body cannot be empty" in result.output

    def test_reply_whitespace_only_body(self, runner: CliRunner) -> None:
        """Test reply with whitespace-only body."""
        result = runner.invoke(cli, ["reply", "--id", "123456789", "--body", "   "])
        assert result.exit_code != 0
        assert "Reply body cannot be empty" in result.output

    def test_reply_body_too_long(self, runner: CliRunner) -> None:
        """Test reply with body exceeding maximum length."""
        long_body = "x" * 65537  # One character over the limit
        result = runner.invoke(cli, ["reply", "--id", "123456789", "--body", long_body])
        assert result.exit_code != 0
        assert "Reply body cannot exceed 65,536 characters" in result.output

    @patch("toady.commands.reply.ReplyService")
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
        result = runner.invoke(cli, ["reply", "--id", "123456789", "--body", max_body])
        assert result.exit_code == 0

    @patch("toady.commands.reply.ReplyService")
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
                "--id",
                "123456789",
                "--body",
                "@user thanks!",
                "--pretty",
            ],
        )
        assert result.exit_code == 0
        assert (
            "⚠️  Note: Reply starts with '@' - this will mention users" in result.output
        )

    @patch("toady.commands.reply.ReplyService")
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
            cli, ["reply", "--id", "123456789", "--body", "@user thanks!"]
        )
        assert result.exit_code == 0
        assert "⚠️" not in result.output

    @patch("toady.commands.reply.ReplyService")
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
            cli, ["reply", "--id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert "id" in output
        assert "reply_posted" in output
        assert "reply_url" in output
        assert "reply_id" in output
        assert "created_at" in output
        assert "author" in output
        assert output["id"] == "123456789"
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
        assert "--id" in result.output
        assert "--body" in result.output

    def test_reply_parameter_metavars(self, runner: CliRunner) -> None:
        """Test that parameter metavars are displayed correctly."""
        result = runner.invoke(cli, ["reply", "--help"])
        assert result.exit_code == 0
        assert "ID" in result.output  # metavar for comment-id
        assert "TEXT" in result.output  # metavar for body

    @patch("toady.commands.reply.ReplyService")
    def test_reply_comment_not_found_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with comment not found error in pretty mode."""
        from toady.services.reply_service import CommentNotFoundError

        mock_service = Mock()
        mock_service.post_reply.side_effect = CommentNotFoundError(
            "Comment 999 not found in PR #1"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--id", "999", "--body", "Test reply", "--pretty"]
        )
        assert result.exit_code == 1
        assert "❌ Comment not found: Comment 999 not found in PR #1" in result.output

    @patch("toady.commands.reply.ReplyService")
    def test_reply_comment_not_found_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with comment not found error in JSON mode."""
        from toady.services.reply_service import CommentNotFoundError

        mock_service = Mock()
        mock_service.post_reply.side_effect = CommentNotFoundError(
            "Comment 999 not found in PR #1"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(cli, ["reply", "--id", "999", "--body", "Test reply"])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["reply_posted"] is False
        assert output["error"] == "comment_not_found"
        assert "Comment 999 not found" in output["error_message"]

    @patch("toady.commands.reply.ReplyService")
    def test_reply_authentication_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with authentication error in pretty mode."""
        from toady.exceptions import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.post_reply.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            ["reply", "--id", "123456789", "--body", "Test reply", "--pretty"],
        )
        assert result.exit_code == 1
        assert (
            "❌ Authentication failed: [GITHUB_AUTHENTICATION_ERROR]" in result.output
        )
        assert "💡 Try running: gh auth login" in result.output

    @patch("toady.commands.reply.ReplyService")
    def test_reply_authentication_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with authentication error in JSON mode."""
        from toady.exceptions import GitHubAuthenticationError

        mock_service = Mock()
        mock_service.post_reply.side_effect = GitHubAuthenticationError(
            "Authentication failed"
        )
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["reply_posted"] is False
        assert output["error"] == "authentication_failed"
        assert "Authentication failed" in output["error_message"]

    @patch("toady.commands.reply.ReplyService")
    def test_reply_api_error_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with API error in pretty mode."""
        from toady.services.reply_service import ReplyServiceError

        mock_service = Mock()
        mock_service.post_reply.side_effect = ReplyServiceError("API request failed")
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            ["reply", "--id", "123456789", "--body", "Test reply", "--pretty"],
        )
        assert result.exit_code == 1
        assert "❌ Failed to post reply: API request failed" in result.output

    @patch("toady.commands.reply.ReplyService")
    def test_reply_api_error_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with API error in JSON mode."""
        from toady.services.reply_service import ReplyServiceError

        mock_service = Mock()
        mock_service.post_reply.side_effect = ReplyServiceError("API request failed")
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli, ["reply", "--id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["reply_posted"] is False
        assert output["error"] == "api_error"
        assert "API request failed" in output["error_message"]

    def test_reply_enhanced_id_validation(self, runner: CliRunner) -> None:
        """Test enhanced id validation edge cases."""
        # Test numeric ID validation
        test_cases = [
            ("0", "Reply target ID must be a positive integer"),
            (
                "123456789012345678901",
                "Numeric reply target id must be between 1 and 20 digits",
            ),
            ("abc123", "Reply target ID must start with one of"),
            ("IC_", "appears too short"),
            ("IC_" + "a" * 101, "appears too long"),
            ("IC_kwDO@#$%", "contains invalid characters"),
        ]

        for id, expected_error in test_cases:
            result = runner.invoke(cli, ["reply", "--id", id, "--body", "test"])
            assert result.exit_code == 2, f"Should fail for id: {id}"
            assert expected_error in result.output, f"Expected error for {id}"

    def test_reply_enhanced_body_validation(self, runner: CliRunner) -> None:
        """Test enhanced body validation."""
        test_cases = [
            ("ab", "Reply body must be at least 3 characters long"),
            (
                ".",
                "Reply body must be at least 3 characters long",
            ),  # Length check comes first
            ("???", "Reply body appears to be placeholder text"),
            ("   \n\t   ", "Reply body cannot be empty"),  # Stripped to empty
            (
                "...",
                "Reply body appears to be placeholder text",
            ),  # Test placeholder after length
            (
                "a  \n\t  b",
                "Reply body must contain at least 3 non-whitespace characters",
            ),  # Valid length but mostly whitespace
        ]

        for body, expected_error in test_cases:
            result = runner.invoke(cli, ["reply", "--id", "123456789", "--body", body])
            assert result.exit_code == 2, f"Should fail for body: {body!r}"
            assert expected_error in result.output, f"Expected error for {body!r}"

    @patch("toady.commands.reply.ReplyService")
    def test_reply_with_verbose_mode_pretty(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with verbose mode in pretty format."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
            "pr_number": "42",
            "pr_title": "Add awesome feature",
            "parent_comment_author": "reviewer123",
            "body_preview": "This is a test reply that demonstrates...",
            "thread_url": "https://github.com/owner/repo/pull/42#pullrequestreview-123456",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            [
                "reply",
                "--id",
                "123456789",
                "--body",
                "This is a test reply that demonstrates the verbose feature",
                "--pretty",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "✅ Reply posted successfully" in result.output
        assert "📋 Reply Details:" in result.output
        assert "Pull Request: #42 - Add awesome feature" in result.output
        assert "Replying to: @reviewer123" in result.output
        assert "Your reply: This is a test reply that demonstrates..." in result.output
        assert "Thread URL:" in result.output
        assert "Posted at: 2023-01-01T12:00:00Z" in result.output
        assert "Posted by: @testuser" in result.output

    @patch("toady.commands.reply.ReplyService")
    def test_reply_with_verbose_mode_json(
        self, mock_service_class: Mock, runner: CliRunner
    ) -> None:
        """Test reply with verbose mode in JSON format."""
        mock_service = Mock()
        mock_service.post_reply.return_value = {
            "reply_id": "987654321",
            "reply_url": "https://github.com/owner/repo/pull/1#discussion_r987654321",
            "comment_id": "123456789",
            "created_at": "2023-01-01T12:00:00Z",
            "author": "testuser",
            "pr_number": "42",
            "pr_title": "Add awesome feature",
            "parent_comment_author": "reviewer123",
            "body_preview": "Test reply",
            "thread_url": "https://github.com/owner/repo/pull/42#pullrequestreview-123456",
            "review_id": "123456",
        }
        mock_service_class.return_value = mock_service

        result = runner.invoke(
            cli,
            [
                "reply",
                "--id",
                "123456789",
                "--body",
                "Test reply",
                "--verbose",
            ],
        )
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["reply_posted"] is True
        assert output["pr_number"] == "42"
        assert output["pr_title"] == "Add awesome feature"
        assert output["parent_comment_author"] == "reviewer123"
        assert output["body_preview"] == "Test reply"
        assert (
            output["thread_url"]
            == "https://github.com/owner/repo/pull/42#pullrequestreview-123456"
        )
        assert output["review_id"] == "123456"
        assert output["verbose"] is True

    def test_reply_help_ids_flag(self, runner: CliRunner) -> None:
        """Test the --help-ids flag shows detailed ID guidance."""
        result = runner.invoke(cli, ["reply", "--help-ids"])
        assert result.exit_code == 0
        assert "🎯 GitHub ID Types for Reply Command" in result.output
        assert "SUPPORTED ID TYPES:" in result.output
        assert "Thread IDs (Recommended):" in result.output
        assert "PRRT_kwDOABcD12MAAAABcDE3fg" in result.output
        assert "NOT SUPPORTED:" in result.output
        assert "PRRC_kwDOABcD12MAAAABcDE3fg" in result.output
        assert "HOW TO FIND THE RIGHT ID:" in result.output
        assert "toady fetch --format pretty" in result.output
        assert "TROUBLESHOOTING:" in result.output

    def test_reply_prrc_id_error_handling(self, runner: CliRunner) -> None:
        """Test enhanced error handling for PRRC_ IDs."""
        result = runner.invoke(
            cli,
            ["reply", "--id", "PRRC_kwDOABcD12MAAAABcDE3fg", "--body", "test"],
        )
        assert result.exit_code == 2
        assert "Individual comment IDs from submitted reviews (PRRC_)" in result.output
        assert "Use the thread ID instead" in result.output
        assert "Run: toady fetch --format pretty" in result.output
        assert (
            "Look for the thread ID (starts with PRRT_, PRT_, or RT_)" in result.output
        )
        assert "toady reply --help-ids" in result.output
