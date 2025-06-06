"""Tests for the CLI interface."""

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
        assert "fetch" in result.output
        assert "reply" in result.output
        assert "resolve" in result.output


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
        assert "[]" in result.output  # JSON output by default

    def test_fetch_with_pretty_flag(self, runner: CliRunner) -> None:
        """Test fetch with pretty output flag."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "🔍 Fetching unresolved threads for PR #123" in result.output
        assert "📝 Found 0 review threads" in result.output

    def test_fetch_with_resolved_flag(self, runner: CliRunner) -> None:
        """Test fetch with resolved threads included."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--resolved", "--pretty"])
        assert result.exit_code == 0
        assert "🔍 Fetching all threads for PR #123" in result.output

    def test_fetch_with_custom_limit(self, runner: CliRunner) -> None:
        """Test fetch with custom limit."""
        result = runner.invoke(
            cli, ["fetch", "--pr", "123", "--limit", "50", "--pretty"]
        )
        assert result.exit_code == 0
        assert "limit: 50" in result.output

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
            cli, ["fetch", "--pr", "123", "--pretty", "--resolved", "--limit", "200"]
        )
        assert result.exit_code == 0
        assert "🔍 Fetching all threads for PR #123 (limit: 200)" in result.output

    def test_fetch_help(self, runner: CliRunner) -> None:
        """Test fetch command help."""
        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "Fetch review threads from a GitHub pull request" in result.output
        assert "Examples:" in result.output
        assert "--resolved" in result.output
        assert "--limit" in result.output

    def test_fetch_pr_parameter_type_validation(self, runner: CliRunner) -> None:
        """Test that PR parameter validates integer type."""
        result = runner.invoke(cli, ["fetch", "--pr", "not-a-number"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_fetch_limit_parameter_type_validation(self, runner: CliRunner) -> None:
        """Test that limit parameter validates integer type."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--limit", "not-a-number"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_fetch_default_limit(self, runner: CliRunner) -> None:
        """Test that default limit is applied correctly."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "(limit: 100)" in result.output  # Default limit


class TestReplyCommand:
    """Test the reply command."""

    def test_reply_requires_options(self, runner: CliRunner) -> None:
        """Test that reply requires both --comment-id and --body."""
        result = runner.invoke(cli, ["reply"])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_reply_requires_body(self, runner: CliRunner) -> None:
        """Test that reply requires --body option."""
        result = runner.invoke(cli, ["reply", "--comment-id", "12345"])
        assert result.exit_code != 0
        assert "Missing option '--body'" in result.output

    def test_reply_requires_comment_id(self, runner: CliRunner) -> None:
        """Test that reply requires --comment-id option."""
        result = runner.invoke(cli, ["reply", "--body", "Test reply"])
        assert result.exit_code != 0
        assert "Missing option '--comment-id'" in result.output

    def test_reply_with_valid_numeric_id(self, runner: CliRunner) -> None:
        """Test reply with valid numeric comment ID."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 0
        assert '"comment_id": "123456789"' in result.output
        assert '"reply_posted": true' in result.output

    def test_reply_with_valid_node_id(self, runner: CliRunner) -> None:
        """Test reply with valid GitHub node ID."""
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

    def test_reply_with_pretty_output(self, runner: CliRunner) -> None:
        """Test reply with pretty output format."""
        result = runner.invoke(
            cli,
            ["reply", "--comment-id", "123456789", "--body", "Test reply", "--pretty"],
        )
        assert result.exit_code == 0
        assert "💬 Posting reply to comment 123456789" in result.output
        assert "📝 Reply: Test reply" in result.output
        assert "✅ Reply posted successfully" in result.output

    def test_reply_empty_comment_id(self, runner: CliRunner) -> None:
        """Test reply with empty comment ID."""
        result = runner.invoke(cli, ["reply", "--comment-id", "", "--body", "Test"])
        assert result.exit_code != 0
        assert "Comment ID cannot be empty" in result.output

    def test_reply_whitespace_comment_id(self, runner: CliRunner) -> None:
        """Test reply with whitespace-only comment ID."""
        result = runner.invoke(cli, ["reply", "--comment-id", "   ", "--body", "Test"])
        assert result.exit_code != 0
        assert "Comment ID cannot be empty" in result.output

    def test_reply_invalid_comment_id_format(self, runner: CliRunner) -> None:
        """Test reply with invalid comment ID format."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "invalid-id", "--body", "Test"]
        )
        assert result.exit_code != 0
        assert "Comment ID must be numeric" in result.output
        assert "or a GitHub node ID starting with 'IC_'" in result.output

    def test_reply_invalid_node_id_too_short(self, runner: CliRunner) -> None:
        """Test reply with too short node ID."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "IC_abc", "--body", "Test"]
        )
        assert result.exit_code != 0
        assert "GitHub node ID appears too short to be valid" in result.output

    def test_reply_empty_body(self, runner: CliRunner) -> None:
        """Test reply with empty body."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", ""]
        )
        assert result.exit_code != 0
        assert "Reply body cannot be empty" in result.output

    def test_reply_whitespace_only_body(self, runner: CliRunner) -> None:
        """Test reply with whitespace-only body."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "   \n\t   "]
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

    def test_reply_body_at_maximum_length(self, runner: CliRunner) -> None:
        """Test reply with body at maximum length."""
        max_body = "x" * 65536  # Exactly at the limit
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", max_body]
        )
        assert result.exit_code == 0
        assert '"reply_posted": true' in result.output

    def test_reply_body_with_mention_warning(self, runner: CliRunner) -> None:
        """Test reply with body starting with @ shows warning."""
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
        assert (
            "⚠️  Note: Reply starts with '@' - this will mention users" in result.output
        )

    def test_reply_body_with_mention_no_warning_json(self, runner: CliRunner) -> None:
        """Test reply with @ mention doesn't show warning in JSON mode."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "@user thanks!"]
        )
        assert result.exit_code == 0
        assert "⚠️" not in result.output

    def test_reply_long_body_truncation_in_pretty_mode(self, runner: CliRunner) -> None:
        """Test that long reply body is truncated in pretty output."""
        long_body = (
            "This is a very long reply body that should be truncated in the "
            "pretty output mode to avoid cluttering the terminal with too much text"
        )
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", long_body, "--pretty"]
        )
        assert result.exit_code == 0
        # Check that truncation occurs at around 100 characters
        assert (
            "📝 Reply: This is a very long reply body that should be truncated"
            in result.output
        )
        assert "..." in result.output

    def test_reply_various_comment_id_formats(self, runner: CliRunner) -> None:
        """Test reply with various valid comment ID formats."""
        test_cases = [
            "1",
            "123",
            "123456789",
            "IC_kwDOABcD12M",
            "IC_kwDOABcD12MAAAABcDE3fg",
        ]

        for comment_id in test_cases:
            result = runner.invoke(
                cli, ["reply", "--comment-id", comment_id, "--body", "Test reply"]
            )
            assert result.exit_code == 0, f"Failed for comment ID: {comment_id}"

    def test_reply_invalid_comment_id_formats(self, runner: CliRunner) -> None:
        """Test reply with various invalid comment ID formats."""
        test_cases = [
            "abc123",  # Invalid: starts with letters
            "123abc",  # Invalid: ends with letters
            "PR_123",  # Invalid: wrong prefix
            "IC_a",  # Invalid: too short node ID
            "12.34",  # Invalid: contains decimal
            "-123",  # Invalid: negative number
            "123 456",  # Invalid: contains space
        ]

        for comment_id in test_cases:
            result = runner.invoke(
                cli, ["reply", "--comment-id", comment_id, "--body", "Test reply"]
            )
            assert (
                result.exit_code != 0
            ), f"Should have failed for comment ID: {comment_id}"

    def test_reply_json_output_structure(self, runner: CliRunner) -> None:
        """Test that JSON output has correct structure."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "123456789", "--body", "Test reply"]
        )
        assert result.exit_code == 0

        import json

        output = json.loads(result.output)
        assert "comment_id" in output
        assert "reply_posted" in output
        assert "reply_url" in output
        assert output["comment_id"] == "123456789"
        assert output["reply_posted"] is True
        assert "https://github.com/" in output["reply_url"]

    def test_reply_help_content(self, runner: CliRunner) -> None:
        """Test reply command help content."""
        result = runner.invoke(cli, ["reply", "--help"])
        assert result.exit_code == 0
        assert "Post a reply to a specific review comment" in result.output
        assert "Examples:" in result.output
        assert "--comment-id" in result.output
        assert "--body" in result.output
        assert "--pretty" in result.output
        assert "numeric ID" in result.output
        assert "node ID" in result.output

    def test_reply_parameter_metavars(self, runner: CliRunner) -> None:
        """Test that parameter metavars are displayed correctly."""
        result = runner.invoke(cli, ["reply", "--help"])
        assert result.exit_code == 0
        assert "ID" in result.output  # metavar for comment-id
        assert "TEXT" in result.output  # metavar for body


class TestResolveCommand:
    """Test the resolve command."""

    def test_resolve_requires_thread_id(self, runner: CliRunner) -> None:
        """Test that resolve requires --thread-id option."""
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert "Missing option '--thread-id'" in result.output

    def test_resolve_with_valid_numeric_id(self, runner: CliRunner) -> None:
        """Test resolve with valid numeric thread ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 0
        assert '"thread_id": "123456789"' in result.output
        assert '"action": "resolve"' in result.output
        assert '"success": true' in result.output

    def test_resolve_with_valid_node_id(self, runner: CliRunner) -> None:
        """Test resolve with valid GitHub node ID."""
        result = runner.invoke(
            cli, ["resolve", "--thread-id", "PRT_kwDOABcD12MAAAABcDE3fg"]
        )
        assert result.exit_code == 0
        assert '"thread_id": "PRT_kwDOABcD12MAAAABcDE3fg"' in result.output

    def test_resolve_with_undo_flag(self, runner: CliRunner) -> None:
        """Test resolve with undo flag."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--undo"])
        assert result.exit_code == 0
        assert '"action": "unresolve"' in result.output
        assert '"success": true' in result.output

    def test_resolve_with_pretty_output(self, runner: CliRunner) -> None:
        """Test resolve with pretty output format."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--pretty"])
        assert result.exit_code == 0
        assert "🔒 Resolving thread 123456789" in result.output
        assert "✅ Thread resolved successfully" in result.output

    def test_resolve_with_undo_pretty_output(self, runner: CliRunner) -> None:
        """Test unresolve with pretty output format."""
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
        result = runner.invoke(cli, ["resolve", "--thread-id", "invalid-id"])
        assert result.exit_code != 0
        assert "Thread ID must be numeric" in result.output
        assert "or a GitHub node ID starting with 'PRT_'" in result.output

    def test_resolve_invalid_node_id_too_short(self, runner: CliRunner) -> None:
        """Test resolve with too short node ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "PRT_abc"])
        assert result.exit_code != 0
        assert "GitHub node ID appears too short to be valid" in result.output

    def test_resolve_various_thread_id_formats(self, runner: CliRunner) -> None:
        """Test resolve with various valid thread ID formats."""
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

    def test_resolve_json_output_structure(self, runner: CliRunner) -> None:
        """Test that JSON output has correct structure."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789"])
        assert result.exit_code == 0

        import json

        output = json.loads(result.output)
        assert "thread_id" in output
        assert "action" in output
        assert "success" in output
        assert "thread_url" in output
        assert output["thread_id"] == "123456789"
        assert output["action"] == "resolve"
        assert output["success"] is True
        assert "https://github.com/" in output["thread_url"]

    def test_resolve_json_output_with_undo(self, runner: CliRunner) -> None:
        """Test that JSON output has correct structure with undo flag."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "123456789", "--undo"])
        assert result.exit_code == 0

        import json

        output = json.loads(result.output)
        assert output["action"] == "unresolve"

    def test_resolve_help_content(self, runner: CliRunner) -> None:
        """Test resolve command help content."""
        result = runner.invoke(cli, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "Mark a review thread as resolved or unresolved" in result.output
        assert "Examples:" in result.output
        assert "--thread-id" in result.output
        assert "--undo" in result.output
        assert "--pretty" in result.output
        assert "numeric ID" in result.output
        assert "node ID" in result.output

    def test_resolve_parameter_metavars(self, runner: CliRunner) -> None:
        """Test that parameter metavars are displayed correctly."""
        result = runner.invoke(cli, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "ID" in result.output  # metavar for thread-id

    def test_resolve_all_options_combined(self, runner: CliRunner) -> None:
        """Test resolve with all options combined."""
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
