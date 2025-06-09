"""GraphQL mutations for replying to pull request review comments."""

from typing import Any, Dict, Optional, Tuple

from .node_id_validation import validate_comment_id


class ReplyMutationBuilder:
    """Builder for GraphQL mutations to reply to pull request review comments."""

    def __init__(self) -> None:
        """Initialize the mutation builder."""
        pass

    def build_reply_mutation(self) -> str:
        """Build GraphQL mutation for replying to a review comment thread.

        This uses the addPullRequestReviewThreadReply mutation which is the
        modern GraphQL approach for posting replies to review comment threads.

        Returns:
            GraphQL mutation string for posting a reply.
        """
        return """
        mutation AddPullRequestReviewThreadReply($threadId: ID!, $body: String!) {
            addPullRequestReviewThreadReply(input: {
                pullRequestReviewThreadId: $threadId,
                body: $body
            }) {
                comment {
                    id
                    body
                    createdAt
                    updatedAt
                    author {
                        login
                    }
                    url
                    pullRequestReview {
                        id
                    }
                    replyTo {
                        id
                    }
                }
            }
        }
        """.strip()

    def build_reply_to_comment_mutation(self) -> str:
        """Build GraphQL mutation for replying to a specific review comment.

        This uses the deprecated addPullRequestReviewComment mutation with inReplyTo
        for backward compatibility with numeric comment IDs.

        Returns:
            GraphQL mutation string for posting a reply to a specific comment.
        """
        return """
        mutation AddPullRequestReviewComment($reviewId: ID!, $commentId: ID!, $body: String!) {
            addPullRequestReviewComment(input: {
                pullRequestReviewId: $reviewId,
                inReplyTo: $commentId,
                body: $body
            }) {
                comment {
                    id
                    body
                    createdAt
                    updatedAt
                    author {
                        login
                    }
                    url
                    pullRequestReview {
                        id
                    }
                    replyTo {
                        id
                    }
                }
            }
        }
        """.strip()

    def build_variables_for_thread_reply(
        self, thread_id: str, reply_body: str
    ) -> Dict[str, Any]:
        """Build variables dictionary for the thread reply mutation.

        Args:
            thread_id: The GitHub thread ID (must be a node ID starting with PRT_/PRRT_/RT_).
            reply_body: The reply message body.

        Returns:
            Variables dictionary for the GraphQL mutation.

        Raises:
            ValueError: If thread_id or reply_body is empty or invalid.
        """
        if not thread_id or not thread_id.strip():
            raise ValueError("Thread ID cannot be empty")
        if not reply_body or not reply_body.strip():
            raise ValueError("Reply body cannot be empty")

        thread_id = thread_id.strip()
        reply_body = reply_body.strip()

        # Validate thread ID format - must be a node ID for GraphQL
        # We'll validate it using the comment validator since threads and comments
        # share similar validation patterns
        from .node_id_validation import create_thread_validator

        validator = create_thread_validator()
        validator.validate_id(thread_id, "Thread ID")

        return {"threadId": thread_id, "body": reply_body}

    def build_variables_for_comment_reply(
        self, review_id: str, comment_id: str, reply_body: str
    ) -> Dict[str, Any]:
        """Build variables dictionary for the comment reply mutation.

        Args:
            review_id: The GitHub review ID (node ID starting with PRR_).
            comment_id: The GitHub comment ID being replied to.
            reply_body: The reply message body.

        Returns:
            Variables dictionary for the GraphQL mutation.

        Raises:
            ValueError: If any parameter is empty or invalid.
        """
        if not review_id or not review_id.strip():
            raise ValueError("Review ID cannot be empty")
        if not comment_id or not comment_id.strip():
            raise ValueError("Comment ID cannot be empty")
        if not reply_body or not reply_body.strip():
            raise ValueError("Reply body cannot be empty")

        review_id = review_id.strip()
        comment_id = comment_id.strip()
        reply_body = reply_body.strip()

        # Validate comment ID using centralized validation
        validate_comment_id(comment_id)

        return {"reviewId": review_id, "commentId": comment_id, "body": reply_body}


def create_thread_reply_mutation(
    thread_id: str, reply_body: str
) -> Tuple[str, Dict[str, Any]]:
    """Create a complete thread reply mutation with variables.

    Args:
        thread_id: The GitHub thread ID to reply to (node ID).
        reply_body: The reply message body.

    Returns:
        Tuple of (mutation_string, variables_dict).

    Raises:
        ValueError: If thread_id or reply_body is invalid.
    """
    builder = ReplyMutationBuilder()
    mutation = builder.build_reply_mutation()
    variables = builder.build_variables_for_thread_reply(thread_id, reply_body)
    return mutation, variables


def create_comment_reply_mutation(
    review_id: str, comment_id: str, reply_body: str
) -> Tuple[str, Dict[str, Any]]:
    """Create a complete comment reply mutation with variables.

    Args:
        review_id: The GitHub review ID.
        comment_id: The GitHub comment ID to reply to.
        reply_body: The reply message body.

    Returns:
        Tuple of (mutation_string, variables_dict).

    Raises:
        ValueError: If any parameter is invalid.
    """
    builder = ReplyMutationBuilder()
    mutation = builder.build_reply_to_comment_mutation()
    variables = builder.build_variables_for_comment_reply(
        review_id, comment_id, reply_body
    )
    return mutation, variables


def determine_reply_strategy(comment_id: str) -> str:
    """Determine the best reply strategy based on the comment ID format.

    Args:
        comment_id: The comment ID to analyze.

    Returns:
        Either "thread_reply" for node IDs or "comment_reply" for numeric IDs.
    """
    # If it's a numeric ID, we need to use the legacy comment reply approach
    if comment_id.isdigit():
        return "comment_reply"

    # For node IDs, we need to determine if it's a thread ID or comment ID
    # Thread IDs start with PRT_, PRRT_, RT_
    # Comment IDs start with IC_, PRRC_, RP_
    if comment_id.startswith(("PRT_", "PRRT_", "RT_")):
        return "thread_reply"
    elif comment_id.startswith(("IC_", "PRRC_", "RP_")):
        return "comment_reply"
    else:
        # Default to comment reply for unknown formats
        return "comment_reply"