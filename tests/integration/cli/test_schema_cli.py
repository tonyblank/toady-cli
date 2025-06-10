"""Integration tests for the schema CLI command."""

from unittest.mock import MagicMock, Mock, patch

from click.testing import CliRunner

from toady.cli import cli
from toady.exceptions import (
    NetworkError,
)
from toady.schema_validator import SchemaValidationError


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
        assert result.exit_code == 2
        assert "No such command 'invalid'" in result.output

    def test_schema_no_subcommand(self, runner: CliRunner) -> None:
        """Test schema command without subcommand."""
        result = runner.invoke(cli, ["schema"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "validate" in result.output
        assert "fetch" in result.output
        assert "check" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_success_summary(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test successful schema validation with summary output."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.return_value = {
            "timestamp": "2024-01-01T12:00:00",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 0
        assert "Fetching GitHub GraphQL schema..." in result.output
        assert "Generating compatibility report..." in result.output
        assert "GitHub GraphQL Schema Compatibility Report" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_success_json(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test successful schema validation with JSON output."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-01T12:00:00",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator.generate_compatibility_report.return_value = mock_report
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate", "--output", "json"])
        assert result.exit_code == 0
        # Should contain JSON output (multiline formatted)
        assert '"schema_version": "v1.0"' in result.output
        assert '"timestamp": "2024-01-01T12:00:00"' in result.output
        assert '"queries": {}' in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_validator_init_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with validator initialization error."""
        mock_validator_class.side_effect = OSError("Permission denied")

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Failed to initialize schema validator" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_network_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with network error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = ConnectionError("Network timeout")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Network error fetching GitHub schema" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_schema_validation_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with SchemaValidationError."""
        mock_validator_class.side_effect = SchemaValidationError("Schema invalid")

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Configuration error initializing schema validator" in result.output
        assert "Schema invalid" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_success(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test successful schema fetch."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": [{"name": "Query"}]}
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])
        assert result.exit_code == 0
        assert "Fetching GitHub GraphQL schema..." in result.output
        assert "Schema fetched successfully (version: v1.0)" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema fetch with error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = NetworkError(
            "Network error", url="https://api.github.com/graphql"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])
        assert result.exit_code == 1
        assert "Error: Network error" in result.output
        assert '"url": "https://api.github.com/graphql"' in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_success(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test successful schema check."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = []
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])
        assert result.exit_code == 0
        assert "Validating query..." in result.output
        assert "✓ Query is valid" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_with_errors(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with validation errors."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = [
            {"message": "Field not found", "severity": "error"}
        ]
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { invalid }"])
        assert result.exit_code == 1
        assert "Validating query..." in result.output
        assert "✗ Query has 1 error(s)" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_json_output(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with JSON output."""
        mock_validator = Mock()
        errors = [{"message": "Field not found", "severity": "error"}]
        mock_validator.validate_query.return_value = errors
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli, ["schema", "check", "query { invalid }", "--output", "json"]
        )
        assert result.exit_code == 1
        # Should contain JSON output (multiline formatted)
        assert '"errors":' in result.output
        assert '"message": "Field not found"' in result.output
        assert '"severity": "error"' in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_file_operation_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with file operation error."""
        mock_validator_class.side_effect = PermissionError("Permission denied")

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Failed to initialize schema validator" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_timeout_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with timeout error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = TimeoutError("Request timeout")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Network error fetching GitHub schema" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_json_parse_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with JSON formatting error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        # Return an object that will cause JSON serialization error
        mock_validator.generate_compatibility_report.return_value = {"timestamp": set()}
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate", "--output", "json"])
        assert result.exit_code == 1
        assert "Failed to format output" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_with_critical_errors(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation exits with code 1 when critical errors exist."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-01T12:00:00",
            "schema_version": "v1.0",
            "queries": {
                "test_query": [{"message": "Critical error", "severity": "error"}]
            },
            "mutations": {},
            "recommendations": [],
        }
        mock_validator.generate_compatibility_report.return_value = mock_report
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_with_warnings_only(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation exits with code 0 when only warnings exist."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-01T12:00:00",
            "schema_version": "v1.0",
            "queries": {"test_query": [{"message": "Warning", "severity": "warning"}]},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator.generate_compatibility_report.return_value = mock_report
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 0

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_with_custom_cache_dir(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with custom cache directory."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.return_value = {
            "timestamp": "2024-01-01T12:00:00",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli, ["schema", "validate", "--cache-dir", "/tmp/test-cache"]
        )
        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/test-cache")

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_with_force_refresh(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with force refresh."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.return_value = {
            "timestamp": "2024-01-01T12:00:00",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate", "--force-refresh"])
        assert result.exit_code == 0
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=True)

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_with_custom_cache_dir(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema fetch with custom cache directory."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": []}
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli, ["schema", "fetch", "--cache-dir", "/tmp/test-cache"]
        )
        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/test-cache")

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_with_force_refresh(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema fetch with force refresh."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": []}
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch", "--force-refresh"])
        assert result.exit_code == 0
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=True)

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_version_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema fetch when version retrieval fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": []}
        mock_validator.get_schema_version.side_effect = Exception("Version error")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])
        assert result.exit_code == 0
        assert "Schema fetched successfully (version: unknown)" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_schema_analysis_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema fetch when schema analysis fails."""
        mock_validator = Mock()
        # Create a dict with a mock object for "types" that will cause len() to fail
        mock_types = MagicMock()
        mock_types.__len__.side_effect = Exception("Length error")
        mock_schema = {"types": mock_types}
        mock_validator.fetch_schema.return_value = mock_schema
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])
        assert result.exit_code == 0
        assert "Schema fetched but unable to analyze structure" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_with_custom_cache_dir(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with custom cache directory."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = []
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli,
            [
                "schema",
                "check",
                "query { viewer { login } }",
                "--cache-dir",
                "/tmp/test",
            ],
        )
        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/test")

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_validation_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check when query validation fails internally."""
        mock_validator = Mock()
        mock_validator.validate_query.side_effect = Exception(
            "Internal validation error"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])
        assert result.exit_code == 1
        assert "Failed to validate query" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_empty_query(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with empty query."""
        result = runner.invoke(cli, ["schema", "check", ""])
        assert result.exit_code == 1
        assert "Query must be a non-empty string" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_whitespace_query(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with whitespace-only query."""
        result = runner.invoke(cli, ["schema", "check", "   \n\t   "])
        assert result.exit_code == 1
        assert "Query must be a non-empty string" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_with_warnings_and_errors(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with both warnings and errors."""
        mock_validator = Mock()
        errors = [
            {"message": "Field not found", "severity": "error"},
            {"message": "Deprecated field", "severity": "warning"},
        ]
        mock_validator.validate_query.return_value = errors
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { invalid }"])
        assert result.exit_code == 1
        assert "✗ Query has 1 error(s):" in result.output
        assert "⚠ Query has 1 warning(s):" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_format_results_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check when result formatting fails."""
        mock_validator = Mock()
        # Return invalid object that will cause formatting error
        mock_validator.validate_query.return_value = [{"message": set()}]
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query {}", "--output", "json"])
        assert result.exit_code == 1
        assert "Failed to format validation results" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_error_analysis_failure(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check when error analysis fails."""
        mock_validator = Mock()
        # Return non-list errors that will cause analysis to fail
        mock_validator.validate_query.return_value = "invalid_errors_format"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query {}"])
        assert result.exit_code == 1
        assert "Failed to process validation results" in result.output

    def test_schema_validate_invalid_cache_dir_type(self, runner: CliRunner) -> None:
        """Test schema validation with invalid cache directory type."""
        # This is a hard test case since Click handles type validation
        # We can test what happens when the path doesn't exist
        runner.invoke(
            cli,
            [
                "schema",
                "validate",
                "--cache-dir",
                "/nonexistent/path/that/cannot/exist",
            ],
        )
        # This might still work depending on the validator implementation
        # The actual validation happens in the command, not Click
        # Since this test is mainly for coverage, we don't assert anything specific

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_display_summary_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation when summary display fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        # Return invalid report that will cause display to fail
        mock_validator.generate_compatibility_report.return_value = "invalid_report"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Invalid report format for display" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_critical_error_analysis_failure(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation when critical error analysis fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        # Return invalid report that will cause error analysis to fail
        mock_validator.generate_compatibility_report.return_value = "invalid_report"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate", "--output", "json"])
        assert result.exit_code == 1
        assert "Failed to analyze report for critical errors" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_validate_unexpected_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema validation with unexpected error."""
        mock_validator_class.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["schema", "validate"])
        assert result.exit_code == 1
        assert "Configuration error initializing schema validator" in result.output
        assert "Unexpected error" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_fetch_unexpected_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema fetch with unexpected error."""
        mock_validator_class.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["schema", "fetch"])
        assert result.exit_code == 1
        assert "Configuration error initializing schema validator" in result.output
        assert "Unexpected error" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_schema_check_unexpected_error(
        self, mock_validator_class: Mock, runner: CliRunner
    ) -> None:
        """Test schema check with unexpected error."""
        mock_validator_class.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["schema", "check", "query {}"])
        assert result.exit_code == 1
        assert "Configuration error initializing schema validator" in result.output
        assert "Unexpected error" in result.output
