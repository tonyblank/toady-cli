"""Integration tests for the schema CLI command."""

from click.testing import CliRunner

from toady.cli import cli


class TestSchemaCLI:
    """Test the schema command CLI integration."""

    def test_schema_help_content(self, runner: CliRunner) -> None:
        """Test schema command help content."""
        result = runner.invoke(cli, ["schema", "--help"])
        assert result.exit_code == 0
        assert "Schema validation commands" in result.output

    def test_schema_subcommand_help(self, runner: CliRunner) -> None:
        """Test that schema subcommands show proper help."""
        # Test validate subcommand help
        result = runner.invoke(cli, ["schema", "validate", "--help"])
        assert result.exit_code == 0
        assert "Validate all GraphQL queries and mutations" in result.output

        # Test fetch subcommand help
        result = runner.invoke(cli, ["schema", "fetch", "--help"])
        assert result.exit_code == 0
        assert "Fetch and cache the GitHub GraphQL schema" in result.output

        # Test check subcommand help
        result = runner.invoke(cli, ["schema", "check", "--help"])
        assert result.exit_code == 0
        assert "Validate a specific GraphQL query" in result.output

    def test_schema_invalid_subcommand(self, runner: CliRunner) -> None:
        """Test schema with invalid subcommand."""
        result = runner.invoke(cli, ["schema", "invalid"])
        assert result.exit_code != 0
        assert "No such command 'invalid'" in result.output

    def test_schema_no_subcommand(self, runner: CliRunner) -> None:
        """Test schema command without subcommand."""
        result = runner.invoke(cli, ["schema"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "validate" in result.output
        assert "fetch" in result.output
        assert "check" in result.output
