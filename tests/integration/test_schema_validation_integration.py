"""Integration tests for GitHub GraphQL schema validation.

These tests work against the real GitHub API and require proper
authentication via the gh CLI.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from toady.schema_validator import GitHubSchemaValidator, SchemaValidationError


class TestSchemaValidationIntegration:
    """Integration tests for schema validation against real GitHub API."""

    def _check_gh_auth(self):
        """Check if gh CLI is authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @pytest.fixture
    def validator(self):
        """Create a validator instance with temporary cache for integration tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield GitHubSchemaValidator(cache_dir=Path(temp_dir))

    @pytest.mark.integration
    def test_fetch_real_github_schema(self, validator):
        """Test fetching the real GitHub GraphQL schema."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # Fetch the schema
        schema = validator.fetch_schema()

        # Verify basic schema structure
        assert "queryType" in schema
        assert "mutationType" in schema
        assert "types" in schema
        assert len(schema["types"]) > 0

        # Verify essential types exist
        type_names = {t["name"] for t in schema["types"] if t.get("name")}
        assert "Query" in type_names
        assert "Mutation" in type_names
        assert "Repository" in type_names
        assert "PullRequest" in type_names

    @pytest.mark.integration
    def test_validate_review_threads_query_against_real_schema(self, validator):
        """Test validating our review threads query against real GitHub schema."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        from toady.graphql_queries import ReviewThreadQueryBuilder

        # Build our actual query
        builder = ReviewThreadQueryBuilder()
        query = builder.build_query()

        # Validate against real schema
        errors = validator.validate_query(query)

        # Should have no errors (or only warnings)
        critical_errors = [e for e in errors if e.get("severity") != "warning"]
        assert (
            len(critical_errors) == 0
        ), f"Critical validation errors: {critical_errors}"

    @pytest.mark.integration
    def test_validate_resolve_mutations_against_real_schema(self, validator):
        """Test validating resolve/unresolve mutations against real GitHub schema."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        from toady.resolve_mutations import ResolveThreadMutationBuilder

        builder = ResolveThreadMutationBuilder()

        # Test resolve mutation
        resolve_mutation = builder.build_resolve_mutation()
        resolve_errors = validator.validate_query(resolve_mutation)
        critical_resolve_errors = [
            e for e in resolve_errors if e.get("severity") != "warning"
        ]
        assert (
            len(critical_resolve_errors) == 0
        ), f"Resolve mutation errors: {critical_resolve_errors}"

        # Test unresolve mutation
        unresolve_mutation = builder.build_unresolve_mutation()
        unresolve_errors = validator.validate_query(unresolve_mutation)
        critical_unresolve_errors = [
            e for e in unresolve_errors if e.get("severity") != "warning"
        ]
        assert (
            len(critical_unresolve_errors) == 0
        ), f"Unresolve mutation errors: {critical_unresolve_errors}"

    @pytest.mark.integration
    def test_schema_caching_with_real_github_api(self, validator):
        """Test schema caching with real GitHub API."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # First fetch should hit the API
        schema1 = validator.fetch_schema()

        # Verify cache files exist
        assert validator._get_cache_path().exists()
        assert validator._get_cache_metadata_path().exists()

        # Second fetch should use cache
        schema2 = validator.fetch_schema()

        # Should be identical
        assert schema1 == schema2

        # Force refresh should hit API again
        schema3 = validator.fetch_schema(force_refresh=True)
        assert schema3 == schema1

    @pytest.mark.integration
    def test_compatibility_report_with_real_schema(self, validator):
        """Test generating compatibility report with real GitHub schema."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # Generate compatibility report
        report = validator.generate_compatibility_report()

        # Verify report structure
        assert "timestamp" in report
        assert "schema_version" in report
        assert "queries" in report
        assert "mutations" in report
        assert "deprecations" in report
        assert "recommendations" in report

        # Check that our mutations validate
        mutation_errors = report["mutations"]
        for mutation_name, errors in mutation_errors.items():
            critical_errors = [e for e in errors if e.get("severity") != "warning"]
            assert (
                len(critical_errors) == 0
            ), f"Critical errors in {mutation_name}: {critical_errors}"

    @pytest.mark.integration
    def test_deprecation_warnings_with_real_schema(self, validator):
        """Test deprecation detection with real GitHub schema."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # Test a query that might use deprecated fields
        test_query = """
        query {
            repository(owner: "octocat", name: "Hello-World") {
                name
                description
            }
        }
        """

        deprecations = validator.check_deprecations(test_query)
        # We don't assert specific deprecations since they change over time
        # Just verify the method works without error
        assert isinstance(deprecations, list)

    @pytest.mark.integration
    def test_field_suggestions_with_real_schema(self, validator):
        """Test field suggestions with real GitHub schema."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # Test getting suggestions for PullRequest type
        suggestions = validator.get_field_suggestions("PullRequest", "ti")
        assert isinstance(suggestions, list)
        # Should likely include "title"
        assert any("title" in s for s in suggestions)

    @pytest.mark.integration
    def test_schema_version_tracking(self, validator):
        """Test schema version tracking with real GitHub API."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # Get schema version
        version = validator.get_schema_version()
        assert version is not None
        assert len(version) == 12  # Should be first 12 chars of hash

        # Version should be consistent for same schema
        version2 = validator.get_schema_version()
        assert version == version2

    @pytest.mark.integration
    def test_error_handling_with_invalid_auth(self):
        """Test error handling when GitHub authentication fails."""
        # Create validator and temporarily break auth by using invalid command
        validator = GitHubSchemaValidator()

        # Mock the GitHub service to fail
        import unittest.mock

        from toady.github_service import GitHubAuthenticationError

        validator._github_service.run_gh_command = unittest.mock.Mock(
            side_effect=GitHubAuthenticationError("Authentication failed")
        )

        with pytest.raises(SchemaValidationError) as exc_info:
            validator.fetch_schema()

        assert "Failed to fetch GitHub schema" in str(exc_info.value)

    @pytest.mark.integration
    def test_large_query_validation_performance(self, validator):
        """Test validation performance with a large complex query."""
        if not self._check_gh_auth():
            pytest.skip("gh CLI not authenticated - skipping integration test")

        # Create a large query with many nested fields
        large_query = """
        query($owner: String!, $repo: String!) {
            repository(owner: $owner, name: $repo) {
                id
                name
                description
                url
                isPrivate
                isFork
                isArchived
                diskUsage
                stargazerCount
                forkCount
                watchers {
                    totalCount
                }
                issues(first: 100) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        number
                        title
                        body
                        state
                        createdAt
                        updatedAt
                        author {
                            login
                            ... on User {
                                name
                                email
                            }
                        }
                        assignees(first: 10) {
                            nodes {
                                login
                                name
                            }
                        }
                        labels(first: 20) {
                            nodes {
                                id
                                name
                                color
                                description
                            }
                        }
                        comments(first: 50) {
                            totalCount
                            nodes {
                                id
                                body
                                createdAt
                                author {
                                    login
                                }
                            }
                        }
                    }
                }
                pullRequests(first: 100) {
                    totalCount
                    nodes {
                        id
                        number
                        title
                        body
                        state
                        isDraft
                        mergeable
                        createdAt
                        updatedAt
                        author {
                            login
                        }
                        assignees(first: 10) {
                            nodes {
                                login
                            }
                        }
                        reviewRequests(first: 10) {
                            nodes {
                                requestedReviewer {
                                    ... on User {
                                        login
                                    }
                                }
                            }
                        }
                        reviews(first: 50) {
                            nodes {
                                id
                                state
                                submittedAt
                                author {
                                    login
                                }
                                comments(first: 100) {
                                    nodes {
                                        id
                                        body
                                        path
                                        line
                                        originalLine
                                        diffHunk
                                        author {
                                            login
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        import time

        start_time = time.time()
        errors = validator.validate_query(large_query)
        validation_time = time.time() - start_time

        # Validation should complete within reasonable time (10 seconds)
        assert validation_time < 10.0, f"Validation took too long: {validation_time}s"

        # Query should be valid (only warnings acceptable)
        critical_errors = [e for e in errors if e.get("severity") != "warning"]
        assert (
            len(critical_errors) == 0
        ), f"Critical validation errors: {critical_errors}"
