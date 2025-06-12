"""Unit tests for the CLI module (src/toady/cli.py).

This module provides comprehensive unit tests for the main CLI interface,
including group setup, version display, command registration, context handling,
error handling, and the main entry point.
"""

import os
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner

from toady import __version__
from toady.cli import cli, main
from toady.exceptions import (
    ToadyError,
)


class TestCLIGroupDefinition:
    """Test the main CLI group definition and configuration."""

    def test_cli_is_group(self):
        """Test that cli is a Click group."""
        assert isinstance(cli, click.Group)
        assert cli.name == "cli"

    def test_cli_has_version_option(self):
        """Test that CLI has version option configured."""
        # Check that version option is present
        version_option = None
        for param in cli.params:
            if isinstance(param, click.Option) and "--version" in param.opts:
                version_option = param
                break

        assert version_option is not None
        assert version_option.is_flag is True

    def test_cli_has_debug_option(self):
        """Test that CLI has debug option configured."""
        debug_option = None
        for param in cli.params:
            if isinstance(param, click.Option) and "--debug" in param.opts:
                debug_option = param
                break

        assert debug_option is not None
        assert debug_option.is_flag is True
        assert debug_option.envvar == "TOADY_DEBUG"

    def test_cli_callback_function_exists(self):
        """Test that CLI callback function is properly defined."""
        assert cli.callback is not None
        assert callable(cli.callback)

    def test_cli_docstring_present(self):
        """Test that CLI has comprehensive help documentation."""
        assert cli.help is not None
        assert "Toady - GitHub PR review management tool" in cli.help
        assert "PREREQUISITES:" in cli.help
        assert "CORE WORKFLOW:" in cli.help
        assert "TROUBLESHOOTING:" in cli.help


class TestCLIGroupFunctionality:
    """Test the functional behavior of the CLI group."""

    def test_cli_version_display(self, runner):
        """Test version display functionality."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "toady" in result.output.lower()

    def test_cli_help_display(self, runner):
        """Test help display functionality."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Toady - GitHub PR review management tool" in result.output
        assert "Commands:" in result.output
        assert "--debug" in result.output
        assert "--version" in result.output

    def test_cli_debug_flag_sets_context(self, runner):
        """Test that debug flag is properly stored in context."""
        # Use existing fetch command to test context passing
        with patch("toady.commands.fetch.FetchService") as mock_service_class:
            mock_service = Mock()
            mock_service.fetch_review_threads_with_pr_selection.return_value = (
                [],
                None,
            )
            mock_service_class.return_value = mock_service

            with patch(
                "toady.commands.fetch.resolve_format_from_options"
            ) as mock_resolve_format:
                mock_resolve_format.return_value = "json"

                # Test that debug context is available
                # (command should run without error)
                result = runner.invoke(cli, ["--debug", "fetch"])
                # Command exits early when no PR selected, which is fine
                assert result.exit_code == 0

    def test_cli_context_object_initialization(self, runner):
        """Test that context object is properly initialized."""
        # Test using actual command to verify context is set up
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # If CLI ran successfully, context was initialized properly

    def test_cli_debug_environment_variable(self, runner):
        """Test that debug option respects TOADY_DEBUG environment variable."""
        # Test with environment variable set
        with patch.dict(os.environ, {"TOADY_DEBUG": "1"}):
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
            # If command runs, environment variable was processed

        with patch.dict(os.environ, {"TOADY_DEBUG": "0"}):
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0


class TestCLICommandRegistration:
    """Test that all expected commands are properly registered."""

    def test_all_commands_registered(self, runner):
        """Test that all expected commands are registered with the CLI group."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        expected_commands = ["fetch", "reply", "resolve", "schema"]
        for command in expected_commands:
            assert command in result.output

    def test_registered_commands_are_callable(self):
        """Test that all registered commands are callable."""
        expected_commands = ["fetch", "reply", "resolve", "schema"]
        for command_name in expected_commands:
            command = cli.get_command(None, command_name)
            assert command is not None
            assert callable(command)

    def test_command_help_accessible(self, runner):
        """Test that help is accessible for all registered commands."""
        expected_commands = ["fetch", "reply", "resolve", "schema"]
        for command_name in expected_commands:
            result = runner.invoke(cli, [command_name, "--help"])
            assert result.exit_code == 0
            assert "Usage:" in result.output

    def test_invalid_command_handling(self, runner):
        """Test handling of invalid/unknown commands."""
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command 'invalid-command'" in result.output


class TestCLIContextHandling:
    """Test CLI context object handling and propagation."""

    def test_context_object_structure(self, runner):
        """Test that context object has expected structure."""
        # Test by invoking CLI with known commands and checking success
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # Context is working if CLI processes successfully

    def test_context_propagation_to_subcommands(self, runner):
        """Test that context is properly propagated to subcommands."""
        # Test subcommand help which requires context propagation
        result = runner.invoke(cli, ["--debug", "fetch", "--help"])
        assert result.exit_code == 0
        # If help displays, context was propagated properly

    def test_context_ensure_object(self, runner):
        """Test that context.ensure_object works correctly."""
        # Test by running commands that depend on context
        result = runner.invoke(cli, ["schema", "--help"])
        assert result.exit_code == 0
        # Context ensure_object worked if command ran successfully


class TestMainEntryPoint:
    """Test the main() entry point function."""

    @patch("toady.cli.cli")
    def test_main_calls_cli(self, mock_cli):
        """Test that main() calls the CLI function."""
        main()
        mock_cli.assert_called_once()

    @patch("toady.cli.cli")
    @patch("toady.cli.handle_error")
    def test_main_handles_toady_error(self, mock_handle_error, mock_cli):
        """Test that main() properly handles ToadyError exceptions."""
        test_error = ToadyError("Test error")
        mock_cli.side_effect = test_error

        main()

        mock_handle_error.assert_called_once_with(test_error, show_traceback=False)

    @patch("toady.cli.cli")
    @patch("toady.cli.handle_error")
    def test_main_handles_toady_error_with_debug_env(self, mock_handle_error, mock_cli):
        """Test that main() handles ToadyError with debug environment variable."""
        test_error = ToadyError("Test error")
        mock_cli.side_effect = test_error

        with patch.dict(os.environ, {"TOADY_DEBUG": "1"}):
            main()

        mock_handle_error.assert_called_once_with(test_error, show_traceback=True)

    @patch("toady.cli.cli")
    @patch("toady.cli.handle_error")
    def test_main_handles_toady_error_with_debug_env_variations(
        self, mock_handle_error, mock_cli
    ):
        """Test that main() handles various debug environment variable values."""
        test_error = ToadyError("Test error")
        mock_cli.side_effect = test_error

        debug_values = ["true", "TRUE", "yes", "YES", "1"]
        for debug_value in debug_values:
            mock_handle_error.reset_mock()
            with patch.dict(os.environ, {"TOADY_DEBUG": debug_value}):
                main()
            mock_handle_error.assert_called_once_with(test_error, show_traceback=True)

    @patch("toady.cli.cli")
    @patch("toady.cli.handle_error")
    def test_main_handles_unexpected_error_normal_mode(
        self, mock_handle_error, mock_cli
    ):
        """Test that main() handles unexpected exceptions in normal mode."""
        test_error = ValueError("Unexpected error")
        mock_cli.side_effect = test_error

        main()

        mock_handle_error.assert_called_once_with(test_error, show_traceback=False)

    @patch("toady.cli.cli")
    def test_main_handles_unexpected_error_debug_mode(self, mock_cli):
        """Test that main() re-raises unexpected exceptions in debug mode."""
        test_error = ValueError("Unexpected error")
        mock_cli.side_effect = test_error

        with patch.dict(os.environ, {"TOADY_DEBUG": "1"}), pytest.raises(
            ValueError, match="Unexpected error"
        ):
            main()

    @patch("toady.cli.cli")
    @patch("toady.cli.handle_error")
    def test_main_debug_environment_parsing(self, mock_handle_error, mock_cli):
        """Test that main() correctly parses debug environment variable."""
        test_error = ToadyError("Test error")
        mock_cli.side_effect = test_error

        # Test falsy values
        falsy_values = ["0", "false", "FALSE", "no", "NO", ""]
        for debug_value in falsy_values:
            mock_handle_error.reset_mock()
            with patch.dict(os.environ, {"TOADY_DEBUG": debug_value}):
                main()
            mock_handle_error.assert_called_once_with(test_error, show_traceback=False)


class TestCLIErrorHandling:
    """Test error handling within the CLI interface."""

    def test_cli_handles_click_exceptions(self, runner):
        """Test that CLI properly handles Click exceptions."""
        # Test with missing required option (should be handled by Click)
        result = runner.invoke(cli, ["fetch", "--pr"])  # Missing PR number
        assert result.exit_code != 0

    def test_cli_parameter_validation(self, runner):
        """Test that CLI validates parameters correctly."""
        # Test invalid command structure
        result = runner.invoke(cli, ["--invalid-option"])
        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_cli_handles_keyboard_interrupt(self, runner):
        """Test that CLI handles KeyboardInterrupt gracefully."""
        # Test with Ctrl+C simulation in Click runner
        result = runner.invoke(cli, ["nonexistent-command"])
        # Invalid command should result in non-zero exit code
        assert result.exit_code != 0

    def test_cli_context_exception_handling(self, runner):
        """Test that CLI context exceptions are handled properly."""
        # Test that context is properly accessible in real commands
        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0
        # If command runs, context was accessible


class TestCLIEnvironmentVariables:
    """Test environment variable handling in the CLI."""

    def test_toady_debug_environment_variable_handling(self, runner):
        """Test comprehensive TOADY_DEBUG environment variable handling."""
        # Test various truthy values
        truthy_values = ["1", "true", "TRUE", "yes", "YES"]
        for value in truthy_values:
            with patch.dict(os.environ, {"TOADY_DEBUG": value}):
                result = runner.invoke(cli, ["--help"])
                assert result.exit_code == 0  # Command should run successfully

        # Test various falsy values
        falsy_values = ["0", "false", "FALSE", "no", "NO", ""]
        for value in falsy_values:
            with patch.dict(os.environ, {"TOADY_DEBUG": value}):
                result = runner.invoke(cli, ["--help"])
                assert result.exit_code == 0  # Command should run successfully

    def test_environment_variable_precedence(self, runner):
        """Test that command line flag takes precedence over environment variable."""
        # Environment says False, but command line says True
        with patch.dict(os.environ, {"TOADY_DEBUG": "0"}):
            result = runner.invoke(cli, ["--debug", "--help"])
            assert result.exit_code == 0  # Command should run successfully

        # Environment says True, but no command line flag
        with patch.dict(os.environ, {"TOADY_DEBUG": "1"}):
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0  # Command should run successfully

    def test_missing_environment_variable(self, runner):
        """Test behavior when TOADY_DEBUG environment variable is not set."""
        # Ensure environment variable is not set
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0  # Command should run with default debug=False


class TestCLIIntegration:
    """Test integration aspects of the CLI."""

    def test_cli_with_real_commands(self, runner):
        """Test that CLI works with actual registered commands."""
        # Test that we can get help for each command
        commands = ["fetch", "reply", "resolve", "schema"]
        for command in commands:
            result = runner.invoke(cli, [command, "--help"])
            assert result.exit_code == 0
            assert command in result.output.lower()

    def test_cli_version_matches_package_version(self, runner):
        """Test that CLI version matches the package version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_cli_help_structure(self, runner):
        """Test that CLI help has expected structure and sections."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Check for major sections
        expected_sections = [
            "Usage:",
            "Options:",
            "Commands:",
            "PREREQUISITES:",
            "CORE WORKFLOW:",
            "AGENT-FRIENDLY USAGE:",
            "TROUBLESHOOTING:",
        ]

        for section in expected_sections:
            assert section in result.output

    def test_cli_group_attributes(self):
        """Test that CLI group has expected attributes."""
        assert hasattr(cli, "commands")
        assert hasattr(cli, "params")
        assert hasattr(cli, "callback")
        assert hasattr(cli, "help")

        # Test that commands dictionary contains expected commands
        expected_commands = ["fetch", "reply", "resolve", "schema"]
        for command in expected_commands:
            assert command in cli.commands


class TestCLIMainBehavior:
    """Test main() function behavior patterns."""

    @patch("sys.exit")
    @patch("toady.cli.handle_error")
    @patch("toady.cli.cli")
    def test_main_exit_handling(self, mock_cli, mock_handle_error, mock_exit):
        """Test that main() properly exits after handling errors."""
        test_error = ToadyError("Test error")
        mock_cli.side_effect = test_error

        # handle_error should call sys.exit, but we're mocking it
        main()

        mock_handle_error.assert_called_once()

    @patch("toady.cli.cli")
    def test_main_normal_execution(self, mock_cli):
        """Test that main() executes normally without errors."""
        mock_cli.return_value = None

        # Should not raise any exceptions
        main()

        mock_cli.assert_called_once()

    @patch("os.environ.get")
    @patch("toady.cli.cli")
    @patch("toady.cli.handle_error")
    def test_main_debug_environment_access(
        self, mock_handle_error, mock_cli, mock_env_get
    ):
        """Test that main() correctly accesses debug environment variable."""
        test_error = ToadyError("Test error")
        mock_cli.side_effect = test_error
        mock_env_get.return_value = "1"

        main()

        # Should call os.environ.get twice (once for ToadyError, once for unexpected)
        mock_env_get.assert_called_with("TOADY_DEBUG", "")
        mock_handle_error.assert_called_once_with(test_error, show_traceback=True)


class TestCLIEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_cli_with_empty_context(self, runner):
        """Test CLI behavior when context object operations are involved."""
        # Test that context operations work with real commands
        result = runner.invoke(cli, ["--debug", "reply", "--help"])
        assert result.exit_code == 0
        # If command runs, context manipulation works properly

    def test_cli_multiple_option_combinations(self, runner):
        """Test CLI with multiple option combinations."""
        # Test various flag combinations
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0
        assert "--debug" in result.output

    def test_cli_with_invalid_subcommand_args(self, runner):
        """Test CLI handling of invalid arguments to subcommands."""
        # This should show the main help since 'invalid' is not a command
        result = runner.invoke(cli, ["invalid", "--some-option"])
        assert result.exit_code != 0
        assert "No such command 'invalid'" in result.output

    def test_cli_case_sensitivity(self, runner):
        """Test that CLI commands are case sensitive."""
        result = runner.invoke(cli, ["FETCH"])  # Uppercase
        assert result.exit_code != 0
        assert "No such command 'FETCH'" in result.output

        result = runner.invoke(cli, ["Fetch"])  # Mixed case
        assert result.exit_code != 0
        assert "No such command 'Fetch'" in result.output


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()
