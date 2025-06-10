"""Data models for GitHub review threads and comments."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError, create_validation_error
from .utils import parse_datetime


def _parse_datetime(date_str: str) -> datetime:
    """Parse datetime string in various ISO formats.

    Args:
        date_str: Date string in ISO format

    Returns:
        datetime object

    Raises:
        ValidationError: If date string cannot be parsed
    """
    try:
        return parse_datetime(date_str)
    except Exception as e:
        # parse_datetime now raises ValidationError, but handle any edge cases
        if hasattr(e, "error_code"):
            # Already a ValidationError
            raise
        raise create_validation_error(
            field_name="date_str",
            invalid_value=date_str,
            expected_format="ISO datetime string",
            message=f"Failed to parse datetime: {str(e)}",
        ) from e


@dataclass
class ReviewThread:
    """Represents a GitHub pull request review thread.

    Attributes:
        thread_id: Unique identifier for the review thread
        title: Title or first line of the review comment
        created_at: When the thread was created
        updated_at: When the thread was last updated
        status: Current status (RESOLVED, UNRESOLVED, PENDING, OUTDATED, DISMISSED)
        author: Username of the thread author
        comments: List of Comment objects in this thread
    """

    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    status: str
    author: str
    comments: List["Comment"] = field(default_factory=list)

    # Valid status values
    VALID_STATUSES = {"RESOLVED", "UNRESOLVED", "PENDING", "OUTDATED", "DISMISSED"}

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValidationError: If any field validation fails
        """
        try:
            # Validate thread_id
            if not isinstance(self.thread_id, str):
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value=type(self.thread_id).__name__,
                    expected_format="non-empty string",
                    message="thread_id must be a string",
                )
            if not self.thread_id.strip():
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="thread_id cannot be empty",
                )

            # Validate title
            if not isinstance(self.title, str):
                raise create_validation_error(
                    field_name="title",
                    invalid_value=type(self.title).__name__,
                    expected_format="non-empty string",
                    message="title must be a string",
                )
            if not self.title.strip():
                raise create_validation_error(
                    field_name="title",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="title cannot be empty",
                )

            # Validate status
            if not isinstance(self.status, str):
                raise create_validation_error(
                    field_name="status",
                    invalid_value=type(self.status).__name__,
                    expected_format=f"one of {', '.join(sorted(self.VALID_STATUSES))}",
                    message="status must be a string",
                )
            if self.status not in self.VALID_STATUSES:
                raise create_validation_error(
                    field_name="status",
                    invalid_value=self.status,
                    expected_format=f"one of {', '.join(sorted(self.VALID_STATUSES))}",
                    message=(
                        "status must be one of "
                        f"{', '.join(sorted(self.VALID_STATUSES))}"
                    ),
                )

            # Validate author
            if not isinstance(self.author, str):
                raise create_validation_error(
                    field_name="author",
                    invalid_value=type(self.author).__name__,
                    expected_format="non-empty string",
                    message="author must be a string",
                )
            if not self.author.strip():
                raise create_validation_error(
                    field_name="author",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="author cannot be empty",
                )

            # Validate dates
            if not isinstance(self.created_at, datetime):
                raise create_validation_error(
                    field_name="created_at",
                    invalid_value=type(self.created_at).__name__,
                    expected_format="datetime object",
                    message="created_at must be a datetime object",
                )
            if not isinstance(self.updated_at, datetime):
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=type(self.updated_at).__name__,
                    expected_format="datetime object",
                    message="updated_at must be a datetime object",
                )
            if self.updated_at < self.created_at:
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=self.updated_at.isoformat(),
                    expected_format=f"datetime >= {self.created_at.isoformat()}",
                    message="updated_at cannot be before created_at",
                )

            # Validate comments list
            if not isinstance(self.comments, list):
                raise create_validation_error(
                    field_name="comments",
                    invalid_value=type(self.comments).__name__,
                    expected_format="list of comments",
                    message="comments must be a list",
                )

            # Ensure comments is a copy to prevent external modifications
            self.comments = list(self.comments)

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except Exception as e:
            # Wrap any unexpected errors
            raise create_validation_error(
                field_name="ReviewThread",
                invalid_value="validation failure",
                expected_format="valid ReviewThread object",
                message=f"Unexpected error during ReviewThread validation: {str(e)}",
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert the ReviewThread to a dictionary for serialization.

        Returns:
            Dictionary representation of the ReviewThread
        """
        # Convert Comment objects to dictionaries
        serialized_comments = [comment.to_dict() for comment in self.comments]

        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "author": self.author,
            "comments": serialized_comments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewThread":
        """Create a ReviewThread from a dictionary.

        Args:
            data: Dictionary containing ReviewThread fields

        Returns:
            ReviewThread instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Check required fields
        required_fields = {
            "thread_id",
            "title",
            "created_at",
            "updated_at",
            "status",
            "author",
        }
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise create_validation_error(
                field_name="from_dict",
                invalid_value=f"missing: {', '.join(missing_fields)}",
                expected_format="dictionary with all required fields",
                message=f"Missing required field: {', '.join(missing_fields)}",
            )

        # Parse dates
        try:
            created_at = _parse_datetime(data["created_at"])
        except (ValueError, ValidationError) as err:
            raise create_validation_error(
                field_name="created_at",
                invalid_value=data["created_at"],
                expected_format="ISO datetime string",
                message=f"Invalid date format for created_at: {data['created_at']}",
            ) from err

        try:
            updated_at = _parse_datetime(data["updated_at"])
        except (ValueError, ValidationError) as err:
            raise create_validation_error(
                field_name="updated_at",
                invalid_value=data["updated_at"],
                expected_format="ISO datetime string",
                message=f"Invalid date format for updated_at: {data['updated_at']}",
            ) from err

        # Parse comments from dictionaries to Comment objects
        comments = []
        for comment_data in data.get("comments", []):
            if isinstance(comment_data, dict):
                comments.append(Comment.from_dict(comment_data))
            else:
                # If it's already a Comment object, use it as is
                comments.append(comment_data)

        # Create instance
        return cls(
            thread_id=data["thread_id"],
            title=data["title"],
            created_at=created_at,
            updated_at=updated_at,
            status=data["status"],
            author=data["author"],
            comments=comments,
        )

    @property
    def is_resolved(self) -> bool:
        """Check if the review thread is resolved.

        Returns:
            True if the thread is resolved, False otherwise
        """
        return self.status == "RESOLVED"

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"ReviewThread(id={self.thread_id}, title='{self.title}', "
            f"status={self.status}, author={self.author})"
        )


@dataclass
class Comment:
    """Represents a GitHub pull request review comment.

    Attributes:
        comment_id: Unique identifier for the comment
        content: Text content of the comment
        author: Username of the comment author
        created_at: When the comment was created
        updated_at: When the comment was last updated
        parent_id: ID of parent comment if this is a reply (None for top-level)
        thread_id: ID of the review thread this comment belongs to
        review_id: ID of the pull request review this comment belongs to (optional)
        review_state: State of the review (PENDING, SUBMITTED, etc.) (optional)
    """

    comment_id: str
    content: str
    author: str
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[str]
    thread_id: str
    review_id: Optional[str] = None
    review_state: Optional[str] = None

    # Content length limit (GitHub's actual limit)
    MAX_CONTENT_LENGTH = 65536

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValidationError: If any field validation fails
        """
        try:
            # Validate comment_id
            if not isinstance(self.comment_id, str):
                raise create_validation_error(
                    field_name="comment_id",
                    invalid_value=type(self.comment_id).__name__,
                    expected_format="non-empty string",
                    message="comment_id must be a string",
                )
            if not self.comment_id.strip():
                raise create_validation_error(
                    field_name="comment_id",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="comment_id cannot be empty",
                )

            # Validate content
            if not isinstance(self.content, str):
                raise create_validation_error(
                    field_name="content",
                    invalid_value=type(self.content).__name__,
                    expected_format="non-empty string",
                    message="content must be a string",
                )
            if not self.content.strip():
                raise create_validation_error(
                    field_name="content",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="content cannot be empty",
                )
            if len(self.content) > self.MAX_CONTENT_LENGTH:
                raise create_validation_error(
                    field_name="content",
                    invalid_value=f"{len(self.content)} characters",
                    expected_format=(
                        f"string with <= {self.MAX_CONTENT_LENGTH} characters"
                    ),
                    message=(
                        f"content cannot exceed {self.MAX_CONTENT_LENGTH} characters"
                    ),
                )

            # Validate author
            if not isinstance(self.author, str):
                raise create_validation_error(
                    field_name="author",
                    invalid_value=type(self.author).__name__,
                    expected_format="non-empty string",
                    message="author must be a string",
                )
            if not self.author.strip():
                raise create_validation_error(
                    field_name="author",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="author cannot be empty",
                )

            # Validate thread_id
            if not isinstance(self.thread_id, str):
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value=type(self.thread_id).__name__,
                    expected_format="non-empty string",
                    message="thread_id must be a string",
                )
            if not self.thread_id.strip():
                raise create_validation_error(
                    field_name="thread_id",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="thread_id cannot be empty",
                )

            # Validate dates
            if not isinstance(self.created_at, datetime):
                raise create_validation_error(
                    field_name="created_at",
                    invalid_value=type(self.created_at).__name__,
                    expected_format="datetime object",
                    message="created_at must be a datetime object",
                )
            if not isinstance(self.updated_at, datetime):
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=type(self.updated_at).__name__,
                    expected_format="datetime object",
                    message="updated_at must be a datetime object",
                )
            if self.updated_at < self.created_at:
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=self.updated_at.isoformat(),
                    expected_format=f"datetime >= {self.created_at.isoformat()}",
                    message="updated_at cannot be before created_at",
                )

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except Exception as e:
            # Wrap any unexpected errors
            raise create_validation_error(
                field_name="Comment",
                invalid_value="validation failure",
                expected_format="valid Comment object",
                message=f"Unexpected error during Comment validation: {str(e)}",
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Comment to a dictionary for serialization.

        Returns:
            Dictionary representation of the Comment

        Raises:
            ValidationError: If serialization fails
        """
        try:
            return {
                "comment_id": self.comment_id,
                "content": self.content,
                "author": self.author,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "parent_id": self.parent_id,
                "thread_id": self.thread_id,
                "review_id": self.review_id,
                "review_state": self.review_state,
            }
        except Exception as e:
            raise create_validation_error(
                field_name="Comment",
                invalid_value="serialization failure",
                expected_format="serializable Comment object",
                message=f"Failed to serialize Comment to dictionary: {str(e)}",
            ) from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        """Create a Comment from a dictionary.

        Args:
            data: Dictionary containing Comment fields

        Returns:
            Comment instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        try:
            # Validate input data
            if not isinstance(data, dict):
                raise create_validation_error(
                    field_name="data",
                    invalid_value=type(data).__name__,
                    expected_format="dictionary",
                    message="Input data must be a dictionary",
                )

            # Check required fields
            required_fields = {
                "comment_id",
                "content",
                "author",
                "created_at",
                "updated_at",
                "thread_id",
            }
            missing_fields = required_fields - set(data.keys())
            if missing_fields:
                raise create_validation_error(
                    field_name="required_fields",
                    invalid_value=f"missing: {', '.join(sorted(missing_fields))}",
                    expected_format=(
                        f"dictionary with fields: {', '.join(sorted(required_fields))}"
                    ),
                    message=(
                        f"Missing required field: {', '.join(sorted(missing_fields))}"
                    ),
                )

            # Parse dates with enhanced error handling
            try:
                created_at = _parse_datetime(data["created_at"])
            except (ValueError, ValidationError) as err:
                raise create_validation_error(
                    field_name="created_at",
                    invalid_value=data.get("created_at", "missing"),
                    expected_format="ISO datetime string",
                    message=f"Invalid date format for created_at: {str(err)}",
                ) from err

            try:
                updated_at = _parse_datetime(data["updated_at"])
            except (ValueError, ValidationError) as err:
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=data.get("updated_at", "missing"),
                    expected_format="ISO datetime string",
                    message=f"Invalid date format for updated_at: {str(err)}",
                ) from err

            # Create instance with proper error handling
            try:
                return cls(
                    comment_id=data["comment_id"],
                    content=data["content"],
                    author=data["author"],
                    created_at=created_at,
                    updated_at=updated_at,
                    parent_id=data.get("parent_id"),
                    thread_id=data["thread_id"],
                    review_id=data.get("review_id"),
                    review_state=data.get("review_state"),
                )
            except ValidationError:
                # Re-raise ValidationErrors from __post_init__
                raise
            except Exception as e:
                raise create_validation_error(
                    field_name="Comment",
                    invalid_value="construction failure",
                    expected_format="valid Comment object",
                    message=f"Failed to create Comment from dictionary: {str(e)}",
                ) from e

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except Exception as e:
            raise create_validation_error(
                field_name="data",
                invalid_value=str(type(data)),
                expected_format="valid dictionary for Comment creation",
                message=f"Unexpected error creating Comment from dictionary: {str(e)}",
            ) from e

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"Comment(id={self.comment_id}, author={self.author}, "
            f"thread={self.thread_id}, parent={self.parent_id})"
        )


@dataclass
class PullRequest:
    """Represents a GitHub pull request with basic metadata.

    Attributes:
        number: Pull request number
        title: Pull request title
        author: Username of the PR author
        head_ref: Name of the head branch
        base_ref: Name of the base branch
        is_draft: Whether the PR is a draft
        created_at: When the PR was created
        updated_at: When the PR was last updated
        url: GitHub URL for the PR
        review_thread_count: Number of review threads
        node_id: GitHub node ID for the PR (optional)
    """

    number: int
    title: str
    author: str
    head_ref: str
    base_ref: str
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    url: str
    review_thread_count: int
    node_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValidationError: If any field validation fails
        """
        try:
            # Validate number
            if not isinstance(self.number, int):
                raise create_validation_error(
                    field_name="number",
                    invalid_value=type(self.number).__name__,
                    expected_format="positive integer",
                    message="number must be an integer",
                )
            if self.number <= 0:
                raise create_validation_error(
                    field_name="number",
                    invalid_value=str(self.number),
                    expected_format="positive integer",
                    message="number must be positive",
                )

            # Validate title
            if not isinstance(self.title, str):
                raise create_validation_error(
                    field_name="title",
                    invalid_value=type(self.title).__name__,
                    expected_format="non-empty string",
                    message="title must be a string",
                )
            if not self.title.strip():
                raise create_validation_error(
                    field_name="title",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="title cannot be empty",
                )

            # Validate author
            if not isinstance(self.author, str):
                raise create_validation_error(
                    field_name="author",
                    invalid_value=type(self.author).__name__,
                    expected_format="non-empty string",
                    message="author must be a string",
                )
            if not self.author.strip():
                raise create_validation_error(
                    field_name="author",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="author cannot be empty",
                )

            # Validate head_ref
            if not isinstance(self.head_ref, str):
                raise create_validation_error(
                    field_name="head_ref",
                    invalid_value=type(self.head_ref).__name__,
                    expected_format="non-empty string",
                    message="head_ref must be a string",
                )
            if not self.head_ref.strip():
                raise create_validation_error(
                    field_name="head_ref",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="head_ref cannot be empty",
                )

            # Validate base_ref
            if not isinstance(self.base_ref, str):
                raise create_validation_error(
                    field_name="base_ref",
                    invalid_value=type(self.base_ref).__name__,
                    expected_format="non-empty string",
                    message="base_ref must be a string",
                )
            if not self.base_ref.strip():
                raise create_validation_error(
                    field_name="base_ref",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="base_ref cannot be empty",
                )

            # Validate is_draft
            if not isinstance(self.is_draft, bool):
                raise create_validation_error(
                    field_name="is_draft",
                    invalid_value=type(self.is_draft).__name__,
                    expected_format="boolean",
                    message="is_draft must be a boolean",
                )

            # Validate url
            if not isinstance(self.url, str):
                raise create_validation_error(
                    field_name="url",
                    invalid_value=type(self.url).__name__,
                    expected_format="non-empty string",
                    message="url must be a string",
                )
            if not self.url.strip():
                raise create_validation_error(
                    field_name="url",
                    invalid_value="empty string",
                    expected_format="non-empty string",
                    message="url cannot be empty",
                )

            # Validate review_thread_count
            if not isinstance(self.review_thread_count, int):
                raise create_validation_error(
                    field_name="review_thread_count",
                    invalid_value=type(self.review_thread_count).__name__,
                    expected_format="non-negative integer",
                    message="review_thread_count must be an integer",
                )
            if self.review_thread_count < 0:
                raise create_validation_error(
                    field_name="review_thread_count",
                    invalid_value=str(self.review_thread_count),
                    expected_format="non-negative integer",
                    message="review_thread_count cannot be negative",
                )

            # Validate dates
            if not isinstance(self.created_at, datetime):
                raise create_validation_error(
                    field_name="created_at",
                    invalid_value=type(self.created_at).__name__,
                    expected_format="datetime object",
                    message="created_at must be a datetime object",
                )
            if not isinstance(self.updated_at, datetime):
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=type(self.updated_at).__name__,
                    expected_format="datetime object",
                    message="updated_at must be a datetime object",
                )
            if self.updated_at < self.created_at:
                raise create_validation_error(
                    field_name="updated_at",
                    invalid_value=self.updated_at.isoformat(),
                    expected_format=f"datetime >= {self.created_at.isoformat()}",
                    message="updated_at cannot be before created_at",
                )

        except ValidationError:
            # Re-raise ValidationErrors as-is
            raise
        except Exception as e:
            # Wrap any unexpected errors
            raise create_validation_error(
                field_name="PullRequest",
                invalid_value="validation failure",
                expected_format="valid PullRequest object",
                message=f"Unexpected error during PullRequest validation: {str(e)}",
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert the PullRequest to a dictionary for serialization.

        Returns:
            Dictionary representation of the PullRequest
        """
        return {
            "number": self.number,
            "title": self.title,
            "author": self.author,
            "head_ref": self.head_ref,
            "base_ref": self.base_ref,
            "is_draft": self.is_draft,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "url": self.url,
            "review_thread_count": self.review_thread_count,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PullRequest":
        """Create a PullRequest from a dictionary.

        Args:
            data: Dictionary containing PullRequest fields

        Returns:
            PullRequest instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Check required fields
        required_fields = {
            "number",
            "title",
            "author",
            "head_ref",
            "base_ref",
            "is_draft",
            "created_at",
            "updated_at",
            "url",
            "review_thread_count",
        }
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise create_validation_error(
                field_name="from_dict",
                invalid_value=f"missing: {', '.join(missing_fields)}",
                expected_format="dictionary with all required fields",
                message=f"Missing required field: {', '.join(missing_fields)}",
            )

        # Parse dates
        try:
            created_at = _parse_datetime(data["created_at"])
        except (ValueError, ValidationError) as err:
            raise create_validation_error(
                field_name="created_at",
                invalid_value=data["created_at"],
                expected_format="ISO datetime string",
                message=f"Invalid date format for created_at: {data['created_at']}",
            ) from err

        try:
            updated_at = _parse_datetime(data["updated_at"])
        except (ValueError, ValidationError) as err:
            raise create_validation_error(
                field_name="updated_at",
                invalid_value=data["updated_at"],
                expected_format="ISO datetime string",
                message=f"Invalid date format for updated_at: {data['updated_at']}",
            ) from err

        # Create instance
        return cls(
            number=data["number"],
            title=data["title"],
            author=data["author"],
            head_ref=data["head_ref"],
            base_ref=data["base_ref"],
            is_draft=data["is_draft"],
            created_at=created_at,
            updated_at=updated_at,
            url=data["url"],
            review_thread_count=data["review_thread_count"],
            node_id=data.get("node_id"),
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        draft_text = " (draft)" if self.is_draft else ""
        return (
            f"PR #{self.number}: {self.title} by {self.author} "
            f"({self.head_ref} -> {self.base_ref}){draft_text}"
        )
