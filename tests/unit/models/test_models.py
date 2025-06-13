"""Tests for data models."""

from datetime import datetime
from typing import Any

import pytest

from toady.exceptions import ValidationError
from toady.models.models import Comment, PullRequest, ReviewThread, _parse_datetime


@pytest.mark.model
@pytest.mark.unit
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
        with pytest.raises(ValidationError, match="thread_id cannot be empty"):
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
        with pytest.raises(ValidationError, match="title cannot be empty"):
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
        with pytest.raises(ValidationError, match="status must be one of"):
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
        with pytest.raises(ValidationError, match="author cannot be empty"):
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
        with pytest.raises(
            ValidationError, match="updated_at cannot be before created_at"
        ):
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
        comment1 = Comment(
            comment_id="comment1",
            content="First comment",
            author="johndoe",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            thread_id="RT_123",
            parent_id=None,
            review_id=None,
            review_state=None,
        )
        comment2 = Comment(
            comment_id="comment2",
            content="Second comment",
            author="janedoe",
            created_at=datetime(2024, 1, 2, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0),
            thread_id="RT_123",
            parent_id=None,
            review_id=None,
            review_state=None,
        )
        thread = ReviewThread(
            thread_id="RT_123",
            title="Test Review",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 13, 0, 0),
            status="RESOLVED",
            author="johndoe",
            comments=[comment1, comment2],
        )

        result = thread.to_dict()

        assert result == {
            "thread_id": "RT_123",
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T13:00:00",
            "status": "RESOLVED",
            "author": "johndoe",
            "comments": [
                {
                    "comment_id": "comment1",
                    "content": "First comment",
                    "author": "johndoe",
                    "created_at": "2024-01-01T12:00:00",
                    "updated_at": "2024-01-01T12:00:00",
                    "thread_id": "RT_123",
                    "parent_id": None,
                    "review_id": None,
                    "review_state": None,
                    "url": None,
                    "author_name": None,
                },
                {
                    "comment_id": "comment2",
                    "content": "Second comment",
                    "author": "janedoe",
                    "created_at": "2024-01-02T12:00:00",
                    "updated_at": "2024-01-02T12:00:00",
                    "thread_id": "RT_123",
                    "parent_id": None,
                    "review_id": None,
                    "review_state": None,
                    "url": None,
                    "author_name": None,
                },
            ],
            "file_path": None,
            "line": None,
            "original_line": None,
            "start_line": None,
            "original_start_line": None,
            "diff_side": None,
            "is_outdated": False,
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
        data: dict[str, Any] = {
            "title": "Test Review",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T13:00:00",
            "status": "UNRESOLVED",
            "author": "johndoe",
            "comments": [],
        }

        with pytest.raises(ValidationError, match="Missing required field: thread_id"):
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

        with pytest.raises(ValidationError, match="Invalid date format for created_at"):
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
        comments = [
            Comment(
                comment_id="c1",
                content="Comment 1",
                author="johndoe",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
            Comment(
                comment_id="c2",
                content="Comment 2",
                author="johndoe",
                created_at=datetime(2024, 1, 1, 13, 0, 0),
                updated_at=datetime(2024, 1, 1, 13, 0, 0),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
            Comment(
                comment_id="c3",
                content="Comment 3",
                author="johndoe",
                created_at=datetime(2024, 1, 1, 14, 0, 0),
                updated_at=datetime(2024, 1, 1, 14, 0, 0),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
        ]
        original = ReviewThread(
            thread_id="RT_123",
            title="Test Review",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 13, 0, 0),
            status="RESOLVED",
            author="johndoe",
            comments=comments,
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

    def test_is_resolved_property(self) -> None:
        """Test the is_resolved property works correctly."""
        # Test resolved thread
        resolved_thread = ReviewThread(
            thread_id="RT_123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="RESOLVED",
            author="user",
            comments=[],
        )
        assert resolved_thread.is_resolved is True

        # Test unresolved thread
        unresolved_thread = ReviewThread(
            thread_id="RT_124",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="UNRESOLVED",
            author="user",
            comments=[],
        )
        assert unresolved_thread.is_resolved is False

        # Test other statuses
        for status in ["PENDING", "OUTDATED", "DISMISSED"]:
            thread = ReviewThread(
                thread_id="RT_125",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status=status,
                author="user",
                comments=[],
            )
            assert thread.is_resolved is False

    def test_comments_list_immutability(self) -> None:
        """Test that comments list changes don't affect the original."""
        comments = [
            Comment(
                comment_id="C_1",
                content="Comment 1",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            ),
            Comment(
                comment_id="C_2",
                content="Comment 2",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            ),
        ]
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
        comments.append(
            Comment(
                comment_id="C_3",
                content="Comment 3",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                parent_id=None,
                thread_id="RT_123",
            )
        )

        # Thread should still have original comments
        assert len(thread.comments) == 2
        assert thread.comments[0].comment_id == "C_1"
        assert thread.comments[1].comment_id == "C_2"

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
        with pytest.raises(ValidationError, match="Unable to parse datetime"):
            _parse_datetime("not a date")


@pytest.mark.model
@pytest.mark.unit
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
        with pytest.raises(ValidationError, match="comment_id cannot be empty"):
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
        with pytest.raises(ValidationError, match="content cannot be empty"):
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
        with pytest.raises(
            ValidationError, match="content cannot exceed 65536 characters"
        ):
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
        with pytest.raises(ValidationError, match="author cannot be empty"):
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
        with pytest.raises(ValidationError, match="thread_id cannot be empty"):
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

        with pytest.raises(
            ValidationError, match="updated_at cannot be before created_at"
        ):
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
            "review_id": None,
            "review_state": None,
            "url": None,
            "author_name": None,
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
            "review_id": None,
            "review_state": None,
            "url": None,
            "author_name": None,
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

        with pytest.raises(ValidationError, match="Missing required field"):
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

        with pytest.raises(ValidationError, match="Invalid date format for created_at"):
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

        with pytest.raises(ValidationError, match="Invalid date format for updated_at"):
            Comment.from_dict(data)


@pytest.mark.model
@pytest.mark.unit
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

        with pytest.raises(ValidationError, match="Invalid date format for updated_at"):
            ReviewThread.from_dict(data)

    @pytest.mark.parametrize("invalid_id", ["", "   ", "\t", "\n"])
    def test_thread_id_validation_whitespace(self, invalid_id: str) -> None:
        """Test thread_id validation with various whitespace scenarios."""
        with pytest.raises(ValidationError, match="thread_id cannot be empty"):
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
        with pytest.raises(ValidationError, match="title cannot be empty"):
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
        with pytest.raises(ValidationError, match="author cannot be empty"):
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
        with pytest.raises(ValidationError, match="status must be one of"):
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
        original_comments = [
            Comment(
                comment_id="C_1",
                content="Comment 1",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
            Comment(
                comment_id="C_2",
                content="Comment 2",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
        ]
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
        original_comments.append(
            Comment(
                comment_id="C_3",
                content="Comment 3",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            )
        )

        # Thread's comments should be unchanged
        assert len(thread.comments) == 2
        assert thread.comments[0].comment_id == "C_1"
        assert thread.comments[1].comment_id == "C_2"

        # Modify thread's comments list
        thread.comments.append(
            Comment(
                comment_id="C_4",
                content="Comment 4",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            )
        )

        # Original list should be unchanged
        assert len(original_comments) == 3
        assert original_comments[2].comment_id == "C_3"

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
        large_comments = [
            Comment(
                comment_id=f"C_{i}",
                content=f"Comment {i}",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            )
            for i in range(1000)
        ]

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
        assert thread.comments[0].comment_id == "C_0"
        assert thread.comments[999].comment_id == "C_999"


@pytest.mark.model
@pytest.mark.unit
class TestCommentEdgeCases:
    """Additional edge case tests for Comment."""

    @pytest.mark.parametrize("invalid_id", ["", "   ", "\t", "\n"])
    def test_comment_id_validation_whitespace(self, invalid_id: str) -> None:
        """Test comment_id validation with various whitespace scenarios."""
        with pytest.raises(ValidationError, match="comment_id cannot be empty"):
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
        with pytest.raises(ValidationError, match="content cannot be empty"):
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
        with pytest.raises(ValidationError, match="author cannot be empty"):
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
        with pytest.raises(ValidationError, match="thread_id cannot be empty"):
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
            with pytest.raises(ValidationError, match="content cannot exceed"):
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


@pytest.mark.model
@pytest.mark.unit
class TestSerializationRoundTrips:
    """Test serialization and deserialization round-trips."""

    def test_review_thread_roundtrip_with_complex_data(self) -> None:
        """Test ReviewThread serialization roundtrip with complex data."""
        comments = [
            Comment(
                comment_id="C_1",
                content="Comment 1 with special chars: ñáéíóú",
                author="user.name_123",
                created_at=datetime(2024, 3, 15, 14, 30, 45, 123456),
                updated_at=datetime(2024, 3, 15, 14, 30, 45, 123456),
                thread_id="RT_123-456.789",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
            Comment(
                comment_id="C_2",
                content="Comment 2",
                author="user.name_123",
                created_at=datetime(2024, 3, 15, 15, 0, 0),
                updated_at=datetime(2024, 3, 15, 15, 0, 0),
                thread_id="RT_123-456.789",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
            Comment(
                comment_id="C_3",
                content="Comment 3",
                author="user.name_123",
                created_at=datetime(2024, 3, 15, 15, 30, 0),
                updated_at=datetime(2024, 3, 15, 15, 30, 0),
                thread_id="RT_123-456.789",
                parent_id=None,
                review_id=None,
                review_state=None,
            ),
        ]

        original = ReviewThread(
            thread_id="RT_123-456.789",
            title="Complex Review Thread with Special Chars: ñáéíóú",
            created_at=datetime(2024, 3, 15, 14, 30, 45, 123456),
            updated_at=datetime(2024, 3, 16, 16, 45, 30, 987654),
            status="RESOLVED",
            author="user.name_123",
            comments=comments,
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
        assert len(reconstructed.comments) == len(original.comments)
        for i, comment in enumerate(reconstructed.comments):
            assert comment.comment_id == original.comments[i].comment_id
            assert comment.content == original.comments[i].content

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
            comments = [
                Comment(
                    comment_id=f"C_{i}_1",
                    content=f"Comment {i}_1",
                    author=f"user_{i}",
                    created_at=datetime(2024, 1, i + 1, 12, 0, 0),
                    updated_at=datetime(2024, 1, i + 1, 12, 0, 0),
                    thread_id=f"RT_{i}",
                    parent_id=None,
                    review_id=None,
                    review_state=None,
                ),
                Comment(
                    comment_id=f"C_{i}_2",
                    content=f"Comment {i}_2",
                    author=f"user_{i}",
                    created_at=datetime(2024, 1, i + 1, 12, 30, 0),
                    updated_at=datetime(2024, 1, i + 1, 12, 30, 0),
                    thread_id=f"RT_{i}",
                    parent_id=None,
                    review_id=None,
                    review_state=None,
                ),
            ]
            thread = ReviewThread(
                thread_id=f"RT_{i}",
                title=f"Thread {i}",
                created_at=datetime(2024, 1, i + 1, 12, 0, 0),
                updated_at=datetime(2024, 1, i + 1, 13, 0, 0),
                status="UNRESOLVED",
                author=f"user_{i}",
                comments=comments,
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
            assert len(obj.comments) == 2
            assert obj.comments[0].comment_id == f"C_{i}_1"
            assert obj.comments[1].comment_id == f"C_{i}_2"


@pytest.mark.model
@pytest.mark.unit
@pytest.mark.slow
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
        large_comments = [
            Comment(
                comment_id=f"C_{i}",
                content=f"Comment {i}",
                author="user",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                thread_id="RT_123",
                parent_id=None,
                review_id=None,
                review_state=None,
            )
            for i in range(10000)
        ]

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
        assert reconstructed.comments[0].comment_id == "C_0"
        assert reconstructed.comments[9999].comment_id == "C_9999"


@pytest.mark.model
@pytest.mark.unit
class TestPullRequest:
    """Test the PullRequest dataclass."""

    def test_create_valid_pull_request(self) -> None:
        """Test creating a valid PullRequest instance."""
        pr = PullRequest(
            number=42,
            title="Add new feature",
            author="testuser",
            head_ref="feature-branch",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            url="https://github.com/testowner/testrepo/pull/42",
            review_thread_count=3,
            node_id="PR_kwDOAbc123",
        )

        assert pr.number == 42
        assert pr.title == "Add new feature"
        assert pr.author == "testuser"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.is_draft is False
        assert pr.created_at == datetime(2024, 1, 15, 10, 30, 0)
        assert pr.updated_at == datetime(2024, 1, 15, 11, 0, 0)
        assert pr.url == "https://github.com/testowner/testrepo/pull/42"
        assert pr.review_thread_count == 3
        assert pr.node_id == "PR_kwDOAbc123"

    def test_create_pull_request_without_node_id(self) -> None:
        """Test creating a PullRequest without node_id (optional field)."""
        pr = PullRequest(
            number=43,
            title="Fix bug",
            author="contributor",
            head_ref="bugfix",
            base_ref="main",
            is_draft=True,
            created_at=datetime(2024, 1, 16, 9, 15, 0),
            updated_at=datetime(2024, 1, 16, 10, 45, 0),
            url="https://github.com/testowner/testrepo/pull/43",
            review_thread_count=0,
        )

        assert pr.node_id is None

    def test_pull_request_validation_invalid_number(self) -> None:
        """Test PullRequest validation with invalid number."""
        with pytest.raises(ValidationError, match="number must be positive"):
            PullRequest(
                number=0,  # Invalid: must be positive
                title="Test PR",
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/0",
                review_thread_count=0,
            )

        with pytest.raises(ValidationError, match="number must be positive"):
            PullRequest(
                number=-1,  # Invalid: negative
                title="Test PR",
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/-1",
                review_thread_count=0,
            )

    def test_pull_request_validation_empty_title(self) -> None:
        """Test PullRequest validation with empty title."""
        with pytest.raises(ValidationError, match="title cannot be empty"):
            PullRequest(
                number=42,
                title="",  # Invalid: empty
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

        with pytest.raises(ValidationError, match="title cannot be empty"):
            PullRequest(
                number=42,
                title="   ",  # Invalid: whitespace only
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

    def test_pull_request_validation_empty_author(self) -> None:
        """Test PullRequest validation with empty author."""
        with pytest.raises(ValidationError, match="author cannot be empty"):
            PullRequest(
                number=42,
                title="Test PR",
                author="",  # Invalid: empty
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

    def test_pull_request_validation_empty_refs(self) -> None:
        """Test PullRequest validation with empty branch refs."""
        with pytest.raises(ValidationError, match="head_ref cannot be empty"):
            PullRequest(
                number=42,
                title="Test PR",
                author="testuser",
                head_ref="",  # Invalid: empty
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

        with pytest.raises(ValidationError, match="base_ref cannot be empty"):
            PullRequest(
                number=42,
                title="Test PR",
                author="testuser",
                head_ref="feature",
                base_ref="",  # Invalid: empty
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

    def test_pull_request_validation_invalid_is_draft(self) -> None:
        """Test PullRequest validation with invalid is_draft type."""
        with pytest.raises(ValidationError, match="is_draft must be a boolean"):
            PullRequest(
                number=42,
                title="Test PR",
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft="false",  # type: ignore  # Invalid: string instead of boolean
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

    def test_pull_request_validation_negative_review_thread_count(self) -> None:
        """Test PullRequest validation with negative review thread count."""
        with pytest.raises(
            ValidationError, match="review_thread_count cannot be negative"
        ):
            PullRequest(
                number=42,
                title="Test PR",
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                url="https://github.com/test/repo/pull/42",
                review_thread_count=-1,  # Invalid: negative
            )

    def test_pull_request_validation_invalid_dates(self) -> None:
        """Test PullRequest validation with invalid date ordering."""
        created = datetime(2024, 1, 15, 12, 0, 0)
        updated = datetime(2024, 1, 15, 10, 0, 0)  # Before created

        with pytest.raises(
            ValidationError, match="updated_at cannot be before created_at"
        ):
            PullRequest(
                number=42,
                title="Test PR",
                author="testuser",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=created,
                updated_at=updated,  # Invalid: before created_at
                url="https://github.com/test/repo/pull/42",
                review_thread_count=0,
            )

    def test_pull_request_to_dict(self) -> None:
        """Test PullRequest serialization to dictionary."""
        pr = PullRequest(
            number=42,
            title="Add new feature",
            author="testuser",
            head_ref="feature-branch",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            url="https://github.com/testowner/testrepo/pull/42",
            review_thread_count=3,
            node_id="PR_kwDOAbc123",
        )

        data = pr.to_dict()

        expected = {
            "number": 42,
            "title": "Add new feature",
            "author": "testuser",
            "head_ref": "feature-branch",
            "base_ref": "main",
            "is_draft": False,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T11:00:00",
            "url": "https://github.com/testowner/testrepo/pull/42",
            "review_thread_count": 3,
            "node_id": "PR_kwDOAbc123",
        }

        assert data == expected

    def test_pull_request_from_dict(self) -> None:
        """Test PullRequest deserialization from dictionary."""
        data = {
            "number": 42,
            "title": "Add new feature",
            "author": "testuser",
            "head_ref": "feature-branch",
            "base_ref": "main",
            "is_draft": False,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T11:00:00",
            "url": "https://github.com/testowner/testrepo/pull/42",
            "review_thread_count": 3,
            "node_id": "PR_kwDOAbc123",
        }

        pr = PullRequest.from_dict(data)

        assert pr.number == 42
        assert pr.title == "Add new feature"
        assert pr.author == "testuser"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.is_draft is False
        assert pr.created_at == datetime(2024, 1, 15, 10, 30, 0)
        assert pr.updated_at == datetime(2024, 1, 15, 11, 0, 0)
        assert pr.url == "https://github.com/testowner/testrepo/pull/42"
        assert pr.review_thread_count == 3
        assert pr.node_id == "PR_kwDOAbc123"

    def test_pull_request_from_dict_missing_fields(self) -> None:
        """Test PullRequest deserialization with missing required fields."""
        data = {
            "number": 42,
            "title": "Test PR",
            # Missing head_ref, base_ref, etc.
        }

        with pytest.raises(ValidationError, match="Missing required field"):
            PullRequest.from_dict(data)

    def test_pull_request_from_dict_invalid_dates(self) -> None:
        """Test PullRequest deserialization with invalid date formats."""
        data = {
            "number": 42,
            "title": "Test PR",
            "author": "testuser",
            "head_ref": "feature",
            "base_ref": "main",
            "is_draft": False,
            "created_at": "invalid-date",
            "updated_at": "2024-01-15T11:00:00",
            "url": "https://github.com/test/repo/pull/42",
            "review_thread_count": 0,
        }

        with pytest.raises(ValidationError, match="Invalid date format for created_at"):
            PullRequest.from_dict(data)

    def test_pull_request_str_representation(self) -> None:
        """Test PullRequest string representation."""
        pr = PullRequest(
            number=42,
            title="Add new feature",
            author="testuser",
            head_ref="feature-branch",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            url="https://github.com/testowner/testrepo/pull/42",
            review_thread_count=3,
        )

        expected = "PR #42: Add new feature by testuser (feature-branch -> main)"
        assert str(pr) == expected

    def test_pull_request_str_representation_draft(self) -> None:
        """Test PullRequest string representation for draft PR."""
        pr = PullRequest(
            number=43,
            title="Draft: Work in progress",
            author="contributor",
            head_ref="wip-feature",
            base_ref="main",
            is_draft=True,
            created_at=datetime(2024, 1, 16, 9, 15, 0),
            updated_at=datetime(2024, 1, 16, 10, 45, 0),
            url="https://github.com/testowner/testrepo/pull/43",
            review_thread_count=0,
        )

        expected = (
            "PR #43: Draft: Work in progress by contributor "
            "(wip-feature -> main) (draft)"
        )
        assert str(pr) == expected

    def test_pull_request_roundtrip_serialization(self) -> None:
        """Test PullRequest serialization and deserialization roundtrip."""
        original = PullRequest(
            number=42,
            title="Add new feature",
            author="testuser",
            head_ref="feature-branch",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
            url="https://github.com/testowner/testrepo/pull/42",
            review_thread_count=3,
            node_id="PR_kwDOAbc123",
        )

        # Serialize to dict
        data = original.to_dict()

        # Deserialize back to object
        reconstructed = PullRequest.from_dict(data)

        # Verify all fields match
        assert reconstructed.number == original.number
        assert reconstructed.title == original.title
        assert reconstructed.author == original.author
        assert reconstructed.head_ref == original.head_ref
        assert reconstructed.base_ref == original.base_ref
        assert reconstructed.is_draft == original.is_draft
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at
        assert reconstructed.url == original.url
        assert reconstructed.review_thread_count == original.review_thread_count
        assert reconstructed.node_id == original.node_id


@pytest.mark.model
@pytest.mark.unit
class TestTypeValidationEdgeCases:
    """Test type validation edge cases for better coverage."""

    def test_review_thread_invalid_thread_id_type(self) -> None:
        """Test ReviewThread with invalid thread_id type."""
        with pytest.raises(ValidationError, match="thread_id must be a string"):
            ReviewThread(
                thread_id=123,  # type: ignore  # Invalid: not a string
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    def test_review_thread_invalid_title_type(self) -> None:
        """Test ReviewThread with invalid title type."""
        with pytest.raises(ValidationError, match="title must be a string"):
            ReviewThread(
                thread_id="RT_123",
                title=456,  # type: ignore  # Invalid: not a string
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user",
                comments=[],
            )

    def test_review_thread_invalid_status_type(self) -> None:
        """Test ReviewThread with invalid status type."""
        with pytest.raises(ValidationError, match="status must be a string"):
            ReviewThread(
                thread_id="RT_123",
                title="Test",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status=789,  # type: ignore  # Invalid: not a string
                author="user",
                comments=[],
            )

    def test_parse_datetime_validation_error_edge_case(self) -> None:
        """Test _parse_datetime with edge case exception handling."""
        # Test with an exception that doesn't have error_code attribute
        with pytest.raises(ValidationError, match="Unable to parse datetime"):
            _parse_datetime("completely-invalid-format")
