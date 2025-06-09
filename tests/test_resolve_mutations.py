"""Tests for the resolve mutations module."""

import pytest

from toady.resolve_mutations import (
    ResolveThreadMutationBuilder,
    create_resolve_mutation,
    create_unresolve_mutation,
)


class TestResolveThreadMutationBuilder:
    """Test the ResolveThreadMutationBuilder class."""

    def test_init(self) -> None:
        """Test ResolveThreadMutationBuilder initialization."""
        builder = ResolveThreadMutationBuilder()
        assert builder is not None

    def test_build_resolve_mutation(self) -> None:
        """Test building resolve mutation."""
        builder = ResolveThreadMutationBuilder()
        mutation = builder.build_resolve_mutation()

        assert "mutation ResolveReviewThread" in mutation
        assert "$threadId: ID!" in mutation
        assert "resolveReviewThread(input: {threadId: $threadId})" in mutation
        assert "thread {" in mutation
        assert "id" in mutation
        assert "isResolved" in mutation

    def test_build_unresolve_mutation(self) -> None:
        """Test building unresolve mutation."""
        builder = ResolveThreadMutationBuilder()
        mutation = builder.build_unresolve_mutation()

        assert "mutation UnresolveReviewThread" in mutation
        assert "$threadId: ID!" in mutation
        assert "unresolveReviewThread(input: {threadId: $threadId})" in mutation
        assert "thread {" in mutation
        assert "id" in mutation
        assert "isResolved" in mutation

    def test_build_variables_with_numeric_id(self) -> None:
        """Test building variables with numeric thread ID."""
        builder = ResolveThreadMutationBuilder()
        variables = builder.build_variables("123456789")

        assert variables == {"threadId": "123456789"}

    def test_build_variables_with_node_id(self) -> None:
        """Test building variables with GitHub node ID."""
        builder = ResolveThreadMutationBuilder()
        variables = builder.build_variables("PRT_kwDOABcD12MAAAABcDE3fg")

        assert variables == {"threadId": "PRT_kwDOABcD12MAAAABcDE3fg"}

    def test_build_variables_empty_thread_id(self) -> None:
        """Test building variables with empty thread ID."""
        builder = ResolveThreadMutationBuilder()

        with pytest.raises(ValueError) as exc_info:
            builder.build_variables("")
        assert "Thread ID cannot be empty" in str(exc_info.value)

    def test_build_variables_whitespace_thread_id(self) -> None:
        """Test building variables with whitespace-only thread ID."""
        builder = ResolveThreadMutationBuilder()

        with pytest.raises(ValueError) as exc_info:
            builder.build_variables("   ")
        assert "Thread ID cannot be empty" in str(exc_info.value)

    def test_build_variables_invalid_format(self) -> None:
        """Test building variables with invalid thread ID format."""
        builder = ResolveThreadMutationBuilder()

        with pytest.raises(ValueError) as exc_info:
            builder.build_variables("invalid-id")
        assert "Thread ID must start with one of" in str(exc_info.value)

    def test_build_variables_short_node_id(self) -> None:
        """Test building variables with short node ID."""
        builder = ResolveThreadMutationBuilder()

        # Short PRT_ IDs should fail with new validation
        with pytest.raises(ValueError, match="appears too short to be valid"):
            builder.build_variables("PRT_abc")

    def test_build_variables_strips_whitespace(self) -> None:
        """Test that build_variables strips whitespace from thread ID."""
        builder = ResolveThreadMutationBuilder()
        variables = builder.build_variables("  123456789  ")

        assert variables == {"threadId": "123456789"}

    def test_build_variables_various_valid_formats(self) -> None:
        """Test building variables with various valid thread ID formats."""
        builder = ResolveThreadMutationBuilder()

        test_cases = [
            "1",
            "123",
            "123456789",
            "PRT_kwDOABcD12M",
            "PRT_kwDOABcD12MAAAABcDE3fg",
            "PRRT_kwDOABcD12M",
            "RT_kwDOABcD12M",
        ]

        for thread_id in test_cases:
            variables = builder.build_variables(thread_id)
            assert variables == {"threadId": thread_id}

    def test_build_variables_various_invalid_formats(self) -> None:
        """Test building variables with various invalid thread ID formats."""
        builder = ResolveThreadMutationBuilder()

        # Test cases that should still raise ValueError (not numeric, not PRT_ prefix)
        test_cases = [
            "abc123",  # Invalid: starts with letters
            "123abc",  # Invalid: ends with letters
            "IC_123",  # Invalid: wrong prefix
            "12.34",  # Invalid: contains decimal
            "-123",  # Invalid: negative number
            "123 456",  # Invalid: contains space
        ]

        for thread_id in test_cases:
            with pytest.raises(ValueError):
                builder.build_variables(thread_id)

        # Test cases that should now be accepted (longer node IDs with valid prefixes)
        valid_node_cases = [
            "PRT_kwDOABcD12M",  # Valid PRT_ ID
            "PRRT_kwDOABcD12M",  # Valid PRRT_ ID
            "RT_kwDOABcD12M",  # Valid RT_ ID
        ]

        for thread_id in valid_node_cases:
            variables = builder.build_variables(thread_id)
            assert variables == {"threadId": thread_id}


class TestCreateResolveMutation:
    """Test the create_resolve_mutation function."""

    def test_create_resolve_mutation_success(self) -> None:
        """Test successful creation of resolve mutation."""
        mutation, variables = create_resolve_mutation("123456789")

        assert "mutation ResolveReviewThread" in mutation
        assert variables == {"threadId": "123456789"}

    def test_create_resolve_mutation_with_node_id(self) -> None:
        """Test creating resolve mutation with GitHub node ID."""
        mutation, variables = create_resolve_mutation("PRT_kwDOABcD12MAAAABcDE3fg")

        assert "mutation ResolveReviewThread" in mutation
        assert variables == {"threadId": "PRT_kwDOABcD12MAAAABcDE3fg"}

    def test_create_resolve_mutation_with_prrt_node_id(self) -> None:
        """Test creating resolve mutation with PRRT_ GitHub node ID."""
        mutation, variables = create_resolve_mutation("PRRT_kwDOO3WQIc5RvXMO")

        assert "mutation ResolveReviewThread" in mutation
        assert variables == {"threadId": "PRRT_kwDOO3WQIc5RvXMO"}

    def test_create_resolve_mutation_with_rt_node_id(self) -> None:
        """Test creating resolve mutation with RT_ GitHub node ID."""
        mutation, variables = create_resolve_mutation("RT_kwDOABcD12MAAAABcDE3fg")

        assert "mutation ResolveReviewThread" in mutation
        assert variables == {"threadId": "RT_kwDOABcD12MAAAABcDE3fg"}

    def test_create_resolve_mutation_invalid_id(self) -> None:
        """Test creating resolve mutation with invalid thread ID."""
        with pytest.raises(ValueError) as exc_info:
            create_resolve_mutation("invalid-id")
        assert "Thread ID must start with one of" in str(exc_info.value)


class TestCreateUnresolveMutation:
    """Test the create_unresolve_mutation function."""

    def test_create_unresolve_mutation_success(self) -> None:
        """Test successful creation of unresolve mutation."""
        mutation, variables = create_unresolve_mutation("123456789")

        assert "mutation UnresolveReviewThread" in mutation
        assert variables == {"threadId": "123456789"}

    def test_create_unresolve_mutation_with_node_id(self) -> None:
        """Test creating unresolve mutation with GitHub node ID."""
        mutation, variables = create_unresolve_mutation("PRT_kwDOABcD12MAAAABcDE3fg")

        assert "mutation UnresolveReviewThread" in mutation
        assert variables == {"threadId": "PRT_kwDOABcD12MAAAABcDE3fg"}

    def test_create_unresolve_mutation_with_prrt_node_id(self) -> None:
        """Test creating unresolve mutation with PRRT_ GitHub node ID."""
        mutation, variables = create_unresolve_mutation("PRRT_kwDOO3WQIc5RvXMO")

        assert "mutation UnresolveReviewThread" in mutation
        assert variables == {"threadId": "PRRT_kwDOO3WQIc5RvXMO"}

    def test_create_unresolve_mutation_with_rt_node_id(self) -> None:
        """Test creating unresolve mutation with RT_ GitHub node ID."""
        mutation, variables = create_unresolve_mutation("RT_kwDOABcD12MAAAABcDE3fg")

        assert "mutation UnresolveReviewThread" in mutation
        assert variables == {"threadId": "RT_kwDOABcD12MAAAABcDE3fg"}

    def test_create_unresolve_mutation_invalid_id(self) -> None:
        """Test creating unresolve mutation with invalid thread ID."""
        with pytest.raises(ValueError) as exc_info:
            create_unresolve_mutation("invalid-id")
        assert "Thread ID must start with one of" in str(exc_info.value)


class TestMutationStructure:
    """Test the structure and format of generated mutations."""

    def test_resolve_mutation_structure(self) -> None:
        """Test that resolve mutation has correct GraphQL structure."""
        builder = ResolveThreadMutationBuilder()
        mutation = builder.build_resolve_mutation()

        # Check for proper GraphQL syntax
        lines = [line.strip() for line in mutation.split("\n") if line.strip()]

        # Should start with mutation declaration
        assert lines[0].startswith("mutation ResolveReviewThread")

        # Should have proper variable declaration
        assert "$threadId: ID!" in mutation

        # Should have proper mutation call
        assert "resolveReviewThread(input: {threadId: $threadId})" in mutation

        # Should request proper fields
        assert "thread {" in mutation
        assert "id" in mutation
        assert "isResolved" in mutation

    def test_unresolve_mutation_structure(self) -> None:
        """Test that unresolve mutation has correct GraphQL structure."""
        builder = ResolveThreadMutationBuilder()
        mutation = builder.build_unresolve_mutation()

        # Check for proper GraphQL syntax
        lines = [line.strip() for line in mutation.split("\n") if line.strip()]

        # Should start with mutation declaration
        assert lines[0].startswith("mutation UnresolveReviewThread")

        # Should have proper variable declaration
        assert "$threadId: ID!" in mutation

        # Should have proper mutation call
        assert "unresolveReviewThread(input: {threadId: $threadId})" in mutation

        # Should request proper fields
        assert "thread {" in mutation
        assert "id" in mutation
        assert "isResolved" in mutation

    def test_mutations_are_different(self) -> None:
        """Test that resolve and unresolve mutations are different."""
        builder = ResolveThreadMutationBuilder()
        resolve_mutation = builder.build_resolve_mutation()
        unresolve_mutation = builder.build_unresolve_mutation()

        assert resolve_mutation != unresolve_mutation

        # Check that each mutation contains its own operation
        assert "mutation ResolveReviewThread" in resolve_mutation
        assert "mutation UnresolveReviewThread" in unresolve_mutation

        # Check that operations are different
        assert "resolveReviewThread(input:" in resolve_mutation
        assert "unresolveReviewThread(input:" in unresolve_mutation

        # Ensure they don't contain each other's mutation names
        assert "mutation UnresolveReviewThread" not in resolve_mutation
        assert "mutation ResolveReviewThread" not in unresolve_mutation


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_thread_id(self) -> None:
        """Test with very long (but valid) thread ID."""
        builder = ResolveThreadMutationBuilder()
        long_id = "PRT_" + "a" * 100  # Long but valid node ID format

        variables = builder.build_variables(long_id)
        assert variables == {"threadId": long_id}

    def test_single_digit_thread_id(self) -> None:
        """Test with single digit thread ID."""
        builder = ResolveThreadMutationBuilder()
        variables = builder.build_variables("1")

        assert variables == {"threadId": "1"}

    def test_minimum_valid_node_id(self) -> None:
        """Test with minimum valid node ID length."""
        builder = ResolveThreadMutationBuilder()
        min_id = "PRT_kwDOABcD"  # Minimum valid length (12 characters)

        variables = builder.build_variables(min_id)
        assert variables == {"threadId": min_id}

    def test_case_sensitivity_node_id(self) -> None:
        """Test that node ID prefix is case sensitive."""
        builder = ResolveThreadMutationBuilder()

        # Should work with correct case
        variables = builder.build_variables("PRT_kwDOABcD12M")
        assert variables == {"threadId": "PRT_kwDOABcD12M"}

        # Should fail with wrong case
        with pytest.raises(ValueError):
            builder.build_variables("prt_kwDOABcD12M")

        with pytest.raises(ValueError):
            builder.build_variables("Prt_kwDOABcD12M")
