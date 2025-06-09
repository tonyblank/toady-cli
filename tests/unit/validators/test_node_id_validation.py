"""Tests for GitHub node ID validation utilities."""

import pytest

from toady.node_id_validation import (
    GitHubEntityType,
    NodeIDValidator,
    create_comment_validator,
    create_review_validator,
    create_thread_validator,
    create_universal_validator,
    get_comment_id_format_message,
    get_thread_id_format_message,
    validate_comment_id,
    validate_thread_id,
)


class TestGitHubEntityType:
    """Test the GitHubEntityType enumeration."""

    def test_entity_type_values(self):
        """Test that entity types have expected values."""
        assert GitHubEntityType.ISSUE_COMMENT.value == "IC_"
        assert GitHubEntityType.PULL_REQUEST_REVIEW_COMMENT.value == "PRRC_"
        assert GitHubEntityType.PULL_REQUEST_THREAD.value == "PRT_"
        assert GitHubEntityType.PULL_REQUEST_REVIEW_THREAD.value == "PRRT_"
        assert GitHubEntityType.REVIEW_THREAD.value == "RT_"
        assert GitHubEntityType.PULL_REQUEST_REVIEW.value == "PRR_"
        assert GitHubEntityType.PULL_REQUEST.value == "PR_"
        assert GitHubEntityType.REPOSITORY.value == "R_"
        assert GitHubEntityType.USER.value == "U_"
        assert GitHubEntityType.ORGANIZATION.value == "O_"
        assert GitHubEntityType.TEAM.value == "T_"
        assert GitHubEntityType.DISCUSSION.value == "MDI_"
        assert GitHubEntityType.REPLY.value == "RP_"

    def test_all_entity_types_unique(self):
        """Test that all entity type values are unique."""
        values = [entity.value for entity in GitHubEntityType]
        assert len(values) == len(set(values))


class TestNodeIDValidator:
    """Test the NodeIDValidator class."""

    def test_init_default_allows_all_types(self):
        """Test that default initialization allows all entity types."""
        validator = NodeIDValidator()
        assert validator.allowed_types == set(GitHubEntityType)

    def test_init_with_specific_types(self):
        """Test initialization with specific allowed types."""
        allowed_types = {
            GitHubEntityType.ISSUE_COMMENT,
            GitHubEntityType.PULL_REQUEST_THREAD,
        }
        validator = NodeIDValidator(allowed_types)
        assert validator.allowed_types == allowed_types

    def test_get_allowed_prefixes(self):
        """Test getting allowed prefixes."""
        allowed_types = {
            GitHubEntityType.ISSUE_COMMENT,
            GitHubEntityType.PULL_REQUEST_THREAD,
        }
        validator = NodeIDValidator(allowed_types)
        prefixes = validator.get_allowed_prefixes()
        assert set(prefixes) == {"IC_", "PRT_"}

    def test_identify_entity_type_valid(self):
        """Test identifying entity types from valid node IDs."""
        validator = NodeIDValidator()

        assert (
            validator.identify_entity_type("IC_kwDOABcD12M")
            == GitHubEntityType.ISSUE_COMMENT
        )
        assert (
            validator.identify_entity_type("PRRC_kwDOABcD12M")
            == GitHubEntityType.PULL_REQUEST_REVIEW_COMMENT
        )
        assert (
            validator.identify_entity_type("PRT_kwDOABcD12M")
            == GitHubEntityType.PULL_REQUEST_THREAD
        )
        assert (
            validator.identify_entity_type("PRRT_kwDOABcD12M")
            == GitHubEntityType.PULL_REQUEST_REVIEW_THREAD
        )
        assert (
            validator.identify_entity_type("RT_kwDOABcD12M")
            == GitHubEntityType.REVIEW_THREAD
        )
        assert (
            validator.identify_entity_type("PRR_kwDOABcD12M")
            == GitHubEntityType.PULL_REQUEST_REVIEW
        )
        assert (
            validator.identify_entity_type("PR_kwDOABcD12M")
            == GitHubEntityType.PULL_REQUEST
        )
        assert (
            validator.identify_entity_type("R_kwDOABcD12M")
            == GitHubEntityType.REPOSITORY
        )
        assert validator.identify_entity_type("U_kwDOABcD12M") == GitHubEntityType.USER
        assert (
            validator.identify_entity_type("O_kwDOABcD12M")
            == GitHubEntityType.ORGANIZATION
        )
        assert validator.identify_entity_type("T_kwDOABcD12M") == GitHubEntityType.TEAM
        assert (
            validator.identify_entity_type("MDI_kwDOABcD12M")
            == GitHubEntityType.DISCUSSION
        )
        assert (
            validator.identify_entity_type("RP_kwDOABcD12M") == GitHubEntityType.REPLY
        )

    def test_identify_entity_type_invalid(self):
        """Test identifying entity types from invalid node IDs."""
        validator = NodeIDValidator()

        assert validator.identify_entity_type("UNKNOWN_kwDOABcD12M") is None
        assert validator.identify_entity_type("123456789") is None
        assert validator.identify_entity_type("") is None
        assert validator.identify_entity_type("IC") is None

    def test_validate_numeric_id_valid(self):
        """Test validating valid numeric IDs."""
        validator = NodeIDValidator()

        # Should not raise for valid numeric IDs
        validator.validate_numeric_id("123456789", "Test ID")
        validator.validate_numeric_id("1", "Test ID")
        validator.validate_numeric_id("12345678901234567890", "Test ID")  # 20 digits

    def test_validate_numeric_id_invalid(self):
        """Test validating invalid numeric IDs."""
        validator = NodeIDValidator()

        # Empty string
        with pytest.raises(ValueError, match="Test ID must be numeric"):
            validator.validate_numeric_id("", "Test ID")

        # Non-numeric
        with pytest.raises(ValueError, match="Test ID must be numeric"):
            validator.validate_numeric_id("abc", "Test ID")

        # Too long
        with pytest.raises(ValueError, match="between 1 and 20 digits"):
            validator.validate_numeric_id(
                "123456789012345678901", "Test ID"
            )  # 21 digits

        # Zero
        with pytest.raises(ValueError, match="must be a positive integer"):
            validator.validate_numeric_id("0", "Test ID")

        # Negative (represented as string)
        with pytest.raises(ValueError, match="Test ID must be numeric"):
            validator.validate_numeric_id("-123", "Test ID")

    def test_validate_node_id_format_valid(self):
        """Test validating valid node ID formats."""
        validator = NodeIDValidator()

        # Valid node IDs
        entity_type = validator.validate_node_id_format(
            "IC_kwDOABcD12MAAAABcDE3fg", "Test ID"
        )
        assert entity_type == GitHubEntityType.ISSUE_COMMENT

        entity_type = validator.validate_node_id_format(
            "PRRC_kwDOABcD12MAAAABcDE3fg", "Test ID"
        )
        assert entity_type == GitHubEntityType.PULL_REQUEST_REVIEW_COMMENT

        entity_type = validator.validate_node_id_format("PRT_kwDOABcD12M", "Test ID")
        assert entity_type == GitHubEntityType.PULL_REQUEST_THREAD

        # Minimum length
        entity_type = validator.validate_node_id_format("IC_12345", "Test ID")
        assert entity_type == GitHubEntityType.ISSUE_COMMENT

    def test_validate_node_id_format_invalid_empty(self):
        """Test validating empty node IDs."""
        validator = NodeIDValidator()

        with pytest.raises(ValueError, match="Test ID cannot be empty"):
            validator.validate_node_id_format("", "Test ID")

        with pytest.raises(ValueError, match="Test ID cannot be empty"):
            validator.validate_node_id_format(None, "Test ID")

    def test_validate_node_id_format_invalid_prefix(self):
        """Test validating node IDs with invalid prefixes."""
        validator = NodeIDValidator()

        with pytest.raises(ValueError, match="Test ID must start with one of"):
            validator.validate_node_id_format("UNKNOWN_kwDOABcD12M", "Test ID")

    def test_validate_node_id_format_restricted_types(self):
        """Test validating node IDs with restricted allowed types."""
        allowed_types = {GitHubEntityType.ISSUE_COMMENT}
        validator = NodeIDValidator(allowed_types)

        # Allowed type should work
        entity_type = validator.validate_node_id_format("IC_kwDOABcD12M", "Test ID")
        assert entity_type == GitHubEntityType.ISSUE_COMMENT

        # Disallowed type should fail
        with pytest.raises(ValueError, match="Test ID type 'PRT_' not allowed"):
            validator.validate_node_id_format("PRT_kwDOABcD12M", "Test ID")

    def test_validate_node_id_format_invalid_length(self):
        """Test validating node IDs with invalid lengths."""
        validator = NodeIDValidator()

        # Too short
        with pytest.raises(ValueError, match="appears too short to be valid"):
            validator.validate_node_id_format("IC_123", "Test ID")

        # Too long
        long_id = "IC_" + "x" * 101
        with pytest.raises(ValueError, match="appears too long to be valid"):
            validator.validate_node_id_format(long_id, "Test ID")

    def test_validate_node_id_format_invalid_characters(self):
        """Test validating node IDs with invalid characters."""
        validator = NodeIDValidator()

        with pytest.raises(ValueError, match="contains invalid characters"):
            validator.validate_node_id_format("IC_kwDO@#$%", "Test ID")

        with pytest.raises(ValueError, match="contains invalid characters"):
            validator.validate_node_id_format("IC_kwDO spaces", "Test ID")

    def test_validate_id_numeric(self):
        """Test validating numeric IDs through validate_id."""
        validator = NodeIDValidator()

        result = validator.validate_id("123456789", "Test ID")
        assert result is None  # Numeric IDs return None

    def test_validate_id_node_id(self):
        """Test validating node IDs through validate_id."""
        validator = NodeIDValidator()

        result = validator.validate_id("IC_kwDOABcD12M", "Test ID")
        assert result == GitHubEntityType.ISSUE_COMMENT

    def test_validate_id_empty(self):
        """Test validating empty IDs."""
        validator = NodeIDValidator()

        with pytest.raises(ValueError, match="Test ID cannot be empty"):
            validator.validate_id("", "Test ID")

        with pytest.raises(ValueError, match="Test ID cannot be empty"):
            validator.validate_id("   ", "Test ID")

    def test_format_allowed_types_message_with_numeric(self):
        """Test formatting allowed types message including numeric."""
        allowed_types = {
            GitHubEntityType.ISSUE_COMMENT,
            GitHubEntityType.PULL_REQUEST_THREAD,
        }
        validator = NodeIDValidator(allowed_types)

        message = validator.format_allowed_types_message(include_numeric=True)
        assert "numeric (e.g., 123456789)" in message
        assert "IC_kwDOABcD12MAAAABcDE3fg" in message
        assert "PRT_kwDOABcD12MAAAABcDE3fg" in message

    def test_format_allowed_types_message_without_numeric(self):
        """Test formatting allowed types message excluding numeric."""
        allowed_types = {GitHubEntityType.ISSUE_COMMENT}
        validator = NodeIDValidator(allowed_types)

        message = validator.format_allowed_types_message(include_numeric=False)
        assert "numeric" not in message
        assert "IC_kwDOABcD12MAAAABcDE3fg" in message


class TestPreConfiguredValidators:
    """Test pre-configured validator factory functions."""

    def test_create_comment_validator(self):
        """Test creating a comment validator."""
        validator = create_comment_validator()
        assert validator.allowed_types == NodeIDValidator.COMMENT_TYPES

        prefixes = validator.get_allowed_prefixes()
        assert set(prefixes) == {"IC_", "PRRC_", "RP_"}

    def test_create_thread_validator(self):
        """Test creating a thread validator."""
        validator = create_thread_validator()
        assert validator.allowed_types == NodeIDValidator.THREAD_TYPES

        prefixes = validator.get_allowed_prefixes()
        assert set(prefixes) == {"PRT_", "PRRT_", "RT_"}

    def test_create_review_validator(self):
        """Test creating a review validator."""
        validator = create_review_validator()
        assert validator.allowed_types == NodeIDValidator.REVIEW_TYPES

        prefixes = validator.get_allowed_prefixes()
        assert set(prefixes) == {"PRR_"}

    def test_create_universal_validator(self):
        """Test creating a universal validator."""
        validator = create_universal_validator()
        assert validator.allowed_types == set(GitHubEntityType)


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility."""

    def test_validate_comment_id_numeric(self):
        """Test validating numeric comment IDs."""
        result = validate_comment_id("123456789")
        assert result is None

    def test_validate_comment_id_node_ids(self):
        """Test validating comment node IDs."""
        result = validate_comment_id("IC_kwDOABcD12M")
        assert result == GitHubEntityType.ISSUE_COMMENT

        result = validate_comment_id("PRRC_kwDOABcD12M")
        assert result == GitHubEntityType.PULL_REQUEST_REVIEW_COMMENT

        result = validate_comment_id("RP_kwDOABcD12M")
        assert result == GitHubEntityType.REPLY

    def test_validate_comment_id_invalid_type(self):
        """Test validating comment IDs with invalid types."""
        with pytest.raises(ValueError, match="Comment ID type 'PRT_' not allowed"):
            validate_comment_id("PRT_kwDOABcD12M")

    def test_validate_thread_id_numeric(self):
        """Test validating numeric thread IDs."""
        result = validate_thread_id("123456789")
        assert result is None

    def test_validate_thread_id_node_ids(self):
        """Test validating thread node IDs."""
        result = validate_thread_id("PRT_kwDOABcD12M")
        assert result == GitHubEntityType.PULL_REQUEST_THREAD

        result = validate_thread_id("PRRT_kwDOABcD12M")
        assert result == GitHubEntityType.PULL_REQUEST_REVIEW_THREAD

        result = validate_thread_id("RT_kwDOABcD12M")
        assert result == GitHubEntityType.REVIEW_THREAD

    def test_validate_thread_id_invalid_type(self):
        """Test validating thread IDs with invalid types."""
        with pytest.raises(ValueError, match="Thread ID type 'IC_' not allowed"):
            validate_thread_id("IC_kwDOABcD12M")

    def test_get_comment_id_format_message(self):
        """Test getting comment ID format message."""
        message = get_comment_id_format_message()
        assert "numeric" in message
        assert "IC_" in message
        assert "PRRC_" in message
        assert "RP_" in message

    def test_get_thread_id_format_message(self):
        """Test getting thread ID format message."""
        message = get_thread_id_format_message()
        assert "numeric" in message
        assert "PRT_" in message
        assert "PRRT_" in message
        assert "RT_" in message


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_validate_exact_minimum_length(self):
        """Test validating node IDs at exact minimum length."""
        validator = NodeIDValidator()

        # Minimum valid length (prefix + 5 chars)
        entity_type = validator.validate_node_id_format("IC_12345", "Test ID")
        assert entity_type == GitHubEntityType.ISSUE_COMMENT

    def test_validate_exact_maximum_length(self):
        """Test validating node IDs at exact maximum length."""
        validator = NodeIDValidator()

        # Maximum valid length (prefix + 100 chars)
        max_id = "IC_" + "x" * 100
        entity_type = validator.validate_node_id_format(max_id, "Test ID")
        assert entity_type == GitHubEntityType.ISSUE_COMMENT

    def test_validate_with_special_characters(self):
        """Test validating node IDs with special but valid characters."""
        validator = NodeIDValidator()

        # Valid special characters: hyphens, underscores, equals
        entity_type = validator.validate_node_id_format("IC_kwDO-_=test", "Test ID")
        assert entity_type == GitHubEntityType.ISSUE_COMMENT

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        validator = NodeIDValidator()

        # Leading/trailing whitespace should be stripped
        result = validator.validate_id("  123456789  ", "Test ID")
        assert result is None

        result = validator.validate_id("  IC_kwDOABcD12M  ", "Test ID")
        assert result == GitHubEntityType.ISSUE_COMMENT

    def test_case_sensitivity(self):
        """Test that node ID validation is case-sensitive."""
        validator = NodeIDValidator()

        # Lowercase prefix should not match
        with pytest.raises(ValueError, match="must start with one of"):
            validator.validate_node_id_format("ic_kwDOABcD12M", "Test ID")

    def test_partial_prefix_matching(self):
        """Test that partial prefix matching doesn't work."""
        validator = NodeIDValidator()

        # "IC" without underscore should not match
        with pytest.raises(ValueError, match="must start with one of"):
            validator.validate_node_id_format("ICkwDOABcD12M", "Test ID")

    def test_empty_allowed_types(self):
        """Test validator with empty allowed types."""
        validator = NodeIDValidator(set())

        # Should fail for any node ID due to empty allowed prefixes
        with pytest.raises(ValueError, match="not allowed"):
            validator.validate_node_id_format("IC_kwDOABcD12M", "Test ID")

        # Numeric should still work
        result = validator.validate_id("123456789", "Test ID")
        assert result is None
