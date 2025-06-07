"""Tests for GraphQL query builders."""

import pytest

from toady.graphql_queries import (
    ReviewThreadQueryBuilder,
    build_review_threads_query,
    create_paginated_query,
)


class TestReviewThreadQueryBuilder:
    """Test the ReviewThreadQueryBuilder class."""

    def test_default_initialization(self) -> None:
        """Test default builder initialization."""
        builder = ReviewThreadQueryBuilder()

        assert builder.should_filter_resolved()  # include_resolved=False by default
        assert builder._limit == 100
        assert builder._comment_limit == 10

    def test_include_resolved_setting(self) -> None:
        """Test setting include_resolved flag."""
        builder = ReviewThreadQueryBuilder()

        # Default should not include resolved
        assert builder.should_filter_resolved()

        # Enable including resolved
        result = builder.include_resolved(True)
        assert result is builder  # Should return self for chaining
        assert not builder.should_filter_resolved()

        # Disable including resolved
        builder.include_resolved(False)
        assert builder.should_filter_resolved()

    def test_limit_setting(self) -> None:
        """Test setting thread limit."""
        builder = ReviewThreadQueryBuilder()

        # Valid limit
        result = builder.limit(50)
        assert result is builder  # Should return self for chaining
        assert builder._limit == 50

    def test_limit_validation(self) -> None:
        """Test limit validation."""
        builder = ReviewThreadQueryBuilder()

        # Test invalid limits
        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(0)

        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(101)

        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(-1)

    def test_comment_limit_setting(self) -> None:
        """Test setting comment limit."""
        builder = ReviewThreadQueryBuilder()

        # Valid comment limit
        result = builder.comment_limit(20)
        assert result is builder  # Should return self for chaining
        assert builder._comment_limit == 20

    def test_comment_limit_validation(self) -> None:
        """Test comment limit validation."""
        builder = ReviewThreadQueryBuilder()

        # Test invalid comment limits
        with pytest.raises(ValueError, match="Comment limit must be between 1 and 50"):
            builder.comment_limit(0)

        with pytest.raises(ValueError, match="Comment limit must be between 1 and 50"):
            builder.comment_limit(51)

        with pytest.raises(ValueError, match="Comment limit must be between 1 and 50"):
            builder.comment_limit(-1)

    def test_method_chaining(self) -> None:
        """Test that all methods support chaining."""
        builder = ReviewThreadQueryBuilder()

        result = builder.include_resolved(True).limit(75).comment_limit(15)

        assert result is builder
        assert not builder.should_filter_resolved()
        assert builder._limit == 75
        assert builder._comment_limit == 15

    def test_build_query_structure(self) -> None:
        """Test that build_query produces valid GraphQL structure."""
        builder = ReviewThreadQueryBuilder()
        query = builder.build_query()

        # Check that key GraphQL elements are present
        assert "query($owner: String!, $repo: String!, $number: Int!)" in query
        assert "repository(owner: $owner, name: $repo)" in query
        assert "pullRequest(number: $number)" in query
        assert "reviewThreads(first:" in query
        assert "pageInfo" in query
        assert "hasNextPage" in query
        assert "endCursor" in query
        assert "isResolved" in query
        assert "comments(first:" in query

    def test_build_query_with_custom_limits(self) -> None:
        """Test build_query with custom limits."""
        builder = ReviewThreadQueryBuilder()
        builder.limit(25).comment_limit(5)
        query = builder.build_query()

        # Check that custom limits are applied
        assert "reviewThreads(first: 25)" in query
        assert "comments(first: 5)" in query

    def test_build_variables(self) -> None:
        """Test building GraphQL variables."""
        builder = ReviewThreadQueryBuilder()
        variables = builder.build_variables("octocat", "Hello-World", 123)

        expected = {"owner": "octocat", "repo": "Hello-World", "number": 123}

        assert variables == expected

    def test_build_variables_with_special_characters(self) -> None:
        """Test building variables with special characters."""
        builder = ReviewThreadQueryBuilder()
        variables = builder.build_variables("user-name", "repo_name", 456)

        expected = {"owner": "user-name", "repo": "repo_name", "number": 456}

        assert variables == expected


class TestBuildReviewThreadsQuery:
    """Test the build_review_threads_query convenience function."""

    def test_default_parameters(self) -> None:
        """Test function with default parameters."""
        builder = build_review_threads_query()

        assert builder.should_filter_resolved()  # include_resolved=False
        assert builder._limit == 100
        assert builder._comment_limit == 10

    def test_custom_parameters(self) -> None:
        """Test function with custom parameters."""
        builder = build_review_threads_query(
            include_resolved=True, limit=50, comment_limit=20
        )

        assert not builder.should_filter_resolved()  # include_resolved=True
        assert builder._limit == 50
        assert builder._comment_limit == 20

    def test_returns_configured_builder(self) -> None:
        """Test that function returns properly configured builder."""
        builder = build_review_threads_query(include_resolved=True, limit=75)
        query = builder.build_query()

        # Verify the query reflects the configuration
        assert "reviewThreads(first: 75)" in query
        assert not builder.should_filter_resolved()


class TestCreatePaginatedQuery:
    """Test the create_paginated_query function."""

    def test_query_without_cursor(self) -> None:
        """Test creating paginated query without cursor."""
        query = create_paginated_query(limit=50)

        assert "query($owner: String!, $repo: String!, $number: Int!)" in query
        assert "reviewThreads(first: 50)" in query
        assert "after:" not in query
        assert "pageInfo" in query
        assert "totalCount" in query

    def test_query_with_cursor(self) -> None:
        """Test creating paginated query with cursor."""
        cursor = "Y3Vyc29yOnYyOpHOBZnKHA=="
        query = create_paginated_query(limit=25, after_cursor=cursor)

        assert "query($owner: String!, $repo: String!, $number: Int!)" in query
        assert f'reviewThreads(first: 25, after: "{cursor}")' in query
        assert "pageInfo" in query
        assert "totalCount" in query

    def test_query_includes_required_fields(self) -> None:
        """Test that paginated query includes all required fields."""
        query = create_paginated_query()

        # Check for essential fields
        essential_fields = [
            "id",
            "isResolved",
            "isOutdated",
            "line",
            "path",
            "comments",
            "author",
            "login",
            "body",
            "createdAt",
            "url",
        ]

        for field in essential_fields:
            assert field in query

    def test_query_structure_valid(self) -> None:
        """Test that generated query has valid GraphQL structure."""
        query = create_paginated_query(limit=100)

        # Basic structure validation
        assert query.startswith("query(")
        assert query.count("{") == query.count("}")  # Balanced braces
        assert "repository" in query
        assert "pullRequest" in query
        assert "reviewThreads" in query


class TestGraphQLQueryEdgeCases:
    """Test edge cases and error conditions."""

    def test_boundary_values_for_limits(self) -> None:
        """Test boundary values for various limits."""
        builder = ReviewThreadQueryBuilder()

        # Test minimum valid values
        builder.limit(1).comment_limit(1)
        assert builder._limit == 1
        assert builder._comment_limit == 1

        # Test maximum valid values
        builder.limit(100).comment_limit(50)
        assert builder._limit == 100
        assert builder._comment_limit == 50

    def test_query_consistency_across_builds(self) -> None:
        """Test that multiple calls to build_query return consistent results."""
        builder = ReviewThreadQueryBuilder().limit(42).comment_limit(7)

        query1 = builder.build_query()
        query2 = builder.build_query()

        assert query1 == query2

    def test_variables_with_edge_case_values(self) -> None:
        """Test building variables with edge case values."""
        builder = ReviewThreadQueryBuilder()

        # Test with minimal valid PR number
        variables = builder.build_variables("a", "b", 1)
        assert variables["number"] == 1

        # Test with large PR number
        variables = builder.build_variables("owner", "repo", 999999)
        assert variables["number"] == 999999

    def test_empty_cursor_handling(self) -> None:
        """Test pagination with empty cursor."""
        query = create_paginated_query(after_cursor="")

        # Empty cursor should still be included in query
        assert 'after: ""' in query

    def test_special_characters_in_cursor(self) -> None:
        """Test pagination with special characters in cursor."""
        special_cursor = "abc+123/def="
        query = create_paginated_query(after_cursor=special_cursor)

        assert f'after: "{special_cursor}"' in query
