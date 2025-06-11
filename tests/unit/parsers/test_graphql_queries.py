"""Tests for GraphQL query builders."""

import pytest

from toady.parsers.graphql_queries import (
    PullRequestQueryBuilder,
    ReviewThreadQueryBuilder,
    _validate_cursor,
    build_open_prs_query,
    build_review_threads_query,
    create_paginated_query,
    create_paginated_query_variables,
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

        assert (
            "query($owner: String!, $repo: String!, $number: Int!, $after: String)"
            in query
        )
        assert "reviewThreads(first: 25, after: $after)" in query
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
        # Empty cursor should not cause exception, just return query without cursor
        query = create_paginated_query(after_cursor=None)
        assert "$after" not in query

    def test_valid_base64_cursor(self) -> None:
        """Test pagination with valid Base64 cursor."""
        valid_cursor = "Y3Vyc29yOnYyOpHOBZnKHA=="
        query = create_paginated_query(after_cursor=valid_cursor)

        # Should use GraphQL variables instead of string interpolation
        assert "$after: String" in query
        assert "after: $after" in query
        assert valid_cursor not in query  # Cursor should not be in query string

    def test_special_characters_in_cursor(self) -> None:
        """Test pagination with special characters in cursor."""
        special_cursor = "abc+123/def="
        query = create_paginated_query(after_cursor=special_cursor)

        # Should use GraphQL variables
        assert "$after: String" in query
        assert "after: $after" in query


class TestCursorValidation:
    """Test cursor validation functionality."""

    def test_validate_cursor_with_valid_base64(self) -> None:
        """Test cursor validation with valid Base64 strings."""
        valid_cursors = [
            "Y3Vyc29yOnYyOpHOBZnKHA==",
            "dGVzdA==",
            "SGVsbG9Xb3JsZA==",
            "YWJjZGVmZ2hpams=",
        ]

        for cursor in valid_cursors:
            assert _validate_cursor(cursor) is True

    def test_validate_cursor_with_invalid_characters(self) -> None:
        """Test cursor validation with invalid characters."""
        invalid_cursors = [
            "invalid-cursor!",
            "cursor with spaces",
            "cursor\nwith\nnewlines",
            "cursor\twith\ttabs",
            "cursor$with$symbols",
            'cursor"with"quotes',
            "cursor'with'quotes",
        ]

        for cursor in invalid_cursors:
            with pytest.raises(ValueError, match="Invalid cursor format"):
                _validate_cursor(cursor)

    def test_validate_cursor_with_empty_string(self) -> None:
        """Test cursor validation with empty string."""
        assert _validate_cursor("") is False

    def test_validate_cursor_with_invalid_base64(self) -> None:
        """Test cursor validation with invalid Base64."""
        # Missing padding - should fail Base64 validation
        with pytest.raises(ValueError, match="Invalid Base64 cursor"):
            _validate_cursor("YWJjZGVmZ2hpams")

        # Too much padding - should fail format validation
        with pytest.raises(ValueError, match="Invalid cursor format"):
            _validate_cursor("YWJjZGVmZ2hpams===")

        # Invalid character should fail at format check
        with pytest.raises(ValueError, match="Invalid cursor format"):
            _validate_cursor("YWJ!ZGVmZ2hpams=")

    def test_validate_cursor_with_too_long_string(self) -> None:
        """Test cursor validation with excessively long string."""
        long_cursor = "a" * 1001  # Exceeds 1000 character limit
        with pytest.raises(ValueError, match="Cursor exceeds maximum length"):
            _validate_cursor(long_cursor)

    def test_validate_cursor_boundary_length(self) -> None:
        """Test cursor validation at boundary length."""
        # Create a valid Base64 string at exactly 1000 characters
        # Base64 encoding produces 4 characters for every 3 input bytes
        # 999 chars + '=' padding = 1000 chars total
        boundary_cursor = "A" * 999 + "="
        assert _validate_cursor(boundary_cursor) is True


class TestPaginatedQueryVariables:
    """Test the create_paginated_query_variables function."""

    def test_variables_without_cursor(self) -> None:
        """Test creating variables without cursor."""
        variables = create_paginated_query_variables("owner", "repo", 123)

        expected = {"owner": "owner", "repo": "repo", "number": 123}

        assert variables == expected

    def test_variables_with_valid_cursor(self) -> None:
        """Test creating variables with valid cursor."""
        cursor = "Y3Vyc29yOnYyOpHOBZnKHA=="
        variables = create_paginated_query_variables("owner", "repo", 123, cursor)

        expected = {"owner": "owner", "repo": "repo", "number": 123, "after": cursor}

        assert variables == expected

    def test_variables_with_invalid_cursor(self) -> None:
        """Test creating variables with invalid cursor."""
        with pytest.raises(ValueError, match="Invalid cursor format"):
            create_paginated_query_variables("owner", "repo", 123, "invalid-cursor!")

    def test_variables_with_special_repo_names(self) -> None:
        """Test creating variables with special repository names."""
        cursor = "dGVzdA=="
        variables = create_paginated_query_variables(
            "user-name", "repo_name", 456, cursor
        )

        expected = {
            "owner": "user-name",
            "repo": "repo_name",
            "number": 456,
            "after": cursor,
        }

        assert variables == expected


class TestSecurityImprovements:
    """Test security improvements in GraphQL query building."""

    def test_query_uses_variables_not_interpolation(self) -> None:
        """Test that queries use GraphQL variables instead of string interpolation."""
        cursor = "Y3Vyc29yOnYyOpHOBZnKHA=="
        query = create_paginated_query(after_cursor=cursor)

        # Ensure cursor is not directly interpolated into query string
        assert cursor not in query

        # Ensure proper GraphQL variable usage
        assert "$after: String" in query
        assert "after: $after" in query

    def test_injection_attack_prevention(self) -> None:
        """Test that potential injection attacks are prevented."""
        malicious_cursors = [
            '") { malicious { field } }',
            'test" } malicious: query {',
            'cursor\\"} injection {',
            'cursor"; DROP TABLE users; --',
        ]

        for malicious_cursor in malicious_cursors:
            with pytest.raises(ValueError):
                create_paginated_query(after_cursor=malicious_cursor)

    def test_query_structure_unchanged_for_none_cursor(self) -> None:
        """Test that query structure is unchanged when no cursor is provided."""
        query_without_cursor = create_paginated_query()

        # Should not contain cursor-related variables when none provided
        assert "$after" not in query_without_cursor
        assert "after:" not in query_without_cursor

    def test_cursor_validation_in_both_functions(self) -> None:
        """Test that cursor validation is applied in both functions."""
        invalid_cursor = "invalid-cursor!"

        # Both functions should validate cursors
        with pytest.raises(ValueError, match="Invalid cursor format"):
            create_paginated_query(after_cursor=invalid_cursor)

        with pytest.raises(ValueError, match="Invalid cursor format"):
            create_paginated_query_variables("owner", "repo", 123, invalid_cursor)


class TestPullRequestQueryBuilder:
    """Test the PullRequestQueryBuilder class."""

    def test_default_initialization(self) -> None:
        """Test default builder initialization."""
        builder = PullRequestQueryBuilder()

        assert builder.should_filter_drafts()  # include_drafts=False by default
        assert builder._limit == 100
        assert builder._states == ["OPEN"]

    def test_include_drafts_setting(self) -> None:
        """Test setting include_drafts flag."""
        builder = PullRequestQueryBuilder()

        # Default should filter drafts
        assert builder.should_filter_drafts()

        # Enable including drafts
        result = builder.include_drafts(True)
        assert result is builder  # Should return self for chaining
        assert not builder.should_filter_drafts()

        # Disable including drafts
        builder.include_drafts(False)
        assert builder.should_filter_drafts()

    def test_limit_setting(self) -> None:
        """Test setting PR limit."""
        builder = PullRequestQueryBuilder()

        # Valid limit
        result = builder.limit(50)
        assert result is builder  # Should return self for chaining
        assert builder._limit == 50

    def test_limit_validation(self) -> None:
        """Test limit validation."""
        builder = PullRequestQueryBuilder()

        # Invalid limits should raise ValueError
        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(0)

        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(101)

        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(-1)

        # Valid limits should work
        builder.limit(1)
        assert builder._limit == 1

        builder.limit(100)
        assert builder._limit == 100

    def test_build_query_structure(self) -> None:
        """Test that built query has correct structure."""
        builder = PullRequestQueryBuilder()
        query = builder.build_query()

        # Check that query contains expected GraphQL structure
        assert "query($owner: String!, $repo: String!)" in query
        assert "repository(owner: $owner, name: $repo)" in query
        assert "states: OPEN" in query
        assert "orderBy: {field: UPDATED_AT, direction: DESC}" in query
        assert "first: 100" in query  # default limit
        assert "pageInfo" in query
        assert "totalCount" in query
        assert "nodes" in query
        assert "number" in query
        assert "title" in query
        assert "author" in query
        assert "headRefName" in query
        assert "baseRefName" in query
        assert "isDraft" in query
        assert "createdAt" in query
        assert "updatedAt" in query
        assert "url" in query
        assert "reviewThreads(first: 1)" in query

    def test_build_query_with_custom_limit(self) -> None:
        """Test query building with custom limit."""
        builder = PullRequestQueryBuilder()
        builder.limit(25)
        query = builder.build_query()

        assert "first: 25" in query

    def test_build_variables(self) -> None:
        """Test building GraphQL variables."""
        builder = PullRequestQueryBuilder()
        variables = builder.build_variables("testowner", "testrepo")

        expected = {
            "owner": "testowner",
            "repo": "testrepo",
        }

        assert variables == expected

    def test_method_chaining(self) -> None:
        """Test that methods can be chained."""
        builder = PullRequestQueryBuilder()

        # All methods should return self for chaining
        result = builder.include_drafts(True).limit(25)

        assert result is builder
        assert not builder.should_filter_drafts()
        assert builder._limit == 25


class TestBuildOpenPRsQuery:
    """Test the build_open_prs_query convenience function."""

    def test_default_configuration(self) -> None:
        """Test default query configuration."""
        builder = build_open_prs_query()

        assert builder.should_filter_drafts()  # include_drafts=False by default
        assert builder._limit == 100

    def test_custom_configuration(self) -> None:
        """Test custom query configuration."""
        builder = build_open_prs_query(include_drafts=True, limit=50)

        assert not builder.should_filter_drafts()
        assert builder._limit == 50

    def test_limit_validation_in_convenience_function(self) -> None:
        """Test that limit validation is applied in convenience function."""
        # This should work
        builder = build_open_prs_query(limit=50)
        assert builder._limit == 50

        # This should fail when we try to set an invalid limit
        builder = build_open_prs_query()
        with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
            builder.limit(0)
