"""Tests for data models."""

from datetime import datetime
from typing import Any, Dict

import pytest

from toady.models import Comment, ReviewThread


class TestReviewThread:
    """Test the ReviewThread dataclass."""

    def test_create_valid_review_thread(self) -> None:
        """Test creating a valid ReviewThread instance."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Review comment about function naming",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 13, 0, 0),
            status="UNRESOLVED",
            author="johndoe",
            comments=[],
        )

        assert thread.thread_id == "RT_123"
        assert thread.title == "Review comment about function naming"
        assert thread.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert thread.updated_at == datetime(2024, 1, 2, 13, 0, 0)
        assert thread.status == "UNRESOLVED"
        assert thread.author == "johndoe"
        assert thread.comments == []

    def test_thread_id_validation(self) -> None:
        """Test that thread_id cannot be empty."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            ReviewThread(
                thread_id="",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    def test_title_validation(self) -> None:
        """Test that title cannot be empty."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            ReviewThread(
                thread_id="RT_123",
                title="",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    def test_status_validation(self) -> None:
        """Test that status must be valid."""
        with pytest.raises(ValueError, match="status must be one of"):
            ReviewThread(
                thread_id="RT_123",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="INVALID",
                author="user",
                comments=[],
            )

    def test_author_validation(self) -> None:
        """Test that author cannot be empty."""
        with pytest.raises(ValueError, match="author cannot be empty"):
            ReviewThread(
                thread_id="RT_123",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="",
                comments=[],
            )

    def test_date_validation(self) -> None:
        """Test that updated_at cannot be before created_at."""
        with pytest.raises(ValueError, match="updated_at cannot be before created_at"):
            ReviewThread(
                thread_id="RT_123",
                title="Test",
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 1),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test Review",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 13, 0, 0),
            status="RESOLVED",
            author="johndoe",
            comments=["comment1", "comment2"],
        )

        result = thread.to_dict()

        assert result == {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T13:00:00",
            "status": "RESOLVED",
            "author": "johndoe",
            "comments": ["comment1", "comment2"],
        }

    def test_from_dict_valid(self) -> None:
        """Test deserialization from valid dictionary."""
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T13:00:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        thread = ReviewThread.from_dict(data)

        assert thread.thread_id == "RT_123"
        assert thread.title == "Test Review"
        assert thread.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert thread.updated_at == datetime(2024, 1, 2, 13, 0, 0)
        assert thread.status == "UNRESOLVED"
        assert thread.author == "johndoe"
        assert thread.comments == []

    def test_from_dict_missing_required_field(self) -> None:
        """Test deserialization with missing required fields."""
        data: Dict[str, Any] = {
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T13:00:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        with pytest.raises(ValueError, match="Missing required field: thread_id"):
            ReviewThread.from_dict(data)

    def test_from_dict_invalid_date_format(self) -> None:
        """Test deserialization with invalid date format."""
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "invalid-date",
            "updated_at": "2024-01-02T13:00:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        with pytest.raises(ValueError, match="Invalid date format for created_at"):
            ReviewThread.from_dict(data)

    def test_from_dict_with_microseconds(self) -> None:
        """Test deserialization handles ISO format with microseconds."""
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00.123456",
            "updated_at": "2024-01-02T13:00:00.654321",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        thread = ReviewThread.from_dict(data)

        assert thread.created_at == datetime(2024, 1, 1, 12, 0, 0, 123456)
        assert thread.updated_at == datetime(2024, 1, 2, 13, 0, 0, 654321)

    def test_from_dict_with_timezone(self) -> None:
        """Test deserialization handles ISO format with timezone."""
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-02T13:00:00+00:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        thread = ReviewThread.from_dict(data)

        # Should parse without timezone info (naive datetime)
        assert thread.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert thread.updated_at == datetime(2024, 1, 2, 13, 0, 0)

    def test_roundtrip_serialization(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = ReviewThread(
            thread_id="RT_123",
            title="Test Review",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 13, 0, 0),
            status="RESOLVED",
            author="johndoe",
            comments=["c1", "c2", "c3"],
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ReviewThread.from_dict(data)

        # Compare all fields
        assert restored.thread_id == original.thread_id
        assert restored.title == original.title
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at
        assert restored.status == original.status
        assert restored.author == original.author
        assert restored.comments == original.comments

    def test_str_representation(self) -> None:
        """Test string representation of ReviewThread."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Review comment about function naming",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 13, 0, 0),
            status="UNRESOLVED",
            author="johndoe",
            comments=[],
        )

        str_repr = str(thread)
        assert "RT_123" in str_repr
        assert "Review comment about function naming" in str_repr
        assert "UNRESOLVED" in str_repr
        assert "johndoe" in str_repr

    @pytest.mark.parametrize(
        "status",
        ["RESOLVED", "UNRESOLVED", "PENDING", "OUTDATED", "DISMISSED"],
    )
    def test_valid_statuses(self, status: str) -> None:
        """Test all valid status values."""
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=status,
            author="user",
            comments=[],
        )
        assert thread.status == status

    def test_comments_list_immutability(self) -> None:
        """Test that comments list changes don't affect the original."""
        comments = ["c1", "c2"]
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=comments,
        )

        # Modify original list
        comments.append("c3")

        # Thread should still have original comments
        assert len(thread.comments) == 2
        assert "c3" not in thread.comments

    def test_from_dict_with_complex_timezone(self) -> None:
        """Test deserialization handles complex timezone formats."""
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00-05:00",
            "updated_at": "2024-01-02T13:00:00-08:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        thread = ReviewThread.from_dict(data)

        # Should parse without timezone info (naive datetime)
        assert thread.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert thread.updated_at == datetime(2024, 1, 2, 13, 0, 0)

    def test_parse_datetime_edge_cases(self) -> None:
        """Test edge cases in datetime parsing."""
        # Test with dates that have many dashes
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T13:00:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        thread = ReviewThread.from_dict(data)
        assert thread.created_at == datetime(2024, 1, 1, 12, 0, 0)

    def test_parse_datetime_unparseable(self) -> None:
        """Test handling of completely unparseable datetime."""
        with pytest.raises(ValueError, match="Unable to parse datetime"):
            ReviewThread._parse_datetime("not a date")


class TestComment:
    """Test the Comment dataclass."""

    def test_create_valid_comment(self) -> None:
        """Test creating a valid Comment instance."""
        comment = Comment(
            comment_id="C_456",
            content="This looks good to me!",
            author="janedoe",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 5, 0),
            parent_id=None,
            thread_id="RT_123",
        )

        assert comment.comment_id == "C_456"
        assert comment.content == "This looks good to me!"
        assert comment.author == "janedoe"
        assert comment.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert comment.updated_at == datetime(2024, 1, 1, 12, 5, 0)
        assert comment.parent_id is None
        assert comment.thread_id == "RT_123"

    def test_comment_id_validation(self) -> None:
        """Test that comment_id cannot be empty."""
        with pytest.raises(ValueError, match="comment_id cannot be empty"):
            Comment(
                comment_id="",
                content="Test content",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    def test_content_validation_empty(self) -> None:
        """Test that content cannot be empty."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Comment(
                comment_id="C_456",
                content="",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    def test_content_validation_too_long(self) -> None:
        """Test that content cannot exceed maximum length."""
        long_content = "x" * 65537  # Exceed the 65536 character limit
        with pytest.raises(ValueError, match="content cannot exceed 65536 characters"):
            Comment(
                comment_id="C_456",
                content=long_content,
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    def test_author_validation(self) -> None:
        """Test that author cannot be empty."""
        with pytest.raises(ValueError, match="author cannot be empty"):
            Comment(
                comment_id="C_456",
                content="Test content",
                author="",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    def test_thread_id_validation(self) -> None:
        """Test that thread_id cannot be empty."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            Comment(
                comment_id="C_456",
                content="Test content",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="",
            )

    def test_date_validation(self) -> None:
        """Test that updated_at cannot be before created_at."""
        created = datetime(2024, 1, 2, 12, 0, 0)
        updated = datetime(2024, 1, 1, 12, 0, 0)  # Before created

        with pytest.raises(ValueError, match="updated_at cannot be before created_at"):
            Comment(
                comment_id="C_456",
                content="Test content",
                author="user",
                created_at=created,
                updated_at=updated,
                parent_id=None,
                thread_id="RT_123",
            )

    def test_to_dict(self) -> None:
        """Test converting Comment to dictionary."""
        comment = Comment(
            comment_id="C_456",
            content="This looks good!",
            author="janedoe",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 5, 0),
            parent_id="C_123",
            thread_id="RT_123",
        )

        result = comment.to_dict()

        expected = {
            "comment_id": "C_456",
            "content": "This looks good!",
            "author": "janedoe",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:05:00",
            "parent_id": "C_123",
            "thread_id": "RT_123",
        }

        assert result == expected

    def test_to_dict_with_none_parent(self) -> None:
        """Test converting Comment with None parent_id to dictionary."""
        comment = Comment(
            comment_id="C_456",
            content="This looks good!",
            author="janedoe",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 5, 0),
            parent_id=None,
            thread_id="RT_123",
        )

        result = comment.to_dict()

        expected = {
            "comment_id": "C_456",
            "content": "This looks good!",
            "author": "janedoe",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:05:00",
            "parent_id": None,
            "thread_id": "RT_123",
        }

        assert result == expected

    def test_from_dict_valid(self) -> None:
        """Test creating Comment from valid dictionary."""
        data = {
            "comment_id": "C_456",
            "content": "This looks good!",
            "author": "janedoe",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:05:00",
            "parent_id": "C_123",
            "thread_id": "RT_123",
        }

        comment = Comment.from_dict(data)

        assert comment.comment_id == "C_456"
        assert comment.content == "This looks good!"
        assert comment.author == "janedoe"
        assert comment.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert comment.updated_at == datetime(2024, 1, 1, 12, 5, 0)
        assert comment.parent_id == "C_123"
        assert comment.thread_id == "RT_123"

    def test_from_dict_with_none_parent(self) -> None:
        """Test creating Comment from dictionary with None parent_id."""
        data = {
            "comment_id": "C_456",
            "content": "This looks good!",
            "author": "janedoe",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:05:00",
            "parent_id": None,
            "thread_id": "RT_123",
        }

        comment = Comment.from_dict(data)

        assert comment.comment_id == "C_456"
        assert comment.parent_id is None

    def test_from_dict_missing_fields(self) -> None:
        """Test from_dict with missing required fields."""
        data = {
            "comment_id": "C_456",
            "content": "This looks good!",
            # Missing author, created_at, updated_at, thread_id
        }

        with pytest.raises(ValueError, match="Missing required field"):
            Comment.from_dict(data)

    def test_from_dict_invalid_date_format(self) -> None:
        """Test from_dict with invalid date formats."""
        data = {
            "comment_id": "C_456",
            "content": "This looks good!",
            "author": "janedoe",
            "created_at": "invalid-date",
            "updated_at": "2024-01-01T12:05:00",
            "parent_id": None,
            "thread_id": "RT_123",
        }

        with pytest.raises(ValueError, match="Invalid date format for created_at"):
            Comment.from_dict(data)

    def test_str_representation(self) -> None:
        """Test string representation of Comment."""
        comment = Comment(
            comment_id="C_456",
            content="This looks good to me!",
            author="janedoe",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 5, 0),
            parent_id=None,
            thread_id="RT_123",
        )

        expected = "Comment(id=C_456, author=janedoe, thread=RT_123, parent=None)"
        assert str(comment) == expected

    def test_str_representation_with_parent(self) -> None:
        """Test string representation of Comment with parent."""
        comment = Comment(
            comment_id="C_456",
            content="This looks good to me!",
            author="janedoe",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 5, 0),
            parent_id="C_123",
            thread_id="RT_123",
        )

        expected = "Comment(id=C_456, author=janedoe, thread=RT_123, parent=C_123)"
        assert str(comment) == expected

    def test_from_dict_invalid_updated_at_format(self) -> None:
        """Test from_dict with invalid updated_at date format."""
        data = {
            "comment_id": "C_456",
            "content": "This looks good!",
            "author": "janedoe",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "invalid-updated-date",
            "parent_id": None,
            "thread_id": "RT_123",
        }

        with pytest.raises(ValueError, match="Invalid date format for updated_at"):
            Comment.from_dict(data)


class TestReviewThreadEdgeCases:
    """Additional edge case tests for ReviewThread."""

    def test_from_dict_invalid_updated_at_format(self) -> None:
        """Test from_dict with invalid updated_at date format."""
        data = {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "invalid-updated-date",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        with pytest.raises(ValueError, match="Invalid date format for updated_at"):
            ReviewThread.from_dict(data)

    @pytest.mark.parametrize("invalid_id", ["", "   ", "\t", "\n"])
    def test_thread_id_validation_whitespace(self, invalid_id: str) -> None:
        """Test thread_id validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            ReviewThread(
                thread_id=invalid_id,
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    @pytest.mark.parametrize("invalid_title", ["", "   ", "\t", "\n"])
    def test_title_validation_whitespace(self, invalid_title: str) -> None:
        """Test title validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            ReviewThread(
                thread_id="RT_123",
                title=invalid_title,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    @pytest.mark.parametrize("invalid_author", ["", "   ", "\t", "\n"])
    def test_author_validation_whitespace(self, invalid_author: str) -> None:
        """Test author validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="author cannot be empty"):
            ReviewThread(
                thread_id="RT_123",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author=invalid_author,
                comments=[],
            )

    @pytest.mark.parametrize("invalid_status", ["INVALID", "resolved", "pending", ""])
    def test_status_validation_invalid_values(self, invalid_status: str) -> None:
        """Test status validation with invalid values."""
        with pytest.raises(ValueError, match="status must be one of"):
            ReviewThread(
                thread_id="RT_123",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status=invalid_status,
                author="user",
                comments=[],
            )

    def test_comments_list_deep_copy(self) -> None:
        """Test that comments list is properly copied and isolated."""
        original_comments = ["C_1", "C_2"]
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=original_comments,
        )

        # Modify original list
        original_comments.append("C_3")

        # Thread's comments should be unchanged
        assert thread.comments == ["C_1", "C_2"]

    def test_extreme_date_differences(self) -> None:
        """Test with extreme date differences."""
        created = datetime(1970, 1, 1, 0, 0, 0)
        updated = datetime(2030, 12, 31, 23, 59, 59)

        thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=created,
            updated_at=updated,
            status="UNRESOLVED",
            author="user",
            comments=[],
        )

        assert thread.created_at == created
        assert thread.updated_at == updated

    def test_large_comments_list(self) -> None:
        """Test with large comments list."""
        large_comments = [f"C_{i}" for i in range(1000)]

        thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=large_comments,
        )

        assert len(thread.comments) == 1000
        assert thread.comments[0] == "C_0"
        assert thread.comments[999] == "C_999"


class TestCommentEdgeCases:
    """Additional edge case tests for Comment."""

    @pytest.mark.parametrize("invalid_id", ["", "   ", "\t", "\n"])
    def test_comment_id_validation_whitespace(self, invalid_id: str) -> None:
        """Test comment_id validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="comment_id cannot be empty"):
            Comment(
                comment_id=invalid_id,
                content="Test content",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    @pytest.mark.parametrize("invalid_content", ["", "   ", "\t", "\n"])
    def test_content_validation_whitespace(self, invalid_content: str) -> None:
        """Test content validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Comment(
                comment_id="C_456",
                content=invalid_content,
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    @pytest.mark.parametrize("invalid_author", ["", "   ", "\t", "\n"])
    def test_author_validation_whitespace(self, invalid_author: str) -> None:
        """Test author validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="author cannot be empty"):
            Comment(
                comment_id="C_456",
                content="Test content",
                author=invalid_author,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )

    @pytest.mark.parametrize("invalid_thread_id", ["", "   ", "\t", "\n"])
    def test_thread_id_validation_whitespace(self, invalid_thread_id: str) -> None:
        """Test thread_id validation with various whitespace scenarios."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            Comment(
                comment_id="C_456",
                content="Test content",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id=invalid_thread_id,
            )

    @pytest.mark.parametrize("content_length", [1, 100, 1000, 10000, 65535, 65536])
    def test_content_length_boundaries(self, content_length: int) -> None:
        """Test content length at various boundary values."""
        content = "x" * content_length

        if content_length <= Comment.MAX_CONTENT_LENGTH:
            # Should succeed
            comment = Comment(
                comment_id="C_456",
                content=content,
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )
            assert len(comment.content) == content_length
        else:
            # Should fail
            with pytest.raises(ValueError, match="content cannot exceed"):
                Comment(
                    comment_id="C_456",
                    content=content,
                    author="user",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    parent_id=None,
                    thread_id="RT_123",
                )

    def test_parent_id_circular_reference(self) -> None:
        """Test that parent_id can be the same as comment_id."""
        # Note: The model doesn't prevent circular references
        comment = Comment(
            comment_id="C_456",
            content="Test content",
            author="user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parent_id="C_456",  # Same as comment_id
            thread_id="RT_123",
        )

        assert comment.parent_id == comment.comment_id

    def test_extreme_date_differences(self) -> None:
        """Test with extreme date differences."""
        created = datetime(1970, 1, 1, 0, 0, 0)
        updated = datetime(2030, 12, 31, 23, 59, 59)

        comment = Comment(
            comment_id="C_456",
            content="Test content",
            author="user",
            created_at=created,
            updated_at=updated,
            parent_id=None,
            thread_id="RT_123",
        )

        assert comment.created_at == created
        assert comment.updated_at == updated

    def test_unicode_content_handling(self) -> None:
        """Test with Unicode content including emojis and special characters."""
        unicode_content = "Hello 👋 世界 🌍 Testing unicode: ñáéíóú àèìòù äëïöü"

        comment = Comment(
            comment_id="C_456",
            content=unicode_content,
            author="user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parent_id=None,
            thread_id="RT_123",
        )

        assert comment.content == unicode_content

    def test_special_characters_in_ids(self) -> None:
        """Test with special characters in IDs."""
        special_chars = "C_123-456.789_abc"

        comment = Comment(
            comment_id=special_chars,
            content="Test content",
            author="user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parent_id=special_chars,
            thread_id=special_chars,
        )

        assert comment.comment_id == special_chars
        assert comment.parent_id == special_chars
        assert comment.thread_id == special_chars


class TestSerializationRoundTrips:
    """Test serialization and deserialization round-trips."""

    def test_review_thread_roundtrip_with_complex_data(self) -> None:
        """Test ReviewThread serialization roundtrip with complex data."""
        original = ReviewThread(
            thread_id="RT_123-456.789",
            title="Complex Review Thread with Special Chars: ñáéíóú",
            created_at=datetime(2024, 3, 15, 14, 30, 45, 123456),
            updated_at=datetime(2024, 3, 16, 16, 45, 30, 987654),
            status="RESOLVED",
            author="user.name_123",
            comments=["C_1", "C_2", "C_3"],
        )

        # Serialize and deserialize
        data = original.to_dict()
        reconstructed = ReviewThread.from_dict(data)

        # Verify all fields match
        assert reconstructed.thread_id == original.thread_id
        assert reconstructed.title == original.title
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at
        assert reconstructed.status == original.status
        assert reconstructed.author == original.author
        assert reconstructed.comments == original.comments

    def test_comment_roundtrip_with_complex_data(self) -> None:
        """Test Comment serialization roundtrip with complex data."""
        original = Comment(
            comment_id="C_456-789.123",
            content="Complex comment with 🎉 emojis and special chars: ñáéíóú",
            author="user.name_456",
            created_at=datetime(2024, 3, 15, 14, 30, 45, 123456),
            updated_at=datetime(2024, 3, 16, 16, 45, 30, 987654),
            parent_id="C_123-456.789",
            thread_id="RT_789-123.456",
        )

        # Serialize and deserialize
        data = original.to_dict()
        reconstructed = Comment.from_dict(data)

        # Verify all fields match
        assert reconstructed.comment_id == original.comment_id
        assert reconstructed.content == original.content
        assert reconstructed.author == original.author
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at
        assert reconstructed.parent_id == original.parent_id
        assert reconstructed.thread_id == original.thread_id

    def test_multiple_objects_serialization(self) -> None:
        """Test serializing multiple objects to ensure no cross-contamination."""
        objects = []

        for i in range(10):
            thread = ReviewThread(
                thread_id=f"RT_{i}",
                title=f"Thread {i}",
                created_at=datetime(2024, 1, i + 1, 12, 0, 0),
                updated_at=datetime(2024, 1, i + 1, 13, 0, 0),
                status="UNRESOLVED",
                author=f"user_{i}",
                comments=[f"C_{i}_1", f"C_{i}_2"],
            )
            objects.append(thread)

        # Serialize all
        serialized = [obj.to_dict() for obj in objects]

        # Deserialize all
        deserialized = [ReviewThread.from_dict(data) for data in serialized]

        # Verify each object maintained its unique data
        for i, obj in enumerate(deserialized):
            assert obj.thread_id == f"RT_{i}"
            assert obj.title == f"Thread {i}"
            assert obj.author == f"user_{i}"
            assert obj.comments == [f"C_{i}_1", f"C_{i}_2"]


class TestPerformanceAndLargeData:
    """Test performance with large datasets."""

    def test_large_title_performance(self) -> None:
        """Test with large title (within reasonable limits)."""
        large_title = "x" * 10000  # 10KB title

        thread = ReviewThread(
            thread_id="RT_123",
            title=large_title,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
        )

        assert len(thread.title) == 10000

    def test_maximum_content_length(self) -> None:
        """Test Comment with maximum allowed content length."""
        max_content = "x" * Comment.MAX_CONTENT_LENGTH

        comment = Comment(
            comment_id="C_456",
            content=max_content,
            author="user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parent_id=None,
            thread_id="RT_123",
        )

        assert len(comment.content) == Comment.MAX_CONTENT_LENGTH

    def test_large_comments_list_serialization(self) -> None:
        """Test serialization performance with large comments list."""
        large_comments = [f"C_{i}" for i in range(10000)]

        thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=large_comments,
        )

        # Test serialization
        data = thread.to_dict()
        assert len(data["comments"]) == 10000

        # Test deserialization
        reconstructed = ReviewThread.from_dict(data)
        assert len(reconstructed.comments) == 10000
        assert reconstructed.comments[0] == "C_0"
        assert reconstructed.comments[9999] == "C_9999"
