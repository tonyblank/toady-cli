"""GitHub Node ID validation utilities.

This module provides comprehensive validation for all GitHub GraphQL node ID formats.
GitHub node IDs are base64-encoded strings with specific prefixes that identify
the entity type.
"""

import re
from enum import Enum
from typing import List, Optional, Set


class GitHubEntityType(Enum):
    """Enumeration of GitHub entity types with their node ID prefixes."""

    # Comment types
    ISSUE_COMMENT = "IC_"
    PULL_REQUEST_REVIEW_COMMENT = "PRRC_"

    # Thread types
    PULL_REQUEST_THREAD = "PRT_"
    PULL_REQUEST_REVIEW_THREAD = "PRRT_"
    REVIEW_THREAD = "RT_"  # Legacy/alternative format

    # Review types
    PULL_REQUEST_REVIEW = "PRR_"

    # Repository entities
    PULL_REQUEST = "PR_"
    REPOSITORY = "R_"

    # User and organization entities
    USER = "U_"
    ORGANIZATION = "O_"
    TEAM = "T_"

    # Discussion entities
    DISCUSSION = "MDI_"

    # Reply entities (internal/custom)
    REPLY = "RP_"


class NodeIDValidator:
    """Validator for GitHub node IDs with support for all entity types."""

    # Valid characters in the base64-encoded portion of node IDs
    VALID_NODE_ID_CHARS = re.compile(r"^[A-Za-z0-9_=-]+$")

    # Minimum and maximum lengths for node IDs (excluding prefix)
    MIN_NODE_ID_LENGTH = 5
    MAX_NODE_ID_LENGTH = 100

    # Entity type groups for different validation contexts
    COMMENT_TYPES = {
        GitHubEntityType.ISSUE_COMMENT,
        GitHubEntityType.PULL_REQUEST_REVIEW_COMMENT,
        GitHubEntityType.REPLY,
    }

    THREAD_TYPES = {
        GitHubEntityType.PULL_REQUEST_THREAD,
        GitHubEntityType.PULL_REQUEST_REVIEW_THREAD,
        GitHubEntityType.REVIEW_THREAD,
    }

    REVIEW_TYPES = {GitHubEntityType.PULL_REQUEST_REVIEW}

    def __init__(self, allowed_types: Optional[Set[GitHubEntityType]] = None):
        """Initialize validator with optional allowed entity types.

        Args:
            allowed_types: Set of allowed entity types. If None, all types are allowed.
        """
        self.allowed_types = (
            allowed_types if allowed_types is not None else set(GitHubEntityType)
        )
        self._prefix_to_type = {entity.value: entity for entity in GitHubEntityType}

    def get_allowed_prefixes(self) -> List[str]:
        """Get list of allowed node ID prefixes based on allowed types.

        Returns:
            List of allowed prefixes (e.g., ['IC_', 'PRRC_', 'PRT_']).
        """
        return [entity.value for entity in self.allowed_types]

    def identify_entity_type(self, node_id: str) -> Optional[GitHubEntityType]:
        """Identify the GitHub entity type from a node ID.

        Args:
            node_id: The node ID to analyze.

        Returns:
            The identified entity type, or None if not recognized.
        """
        for prefix, entity_type in self._prefix_to_type.items():
            if node_id.startswith(prefix):
                return entity_type
        return None

    def validate_numeric_id(self, node_id: str, context: str = "ID") -> None:
        """Validate a numeric ID.

        Args:
            node_id: The numeric ID string to validate.
            context: Context for error messages (e.g., "Comment ID", "Thread ID").

        Raises:
            ValueError: If the numeric ID is invalid.
        """
        if not node_id.isdigit():
            raise ValueError(f"{context} must be numeric")

        if len(node_id) < 1 or len(node_id) > 20:
            raise ValueError(
                f"Numeric {context.lower()} must be between 1 and 20 digits"
            )

        numeric_value = int(node_id)
        if numeric_value <= 0:
            raise ValueError(f"{context} must be a positive integer")

    def validate_node_id_format(
        self, node_id: str, context: str = "Node ID"
    ) -> GitHubEntityType:
        """Validate the format of a GitHub node ID.

        Args:
            node_id: The node ID to validate.
            context: Context for error messages.

        Returns:
            The identified entity type.

        Raises:
            ValueError: If the node ID format is invalid.
        """
        if not node_id or not isinstance(node_id, str):
            raise ValueError(f"{context} cannot be empty")

        # Identify entity type
        entity_type = self.identify_entity_type(node_id)
        if not entity_type:
            allowed_prefixes = ", ".join(self.get_allowed_prefixes())
            raise ValueError(f"{context} must start with one of: {allowed_prefixes}")

        # Check if entity type is allowed
        if entity_type not in self.allowed_types:
            allowed_prefixes = ", ".join(self.get_allowed_prefixes())
            raise ValueError(
                f"{context} type '{entity_type.value}' not allowed. "
                f"Allowed prefixes: {allowed_prefixes}"
            )

        # Validate length
        prefix_length = len(entity_type.value)
        node_id_part = node_id[prefix_length:]

        if len(node_id_part) < self.MIN_NODE_ID_LENGTH:
            raise ValueError(
                f"{context} appears too short to be valid "
                f"(minimum {self.MIN_NODE_ID_LENGTH + prefix_length} characters)"
            )

        if len(node_id_part) > self.MAX_NODE_ID_LENGTH:
            raise ValueError(
                f"{context} appears too long to be valid "
                f"(maximum {self.MAX_NODE_ID_LENGTH + prefix_length} characters)"
            )

        # Validate character set
        if not self.VALID_NODE_ID_CHARS.match(node_id_part):
            raise ValueError(
                f"{context} contains invalid characters. Should only contain "
                "letters, numbers, hyphens, underscores, and equals signs"
            )

        return entity_type

    def validate_id(
        self, node_id: str, context: str = "ID"
    ) -> Optional[GitHubEntityType]:
        """Validate either a numeric ID or a GitHub node ID.

        Args:
            node_id: The ID to validate (numeric or node ID).
            context: Context for error messages.

        Returns:
            The entity type if it's a node ID, None if it's a numeric ID.

        Raises:
            ValueError: If the ID is invalid.
        """
        if not node_id or not isinstance(node_id, str):
            raise ValueError(f"{context} cannot be empty")

        node_id = node_id.strip()
        if not node_id:
            raise ValueError(f"{context} cannot be empty")

        # Check if it's a numeric ID
        if node_id.isdigit():
            self.validate_numeric_id(node_id, context)
            return None

        # Validate as node ID
        return self.validate_node_id_format(node_id, context)

    def format_allowed_types_message(self, include_numeric: bool = True) -> str:
        """Format a user-friendly message about allowed ID types.

        Args:
            include_numeric: Whether to include numeric IDs in the message.

        Returns:
            Formatted message describing allowed ID formats.
        """
        prefixes = self.get_allowed_prefixes()

        parts = ["numeric (e.g., 123456789)"] if include_numeric else []

        if prefixes:
            prefix_examples = []
            for prefix in sorted(prefixes):
                prefix_examples.append(f"{prefix}kwDOABcD12MAAAABcDE3fg")

            parts.append(
                f"GitHub node ID starting with {', '.join(sorted(prefixes))} "
                f"(e.g., {', '.join(prefix_examples[:2])})"
            )

        return " or ".join(parts)


# Pre-configured validators for common use cases
def create_comment_validator() -> NodeIDValidator:
    """Create a validator for comment IDs (IC_, PRRC_, RP_)."""
    return NodeIDValidator(NodeIDValidator.COMMENT_TYPES)


def create_thread_validator() -> NodeIDValidator:
    """Create a validator for thread IDs (PRT_, PRRT_, RT_)."""
    return NodeIDValidator(NodeIDValidator.THREAD_TYPES)


def create_review_validator() -> NodeIDValidator:
    """Create a validator for review IDs (PRR_)."""
    return NodeIDValidator(NodeIDValidator.REVIEW_TYPES)


def create_universal_validator() -> NodeIDValidator:
    """Create a validator that accepts all GitHub node ID types."""
    return NodeIDValidator()


# Convenience functions for backward compatibility
def validate_comment_id(comment_id: str) -> Optional[GitHubEntityType]:
    """Validate a comment ID (numeric or IC_/PRRC_/RP_).

    Args:
        comment_id: The comment ID to validate.

    Returns:
        The entity type if it's a node ID, None if numeric.

    Raises:
        ValueError: If the comment ID is invalid.
    """
    validator = create_comment_validator()
    return validator.validate_id(comment_id, "Comment ID")


def validate_thread_id(thread_id: str) -> Optional[GitHubEntityType]:
    """Validate a thread ID (numeric or PRT_/PRRT_/RT_).

    Args:
        thread_id: The thread ID to validate.

    Returns:
        The entity type if it's a node ID, None if numeric.

    Raises:
        ValueError: If the thread ID is invalid.
    """
    validator = create_thread_validator()
    return validator.validate_id(thread_id, "Thread ID")


def get_comment_id_format_message() -> str:
    """Get a user-friendly message describing valid comment ID formats."""
    validator = create_comment_validator()
    return validator.format_allowed_types_message()


def get_thread_id_format_message() -> str:
    """Get a user-friendly message describing valid thread ID formats."""
    validator = create_thread_validator()
    return validator.format_allowed_types_message()
