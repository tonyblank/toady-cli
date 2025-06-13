"""Tests for GraphQL schema validation functionality."""

from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock

import pytest

from toady.validators.schema_validator import (
    GitHubSchemaValidator,
    SchemaValidationError,
)


class TestGitHubSchemaValidator:
    """Test cases for GitHubSchemaValidator."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def validator(self, temp_cache_dir):
        """Create a validator instance with temporary cache."""
        return GitHubSchemaValidator(
            cache_dir=temp_cache_dir,
            cache_ttl=timedelta(hours=1),
        )

    @pytest.fixture
    def mock_schema(self):
        """Create a mock GitHub GraphQL schema."""
        return {
            "queryType": {"name": "Query"},
            "mutationType": {"name": "Mutation"},
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "fields": [
                        {
                            "name": "repository",
                            "args": [
                                {
                                    "name": "owner",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {"name": "String"},
                                    },
                                },
                                {
                                    "name": "name",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {"name": "String"},
                                    },
                                },
                            ],
                            "type": {"name": "Repository"},
                            "isDeprecated": False,
                        }
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "Mutation",
                    "fields": [
                        {
                            "name": "resolveReviewThread",
                            "args": [
                                {
                                    "name": "input",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {"name": "ResolveReviewThreadInput"},
                                    },
                                },
                            ],
                            "type": {"name": "ResolveReviewThreadPayload"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "unresolveReviewThread",
                            "args": [
                                {
                                    "name": "input",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {
                                            "name": "UnresolveReviewThreadInput"
                                        },
                                    },
                                },
                            ],
                            "type": {"name": "UnresolveReviewThreadPayload"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "addPullRequestReviewThreadReply",
                            "args": [
                                {
                                    "name": "input",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {
                                            "name": (
                                                "AddPullRequestReviewThreadReplyInput"
                                            )
                                        },
                                    },
                                },
                            ],
                            "type": {"name": "AddPullRequestReviewThreadReplyPayload"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "addPullRequestReviewComment",
                            "args": [
                                {
                                    "name": "input",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {
                                            "name": "AddPullRequestReviewCommentInput"
                                        },
                                    },
                                },
                            ],
                            "type": {"name": "AddPullRequestReviewCommentPayload"},
                            "isDeprecated": False,
                        },
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "Repository",
                    "fields": [
                        {
                            "name": "pullRequest",
                            "args": [
                                {
                                    "name": "number",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {"name": "Int"},
                                    },
                                },
                            ],
                            "type": {"name": "PullRequest"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "name",
                            "args": [],
                            "type": {"name": "String"},
                            "isDeprecated": False,
                        },
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "PullRequest",
                    "fields": [
                        {
                            "name": "id",
                            "args": [],
                            "type": {"name": "ID"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "number",
                            "args": [],
                            "type": {"name": "Int"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "title",
                            "args": [],
                            "type": {"name": "String"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "reviewThreads",
                            "args": [
                                {"name": "first", "type": {"name": "Int"}},
                                {"name": "after", "type": {"name": "String"}},
                            ],
                            "type": {"name": "ReviewThreadConnection"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "oldField",
                            "args": [],
                            "type": {"name": "String"},
                            "isDeprecated": True,
                            "deprecationReason": "Use newField instead",
                        },
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "ReviewThreadConnection",
                    "fields": [
                        {
                            "name": "nodes",
                            "args": [],
                            "type": {
                                "kind": "LIST",
                                "ofType": {"name": "ReviewThread"},
                            },
                            "isDeprecated": False,
                        },
                        {
                            "name": "pageInfo",
                            "args": [],
                            "type": {"name": "PageInfo"},
                            "isDeprecated": False,
                        },
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "ReviewThread",
                    "fields": [
                        {
                            "name": "id",
                            "args": [],
                            "type": {"name": "ID"},
                            "isDeprecated": False,
                        },
                        {
                            "name": "isResolved",
                            "args": [],
                            "type": {"name": "Boolean"},
                            "isDeprecated": False,
                        },
                    ],
                },
            ],
        }

    def test_init(self, temp_cache_dir):
        """Test validator initialization."""
        validator = GitHubSchemaValidator(
            cache_dir=temp_cache_dir,
            cache_ttl=timedelta(hours=2),
        )
        assert validator.cache_dir == temp_cache_dir
        assert validator.cache_ttl == timedelta(hours=2)
        assert validator._schema is None
        assert validator._type_map is None

    def test_cache_paths(self, validator, temp_cache_dir):
        """Test cache path generation."""
        assert validator._get_cache_path() == temp_cache_dir / "github_schema.json"
        assert (
            validator._get_cache_metadata_path()
            == temp_cache_dir / "github_schema_metadata.json"
        )

    def test_cache_validity_no_metadata(self, validator):
        """Test cache validity when metadata doesn't exist."""
        assert not validator._is_cache_valid()

    def test_cache_validity_expired(self, validator, temp_cache_dir):
        """Test cache validity with expired cache."""
        metadata_path = validator._get_cache_metadata_path()
        metadata = {
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "schema_hash": "test_hash",
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        assert not validator._is_cache_valid()

    def test_cache_validity_valid(self, validator, temp_cache_dir):
        """Test cache validity with valid cache."""
        metadata_path = validator._get_cache_metadata_path()
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "schema_hash": "test_hash",
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        assert validator._is_cache_valid()

    def test_load_cached_schema_no_cache(self, validator):
        """Test loading schema when no cache exists."""
        assert validator._load_cached_schema() is None

    def test_load_cached_schema_invalid_json(self, validator, temp_cache_dir):
        """Test loading schema with invalid JSON."""
        # Create valid metadata
        metadata_path = validator._get_cache_metadata_path()
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "schema_hash": "test_hash",
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Create invalid schema file
        cache_path = validator._get_cache_path()
        with open(cache_path, "w") as f:
            f.write("invalid json")

        assert validator._load_cached_schema() is None

    def test_save_schema_to_cache(self, validator, mock_schema):
        """Test saving schema to cache."""
        validator._save_schema_to_cache(mock_schema)

        # Check schema file
        cache_path = validator._get_cache_path()
        assert cache_path.exists()
        with open(cache_path) as f:
            saved_schema = json.load(f)
        assert saved_schema == mock_schema

        # Check metadata file
        metadata_path = validator._get_cache_metadata_path()
        assert metadata_path.exists()
        with open(metadata_path) as f:
            metadata = json.load(f)
        assert "timestamp" in metadata
        assert "schema_hash" in metadata

    def test_fetch_schema_success(self, validator, mock_schema):
        """Test successful schema fetching."""
        # Mock the GitHub service's run_gh_command method

        mock_result = Mock()
        mock_result.stdout = json.dumps({"data": {"__schema": mock_schema}})
        validator._github_service.run_gh_command = Mock(return_value=mock_result)

        schema = validator.fetch_schema()

        assert schema == mock_schema
        assert validator._schema == mock_schema
        assert validator._type_map is not None
        validator._github_service.run_gh_command.assert_called_once()

        # Verify cache was saved
        cache_path = validator._get_cache_path()
        assert cache_path.exists()

    def test_fetch_schema_from_cache(self, validator, mock_schema):
        """Test fetching schema from cache."""
        # Save schema to cache
        validator._save_schema_to_cache(mock_schema)

        # Mock the GitHub service (should not be called)

        validator._github_service.run_gh_command = Mock()

        # Fetch should use cache
        schema = validator.fetch_schema()

        assert schema == mock_schema
        validator._github_service.run_gh_command.assert_not_called()

    def test_fetch_schema_force_refresh(self, validator, mock_schema):
        """Test forcing schema refresh."""
        # Save schema to cache
        validator._save_schema_to_cache(mock_schema)

        # Mock the GitHub service

        mock_result = Mock()
        mock_result.stdout = json.dumps({"data": {"__schema": mock_schema}})
        validator._github_service.run_gh_command = Mock(return_value=mock_result)

        # Force refresh
        schema = validator.fetch_schema(force_refresh=True)

        assert schema == mock_schema
        validator._github_service.run_gh_command.assert_called_once()

    def test_fetch_schema_api_error(self, validator):
        """Test schema fetching with API error."""

        validator._github_service.run_gh_command = Mock(
            side_effect=Exception("API error")
        )

        with pytest.raises(SchemaValidationError) as exc_info:
            validator.fetch_schema()

        assert "Failed to fetch GitHub schema" in str(exc_info.value)

    def test_fetch_schema_invalid_response(self, validator):
        """Test schema fetching with invalid response."""

        mock_result = Mock()
        mock_result.stdout = json.dumps({"error": "Invalid query"})
        validator._github_service.run_gh_command = Mock(return_value=mock_result)

        with pytest.raises(SchemaValidationError) as exc_info:
            validator.fetch_schema()

        assert "Invalid schema response" in str(exc_info.value)

    def test_build_type_map(self, validator, mock_schema):
        """Test building type map from schema."""
        validator._schema = mock_schema
        validator._build_type_map()

        assert validator._type_map is not None
        assert "Query" in validator._type_map
        assert "Mutation" in validator._type_map
        assert "Repository" in validator._type_map
        assert "PullRequest" in validator._type_map

    def test_get_type(self, validator, mock_schema):
        """Test getting type by name."""
        validator._schema = mock_schema
        validator._build_type_map()

        query_type = validator.get_type("Query")
        assert query_type is not None
        assert query_type["name"] == "Query"

        unknown_type = validator.get_type("UnknownType")
        assert unknown_type is None

    def test_validate_empty_query(self, validator, mock_schema):
        """Test validating empty query."""
        validator._schema = mock_schema
        validator._build_type_map()

        errors = validator.validate_query("")
        assert len(errors) == 1
        assert errors[0]["type"] == "empty_query"

    def test_validate_invalid_operation(self, validator, mock_schema):
        """Test validating query with invalid operation."""
        validator._schema = mock_schema
        validator._build_type_map()

        # Test with truly invalid syntax that can't be parsed
        errors = validator.validate_query("invalid syntax {")
        assert len(errors) == 1
        assert errors[0]["type"] == "parse_error"

    def test_validate_valid_query(self, validator, mock_schema):
        """Test validating a valid query."""
        validator._schema = mock_schema
        validator._build_type_map()

        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                pullRequest(number: $number) {
                    id
                    title
                }
            }
        }
        """
        errors = validator.validate_query(query)
        assert len(errors) == 0

    def test_validate_unknown_field(self, validator, mock_schema):
        """Test validating query with unknown field."""
        validator._schema = mock_schema
        validator._build_type_map()

        query = """
        query {
            repository(owner: "test", name: "repo") {
                unknownField
            }
        }
        """
        errors = validator.validate_query(query)
        assert len(errors) > 0
        assert any(e["type"] == "unknown_field" for e in errors)

    def test_validate_deprecated_field(self, validator, mock_schema):
        """Test validating query with deprecated field."""
        validator._schema = mock_schema
        validator._build_type_map()

        query = """
        query {
            repository(owner: "test", name: "repo") {
                pullRequest(number: 1) {
                    oldField
                }
            }
        }
        """
        errors = validator.validate_query(query)
        assert any(e["type"] == "deprecated_field" for e in errors)
        assert any("Use newField instead" in e["message"] for e in errors)

    def test_validate_missing_required_argument(self, validator, mock_schema):
        """Test validating query with missing required argument."""
        validator._schema = mock_schema
        validator._build_type_map()

        query = """
        query {
            repository(owner: "test") {
                name
            }
        }
        """
        errors = validator.validate_query(query)
        assert any(e["type"] == "missing_argument" for e in errors)

    def test_validate_unknown_argument(self, validator, mock_schema):
        """Test validating query with unknown argument."""
        validator._schema = mock_schema
        validator._build_type_map()

        query = """
        query {
            repository(owner: "test", name: "repo", unknown: "arg") {
                name
            }
        }
        """
        errors = validator.validate_query(query)
        assert any(e["type"] == "unknown_argument" for e in errors)

    def test_get_field_suggestions(self, validator, mock_schema):
        """Test getting field suggestions."""
        validator._schema = mock_schema
        validator._build_type_map()

        suggestions = validator.get_field_suggestions("PullRequest", "tit")
        assert "title" in suggestions

        suggestions = validator.get_field_suggestions("UnknownType", "field")
        assert len(suggestions) == 0

    def test_validate_mutations(self, validator, mock_schema):
        """Test validating mutations from codebase."""
        validator._schema = mock_schema
        validator._build_type_map()

        errors = validator.validate_mutations()
        # The mutations should be found even if arguments don't match the mock schema
        # Test that the mutations are being parsed and validated
        assert isinstance(errors, dict)
        # We expect some errors with the mock schema since it doesn't have
        # complete input types
        for mutation_name, _mutation_errors in errors.items():
            assert mutation_name in [
                "resolveReviewThread",
                "unresolveReviewThread",
                "addPullRequestReviewThreadReply",
                "addPullRequestReviewComment",
            ]

    def test_validate_queries_from_codebase(self, validator, mock_schema):
        """Test validating queries from codebase."""
        validator._schema = mock_schema
        validator._build_type_map()

        errors = validator.validate_queries()
        # The actual query in the codebase might have fields not in our mock schema
        # This is expected - the test verifies the validation process works
        assert isinstance(errors, dict)

    def test_get_schema_version(self, validator, mock_schema):
        """Test getting schema version."""
        validator._schema = mock_schema

        version = validator.get_schema_version()
        assert version is not None
        assert len(version) == 12  # First 12 chars of SHA256

    def test_generate_compatibility_report(self, validator, mock_schema):
        """Test generating compatibility report."""
        validator._schema = mock_schema
        validator._build_type_map()

        report = validator.generate_compatibility_report()

        assert "timestamp" in report
        assert "schema_version" in report
        assert "queries" in report
        assert "mutations" in report
        assert "deprecations" in report
        assert "recommendations" in report

    def test_schema_validation_error(self):
        """Test SchemaValidationError class."""
        errors = [{"type": "test", "message": "Test error"}]
        suggestions = ["Fix this", "Try that"]

        error = SchemaValidationError("Test error", errors, suggestions)

        assert str(error) == "Test error"
        assert error.errors == errors
        assert error.suggestions == suggestions

    def test_resolve_field_type(self, validator):
        """Test resolving field types."""
        # Simple type
        type_ref = {"kind": "OBJECT", "name": "String"}
        assert validator._resolve_field_type(type_ref) == "String"

        # NON_NULL wrapper
        type_ref = {"kind": "NON_NULL", "ofType": {"kind": "OBJECT", "name": "String"}}
        assert validator._resolve_field_type(type_ref) == "String"

        # LIST wrapper
        type_ref = {"kind": "LIST", "ofType": {"kind": "OBJECT", "name": "String"}}
        assert validator._resolve_field_type(type_ref) == "String"

        # Nested wrappers
        type_ref = {
            "kind": "NON_NULL",
            "ofType": {"kind": "LIST", "ofType": {"kind": "OBJECT", "name": "String"}},
        }
        assert validator._resolve_field_type(type_ref) == "String"

        # None
        assert validator._resolve_field_type(None) is None

    def test_is_required_type(self, validator):
        """Test checking if type is required."""
        # Required type
        type_ref = {"kind": "NON_NULL", "ofType": {"name": "String"}}
        assert validator._is_required_type(type_ref) is True

        # Optional type
        type_ref = {"kind": "OBJECT", "name": "String"}
        assert validator._is_required_type(type_ref) is False

        # None
        assert validator._is_required_type(None) is False


class TestSchemaValidatorEdgeCases:
    """Test edge cases for schema validator to improve coverage."""

    def test_is_cache_valid_json_decode_error(self, tmp_path):
        """Test cache validation with invalid JSON in metadata."""
        cache_dir = tmp_path / ".toady"
        cache_dir.mkdir()

        # Create invalid JSON metadata file
        metadata_file = cache_dir / "schema_metadata.json"
        metadata_file.write_text("invalid json content")

        validator = GitHubSchemaValidator(cache_dir=cache_dir)
        assert validator._is_cache_valid() is False

    def test_is_cache_valid_key_error(self, tmp_path):
        """Test cache validation with missing timestamp key."""
        cache_dir = tmp_path / ".toady"
        cache_dir.mkdir()

        # Create metadata file without timestamp key
        metadata_file = cache_dir / "schema_metadata.json"
        metadata_file.write_text('{"some_other_key": "value"}')

        validator = GitHubSchemaValidator(cache_dir=cache_dir)
        assert validator._is_cache_valid() is False

    def test_is_cache_valid_value_error(self, tmp_path):
        """Test cache validation with invalid timestamp format."""
        cache_dir = tmp_path / ".toady"
        cache_dir.mkdir()

        # Create metadata file with invalid timestamp format
        metadata_file = cache_dir / "schema_metadata.json"
        metadata_file.write_text('{"timestamp": "invalid-timestamp-format"}')

        validator = GitHubSchemaValidator(cache_dir=cache_dir)
        assert validator._is_cache_valid() is False

    def test_load_cached_schema_not_exists(self, tmp_path):
        """Test loading cached schema when file doesn't exist."""
        cache_dir = tmp_path / ".toady"
        cache_dir.mkdir()

        validator = GitHubSchemaValidator(cache_dir=cache_dir)
        # Create valid metadata but no schema file
        metadata_file = cache_dir / "schema_metadata.json"
        metadata_file.write_text(f'{{"timestamp": "{datetime.now().isoformat()}"}}')

        result = validator._load_cached_schema()
        assert result is None

    def test_load_cached_schema_invalid_json(self, tmp_path):
        """Test loading cached schema with invalid JSON."""
        cache_dir = tmp_path / ".toady"
        cache_dir.mkdir()

        # Create valid metadata
        metadata_file = cache_dir / "schema_metadata.json"
        metadata_file.write_text(f'{{"timestamp": "{datetime.now().isoformat()}"}}')

        # Create invalid JSON schema file
        schema_file = cache_dir / "github_schema.json"
        schema_file.write_text("invalid json content")

        validator = GitHubSchemaValidator(cache_dir=cache_dir)

        from unittest.mock import patch

        with patch.object(validator, "_is_cache_valid", return_value=True):
            result = validator._load_cached_schema()
            assert result is None
