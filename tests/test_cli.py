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
        assert "Fetching unresolved threads for PR #123" in result.output

    def test_fetch_with_pretty_flag(self, runner: CliRunner) -> None:
        """Test fetch with pretty output flag."""
        result = runner.invoke(cli, ["fetch", "--pr", "123", "--pretty"])
        assert result.exit_code == 0
        assert "Fetching unresolved threads for PR #123" in result.output

    def test_fetch_help(self, runner: CliRunner) -> None:
        """Test fetch command help."""
        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "Fetch unresolved review threads" in result.output


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

    def test_reply_with_valid_options(self, runner: CliRunner) -> None:
        """Test reply with valid options."""
        result = runner.invoke(
            cli, ["reply", "--comment-id", "12345", "--body", "Test reply"]
        )
        assert result.exit_code == 0
        assert "Replying to comment 12345" in result.output

    def test_reply_help(self, runner: CliRunner) -> None:
        """Test reply command help."""
        result = runner.invoke(cli, ["reply", "--help"])
        assert result.exit_code == 0
        assert "Post a reply to a specific review comment" in result.output


class TestResolveCommand:
    """Test the resolve command."""

    def test_resolve_requires_thread_id(self, runner: CliRunner) -> None:
        """Test that resolve requires --thread-id option."""
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert "Missing option '--thread-id'" in result.output

    def test_resolve_with_thread_id(self, runner: CliRunner) -> None:
        """Test resolve with valid thread ID."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "abc123"])
        assert result.exit_code == 0
        assert "Resolving thread abc123" in result.output

    def test_resolve_with_undo_flag(self, runner: CliRunner) -> None:
        """Test resolve with undo flag."""
        result = runner.invoke(cli, ["resolve", "--thread-id", "abc123", "--undo"])
        assert result.exit_code == 0
        assert "Unresolving thread abc123" in result.output

    def test_resolve_help(self, runner: CliRunner) -> None:
        """Test resolve command help."""
        result = runner.invoke(cli, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "Mark a review thread as resolved or unresolved" in result.output
