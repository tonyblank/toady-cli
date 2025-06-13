"""GitHub GraphQL schema validation utilities.

This module provides automated validation for GraphQL queries and mutations
against the live GitHub API schema, ensuring compatibility and catching
breaking changes early.
"""

from datetime import datetime, timedelta
import hashlib
import json
import logging
from pathlib import Path
import subprocess
from typing import Any, Optional

from ..parsers.graphql_parser import GraphQLField, GraphQLParser
from ..services.github_service import GitHubService

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails."""

    def __init__(
        self,
        message: str,
        errors: Optional[list[dict[str, Any]]] = None,
        suggestions: Optional[list[str]] = None,
    ):
        """Initialize schema validation error.

        Args:
            message: Error message
            errors: List of specific validation errors
            suggestions: List of suggested fixes
        """
        super().__init__(message)
        self.errors = errors or []
        self.suggestions = suggestions or []


class GitHubSchemaValidator:
    """Validator for GitHub GraphQL queries against the live API schema."""

    # Introspection query to fetch the GitHub GraphQL schema
    # (compact to avoid shell parsing issues)
    INTROSPECTION_QUERY = (
        "query IntrospectionQuery { __schema { queryType { name } "
        "mutationType { name } subscriptionType { name } types { ...FullType } "
        "directives { name description locations args { ...InputValue } } } } "
        "fragment FullType on __Type { kind name description "
        "fields(includeDeprecated: true) { name description args { ...InputValue } "
        "type { ...TypeRef } isDeprecated deprecationReason } "
        "inputFields { ...InputValue } interfaces { ...TypeRef } "
        "enumValues(includeDeprecated: true) { name description isDeprecated "
        "deprecationReason } possibleTypes { ...TypeRef } } "
        "fragment InputValue on __InputValue { name description "
        "type { ...TypeRef } defaultValue } "
        "fragment TypeRef on __Type { kind name ofType { kind name "
        "ofType { kind name ofType { kind name ofType { kind name "
        "ofType { kind name ofType { kind name ofType { kind name } } } } } } } }"
    )

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl: timedelta = timedelta(hours=24),
    ):
        """Initialize the schema validator.

        Args:
            cache_dir: Directory for caching schema (defaults to ~/.toady/cache)
            cache_ttl: Time-to-live for cached schema
        """
        self.cache_dir = cache_dir or Path.home() / ".toady" / "cache"
        self.cache_ttl = cache_ttl
        self._schema: Optional[dict[str, Any]] = None
        self._type_map: Optional[dict[str, Any]] = None
        self._github_service = GitHubService()

    def _get_cache_path(self) -> Path:
        """Get the path to the cached schema file."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir / "github_schema.json"

    def _get_cache_metadata_path(self) -> Path:
        """Get the path to the cache metadata file."""
        return self.cache_dir / "github_schema_metadata.json"

    def _is_cache_valid(self) -> bool:
        """Check if the cached schema is still valid."""
        metadata_path = self._get_cache_metadata_path()
        if not metadata_path.exists():
            return False

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            cached_time = datetime.fromisoformat(metadata["timestamp"])
            return datetime.now() - cached_time < self.cache_ttl
        except (json.JSONDecodeError, KeyError, ValueError):
            return False

    def _load_cached_schema(self) -> Optional[dict[str, Any]]:
        """Load schema from cache if valid."""
        if not self._is_cache_valid():
            return None

        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            logger.warning("Failed to load cached schema")
            return None

    def _save_schema_to_cache(self, schema: dict[str, Any]) -> None:
        """Save schema to cache with metadata."""
        cache_path = self._get_cache_path()
        metadata_path = self._get_cache_metadata_path()

        # Save schema
        with open(cache_path, "w") as f:
            json.dump(schema, f, indent=2)

        # Save metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "schema_hash": hashlib.sha256(
                json.dumps(schema, sort_keys=True).encode()
            ).hexdigest(),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def fetch_schema(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch the GitHub GraphQL schema.

        Args:
            force_refresh: Force fetching fresh schema even if cache is valid

        Returns:
            The GitHub GraphQL schema

        Raises:
            SchemaValidationError: If schema fetching fails
        """
        # Try to use cached schema if not forcing refresh
        if not force_refresh:
            cached_schema = self._load_cached_schema()
            if cached_schema:
                logger.debug("Using cached GitHub schema")
                self._schema = cached_schema
                self._build_type_map()
                return cached_schema

        logger.info("Fetching GitHub GraphQL schema...")

        try:
            # Use GitHub service to execute introspection query
            process_result = self._github_service.run_gh_command(
                ["api", "graphql", "-f", f"query={self.INTROSPECTION_QUERY}"]
            )

            # Parse JSON response
            result = json.loads(process_result.stdout)

            if "data" not in result or "__schema" not in result["data"]:
                raise SchemaValidationError("Invalid schema response from GitHub API")

            schema = result["data"]["__schema"]
            if isinstance(schema, dict):
                self._schema = schema
                self._build_type_map()
                self._save_schema_to_cache(schema)

                logger.info("Successfully fetched GitHub schema")
                return schema
            raise SchemaValidationError("Schema data is not a dictionary")

        except subprocess.CalledProcessError as e:
            raise SchemaValidationError(f"Failed to fetch GitHub schema: {e}") from e
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Failed to parse schema response: {e}") from e
        except Exception as e:
            raise SchemaValidationError(f"Failed to fetch GitHub schema: {e}") from e

    def _build_type_map(self) -> None:
        """Build a map of type names to type definitions."""
        if not self._schema:
            return

        self._type_map = {}
        for type_def in self._schema.get("types", []):
            if type_def.get("name"):
                self._type_map[type_def["name"]] = type_def

    def get_type(self, type_name: str) -> Optional[dict[str, Any]]:
        """Get a type definition by name.

        Args:
            type_name: Name of the type to retrieve

        Returns:
            Type definition or None if not found
        """
        if not self._type_map:
            self.fetch_schema()

        return self._type_map.get(type_name) if self._type_map else None

    def validate_query(self, query: str) -> list[dict[str, Any]]:
        """Validate a GraphQL query against the schema.

        Args:
            query: GraphQL query string to validate

        Returns:
            List of validation errors (empty if valid)
        """
        if not self._schema:
            self.fetch_schema()

        errors = []

        # Basic query structure validation
        if not query.strip():
            errors.append(
                {
                    "type": "empty_query",
                    "message": "Query cannot be empty",
                }
            )
            return errors

        # Parse the query
        parser = GraphQLParser()
        try:
            operation = parser.parse(query)
        except ValueError as e:
            errors.append(
                {
                    "type": "parse_error",
                    "message": f"Failed to parse query: {e!s}",
                }
            )
            return errors

        # Validate operation type
        root_type_name = operation.type.capitalize()
        root_type = self.get_type(root_type_name)
        if not root_type:
            errors.append(
                {
                    "type": "missing_type",
                    "message": f"{root_type_name} type not found in schema",
                }
            )
            return errors

        # Validate fields recursively
        self._validate_selections(
            operation.selections, root_type, errors, [root_type_name]
        )

        return errors

    def _validate_selections(
        self,
        selections: list[GraphQLField],
        parent_type: dict[str, Any],
        errors: list[dict[str, Any]],
        type_path: list[str],
    ) -> None:
        """Validate field selections against a type.

        Args:
            selections: List of field selections to validate
            parent_type: Parent type definition from schema
            errors: List to append errors to
            type_path: Current type path for error messages
        """
        if not parent_type:
            return

        # Get available fields for this type
        fields = parent_type.get("fields")
        if not fields:
            return

        available_fields = {field["name"]: field for field in fields}

        for selection in selections:
            # Skip inline fragments (they start with __fragment_)
            if selection.name.startswith("__fragment_"):
                # For inline fragments, validate the selections directly
                # The type is already embedded in the field name
                fragment_type_name = selection.name.replace("__fragment_", "")
                fragment_type = self.get_type(fragment_type_name)
                if fragment_type:
                    self._validate_selections(
                        selection.selections,
                        fragment_type,
                        errors,
                        type_path + [fragment_type_name],
                    )
                continue

            field_def = available_fields.get(selection.name)

            if not field_def:
                # Field not found
                path = ".".join(type_path + [selection.name])
                errors.append(
                    {
                        "type": "unknown_field",
                        "message": f"Field '{selection.name}' not found on type "
                        f"'{parent_type.get('name', 'Unknown')}'",
                        "path": path,
                        "suggestions": self.get_field_suggestions(
                            parent_type.get("name", ""), selection.name
                        ),
                    }
                )
                continue

            # Check if field is deprecated
            if field_def.get("isDeprecated"):
                path = ".".join(type_path + [selection.name])
                reason = field_def.get("deprecationReason", "No reason provided")
                errors.append(
                    {
                        "type": "deprecated_field",
                        "message": f"Field '{selection.name}' is deprecated: {reason}",
                        "path": path,
                        "severity": "warning",
                    }
                )

            # Validate arguments
            self._validate_arguments(
                selection, field_def, errors, type_path + [selection.name]
            )

            # If field has selections, validate them recursively
            if selection.selections:
                # Get the return type of this field
                field_type = self._resolve_field_type(field_def.get("type"))
                if field_type:
                    next_type = self.get_type(field_type)
                    if next_type:
                        self._validate_selections(
                            selection.selections,
                            next_type,
                            errors,
                            type_path + [selection.name],
                        )

    def _validate_arguments(
        self,
        field: GraphQLField,
        field_def: dict[str, Any],
        errors: list[dict[str, Any]],
        type_path: list[str],
    ) -> None:
        """Validate field arguments against schema.

        Args:
            field: Field with arguments to validate
            field_def: Field definition from schema
            errors: List to append errors to
            type_path: Current type path for error messages
        """
        available_args = {arg["name"]: arg for arg in field_def.get("args", [])}

        # Check provided arguments
        for arg_name, _arg_value in field.arguments.items():
            if arg_name not in available_args:
                path = ".".join(type_path)
                errors.append(
                    {
                        "type": "unknown_argument",
                        "message": f"Unknown argument '{arg_name}' on field "
                        f"'{field.name}'",
                        "path": path,
                    }
                )

        # Check required arguments
        for arg_name, arg_def in available_args.items():
            if (
                self._is_required_type(arg_def.get("type"))
                and arg_name not in field.arguments
            ):
                path = ".".join(type_path)
                errors.append(
                    {
                        "type": "missing_argument",
                        "message": f"Missing required argument '{arg_name}' on field "
                        f"'{field.name}'",
                        "path": path,
                    }
                )

    def _resolve_field_type(self, type_ref: Optional[dict[str, Any]]) -> Optional[str]:
        """Resolve the actual type name from a type reference.

        Args:
            type_ref: Type reference from schema

        Returns:
            Resolved type name or None
        """
        if not type_ref:
            return None

        # Navigate through NON_NULL and LIST wrappers
        while type_ref and type_ref.get("kind") in ["NON_NULL", "LIST"]:
            type_ref = type_ref.get("ofType")

        return type_ref.get("name") if type_ref else None

    def _is_required_type(self, type_ref: Optional[dict[str, Any]]) -> bool:
        """Check if a type is required (NON_NULL).

        Args:
            type_ref: Type reference from schema

        Returns:
            True if the type is required
        """
        return bool(type_ref and type_ref.get("kind") == "NON_NULL")

    def check_deprecations(self, query: str) -> list[dict[str, Any]]:
        """Check for deprecated fields in a query.

        Args:
            query: GraphQL query string to check

        Returns:
            List of deprecation warnings
        """
        if not self._schema:
            self.fetch_schema()

        warnings: list[dict[str, Any]] = []

        # TODO: Implement deprecation checking by parsing query
        # and checking each field against schema
        # For now, just validate and return deprecation warnings from validation
        errors = self.validate_query(query)
        warnings = [e for e in errors if e.get("severity") == "warning"]

        return warnings

    def get_schema_version(self) -> Optional[str]:
        """Get a version identifier for the current schema.

        Returns:
            Schema version hash or None
        """
        if not self._schema:
            self.fetch_schema()

        # Generate a hash of the schema for version tracking
        schema_str = json.dumps(self._schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:12]

    def get_field_suggestions(self, type_name: str, field_name: str) -> list[str]:
        """Get suggestions for a field name on a type.

        Args:
            type_name: Name of the GraphQL type
            field_name: Field name to find suggestions for

        Returns:
            List of suggested field names
        """
        type_def = self.get_type(type_name)
        if not type_def or "fields" not in type_def:
            return []

        field_names = [f["name"] for f in type_def["fields"] if f.get("name")]

        # Simple similarity check - fields starting with same letter
        suggestions = [
            name
            for name in field_names
            if name.lower().startswith(field_name[0].lower())
        ]

        return suggestions[:5]  # Limit to top 5 suggestions

    def validate_mutations(self) -> dict[str, list[dict[str, Any]]]:
        """Validate all mutations defined in the codebase.

        Returns:
            Dictionary mapping mutation names to validation errors
        """
        from ..services.github_service import (
            REPLY_COMMENT_MUTATION,
            REPLY_THREAD_MUTATION,
            RESOLVE_THREAD_MUTATION,
            UNRESOLVE_THREAD_MUTATION,
        )

        errors = {}

        # Validate resolve mutation
        resolve_errors = self.validate_query(RESOLVE_THREAD_MUTATION)
        if resolve_errors:
            errors["resolveReviewThread"] = resolve_errors

        # Validate unresolve mutation
        unresolve_errors = self.validate_query(UNRESOLVE_THREAD_MUTATION)
        if unresolve_errors:
            errors["unresolveReviewThread"] = unresolve_errors

        # Validate reply mutations
        reply_thread_errors = self.validate_query(REPLY_THREAD_MUTATION)
        if reply_thread_errors:
            errors["addPullRequestReviewThreadReply"] = reply_thread_errors

        reply_comment_errors = self.validate_query(REPLY_COMMENT_MUTATION)
        if reply_comment_errors:
            errors["addPullRequestReviewComment"] = reply_comment_errors

        return errors

    def validate_queries(self) -> dict[str, list[dict[str, Any]]]:
        """Validate all queries defined in the codebase.

        Returns:
            Dictionary mapping query names to validation errors
        """
        from ..parsers.graphql_queries import ReviewThreadQueryBuilder

        errors = {}

        # Create query builder
        builder = ReviewThreadQueryBuilder()

        # Validate review threads query
        review_query = builder.build_query()
        review_errors = self.validate_query(review_query)
        if review_errors:
            errors["reviewThreads"] = review_errors

        return errors

    def generate_compatibility_report(self) -> dict[str, Any]:
        """Generate a comprehensive compatibility report.

        Returns:
            Report containing validation results and recommendations
        """
        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "schema_version": self.get_schema_version(),
            "queries": self.validate_queries(),
            "mutations": self.validate_mutations(),
            "deprecations": [],
            "recommendations": [],
        }

        # Add recommendations based on errors
        all_errors: list[dict[str, Any]] = []
        queries = report.get("queries", {})
        mutations = report.get("mutations", {})
        if isinstance(queries, dict):
            all_errors.extend(queries.get("reviewThreads", []))
        if isinstance(mutations, dict):
            all_errors.extend(mutations.get("resolveReviewThread", []))
            all_errors.extend(mutations.get("unresolveReviewThread", []))

        if all_errors:
            report["recommendations"].append(
                "Update GraphQL queries to match current GitHub schema"
            )

        return report
