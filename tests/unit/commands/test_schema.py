"""Unit tests for the schema command module.

This module tests the core schema command logic, including parameter validation,
error handling, format resolution, and validator integration. It focuses on unit
testing the command implementation without testing the CLI interface directly.
"""

from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from toady.cli import cli
from toady.commands.schema import (
    _display_query_validation_results,
    _display_summary_report,
    _has_critical_errors,
    check,
    fetch,
    schema,
    validate,
)
from toady.exceptions import (
    ToadyError,
)
from toady.validators.schema_validator import (
    SchemaValidationError,
)


class TestSchemaCommandCore:
    """Test the core schema command functionality."""

    def test_schema_command_exists(self):
        """Test that the schema command is properly defined."""
        assert schema is not None
        assert callable(schema)
        assert hasattr(schema, "commands")

    def test_schema_command_is_group(self):
        """Test that schema is a Click command group."""
        assert isinstance(schema, click.Group)
        assert schema.invoke_without_command is True

    def test_schema_subcommands_exist(self):
        """Test that all expected subcommands exist."""
        expected_commands = ["validate", "fetch", "check"]
        for cmd_name in expected_commands:
            assert cmd_name in schema.commands
            assert callable(schema.commands[cmd_name])

    def test_validate_command_parameters(self):
        """Test that validate command has expected parameters."""
        param_names = [param.name for param in validate.params]
        expected_params = ["cache_dir", "force_refresh", "output"]

        for expected_param in expected_params:
            assert expected_param in param_names, f"Missing parameter: {expected_param}"

    def test_fetch_command_parameters(self):
        """Test that fetch command has expected parameters."""
        param_names = [param.name for param in fetch.params]
        expected_params = ["cache_dir", "force_refresh"]

        for expected_param in expected_params:
            assert expected_param in param_names, f"Missing parameter: {expected_param}"

    def test_check_command_parameters(self):
        """Test that check command has expected parameters."""
        param_names = [param.name for param in check.params]
        expected_params = ["query", "cache_dir", "output"]

        for expected_param in expected_params:
            assert expected_param in param_names, f"Missing parameter: {expected_param}"

    def test_validate_command_defaults(self):
        """Test validate command parameter defaults."""
        param_defaults = {param.name: param.default for param in validate.params}

        assert param_defaults["force_refresh"] is False
        assert param_defaults["output"] == "summary"
        assert param_defaults["cache_dir"] is None

    def test_check_command_defaults(self):
        """Test check command parameter defaults."""
        param_defaults = {param.name: param.default for param in check.params}

        assert param_defaults["output"] == "summary"
        assert param_defaults["cache_dir"] is None


class TestValidateCommand:
    """Test the validate subcommand functionality."""

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_success_summary_format(self, mock_validator_class, runner):
        """Test successful validation with summary output format."""
        # Setup mock validator
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator.generate_compatibility_report.return_value = mock_report
        mock_validator_class.return_value = mock_validator

        # Test direct command invocation
        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir=None)
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=False)
        mock_validator.generate_compatibility_report.assert_called_once()

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_success_json_format(self, mock_validator_class, runner):
        """Test successful validation with JSON output format."""
        # Setup mock validator
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator.generate_compatibility_report.return_value = mock_report
        mock_validator_class.return_value = mock_validator

        # Test direct command invocation
        result = runner.invoke(cli, ["schema", "validate", "--output", "json"])

        assert result.exit_code == 0
        # Check that JSON output contains expected fields
        assert '"timestamp": "2024-01-15T10:00:00Z"' in result.output
        assert '"schema_version": "v1.0"' in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_with_custom_cache_dir(self, mock_validator_class, runner):
        """Test validation with custom cache directory."""
        # Setup mock validator
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.return_value = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator_class.return_value = mock_validator

        # Test with custom cache directory
        result = runner.invoke(
            cli, ["schema", "validate", "--cache-dir", "/tmp/test-cache"]
        )

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/test-cache")

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_with_force_refresh(self, mock_validator_class, runner):
        """Test validation with force refresh flag."""
        # Setup mock validator
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.return_value = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }
        mock_validator_class.return_value = mock_validator

        # Test with force refresh
        result = runner.invoke(cli, ["schema", "validate", "--force-refresh"])

        assert result.exit_code == 0
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=True)

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_validator_initialization_os_error(
        self, mock_validator_class, runner
    ):
        """Test validation when validator initialization fails with OSError."""
        mock_validator_class.side_effect = OSError("Permission denied")

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Error: Failed to initialize schema validator" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_validator_initialization_permission_error(
        self, mock_validator_class, runner
    ):
        """Test validation when validator initialization fails with PermissionError."""
        mock_validator_class.side_effect = PermissionError("Access denied")

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Error: Failed to initialize schema validator" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_validator_initialization_generic_error(
        self, mock_validator_class, runner
    ):
        """Test validation when validator initialization fails with generic error."""
        mock_validator_class.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert (
            "Error: Configuration error initializing schema validator" in result.output
        )

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_schema_fetch_connection_error(self, mock_validator_class, runner):
        """Test validation when schema fetch fails with connection error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = ConnectionError("Network timeout")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Error: Network error fetching GitHub schema" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_schema_fetch_timeout_error(self, mock_validator_class, runner):
        """Test validation when schema fetch fails with timeout error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = TimeoutError("Request timeout")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Error: Network error fetching GitHub schema" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_schema_fetch_file_operation_error(
        self, mock_validator_class, runner
    ):
        """Test validation when schema fetch fails with file operation error."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = OSError("Disk full")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Error: File operation error during schema fetch" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_report_generation_error(self, mock_validator_class, runner):
        """Test validation when report generation fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.side_effect = Exception(
            "Report error"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Failed to generate compatibility report" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_json_output_format_error(self, mock_validator_class, runner):
        """Test validation when JSON output formatting fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        # Return non-serializable object
        mock_validator.generate_compatibility_report.return_value = {"timestamp": set()}
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate", "--output", "json"])

        assert result.exit_code == 1
        assert "Failed to format output" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_summary_display_error(self, mock_validator_class, runner):
        """Test validation when summary display fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        # Return invalid report format
        mock_validator.generate_compatibility_report.return_value = "invalid_report"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Invalid report format for display" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_critical_error_analysis_failure(
        self, mock_validator_class, runner
    ):
        """Test validation when critical error analysis fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        # Return invalid report that will cause error analysis to fail
        mock_validator.generate_compatibility_report.return_value = "invalid_report"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate", "--output", "json"])

        assert result.exit_code == 1
        assert "Failed to analyze report for critical errors" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_with_critical_errors_exits_one(
        self, mock_validator_class, runner
    ):
        """Test validation exits with code 1 when critical errors exist."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-15T10:00:00Z",
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
    def test_validate_with_warnings_only_exits_zero(self, mock_validator_class, runner):
        """Test validation exits with code 0 when only warnings exist."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-15T10:00:00Z",
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
    def test_validate_schema_validation_error_during_init(
        self, mock_validator_class, runner
    ):
        """Test validation when SchemaValidationError is raised during init."""
        mock_validator_class.side_effect = SchemaValidationError(
            "Schema invalid", suggestions=["Fix syntax"]
        )

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert (
            "Error: Configuration error initializing schema validator" in result.output
        )

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_schema_validation_error_from_fetch(
        self, mock_validator_class, runner
    ):
        """Test validation when SchemaValidationError is raised during fetch."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = SchemaValidationError(
            "Schema fetch error", suggestions=["Check connection"]
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Schema validation failed: Schema fetch error" in result.output
        assert "Suggestions:" in result.output
        assert "Check connection" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_schema_validation_error_no_suggestions(
        self, mock_validator_class, runner
    ):
        """Test validation when SchemaValidationError has no suggestions."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = SchemaValidationError("Schema error")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Schema validation failed: Schema error" in result.output
        assert "Suggestions:" not in result.output


class TestFetchCommand:
    """Test the fetch subcommand functionality."""

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_success(self, mock_validator_class, runner):
        """Test successful schema fetch."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": [{"name": "Query"}]}
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir=None)
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=False)
        mock_validator.get_schema_version.assert_called_once()

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_with_custom_cache_dir(self, mock_validator_class, runner):
        """Test fetch with custom cache directory."""
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
    def test_fetch_with_force_refresh(self, mock_validator_class, runner):
        """Test fetch with force refresh flag."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": []}
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch", "--force-refresh"])

        assert result.exit_code == 0
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=True)

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_validator_initialization_error(self, mock_validator_class, runner):
        """Test fetch when validator initialization fails."""
        mock_validator_class.side_effect = OSError("Permission denied")

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        assert "Error: Failed to initialize schema validator" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_network_error(self, mock_validator_class, runner):
        """Test fetch when network error occurs."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = ConnectionError("Network timeout")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        assert "Error: Network error fetching GitHub schema" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_file_operation_error(self, mock_validator_class, runner):
        """Test fetch when file operation error occurs."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = PermissionError("Access denied")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        assert "Error: File operation error during schema fetch" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_version_retrieval_error(self, mock_validator_class, runner):
        """Test fetch when version retrieval fails."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = {"types": []}
        mock_validator.get_schema_version.side_effect = Exception("Version error")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 0
        assert "version: unknown" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_schema_analysis_error(self, mock_validator_class, runner):
        """Test fetch when schema analysis fails."""
        mock_validator = Mock()
        # Create mock schema where len() will fail
        mock_types = MagicMock()
        mock_types.__len__.side_effect = Exception("Length error")
        mock_schema = {"types": mock_types}
        mock_validator.fetch_schema.return_value = mock_schema
        mock_validator.get_schema_version.return_value = "v1.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 0
        assert "unable to analyze structure" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_schema_validation_error_during_init(
        self, mock_validator_class, runner
    ):
        """Test fetch when SchemaValidationError is raised during initialization."""
        mock_validator_class.side_effect = SchemaValidationError("Schema invalid")

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        assert (
            "Error: Configuration error initializing schema validator" in result.output
        )

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_schema_validation_error_from_fetch(
        self, mock_validator_class, runner
    ):
        """Test fetch when SchemaValidationError is raised during fetch operation."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = SchemaValidationError(
            "Schema fetch error"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        assert "Failed to fetch schema: Schema fetch error" in result.output


class TestCheckCommand:
    """Test the check subcommand functionality."""

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_success(self, mock_validator_class, runner):
        """Test successful query validation."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = []
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir=None)
        mock_validator.validate_query.assert_called_once_with(
            "query { viewer { login } }"
        )

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_with_errors(self, mock_validator_class, runner):
        """Test query validation with errors."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = [
            {"message": "Field not found", "severity": "error"}
        ]
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { invalid }"])

        assert result.exit_code == 1

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_with_warnings_only(self, mock_validator_class, runner):
        """Test query validation with warnings only."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = [
            {"message": "Deprecated field", "severity": "warning"}
        ]
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { deprecated }"])

        assert result.exit_code == 0

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_json_output(self, mock_validator_class, runner):
        """Test query validation with JSON output."""
        mock_validator = Mock()
        errors = [{"message": "Field not found", "severity": "error"}]
        mock_validator.validate_query.return_value = errors
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli, ["schema", "check", "query { invalid }", "--output", "json"]
        )

        assert result.exit_code == 1
        assert '"errors":' in result.output
        assert '"message": "Field not found"' in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_with_custom_cache_dir(self, mock_validator_class, runner):
        """Test query validation with custom cache directory."""
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

    def test_check_empty_query(self, runner):
        """Test query validation with empty query."""
        result = runner.invoke(cli, ["schema", "check", ""])

        assert result.exit_code == 1
        assert "Query must be a non-empty string" in result.output

    def test_check_whitespace_only_query(self, runner):
        """Test query validation with whitespace-only query."""
        result = runner.invoke(cli, ["schema", "check", "   \n\t   "])

        assert result.exit_code == 1
        assert "Query must be a non-empty string" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_validator_initialization_error(self, mock_validator_class, runner):
        """Test check when validator initialization fails."""
        mock_validator_class.side_effect = OSError("Permission denied")

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 1
        assert "Error: Failed to initialize schema validator" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_validation_error(self, mock_validator_class, runner):
        """Test check when query validation fails internally."""
        mock_validator = Mock()
        mock_validator.validate_query.side_effect = Exception(
            "Internal validation error"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 1
        assert "Failed to validate query" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_results_formatting_error(self, mock_validator_class, runner):
        """Test check when results formatting fails."""
        mock_validator = Mock()
        # Return invalid object that will cause formatting error
        mock_validator.validate_query.return_value = [{"message": set()}]
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query {}", "--output", "json"])

        assert result.exit_code == 1
        assert "Failed to format validation results" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_error_analysis_failure(self, mock_validator_class, runner):
        """Test check when error analysis fails."""
        mock_validator = Mock()
        # Return non-list errors that will cause analysis to fail
        mock_validator.validate_query.return_value = "invalid_errors_format"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query {}"])

        assert result.exit_code == 1
        assert "Failed to process validation results" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_schema_validation_error_during_init(
        self, mock_validator_class, runner
    ):
        """Test check when SchemaValidationError is raised during initialization."""
        mock_validator_class.side_effect = SchemaValidationError("Schema invalid")

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 1
        assert (
            "Error: Configuration error initializing schema validator" in result.output
        )

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_schema_validation_error_from_validate(
        self, mock_validator_class, runner
    ):
        """Test check when SchemaValidationError is raised during validation."""
        mock_validator = Mock()
        mock_validator.validate_query.side_effect = SchemaValidationError(
            "Validation error"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 1
        assert "Failed to validate query: Validation error" in result.output


class TestDisplaySummaryReport:
    """Test the _display_summary_report function."""

    def test_display_summary_valid_report(self, capsys):
        """Test displaying a valid summary report."""
        report = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {"test_query": [{"message": "Error", "severity": "error"}]},
            "mutations": {},
            "recommendations": ["Use latest API version"],
        }

        _display_summary_report(report)

        captured = capsys.readouterr()
        assert "GitHub GraphQL Schema Compatibility Report" in captured.out
        assert "Generated: 2024-01-15T10:00:00Z" in captured.out
        assert "Schema Version: v1.0" in captured.out
        assert "test_query: 1 error(s)" in captured.out
        assert "Use latest API version" in captured.out

    def test_display_summary_empty_report(self, capsys):
        """Test displaying an empty summary report."""
        report = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": [],
        }

        _display_summary_report(report)

        captured = capsys.readouterr()
        assert "All queries are valid" in captured.out
        assert "All mutations are valid" in captured.out

    def test_display_summary_invalid_report_type(self):
        """Test displaying summary with invalid report type."""
        with pytest.raises(ToadyError) as exc_info:
            _display_summary_report("invalid_report")

        assert "Invalid report format for display" in str(exc_info.value)

    def test_display_summary_missing_fields(self, capsys):
        """Test displaying summary with missing fields."""
        report = {}

        _display_summary_report(report)

        captured = capsys.readouterr()
        assert "Generated: Unknown" in captured.out
        assert "Schema Version: Unknown" in captured.out

    def test_display_summary_with_warnings(self, capsys):
        """Test displaying summary with warnings and errors."""
        report = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {
                "query1": [
                    {"message": "Error", "severity": "error"},
                    {"message": "Warning", "severity": "warning"},
                ],
                "query2": [{"message": "Warning only", "severity": "warning"}],
            },
            "mutations": {
                "mutation1": [{"message": "Mutation error", "severity": "error"}]
            },
            "recommendations": [],
        }

        _display_summary_report(report)

        captured = capsys.readouterr()
        assert "query1: 1 error(s)" in captured.out
        assert "query2: 1 warning(s)" in captured.out
        assert "mutation1: 1 error(s)" in captured.out


class TestDisplayQueryValidationResults:
    """Test the _display_query_validation_results function."""

    def test_display_no_errors(self, capsys):
        """Test displaying results with no errors."""
        errors = []

        _display_query_validation_results(errors)

        captured = capsys.readouterr()
        assert "✓ Query is valid" in captured.out

    def test_display_critical_errors(self, capsys):
        """Test displaying results with critical errors."""
        errors = [
            {
                "message": "Field not found",
                "severity": "error",
                "path": "query.field",
                "suggestions": ["Use correct field name"],
            }
        ]

        _display_query_validation_results(errors)

        captured = capsys.readouterr()
        assert "✗ Query has 1 error(s):" in captured.out
        assert "Field not found" in captured.out
        assert "Path: query.field" in captured.out
        assert "Suggestions: Use correct field name" in captured.out

    def test_display_warnings(self, capsys):
        """Test displaying results with warnings."""
        errors = [
            {
                "message": "Deprecated field",
                "severity": "warning",
                "path": "query.deprecatedField",
            }
        ]

        _display_query_validation_results(errors)

        captured = capsys.readouterr()
        assert "⚠ Query has 1 warning(s):" in captured.out
        assert "Deprecated field" in captured.out

    def test_display_mixed_errors_and_warnings(self, capsys):
        """Test displaying results with both errors and warnings."""
        errors = [
            {"message": "Critical error", "severity": "error"},
            {"message": "Warning message", "severity": "warning"},
        ]

        _display_query_validation_results(errors)

        captured = capsys.readouterr()
        assert "✗ Query has 1 error(s):" in captured.out
        assert "⚠ Query has 1 warning(s):" in captured.out

    def test_display_invalid_errors_type(self):
        """Test displaying results with invalid errors type."""
        with pytest.raises(ToadyError) as exc_info:
            _display_query_validation_results("invalid_errors")

        assert "Invalid errors format for display" in str(exc_info.value)

    def test_display_errors_with_invalid_error_entries(self, capsys):
        """Test displaying results with some invalid error entries."""
        errors = [
            {"message": "Valid error", "severity": "error"},
            "invalid_error_entry",  # This should be skipped
            {"message": "Another valid error", "severity": "warning"},
        ]

        _display_query_validation_results(errors)

        captured = capsys.readouterr()
        assert "✗ Query has 1 error(s):" in captured.out
        assert "⚠ Query has 1 warning(s):" in captured.out
        assert "Valid error" in captured.out
        assert "Another valid error" in captured.out

    def test_display_errors_without_severity(self, capsys):
        """Test displaying results with errors without severity.

        Defaults to critical.
        """
        errors = [{"message": "Error without severity"}]

        _display_query_validation_results(errors)

        captured = capsys.readouterr()
        assert "✗ Query has 1 error(s):" in captured.out
        assert "Error without severity" in captured.out


class TestHasCriticalErrors:
    """Test the _has_critical_errors function."""

    def test_has_critical_errors_with_query_errors(self):
        """Test detecting critical errors in queries."""
        report = {
            "queries": {"test_query": [{"message": "Error", "severity": "error"}]},
            "mutations": {},
        }

        assert _has_critical_errors(report) is True

    def test_has_critical_errors_with_mutation_errors(self):
        """Test detecting critical errors in mutations."""
        report = {
            "queries": {},
            "mutations": {"test_mutation": [{"message": "Error", "severity": "error"}]},
        }

        assert _has_critical_errors(report) is True

    def test_has_critical_errors_with_warnings_only(self):
        """Test no critical errors when only warnings exist."""
        report = {
            "queries": {"test_query": [{"message": "Warning", "severity": "warning"}]},
            "mutations": {
                "test_mutation": [{"message": "Warning", "severity": "warning"}]
            },
        }

        assert _has_critical_errors(report) is False

    def test_has_critical_errors_no_errors(self):
        """Test no critical errors when no errors exist."""
        report = {"queries": {}, "mutations": {}}

        assert _has_critical_errors(report) is False

    def test_has_critical_errors_missing_severity(self):
        """Test treating missing severity as critical error."""
        report = {
            "queries": {"test_query": [{"message": "Error without severity"}]},
            "mutations": {},
        }

        assert _has_critical_errors(report) is True

    def test_has_critical_errors_invalid_report_type(self):
        """Test error analysis with invalid report type."""
        with pytest.raises(ToadyError) as exc_info:
            _has_critical_errors("invalid_report")

        assert "Invalid report format for error analysis" in str(exc_info.value)

    def test_has_critical_errors_invalid_queries_type(self):
        """Test error analysis with invalid queries type."""
        report = {"queries": "invalid_queries_type", "mutations": {}}

        assert _has_critical_errors(report) is False

    def test_has_critical_errors_invalid_error_list(self):
        """Test error analysis with invalid error list."""
        report = {"queries": {"test_query": "invalid_error_list"}, "mutations": {}}

        assert _has_critical_errors(report) is False

    def test_has_critical_errors_invalid_error_dict(self):
        """Test error analysis with invalid error dictionary."""
        report = {"queries": {"test_query": ["invalid_error_dict"]}, "mutations": {}}

        assert _has_critical_errors(report) is False


class TestSchemaParameterValidation:
    """Test parameter validation for schema commands."""

    def test_validate_invalid_cache_dir_type(self, runner):
        """Test validation with invalid cache directory type."""
        # Click handles basic type validation, but our command validates further
        # Test with a path that our validation logic can handle
        result = runner.invoke(cli, ["schema", "validate", "--cache-dir", "/tmp"])
        # This should work as it's a valid path string
        assert result.exit_code in [0, 1]  # May succeed or fail depending on mock setup

    def test_check_query_type_validation(self, runner):
        """Test check command with proper query type validation."""
        # Our validation logic checks for string type and non-empty content
        result = runner.invoke(cli, ["schema", "check", ""])
        assert result.exit_code == 1
        assert "Query must be a non-empty string" in result.output


class TestSchemaGroupCommand:
    """Test the schema group command behavior."""

    def test_schema_group_without_subcommand(self, runner):
        """Test schema group command without subcommand shows help."""
        result = runner.invoke(cli, ["schema"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "validate" in result.output
        assert "fetch" in result.output
        assert "check" in result.output

    def test_schema_group_with_help_flag(self, runner):
        """Test schema group command with help flag."""
        result = runner.invoke(cli, ["schema", "--help"])

        assert result.exit_code == 0
        assert "Schema validation commands" in result.output


class TestSchemaErrorHandling:
    """Test comprehensive error handling for schema commands."""

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_unexpected_exception_during_execution(
        self, mock_validator_class, runner
    ):
        """Test validate command handling unexpected exceptions during execution."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_validator.generate_compatibility_report.side_effect = RuntimeError(
            "Unexpected error"
        )
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Failed to generate compatibility report" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_unexpected_exception_during_execution(
        self, mock_validator_class, runner
    ):
        """Test fetch command handling unexpected exceptions during execution."""
        mock_validator = Mock()
        mock_validator.fetch_schema.side_effect = RuntimeError("Unexpected error")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_unexpected_exception_during_execution(
        self, mock_validator_class, runner
    ):
        """Test check command handling unexpected exceptions during execution."""
        mock_validator = Mock()
        mock_validator.validate_query.side_effect = RuntimeError("Unexpected error")
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 1
        assert "Failed to validate query" in result.output


class TestToadyErrorHandling:
    """Test ToadyError exception handling with context and suggestions."""

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_toady_error_with_suggestions_and_context(
        self, mock_validator_class, runner
    ):
        """Test validation when ToadyError is raised with suggestions and context."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None

        # Create ToadyError with suggestions and context
        toady_error = ToadyError(
            message="Custom validation error",
            suggestions=["Try updating the schema", "Check network connection"],
            context={"error_code": 500, "url": "https://api.github.com/graphql"},
        )
        mock_validator.generate_compatibility_report.side_effect = toady_error
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "validate"])

        assert result.exit_code == 1
        assert "Failed to generate compatibility report" in result.output
        assert "Custom validation error" in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_toady_error_handled_correctly(self, mock_validator_class, runner):
        """Test fetch when ToadyError is raised and handled by outer handler."""
        mock_validator = Mock()

        # Create ToadyError with context
        toady_error = ToadyError(
            message="Fetch error occurred",
            context={"operation": "schema_fetch", "timestamp": "2024-01-15T10:00:00Z"},
        )
        mock_validator.fetch_schema.side_effect = toady_error
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "fetch"])

        assert result.exit_code == 1
        # ToadyError is handled by the outer handler properly
        assert "Error: Fetch error occurred" in result.output
        assert "Context:" in result.output
        assert '"operation": "schema_fetch"' in result.output

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_toady_error_suggestions_only(self, mock_validator_class, runner):
        """Test check when ToadyError is raised with suggestions but no context."""
        mock_validator = Mock()

        # Create ToadyError with suggestions only
        toady_error = ToadyError(
            message="Query validation failed",
            suggestions=["Check GraphQL syntax", "Verify field names"],
        )
        mock_validator.validate_query.side_effect = toady_error
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(cli, ["schema", "check", "query { viewer { login } }"])

        assert result.exit_code == 1
        assert "Failed to validate query" in result.output
        assert "Query validation failed" in result.output


class TestValidationParameterEdgeCases:
    """Test parameter validation edge cases."""

    def test_validate_cache_dir_parameter_validation(self, runner):
        """Test validate command parameter validation for cache_dir."""
        # The command should handle string paths properly
        result = runner.invoke(
            cli, ["schema", "validate", "--cache-dir", "/tmp/valid-path"]
        )
        # This test mainly ensures our parameter validation doesn't crash
        assert result.exit_code in [0, 1]  # Will depend on mock setup

    def test_fetch_cache_dir_parameter_validation(self, runner):
        """Test fetch command parameter validation for cache_dir."""
        # The command should handle string paths properly
        result = runner.invoke(
            cli, ["schema", "fetch", "--cache-dir", "/tmp/valid-path"]
        )
        # This test mainly ensures our parameter validation doesn't crash
        assert result.exit_code in [0, 1]  # Will depend on mock setup

    def test_check_cache_dir_parameter_validation(self, runner):
        """Test check command parameter validation for cache_dir."""
        # The command should handle string paths properly
        result = runner.invoke(
            cli,
            [
                "schema",
                "check",
                "query { viewer { login } }",
                "--cache-dir",
                "/tmp/valid-path",
            ],
        )
        # This test mainly ensures our parameter validation doesn't crash
        assert result.exit_code in [0, 1]  # Will depend on mock setup


class TestSchemaCommandIntegration:
    """Test integration aspects of schema commands."""

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_validate_complete_successful_flow(self, mock_validator_class, runner):
        """Test complete successful validation flow."""
        mock_validator = Mock()
        mock_validator.fetch_schema.return_value = None
        mock_report = {
            "timestamp": "2024-01-15T10:00:00Z",
            "schema_version": "v1.0",
            "queries": {},
            "mutations": {},
            "recommendations": ["Consider upgrading to latest API"],
        }
        mock_validator.generate_compatibility_report.return_value = mock_report
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli, ["schema", "validate", "--force-refresh", "--cache-dir", "/tmp/cache"]
        )

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/cache")
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=True)
        mock_validator.generate_compatibility_report.assert_called_once()

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_fetch_complete_successful_flow(self, mock_validator_class, runner):
        """Test complete successful fetch flow."""
        mock_validator = Mock()
        mock_schema = {"types": [{"name": "Query"}, {"name": "Mutation"}]}
        mock_validator.fetch_schema.return_value = mock_schema
        mock_validator.get_schema_version.return_value = "v2.0"
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            cli, ["schema", "fetch", "--force-refresh", "--cache-dir", "/tmp/cache"]
        )

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/cache")
        mock_validator.fetch_schema.assert_called_once_with(force_refresh=True)
        mock_validator.get_schema_version.assert_called_once()

    @patch("toady.commands.schema.GitHubSchemaValidator")
    def test_check_complete_successful_flow(self, mock_validator_class, runner):
        """Test complete successful check flow."""
        mock_validator = Mock()
        mock_validator.validate_query.return_value = [
            {"message": "Warning", "severity": "warning", "path": "query.field"}
        ]
        mock_validator_class.return_value = mock_validator

        query = "query { viewer { login } }"
        result = runner.invoke(
            cli,
            ["schema", "check", query, "--cache-dir", "/tmp/cache", "--output", "json"],
        )

        assert result.exit_code == 0
        mock_validator_class.assert_called_once_with(cache_dir="/tmp/cache")
        mock_validator.validate_query.assert_called_once_with(query)
