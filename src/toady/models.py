"""Data models for GitHub review threads and comments."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .utils import parse_datetime


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
        comments: List of comment IDs or comment objects in this thread
    """

    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    status: str
    author: str
    comments: List[Union[str, Any]] = field(default_factory=list)

    # Valid status values
    VALID_STATUSES = {"RESOLVED", "UNRESOLVED", "PENDING", "OUTDATED", "DISMISSED"}

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate thread_id
        if not self.thread_id or not self.thread_id.strip():
            raise ValueError("thread_id cannot be empty")

        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")

        # Validate status
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"status must be one of {', '.join(sorted(self.VALID_STATUSES))}"
            )

        # Validate author
        if not self.author or not self.author.strip():
            raise ValueError("author cannot be empty")

        # Validate dates
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")

        # Ensure comments is a copy to prevent external modifications
        self.comments = list(self.comments)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the ReviewThread to a dictionary for serialization.

        Returns:
            Dictionary representation of the ReviewThread
        """
        # Convert Comment objects to dictionaries, leave strings as-is
        serialized_comments = []
        for comment in self.comments:
            if hasattr(comment, "to_dict"):
                # Comment object - convert to dict
                serialized_comments.append(comment.to_dict())
            else:
                # String ID - keep as-is
                serialized_comments.append(comment)

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
            raise ValueError(f"Missing required field: {', '.join(missing_fields)}")

        # Parse dates
        try:
            created_at = cls._parse_datetime(data["created_at"])
        except ValueError as err:
            raise ValueError(
                f"Invalid date format for created_at: {data['created_at']}"
            ) from err

        try:
            updated_at = cls._parse_datetime(data["updated_at"])
        except ValueError as err:
            raise ValueError(
                f"Invalid date format for updated_at: {data['updated_at']}"
            ) from err

        # Create instance
        return cls(
            thread_id=data["thread_id"],
            title=data["title"],
            created_at=created_at,
            updated_at=updated_at,
            status=data["status"],
            author=data["author"],
            comments=data.get("comments", []),
        )

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime:
        """Parse datetime string in various ISO formats.

        Args:
            date_str: Date string in ISO format

        Returns:
            datetime object

        Raises:
            ValueError: If date string cannot be parsed
        """
        return parse_datetime(date_str)

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
        """Validate fields after initialization."""
        # Validate comment_id
        if not self.comment_id or not self.comment_id.strip():
            raise ValueError("comment_id cannot be empty")

        # Validate content
        if not self.content or not self.content.strip():
            raise ValueError("content cannot be empty")

        if len(self.content) > self.MAX_CONTENT_LENGTH:
            raise ValueError(
                f"content cannot exceed {self.MAX_CONTENT_LENGTH} characters"
            )

        # Validate author
        if not self.author or not self.author.strip():
            raise ValueError("author cannot be empty")

        # Validate thread_id
        if not self.thread_id or not self.thread_id.strip():
            raise ValueError("thread_id cannot be empty")

        # Validate dates
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Comment to a dictionary for serialization.

        Returns:
            Dictionary representation of the Comment
        """
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        """Create a Comment from a dictionary.

        Args:
            data: Dictionary containing Comment fields

        Returns:
            Comment instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
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
            raise ValueError(f"Missing required field: {', '.join(missing_fields)}")

        # Parse dates
        try:
            created_at = cls._parse_datetime(data["created_at"])
        except ValueError as err:
            raise ValueError(
                f"Invalid date format for created_at: {data['created_at']}"
            ) from err

        try:
            updated_at = cls._parse_datetime(data["updated_at"])
        except ValueError as err:
            raise ValueError(
                f"Invalid date format for updated_at: {data['updated_at']}"
            ) from err

        # Create instance
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

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime:
        """Parse datetime string in various ISO formats.

        Args:
            date_str: Date string in ISO format

        Returns:
            datetime object

        Raises:
            ValueError: If date string cannot be parsed
        """
        return parse_datetime(date_str)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"Comment(id={self.comment_id}, author={self.author}, "
            f"thread={self.thread_id}, parent={self.parent_id})"
        )
