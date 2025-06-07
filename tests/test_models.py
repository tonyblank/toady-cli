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
