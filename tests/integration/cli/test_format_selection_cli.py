"""Integration tests for format selection in CLI commands."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from toady.commands.fetch import fetch
from toady.commands.reply import reply
from toady.commands.resolve import resolve


class TestFetchCommandFormatSelection:
    """Test format selection in fetch command."""

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_format_json(self, mock_fetch_service):
        """Test fetch command with --format json."""
        # Mock the service to return empty threads
        mock_service_instance = Mock()
        mock_service_instance.fetch_review_threads_with_pr_selection.return_value = (
            [],
            123,
        )
        mock_fetch_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(fetch, ["--pr", "123", "--format", "json"])

        assert result.exit_code == 0
        # Output should be JSON
        assert result.output.strip() == "[]"

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_format_pretty(self, mock_fetch_service):
        """Test fetch command with --format pretty."""
        # Mock the service to return empty threads
        mock_service_instance = Mock()
        mock_service_instance.fetch_review_threads_with_pr_selection.return_value = (
            [],
            123,
        )
        mock_fetch_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(fetch, ["--pr", "123", "--format", "pretty"])

        assert result.exit_code == 0
        # Output should contain pretty format indicators
        assert "No review threads found" in result.output or "threads" in result.output

    @patch("toady.commands.fetch.FetchService")
    def test_fetch_with_pretty_flag_backward_compatibility(self, mock_fetch_service):
        """Test fetch command with legacy --pretty flag."""
        # Mock the service to return empty threads
        mock_service_instance = Mock()
        mock_service_instance.fetch_review_threads_with_pr_selection.return_value = (
            [],
            123,
        )
        mock_fetch_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(fetch, ["--pr", "123", "--pretty"])

        assert result.exit_code == 0
        # Should behave like --format pretty
        assert "No review threads found" in result.output or "threads" in result.output

    def test_fetch_with_invalid_format(self):
        """Test fetch command with invalid format."""
        runner = CliRunner()
        result = runner.invoke(fetch, ["--pr", "123", "--format", "invalid"])

        assert result.exit_code == 2  # Click returns 2 for invalid option values
        assert "Error:" in result.output
        assert "invalid" in result.output


class TestReplyCommandFormatSelection:
    """Test format selection in reply command."""

    @patch("toady.commands.reply.ReplyService")
    def test_reply_with_format_json(self, mock_reply_service):
        """Test reply command with --format json."""
        # Mock the service
        mock_service_instance = Mock()
        mock_service_instance.post_reply.return_value = {
            "reply_id": "123",
            "reply_url": "https://example.com",
            "created_at": "2024-01-01T00:00:00Z",
            "author": "testuser",
        }
        mock_reply_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            reply,
            ["--id", "123456789", "--body", "Test reply", "--format", "json"],
        )

        assert result.exit_code == 0
        # Output should be valid JSON
        output_data = json.loads(result.output)
        assert output_data["success"] is True
        assert output_data["reply_posted"] is True

    @patch("toady.commands.reply.ReplyService")
    def test_reply_with_format_pretty(self, mock_reply_service):
        """Test reply command with --format pretty."""
        # Mock the service
        mock_service_instance = Mock()
        mock_service_instance.post_reply.return_value = {
            "reply_id": "123",
            "reply_url": "https://example.com",
            "created_at": "2024-01-01T00:00:00Z",
            "author": "testuser",
        }
        mock_reply_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            reply,
            [
                "--id",
                "123456789",
                "--body",
                "Test reply",
                "--format",
                "pretty",
            ],
        )

        assert result.exit_code == 0
        # Output should contain pretty format indicators
        assert "✅" in result.output or "Reply posted" in result.output


class TestResolveCommandFormatSelection:
    """Test format selection in resolve command."""

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_format_json(self, mock_resolve_service):
        """Test resolve command with --format json."""
        # Mock the service
        mock_service_instance = Mock()
        mock_service_instance.resolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://example.com",
        }
        mock_resolve_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            resolve, ["--thread-id", "123456789", "--format", "json"]
        )

        assert result.exit_code == 0
        # Output should be valid JSON
        output_data = json.loads(result.output)
        assert output_data["success"] is True

    @patch("toady.commands.resolve.ResolveService")
    def test_resolve_with_format_pretty(self, mock_resolve_service):
        """Test resolve command with --format pretty."""
        # Mock the service
        mock_service_instance = Mock()
        mock_service_instance.resolve_thread.return_value = {
            "thread_id": "123456789",
            "action": "resolve",
            "success": True,
            "is_resolved": "true",
            "thread_url": "https://example.com",
        }
        mock_resolve_service.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            resolve, ["--thread-id", "123456789", "--format", "pretty"]
        )

        assert result.exit_code == 0
        # Output should contain pretty format indicators
        assert "✅" in result.output or "Resolved" in result.output


class TestEnvironmentVariableIntegration:
    """Test environment variable integration in CLI commands."""

    @patch.dict("os.environ", {"TOADY_DEFAULT_FORMAT": "pretty"})
    @patch("toady.commands.fetch.FetchService")
    def test_environment_variable_default_format(self, mock_fetch_service):
        """Test that environment variable sets default format."""
        # Mock the service to return empty threads
        mock_service_instance = Mock()
        mock_service_instance.fetch_review_threads_with_pr_selection.return_value = (
            [],
            123,
        )
        mock_fetch_service.return_value = mock_service_instance

        runner = CliRunner()
        # No format specified - should use env var
        result = runner.invoke(fetch, ["--pr", "123"])

        assert result.exit_code == 0
        # Should use pretty format due to env var
        assert "No review threads found" in result.output or "threads" in result.output

    @patch.dict("os.environ", {"TOADY_DEFAULT_FORMAT": "pretty"})
    @patch("toady.commands.fetch.FetchService")
    def test_explicit_format_overrides_environment(self, mock_fetch_service):
        """Test that explicit format overrides environment variable."""
        # Mock the service to return empty threads
        mock_service_instance = Mock()
        mock_service_instance.fetch_review_threads_with_pr_selection.return_value = (
            [],
            123,
        )
        mock_fetch_service.return_value = mock_service_instance

        runner = CliRunner()
        # Explicit format should override env var
        result = runner.invoke(fetch, ["--pr", "123", "--format", "json"])

        assert result.exit_code == 0
        # Should use JSON format despite env var setting pretty
        assert result.output.strip() == "[]"


class TestFormatOptionValidation:
    """Test format option validation in CLI commands."""

    def test_invalid_format_option_fetch(self):
        """Test invalid format option in fetch command."""
        runner = CliRunner()
        result = runner.invoke(fetch, ["--format", "invalid"])

        # Should fail with validation error
        assert result.exit_code != 0
        assert "invalid" in result.output.lower()

    def test_invalid_format_option_reply(self):
        """Test invalid format option in reply command."""
        runner = CliRunner()
        result = runner.invoke(
            reply,
            ["--id", "123456789", "--body", "Test", "--format", "invalid"],
        )

        # Should fail with validation error
        assert result.exit_code != 0

    def test_invalid_format_option_resolve(self):
        """Test invalid format option in resolve command."""
        runner = CliRunner()
        result = runner.invoke(
            resolve, ["--thread-id", "123456789", "--format", "invalid"]
        )

        # Should fail with validation error
        assert result.exit_code != 0


class TestMixedFormatOptions:
    """Test behavior when both --format and --pretty are specified."""

    @patch("toady.commands.fetch.FetchService")
    def test_format_option_takes_precedence_over_pretty(self, mock_fetch_service):
        """Test that --format takes precedence over --pretty."""
        # Mock the service to return empty threads
        mock_service_instance = Mock()
        mock_service_instance.fetch_review_threads_with_pr_selection.return_value = (
            [],
            123,
        )
        mock_fetch_service.return_value = mock_service_instance

        runner = CliRunner()
        # Both options specified - format should take precedence
        result = runner.invoke(fetch, ["--pr", "123", "--format", "json", "--pretty"])

        assert result.exit_code == 0
        # Should use JSON format despite --pretty flag
        assert result.output.strip() == "[]"
