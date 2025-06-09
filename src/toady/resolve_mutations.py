"""GraphQL mutations for resolving and unresolving review threads."""

from typing import Any, Dict, Tuple

from .node_id_validation import validate_thread_id


class ResolveThreadMutationBuilder:
    """Builder for GraphQL mutations to resolve and unresolve review threads."""

    def __init__(self) -> None:
        """Initialize the mutation builder."""
        pass

    def build_resolve_mutation(self) -> str:
        """Build GraphQL mutation for resolving a review thread.

        Returns:
            GraphQL mutation string for resolving a thread.
        """
        return """
        mutation ResolveReviewThread($threadId: ID!) {
            resolveReviewThread(input: {threadId: $threadId}) {
                thread {
                    id
                    isResolved
                    url
                }
            }
        }
        """.strip()

    def build_unresolve_mutation(self) -> str:
        """Build GraphQL mutation for unresolving a review thread.

        Returns:
            GraphQL mutation string for unresolving a thread.
        """
        return """
        mutation UnresolveReviewThread($threadId: ID!) {
            unresolveReviewThread(input: {threadId: $threadId}) {
                thread {
                    id
                    isResolved
                    url
                }
            }
        }
        """.strip()

    def build_variables(self, thread_id: str) -> Dict[str, Any]:
        """Build variables dictionary for the mutation.

        Args:
            thread_id: The GitHub thread ID (numeric or node ID).

        Returns:
            Variables dictionary for the GraphQL mutation.

        Raises:
            ValueError: If thread_id is empty or invalid.
        """
        if not thread_id or not thread_id.strip():
            raise ValueError("Thread ID cannot be empty")

        thread_id = thread_id.strip()

        # Use centralized validation
        validate_thread_id(thread_id)

        return {"threadId": thread_id}


def create_resolve_mutation(thread_id: str) -> Tuple[str, Dict[str, Any]]:
    """Create a complete resolve thread mutation with variables.

    Args:
        thread_id: The GitHub thread ID to resolve.

    Returns:
        Tuple of (mutation_string, variables_dict).

    Raises:
        ValueError: If thread_id is invalid.
    """
    builder = ResolveThreadMutationBuilder()
    mutation = builder.build_resolve_mutation()
    variables = builder.build_variables(thread_id)
    return mutation, variables


def create_unresolve_mutation(thread_id: str) -> Tuple[str, Dict[str, Any]]:
    """Create a complete unresolve thread mutation with variables.

    Args:
        thread_id: The GitHub thread ID to unresolve.

    Returns:
        Tuple of (mutation_string, variables_dict).

    Raises:
        ValueError: If thread_id is invalid.
    """
    builder = ResolveThreadMutationBuilder()
    mutation = builder.build_unresolve_mutation()
    variables = builder.build_variables(thread_id)
    return mutation, variables
