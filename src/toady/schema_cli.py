"""CLI commands for schema validation."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from .schema_validator import GitHubSchemaValidator, SchemaValidationError


@click.group()
def schema() -> None:
    """Schema validation commands."""
    pass


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
        validator = GitHubSchemaValidator(cache_dir=cache_dir)

        click.echo("Fetching GitHub GraphQL schema...", err=True)
        validator.fetch_schema(force_refresh=force_refresh)

        click.echo("Generating compatibility report...", err=True)
        report = validator.generate_compatibility_report()

        if output == "json":
            click.echo(json.dumps(report, indent=2))
        else:
            _display_summary_report(report)

        # Set exit code based on critical errors
        has_critical_errors = _has_critical_errors(report)
        sys.exit(1 if has_critical_errors else 0)

    except SchemaValidationError as e:
        click.echo(f"Schema validation failed: {e}", err=True)
        if e.suggestions:
            click.echo("\nSuggestions:", err=True)
            for suggestion in e.suggestions:
                click.echo(f"  - {suggestion}", err=True)
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
        validator = GitHubSchemaValidator(cache_dir=cache_dir)

        click.echo("Fetching GitHub GraphQL schema...", err=True)
        schema = validator.fetch_schema(force_refresh=force_refresh)

        version = validator.get_schema_version()
        click.echo(f"Schema fetched successfully (version: {version})", err=True)

        # Output basic stats
        type_count = len(schema.get("types", []))
        click.echo(f"Schema contains {type_count} types", err=True)

    except SchemaValidationError as e:
        click.echo(f"Failed to fetch schema: {e}", err=True)
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
        validator = GitHubSchemaValidator(cache_dir=cache_dir)

        click.echo("Validating query...", err=True)
        errors = validator.validate_query(query)

        if output == "json":
            click.echo(json.dumps({"errors": errors}, indent=2))
        else:
            _display_query_validation_results(errors)

        # Set exit code based on critical errors
        critical_errors = [e for e in errors if e.get("severity") != "warning"]
        sys.exit(1 if critical_errors else 0)

    except SchemaValidationError as e:
        click.echo(f"Schema validation failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


def _display_summary_report(report: Dict[str, Any]) -> None:
    """Display a human-readable summary of the validation report."""
    click.echo("\n" + "=" * 60)
    click.echo("GitHub GraphQL Schema Compatibility Report")
    click.echo("=" * 60)

    click.echo(f"Generated: {report['timestamp']}")
    click.echo(f"Schema Version: {report['schema_version']}")

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
    """Display validation results for a single query."""
    if not errors:
        click.echo("✓ Query is valid")
        return

    critical_errors = [e for e in errors if e.get("severity") != "warning"]
    warnings = [e for e in errors if e.get("severity") == "warning"]

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
    """Check if the report contains any critical errors."""
    for errors in report.get("queries", {}).values():
        if any(e.get("severity") != "warning" for e in errors):
            return True

    for errors in report.get("mutations", {}).values():
        if any(e.get("severity") != "warning" for e in errors):
            return True

    return False


if __name__ == "__main__":
    schema()
