"""Tests for GraphQL reply mutations."""

import pytest

from toady.reply_mutations import (
    ReplyMutationBuilder,
    create_comment_reply_mutation,
    create_thread_reply_mutation,
    determine_reply_strategy,
)


class TestReplyMutationBuilder:
    """Test cases for ReplyMutationBuilder class."""

    def test_initialization(self):
        """Test ReplyMutationBuilder can be initialized."""
        builder = ReplyMutationBuilder()
        assert builder is not None

    def test_build_reply_mutation(self):
        """Test building the thread reply mutation."""
        builder = ReplyMutationBuilder()
        mutation = builder.build_reply_mutation()

        assert "addPullRequestReviewThreadReply" in mutation
        assert "pullRequestReviewThreadId" in mutation
        assert "$threadId: ID!" in mutation
        assert "$body: String!" in mutation
        assert "comment {" in mutation
        assert "id" in mutation
        assert "author {" in mutation

    def test_build_reply_to_comment_mutation(self):
        """Test building the comment reply mutation."""
        builder = ReplyMutationBuilder()
        mutation = builder.build_reply_to_comment_mutation()

        assert "addPullRequestReviewComment" in mutation
        assert "pullRequestReviewId" in mutation
        assert "inReplyTo" in mutation
        assert "$reviewId: ID!" in mutation
        assert "$commentId: ID!" in mutation
        assert "$body: String!" in mutation

    def test_build_variables_for_thread_reply_valid(self):
        """Test building variables for thread reply with valid inputs."""
        builder = ReplyMutationBuilder()
        thread_id = "PRT_kwDOABcD12MAAAABcDE3fg"
        reply_body = "This is a test reply"

        variables = builder.build_variables_for_thread_reply(thread_id, reply_body)

        assert variables["threadId"] == thread_id
        assert variables["body"] == reply_body

    def test_build_variables_for_thread_reply_empty_thread_id(self):
        """Test building variables with empty thread ID raises ValueError."""
        builder = ReplyMutationBuilder()

        with pytest.raises(ValueError, match="Thread ID cannot be empty"):
            builder.build_variables_for_thread_reply("", "test reply")

    def test_build_variables_for_thread_reply_empty_body(self):
        """Test building variables with empty reply body raises ValueError."""
        builder = ReplyMutationBuilder()

        with pytest.raises(ValueError, match="Reply body cannot be empty"):
            builder.build_variables_for_thread_reply("PRT_kwDOABcD12MAAAABcDE3fg", "")

    def test_build_variables_for_thread_reply_whitespace_only(self):
        """Test building variables with whitespace-only inputs raises ValueError."""
        builder = ReplyMutationBuilder()

        with pytest.raises(ValueError, match="Thread ID cannot be empty"):
            builder.build_variables_for_thread_reply("   ", "test reply")

        with pytest.raises(ValueError, match="Reply body cannot be empty"):
            builder.build_variables_for_thread_reply(
                "PRT_kwDOABcD12MAAAABcDE3fg", "   "
            )

    def test_build_variables_for_thread_reply_strips_whitespace(self):
        """Test that variables strip leading/trailing whitespace."""
        builder = ReplyMutationBuilder()
        thread_id = "  PRT_kwDOABcD12MAAAABcDE3fg  "
        reply_body = "  This is a test reply  "

        variables = builder.build_variables_for_thread_reply(thread_id, reply_body)

        assert variables["threadId"] == thread_id.strip()
        assert variables["body"] == reply_body.strip()

    def test_build_variables_for_comment_reply_valid(self):
        """Test building variables for comment reply with valid inputs."""
        builder = ReplyMutationBuilder()
        review_id = "PRR_kwDOABcD12MAAAABcDE3fg"
        comment_id = "PRRC_kwDOABcD12MAAAABcDE3fg"
        reply_body = "This is a test reply"

        variables = builder.build_variables_for_comment_reply(
            review_id, comment_id, reply_body
        )

        assert variables["reviewId"] == review_id
        assert variables["commentId"] == comment_id
        assert variables["body"] == reply_body

    def test_build_variables_for_comment_reply_empty_review_id(self):
        """Test building variables with empty review ID raises ValueError."""
        builder = ReplyMutationBuilder()

        with pytest.raises(ValueError, match="Review ID cannot be empty"):
            builder.build_variables_for_comment_reply(
                "", "PRRC_kwDOABcD12MAAAABcDE3fg", "test reply"
            )

    def test_build_variables_for_comment_reply_empty_comment_id(self):
        """Test building variables with empty comment ID raises ValueError."""
        builder = ReplyMutationBuilder()

        with pytest.raises(ValueError, match="Comment ID cannot be empty"):
            builder.build_variables_for_comment_reply(
                "PRR_kwDOABcD12MAAAABcDE3fg", "", "test reply"
            )

    def test_build_variables_for_comment_reply_empty_body(self):
        """Test building variables with empty reply body raises ValueError."""
        builder = ReplyMutationBuilder()

        with pytest.raises(ValueError, match="Reply body cannot be empty"):
            builder.build_variables_for_comment_reply(
                "PRR_kwDOABcD12MAAAABcDE3fg",
                "PRRC_kwDOABcD12MAAAABcDE3fg",
                "",
            )


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_create_thread_reply_mutation(self):
        """Test create_thread_reply_mutation function."""
        thread_id = "PRT_kwDOABcD12MAAAABcDE3fg"
        reply_body = "This is a test reply"

        mutation, variables = create_thread_reply_mutation(thread_id, reply_body)

        assert "addPullRequestReviewThreadReply" in mutation
        assert variables["threadId"] == thread_id
        assert variables["body"] == reply_body

    def test_create_comment_reply_mutation(self):
        """Test create_comment_reply_mutation function."""
        review_id = "PRR_kwDOABcD12MAAAABcDE3fg"
        comment_id = "PRRC_kwDOABcD12MAAAABcDE3fg"
        reply_body = "This is a test reply"

        mutation, variables = create_comment_reply_mutation(
            review_id, comment_id, reply_body
        )

        assert "addPullRequestReviewComment" in mutation
        assert variables["reviewId"] == review_id
        assert variables["commentId"] == comment_id
        assert variables["body"] == reply_body

    def test_create_thread_reply_mutation_invalid_thread_id(self):
        """Test create_thread_reply_mutation with invalid thread ID."""
        with pytest.raises(ValueError):
            create_thread_reply_mutation("invalid_id", "test reply")

    def test_create_comment_reply_mutation_invalid_comment_id(self):
        """Test create_comment_reply_mutation with invalid comment ID."""
        with pytest.raises(ValueError):
            create_comment_reply_mutation(
                "PRR_kwDOABcD12MAAAABcDE3fg", "invalid_id", "test reply"
            )


class TestDetermineReplyStrategy:
    """Test cases for determine_reply_strategy function."""

    def test_numeric_comment_id(self):
        """Test numeric comment ID returns comment_reply strategy."""
        assert determine_reply_strategy("123456789") == "comment_reply"
        assert determine_reply_strategy("1") == "comment_reply"
        assert determine_reply_strategy("999999999999999999") == "comment_reply"

    def test_thread_node_ids(self):
        """Test thread node IDs return thread_reply strategy."""
        assert determine_reply_strategy("PRT_kwDOABcD12MAAAABcDE3fg") == "thread_reply"
        assert determine_reply_strategy("PRRT_kwDOABcD12MAAAABcDE3fg") == "thread_reply"
        assert determine_reply_strategy("RT_kwDOABcD12MAAAABcDE3fg") == "thread_reply"

    def test_comment_node_ids(self):
        """Test comment node IDs return comment_reply strategy."""
        assert determine_reply_strategy("IC_kwDOABcD12MAAAABcDE3fg") == "comment_reply"
        assert (
            determine_reply_strategy("PRRC_kwDOABcD12MAAAABcDE3fg") == "comment_reply"
        )
        assert determine_reply_strategy("RP_kwDOABcD12MAAAABcDE3fg") == "comment_reply"

    def test_unknown_format_defaults_to_comment_reply(self):
        """Test unknown formats default to comment_reply strategy."""
        assert (
            determine_reply_strategy("UNKNOWN_kwDOABcD12MAAAABcDE3fg")
            == "comment_reply"
        )
        assert determine_reply_strategy("XYZ_123") == "comment_reply"
        assert determine_reply_strategy("random_string") == "comment_reply"

    def test_empty_string_defaults_to_comment_reply(self):
        """Test empty string defaults to comment_reply strategy."""
        assert determine_reply_strategy("") == "comment_reply"


class TestMutationStructure:
    """Test cases for mutation structure validation."""

    def test_thread_reply_mutation_structure(self):
        """Test that thread reply mutation has correct structure."""
        builder = ReplyMutationBuilder()
        mutation = builder.build_reply_mutation()

        # Check that the mutation includes all required fields
        required_fields = [
            "id",
            "body",
            "createdAt",
            "updatedAt",
            "author",
            "url",
            "pullRequestReview",
            "replyTo",
        ]

        for field in required_fields:
            assert field in mutation, f"Required field '{field}' missing from mutation"

    def test_comment_reply_mutation_structure(self):
        """Test that comment reply mutation has correct structure."""
        builder = ReplyMutationBuilder()
        mutation = builder.build_reply_to_comment_mutation()

        # Check that the mutation includes all required fields
        required_fields = [
            "id",
            "body",
            "createdAt",
            "updatedAt",
            "author",
            "url",
            "pullRequestReview",
            "replyTo",
        ]

        for field in required_fields:
            assert field in mutation, f"Required field '{field}' missing from mutation"

    def test_mutation_variable_definitions(self):
        """Test that mutations have correct variable definitions."""
        builder = ReplyMutationBuilder()

        thread_mutation = builder.build_reply_mutation()
        assert "$threadId: ID!" in thread_mutation
        assert "$body: String!" in thread_mutation

        comment_mutation = builder.build_reply_to_comment_mutation()
        assert "$reviewId: ID!" in comment_mutation
        assert "$commentId: ID!" in comment_mutation
        assert "$body: String!" in comment_mutation


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_very_long_reply_body(self):
        """Test handling of very long reply bodies."""
        builder = ReplyMutationBuilder()
        thread_id = "PRT_kwDOABcD12MAAAABcDE3fg"
        long_body = "x" * 65536  # GitHub's maximum comment length

        # Should not raise an exception
        variables = builder.build_variables_for_thread_reply(thread_id, long_body)
        assert variables["body"] == long_body

    def test_unicode_in_reply_body(self):
        """Test handling of unicode characters in reply body."""
        builder = ReplyMutationBuilder()
        thread_id = "PRT_kwDOABcD12MAAAABcDE3fg"
        unicode_body = "This is a test with unicode: 🚀 ✨ 💯"

        variables = builder.build_variables_for_thread_reply(thread_id, unicode_body)
        assert variables["body"] == unicode_body

    def test_special_characters_in_reply_body(self):
        """Test handling of special characters in reply body."""
        builder = ReplyMutationBuilder()
        thread_id = "PRT_kwDOABcD12MAAAABcDE3fg"
        special_body = "Test with \"quotes\" and 'apostrophes' and <tags> and &amp;"

        variables = builder.build_variables_for_thread_reply(thread_id, special_body)
        assert variables["body"] == special_body

    def test_newlines_and_formatting_in_reply_body(self):
        """Test handling of newlines and formatting in reply body."""
        builder = ReplyMutationBuilder()
        thread_id = "PRT_kwDOABcD12MAAAABcDE3fg"
        formatted_body = """This is a multi-line reply.

        It has:
        - Bullet points
        - Code blocks: `example`
        - **Bold text**
        - *Italic text*

        And it should work fine."""

        variables = builder.build_variables_for_thread_reply(thread_id, formatted_body)
        assert variables["body"] == formatted_body
