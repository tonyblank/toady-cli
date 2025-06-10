"""Schema command implementation."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from toady.exceptions import (
    ConfigurationError,
    FileOperationError,
    NetworkError,
    ToadyError,
    create_validation_error,
)
from toady.schema_validator import GitHubSchemaValidator, SchemaValidationError


@click.group(invoke_without_command=True)
@click.pass_context
def schema(ctx: click.Context) -> None:
    """Schema validation commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@schema.command()
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Directory for schema cache (default: ~/.toady/cache)",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Force refresh of schema cache",
)
@click.option(
    "--output",
    type=click.Choice(["json", "summary"]),
    default="summary",
    help="Output format",
)
def validate(cache_dir: Optional[Path], force_refresh: bool, output: str) -> None:
    """Validate all GraphQL queries and mutations against GitHub schema."""
    try:
        # Validate input parameters
        if cache_dir is not None and not isinstance(cache_dir, (str, Path)):
            raise create_validation_error(
                field_name="cache_dir",
                invalid_value=type(cache_dir).__name__,
                expected_format="path string or Path object",
                message="cache_dir must be a valid path",
            )

        # Create validator with error handling
        try:
            validator = GitHubSchemaValidator(cache_dir=cache_dir)
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                message=f"Failed to initialize schema validator: {str(e)}",
                file_path=str(cache_dir) if cache_dir else "default cache directory",
                operation="initialize",
            ) from e
        except Exception as e:
            raise ConfigurationError(
                message=f"Configuration error initializing schema validator: {str(e)}",
            ) from e

        # Fetch schema with enhanced error handling
        try:
            click.echo("Fetching GitHub GraphQL schema...", err=True)
            validator.fetch_schema(force_refresh=force_refresh)
        except (ConnectionError, TimeoutError) as e:
            raise NetworkError(
                message=f"Network error fetching GitHub schema: {str(e)}",
                url="https://api.github.com/graphql",
            ) from e
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                message=f"File operation error during schema fetch: {str(e)}",
                file_path=str(cache_dir) if cache_dir else "default cache directory",
                operation="write",
            ) from e

        # Generate report with error handling
        try:
            click.echo("Generating compatibility report...", err=True)
            report = validator.generate_compatibility_report()
        except Exception as e:
            raise ToadyError(
                message=f"Failed to generate compatibility report: {str(e)}",
            ) from e

        # Output results with error handling
        try:
            if output == "json":
                click.echo(json.dumps(report, indent=2))
            else:
                _display_summary_report(report)
        except (TypeError, ValueError) as e:
            raise ToadyError(
                message=f"Failed to format output: {str(e)}",
            ) from e

        # Set exit code based on critical errors
        try:
            has_critical_errors = _has_critical_errors(report)
            sys.exit(1 if has_critical_errors else 0)
        except Exception as e:
            raise ToadyError(
                message=f"Failed to analyze report for critical errors: {str(e)}",
            ) from e

    except SchemaValidationError as e:
        click.echo(f"Schema validation failed: {e}", err=True)
        if hasattr(e, "suggestions") and e.suggestions:
            click.echo("\nSuggestions:", err=True)
            for suggestion in e.suggestions:
                click.echo(f"  - {suggestion}", err=True)
        sys.exit(1)
    except ToadyError as e:
        # Handle our custom exceptions with rich context
        click.echo(f"Error: {e.message}", err=True)
        if e.suggestions:
            click.echo("\nSuggestions:", err=True)
            for suggestion in e.suggestions:
                click.echo(f"  - {suggestion}", err=True)
        if e.context:
            click.echo(f"\nContext: {json.dumps(e.context, indent=2)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@schema.command()
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Directory for schema cache (default: ~/.toady/cache)",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Force refresh of schema cache",
)
def fetch(cache_dir: Optional[Path], force_refresh: bool) -> None:
    """Fetch and cache the GitHub GraphQL schema."""
    try:
        # Validate input parameters
        if cache_dir is not None and not isinstance(cache_dir, (str, Path)):
            raise create_validation_error(
                field_name="cache_dir",
                invalid_value=type(cache_dir).__name__,
                expected_format="path string or Path object",
                message="cache_dir must be a valid path",
            )

        # Create validator with error handling
        try:
            validator = GitHubSchemaValidator(cache_dir=cache_dir)
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                message=f"Failed to initialize schema validator: {str(e)}",
                file_path=str(cache_dir) if cache_dir else "default cache directory",
                operation="initialize",
            ) from e
        except Exception as e:
            raise ConfigurationError(
                message=f"Configuration error initializing schema validator: {str(e)}",
            ) from e

        # Fetch schema with enhanced error handling
        try:
            click.echo("Fetching GitHub GraphQL schema...", err=True)
            schema = validator.fetch_schema(force_refresh=force_refresh)
        except (ConnectionError, TimeoutError) as e:
            raise NetworkError(
                message=f"Network error fetching GitHub schema: {str(e)}",
                url="https://api.github.com/graphql",
            ) from e
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                message=f"File operation error during schema fetch: {str(e)}",
                file_path=str(cache_dir) if cache_dir else "default cache directory",
                operation="write",
            ) from e

        # Get version with error handling
        try:
            version = validator.get_schema_version()
            click.echo(f"Schema fetched successfully (version: {version})", err=True)
        except Exception:
            click.echo("Schema fetched successfully (version: unknown)", err=True)

        # Output basic stats with error handling
        try:
            if isinstance(schema, dict):
                type_count = len(schema.get("types", []))
                click.echo(f"Schema contains {type_count} types", err=True)
        except Exception:
            click.echo("Schema fetched but unable to analyze structure", err=True)

    except SchemaValidationError as e:
        click.echo(f"Failed to fetch schema: {e}", err=True)
        sys.exit(1)
    except ToadyError as e:
        # Handle our custom exceptions with rich context
        click.echo(f"Error: {e.message}", err=True)
        if e.suggestions:
            click.echo("\nSuggestions:", err=True)
            for suggestion in e.suggestions:
                click.echo(f"  - {suggestion}", err=True)
        if e.context:
            click.echo(f"\nContext: {json.dumps(e.context, indent=2)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@schema.command()
@click.argument("query", type=click.STRING)
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Directory for schema cache (default: ~/.toady/cache)",
)
@click.option(
    "--output",
    type=click.Choice(["json", "summary"]),
    default="summary",
    help="Output format",
)
def check(query: str, cache_dir: Optional[Path], output: str) -> None:
    """Validate a specific GraphQL query."""
    try:
        # Validate input parameters
        if not isinstance(query, str) or not query.strip():
            raise create_validation_error(
                field_name="query",
                invalid_value=query if isinstance(query, str) else type(query).__name__,
                expected_format="non-empty GraphQL query string",
                message="Query must be a non-empty string",
            )

        if cache_dir is not None and not isinstance(cache_dir, (str, Path)):
            raise create_validation_error(
                field_name="cache_dir",
                invalid_value=type(cache_dir).__name__,
                expected_format="path string or Path object",
                message="cache_dir must be a valid path",
            )

        # Create validator with error handling
        try:
            validator = GitHubSchemaValidator(cache_dir=cache_dir)
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                message=f"Failed to initialize schema validator: {str(e)}",
                file_path=str(cache_dir) if cache_dir else "default cache directory",
                operation="initialize",
            ) from e
        except Exception as e:
            raise ConfigurationError(
                message=f"Configuration error initializing schema validator: {str(e)}",
            ) from e

        # Validate query with error handling
        try:
            click.echo("Validating query...", err=True)
            errors = validator.validate_query(query)
        except Exception as e:
            raise ToadyError(
                message=f"Failed to validate query: {str(e)}",
                context={"query_length": len(query), "query_preview": query[:100]},
            ) from e

        # Output results with error handling
        try:
            if output == "json":
                click.echo(json.dumps({"errors": errors}, indent=2))
            else:
                _display_query_validation_results(errors)
        except (TypeError, ValueError) as e:
            raise ToadyError(
                message=f"Failed to format validation results: {str(e)}",
            ) from e

        # Set exit code based on critical errors
        try:
            critical_errors = [e for e in errors if e.get("severity") != "warning"]
            sys.exit(1 if critical_errors else 0)
        except Exception as e:
            raise ToadyError(
                message=f"Failed to analyze validation errors: {str(e)}",
            ) from e

    except SchemaValidationError as e:
        click.echo(f"Schema validation failed: {e}", err=True)
        sys.exit(1)
    except ToadyError as e:
        # Handle our custom exceptions with rich context
        click.echo(f"Error: {e.message}", err=True)
        if e.suggestions:
            click.echo("\nSuggestions:", err=True)
            for suggestion in e.suggestions:
                click.echo(f"  - {suggestion}", err=True)
        if e.context:
            click.echo(f"\nContext: {json.dumps(e.context, indent=2)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


def _display_summary_report(report: Dict[str, Any]) -> None:
    """Display a human-readable summary of the validation report.

    Raises:
        ToadyError: If report display fails
    """
    try:
        if not isinstance(report, dict):
            raise ToadyError(
                message="Invalid report format for display",
                context={"report_type": type(report).__name__},
            )

        click.echo("\n" + "=" * 60)
        click.echo("GitHub GraphQL Schema Compatibility Report")
        click.echo("=" * 60)

        # Safely access report fields
        timestamp = report.get("timestamp", "Unknown")
        schema_version = report.get("schema_version", "Unknown")

        click.echo(f"Generated: {timestamp}")
        click.echo(f"Schema Version: {schema_version}")

    except Exception as e:
        raise ToadyError(
            message=f"Failed to display summary report header: {str(e)}",
            context={
                "report_keys": (
                    list(report.keys()) if isinstance(report, dict) else "not_dict"
                )
            },
        ) from e

    # Query validation results
    click.echo("\nQuery Validation:")
    query_errors = report.get("queries", {})
    if not query_errors:
        click.echo("  ✓ All queries are valid")
    else:
        for query_name, errors in query_errors.items():
            critical_errors = [e for e in errors if e.get("severity") != "warning"]
            warnings = [e for e in errors if e.get("severity") == "warning"]

            if critical_errors:
                click.echo(f"  ✗ {query_name}: {len(critical_errors)} error(s)")
                for error in critical_errors[:3]:  # Show first 3 errors
                    click.echo(f"    - {error['message']}")
            elif warnings:
                click.echo(f"  ⚠ {query_name}: {len(warnings)} warning(s)")
            else:
                click.echo(f"  ✓ {query_name}: valid")

    # Mutation validation results
    click.echo("\nMutation Validation:")
    mutation_errors = report.get("mutations", {})
    if not mutation_errors:
        click.echo("  ✓ All mutations are valid")
    else:
        for mutation_name, errors in mutation_errors.items():
            critical_errors = [e for e in errors if e.get("severity") != "warning"]
            warnings = [e for e in errors if e.get("severity") == "warning"]

            if critical_errors:
                click.echo(f"  ✗ {mutation_name}: {len(critical_errors)} error(s)")
                for error in critical_errors[:3]:  # Show first 3 errors
                    click.echo(f"    - {error['message']}")
            elif warnings:
                click.echo(f"  ⚠ {mutation_name}: {len(warnings)} warning(s)")
            else:
                click.echo(f"  ✓ {mutation_name}: valid")

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        click.echo("\nRecommendations:")
        for rec in recommendations:
            click.echo(f"  • {rec}")

    click.echo("\n" + "=" * 60)


def _display_query_validation_results(errors: List[Dict[str, Any]]) -> None:
    """Display validation results for a single query.

    Raises:
        ToadyError: If results display fails
    """
    try:
        if not isinstance(errors, list):
            raise ToadyError(
                message="Invalid errors format for display",
                context={"errors_type": type(errors).__name__},
            )

        if not errors:
            click.echo("✓ Query is valid")
            return

        # Safely categorize errors
        critical_errors = []
        warnings = []

        for error in errors:
            if not isinstance(error, dict):
                # mypy: disable-error-code=unreachable
                continue  # Skip invalid error entries

            severity = error.get("severity")
            if severity == "warning":
                warnings.append(error)
            else:
                # Default to treating as critical error if severity is not "warning"
                critical_errors.append(error)

    except Exception as e:
        raise ToadyError(
            message=f"Failed to process validation results: {str(e)}",
            context={
                "errors_count": len(errors) if isinstance(errors, list) else "not_list"
            },
        ) from e

    if critical_errors:
        click.echo(f"✗ Query has {len(critical_errors)} error(s):")
        for error in critical_errors:
            click.echo(f"  - {error['message']}")
            if error.get("path"):
                click.echo(f"    Path: {error['path']}")
            if error.get("suggestions"):
                click.echo(f"    Suggestions: {', '.join(error['suggestions'])}")

    if warnings:
        click.echo(f"⚠ Query has {len(warnings)} warning(s):")
        for warning in warnings:
            click.echo(f"  - {warning['message']}")
            if warning.get("path"):
                click.echo(f"    Path: {warning['path']}")


def _has_critical_errors(report: Dict[str, Any]) -> bool:
    """Check if the report contains any critical errors.

    Raises:
        ToadyError: If error analysis fails
    """
    try:
        if not isinstance(report, dict):
            raise ToadyError(
                message="Invalid report format for error analysis",
                context={"report_type": type(report).__name__},
            )

        # Check query errors safely
        queries = report.get("queries", {})
        if isinstance(queries, dict):
            for errors in queries.values():
                if isinstance(errors, list):
                    for error in errors:
                        if (
                            isinstance(error, dict)
                            and error.get("severity") != "warning"
                        ):
                            return True

        # Check mutation errors safely
        mutations = report.get("mutations", {})
        if isinstance(mutations, dict):
            for errors in mutations.values():
                if isinstance(errors, list):
                    for error in errors:
                        if (
                            isinstance(error, dict)
                            and error.get("severity") != "warning"
                        ):
                            return True

        return False

    except Exception as e:
        raise ToadyError(
            message=f"Failed to analyze report for critical errors: {str(e)}",
            context={
                "report_keys": (
                    list(report.keys()) if isinstance(report, dict) else "not_dict"
                )
            },
        ) from e
