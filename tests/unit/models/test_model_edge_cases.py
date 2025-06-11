"""Additional edge case tests for model classes to improve coverage."""

from datetime import datetime

import pytest

from toady.exceptions import ValidationError
from toady.models.models import Comment, PullRequest, ReviewThread, _parse_datetime


@pytest.mark.model
@pytest.mark.unit
class TestParseDatetimeWrapper:
    """Test the _parse_datetime wrapper function in models module."""

    def test_parse_datetime_success(self):
        """Test successful datetime parsing."""
        result = _parse_datetime("2024-01-15T10:30:45")
        expected = datetime(2024, 1, 15, 10, 30, 45)
        assert result == expected

    def test_parse_datetime_with_timezone(self):
        """Test datetime parsing with timezone."""
        result = _parse_datetime("2024-01-15T10:30:45Z")
        expected = datetime(2024, 1, 15, 10, 30, 45)
        assert result == expected

    def test_parse_datetime_validation_error_passthrough(self):
        """Test that ValidationError is passed through."""
        with pytest.raises(ValidationError) as exc_info:
            _parse_datetime("invalid-date")

        error = exc_info.value
        assert error.field_name == "date_str"
        assert "Unable to parse datetime" in str(error)

    def test_parse_datetime_unexpected_error_wrapping(self):
        """Test wrapping of unexpected errors."""
        from unittest.mock import patch

        # Mock parse_datetime to raise a non-ValidationError
        with patch(
            "toady.models.models.parse_datetime", side_effect=RuntimeError("Unexpected")
        ):
            with pytest.raises(ValidationError) as exc_info:
                _parse_datetime("2024-01-15T10:30:45")

            error = exc_info.value
            assert error.field_name == "date_str"
            assert "Failed to parse datetime" in str(error)


@pytest.mark.model
@pytest.mark.unit
class TestReviewThreadEdgeCasesAdditional:
    """Additional edge case tests for ReviewThread."""

    def test_review_thread_from_dict_with_comment_objects(self):
        """Test creating ReviewThread from dict with Comment objects in list."""
        existing_comment = Comment(
            comment_id="IC_existing",
            content="Existing comment",
            author="existing_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_test",
        )

        data = {
            "thread_id": "RT_test",
            "title": "Test thread",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "status": "UNRESOLVED",
            "author": "test_user",
            "comments": [existing_comment],  # Comment object instead of dict
        }

        thread = ReviewThread.from_dict(data)
        assert len(thread.comments) == 1
        assert thread.comments[0] is existing_comment

    def test_review_thread_from_dict_mixed_comments(self):
        """Test creating ReviewThread with mix of dict and Comment objects."""
        existing_comment = Comment(
            comment_id="IC_existing",
            content="Existing comment",
            author="existing_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_test",
        )

        data = {
            "thread_id": "RT_test",
            "title": "Test thread",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "status": "UNRESOLVED",
            "author": "test_user",
            "comments": [
                existing_comment,
                {
                    "comment_id": "IC_new",
                    "content": "New comment",
                    "author": "new_user",
                    "created_at": "2024-01-15T10:00:00",
                    "updated_at": "2024-01-15T10:00:00",
                    "parent_id": None,
                    "thread_id": "RT_test",
                },
            ],
        }

        thread = ReviewThread.from_dict(data)
        assert len(thread.comments) == 2
        assert thread.comments[0] is existing_comment
        assert isinstance(thread.comments[1], Comment)
        assert thread.comments[1].comment_id == "IC_new"

    def test_review_thread_all_optional_fields(self):
        """Test ReviewThread creation with all optional fields."""
        data = {
            "thread_id": "RT_full",
            "title": "Full thread",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "status": "RESOLVED",
            "author": "full_user",
            "comments": [],
            "file_path": "src/test.py",
            "line": 42,
            "original_line": 40,
            "start_line": 35,
            "original_start_line": 33,
            "diff_side": "RIGHT",
            "is_outdated": True,
        }

        thread = ReviewThread.from_dict(data)
        assert thread.file_path == "src/test.py"
        assert thread.line == 42
        assert thread.original_line == 40
        assert thread.start_line == 35
        assert thread.original_start_line == 33
        assert thread.diff_side == "RIGHT"
        assert thread.is_outdated is True

    def test_review_thread_is_outdated_boolean_conversion(self):
        """Test is_outdated field boolean conversion."""
        # Test truthy values
        for truthy_value in [True, 1, "true", "yes", [1]]:
            data = {
                "thread_id": "RT_bool",
                "title": "Bool test",
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:00:00",
                "status": "UNRESOLVED",
                "author": "bool_user",
                "comments": [],
                "is_outdated": truthy_value,
            }
            thread = ReviewThread.from_dict(data)
            assert thread.is_outdated is True

        # Test falsy values
        for falsy_value in [False, 0, "", None, []]:
            data = {
                "thread_id": "RT_bool",
                "title": "Bool test",
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:00:00",
                "status": "UNRESOLVED",
                "author": "bool_user",
                "comments": [],
                "is_outdated": falsy_value,
            }
            thread = ReviewThread.from_dict(data)
            assert thread.is_outdated is False


@pytest.mark.model
@pytest.mark.unit
class TestCommentEdgeCasesAdditional:
    """Additional edge case tests for Comment."""

    def test_comment_all_optional_fields(self):
        """Test Comment creation with all optional fields."""
        data = {
            "comment_id": "IC_full",
            "content": "Full comment",
            "author": "full_user",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:30:00",
            "parent_id": "IC_parent",
            "thread_id": "RT_parent",
            "author_name": "Full User",
            "url": "https://github.com/test/repo/pull/1#issuecomment-123",
            "review_id": "PRREV_123",
            "review_state": "APPROVED",
        }

        comment = Comment.from_dict(data)
        assert comment.author_name == "Full User"
        assert comment.url == "https://github.com/test/repo/pull/1#issuecomment-123"
        assert comment.review_id == "PRREV_123"
        assert comment.review_state == "APPROVED"

    def test_comment_minimal_required_fields_only(self):
        """Test Comment creation with only required fields."""
        data = {
            "comment_id": "IC_minimal",
            "content": "Minimal comment",
            "author": "minimal_user",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "parent_id": None,
            "thread_id": "RT_minimal",
        }

        comment = Comment.from_dict(data)
        # Verify optional fields have expected defaults
        assert comment.author_name is None
        assert comment.url is None
        assert comment.review_id is None
        assert comment.review_state is None


@pytest.mark.model
@pytest.mark.unit
class TestPullRequestAdditional:
    """Additional tests for PullRequest model."""

    def test_pull_request_all_fields(self):
        """Test PullRequest creation with all fields."""
        pr = PullRequest(
            number=123,
            title="Test PR",
            author="pr_author",
            head_ref="feature-branch",
            base_ref="main",
            is_draft=False,
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 12, 0, 0),
            url="https://github.com/test/repo/pull/123",
            review_thread_count=5,
            node_id="PR_kwDOABcD12MAAAABcDE3fg",
        )

        assert pr.number == 123
        assert pr.title == "Test PR"
        assert pr.author == "pr_author"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.is_draft is False
        assert pr.url == "https://github.com/test/repo/pull/123"
        assert pr.review_thread_count == 5
        assert pr.node_id == "PR_kwDOABcD12MAAAABcDE3fg"
        assert pr.created_at == datetime(2024, 1, 15, 10, 0, 0)
        assert pr.updated_at == datetime(2024, 1, 15, 12, 0, 0)

    def test_pull_request_from_dict_complete(self):
        """Test PullRequest creation from complete dict."""
        data = {
            "number": 456,
            "title": "Complete PR",
            "author": "complete_author",
            "head_ref": "feature-456",
            "base_ref": "main",
            "is_draft": True,
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T14:00:00",
            "url": "https://github.com/test/repo/pull/456",
            "review_thread_count": 3,
            "node_id": "PR_kwDOABcD12MAAAABcDE456",
        }

        pr = PullRequest.from_dict(data)
        assert pr.number == 456
        assert pr.title == "Complete PR"
        assert pr.author == "complete_author"
        assert pr.head_ref == "feature-456"
        assert pr.base_ref == "main"
        assert pr.is_draft is True
        assert pr.url == "https://github.com/test/repo/pull/456"
        assert pr.review_thread_count == 3
        assert pr.node_id == "PR_kwDOABcD12MAAAABcDE456"
        assert pr.created_at == datetime(2024, 1, 15, 10, 0, 0)
        assert pr.updated_at == datetime(2024, 1, 15, 14, 0, 0)

    def test_pull_request_validation_invalid_number(self):
        """Test PullRequest validation with invalid number."""
        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                number="not_a_number",
                title="Test PR",
                author="test_author",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                url="https://github.com/test/repo/pull/1",
                review_thread_count=0,
            )

        error = exc_info.value
        assert error.field_name == "number"
        assert "number must be an integer" in str(error)

    def test_pull_request_validation_negative_number(self):
        """Test PullRequest validation with negative number."""
        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                number=-5,
                title="Test PR",
                author="test_author",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                url="https://github.com/test/repo/pull/1",
                review_thread_count=0,
            )

        error = exc_info.value
        assert error.field_name == "number"
        assert "number must be positive" in str(error)

    def test_pull_request_validation_zero_number(self):
        """Test PullRequest validation with zero number."""
        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                number=0,
                title="Test PR",
                author="test_author",
                head_ref="feature",
                base_ref="main",
                is_draft=False,
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                url="https://github.com/test/repo/pull/1",
                review_thread_count=0,
            )

        error = exc_info.value
        assert error.field_name == "number"
        assert "number must be positive" in str(error)


@pytest.mark.model
@pytest.mark.unit
class TestModelUtilities:
    """Test model utility functions and edge cases."""

    def test_review_thread_is_resolved_property(self):
        """Test ReviewThread.is_resolved property."""
        # Test resolved status
        resolved_thread = ReviewThread(
            thread_id="RT_resolved",
            title="Resolved thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="RESOLVED",
            author="test_user",
            comments=[],
        )
        assert resolved_thread.is_resolved is True

        # Test unresolved status
        unresolved_thread = ReviewThread(
            thread_id="RT_unresolved",
            title="Unresolved thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="UNRESOLVED",
            author="test_user",
            comments=[],
        )
        assert unresolved_thread.is_resolved is False

        # Test other statuses
        for status in ["PENDING", "OUTDATED", "DISMISSED"]:
            thread = ReviewThread(
                thread_id=f"RT_{status.lower()}",
                title=f"{status} thread",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status=status,
                author="test_user",
                comments=[],
            )
            assert thread.is_resolved is False

    def test_comment_parent_id_logic(self):
        """Test Comment parent_id handling."""
        # Test comment with parent_id (is a reply)
        reply_comment = Comment(
            comment_id="IC_reply",
            content="This is a reply",
            author="reply_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id="IC_parent",
            thread_id="RT_test",
        )
        assert reply_comment.parent_id == "IC_parent"

        # Test comment without parent_id (not a reply)
        original_comment = Comment(
            comment_id="IC_original",
            content="This is an original comment",
            author="original_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_test",
        )
        assert original_comment.parent_id is None

    def test_comment_content_property_edge_cases(self):
        """Test Comment content property with edge cases."""
        # Test with very long content
        long_content = "Very long content. " * 1000  # ~19KB content
        comment = Comment(
            comment_id="IC_long",
            content=long_content,
            author="long_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_test",
        )
        assert comment.content == long_content
        assert len(comment.content) > 15000

        # Test with special characters and unicode
        special_content = (
            "Special chars: !@#$%^&*()[]{}|;':\",./<>?`~\nNewline\tTab\r\nCRLF\n🚀💯🎉"
        )
        comment = Comment(
            comment_id="IC_special",
            content=special_content,
            author="special_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_test",
        )
        assert comment.content == special_content
        assert "🚀💯🎉" in comment.content
