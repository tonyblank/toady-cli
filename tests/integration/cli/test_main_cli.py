"""Integration tests for the main CLI interface."""

from click.testing import CliRunner

from toady import __version__
from toady.cli import cli


class TestMainCLI:
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

    def test_invalid_command(self, runner: CliRunner) -> None:
        """Test invalid command handling."""
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code == 2
        assert "No such command 'invalid-command'" in result.output

    def test_all_commands_registered(self, runner: CliRunner) -> None:
        """Test that all expected commands are registered."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Check that all expected commands are listed
        expected_commands = ["fetch", "reply", "resolve", "schema"]
        for command in expected_commands:
            assert command in result.output
