"""Data models for GitHub review threads and comments."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Union


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
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "author": self.author,
            "comments": self.comments,
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
            "thread_id", "title", "created_at", "updated_at", "status", "author"
        }
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValueError(f"Missing required field: {', '.join(missing_fields)}")
        
        # Parse dates
        try:
            created_at = cls._parse_datetime(data["created_at"])
        except ValueError:
            raise ValueError(f"Invalid date format for created_at: {data['created_at']}")
        
        try:
            updated_at = cls._parse_datetime(data["updated_at"])
        except ValueError:
            raise ValueError(f"Invalid date format for updated_at: {data['updated_at']}")
        
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
        # Remove timezone info if present
        if date_str.endswith("Z"):
            date_str = date_str[:-1]
        elif "+" in date_str and date_str.count(":") >= 3:
            # Handle timezone like +00:00
            date_str = date_str.split("+")[0]
        elif "-" in date_str and date_str.count(":") >= 3:
            # Handle timezone like -05:00 (but not dates like 2024-01-01)
            parts = date_str.split("-")
            if len(parts) > 3:  # Has timezone
                date_str = "-".join(parts[:-1])
        
        # Try parsing with different formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%f",  # With microseconds
            "%Y-%m-%dT%H:%M:%S",      # Without microseconds
        ]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse datetime: {date_str}")
    
    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"ReviewThread(id={self.thread_id}, title='{self.title}', "
            f"status={self.status}, author={self.author})"
        )