"""Rollback handlers for GitHub operations in transactions."""

import logging
from typing import Optional

from .reply_service import ReplyService
from .resolve_service import ResolveService
from .transaction_manager import OperationRecord, OperationType


class ReplyRollbackHandler:
    """Rollback handler for reply operations.

    Note: GitHub API doesn't support deleting comments, so this handler
    tracks replies but cannot actually remove them. It provides logging
    and audit functionality for reply operations.
    """

    def __init__(self, reply_service: Optional[ReplyService] = None) -> None:
        """Initialize the reply rollback handler.

        Args:
            reply_service: Optional ReplyService instance.
        """
        self.reply_service = reply_service or ReplyService()
        self.logger = logging.getLogger(__name__)

    def can_rollback(self, _operation: OperationRecord) -> bool:
        """Check if a reply operation can be rolled back.

        Args:
            operation: The operation record to check.

        Returns:
            False, as GitHub doesn't support deleting comments.
        """
        # GitHub API doesn't support deleting comments via API
        # We can only track that the operation occurred
        return False

    def rollback(self, operation: OperationRecord) -> bool:
        """Attempt to rollback a reply operation.

        Args:
            operation: The operation record to rollback.

        Returns:
            False, as replies cannot be undone.
        """
        self.logger.warning(
            f"Cannot rollback reply operation {operation.operation_id}: "
            f"GitHub API doesn't support deleting comments. "
            f"Reply was posted to thread {operation.thread_id}"
        )

        # Log the attempted rollback for audit purposes
        if operation.rollback_data:
            reply_id = operation.rollback_data.get("reply_id")
            if reply_id:
                self.logger.info(
                    f"Reply {reply_id} posted to thread {operation.thread_id} "
                    f"cannot be automatically removed. Manual intervention required."
                )

        return False


class ResolveRollbackHandler:
    """Rollback handler for thread resolve/unresolve operations."""

    def __init__(self, resolve_service: Optional[ResolveService] = None) -> None:
        """Initialize the resolve rollback handler.

        Args:
            resolve_service: Optional ResolveService instance.
        """
        self.resolve_service = resolve_service or ResolveService()
        self.logger = logging.getLogger(__name__)

    def can_rollback(self, operation: OperationRecord) -> bool:
        """Check if a resolve operation can be rolled back.

        Args:
            operation: The operation record to check.

        Returns:
            True if the operation can be rolled back.
        """
        # We can rollback resolve operations by unresolving the thread
        return operation.operation_type in (
            OperationType.THREAD_RESOLVE,
            OperationType.THREAD_UNRESOLVE,
        )

    def rollback(self, operation: OperationRecord) -> bool:
        """Rollback a resolve operation.

        Args:
            operation: The operation record to rollback.

        Returns:
            True if rollback was successful, False otherwise.
        """
        try:
            if operation.operation_type == OperationType.THREAD_RESOLVE:
                # Rollback resolve by unresolving
                result = self.resolve_service.unresolve_thread(operation.thread_id)
                self.logger.info(
                    f"Rolled back thread resolution for {operation.thread_id}"
                )
                return bool(result.get("success", False))

            elif operation.operation_type == OperationType.THREAD_UNRESOLVE:
                # Rollback unresolve by resolving
                result = self.resolve_service.resolve_thread(operation.thread_id)
                self.logger.info(
                    f"Rolled back thread unresolution for {operation.thread_id}"
                )
                return bool(result.get("success", False))

            else:
                self.logger.error(
                    f"Unsupported operation type for rollback: "
                    f"{operation.operation_type}"
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Failed to rollback {operation.operation_type.value} "
                f"for thread {operation.thread_id}: {e}"
            )
            return False


class CompositeRollbackHandler:
    """Composite rollback handler that delegates to specific handlers."""

    def __init__(
        self,
        reply_service: Optional[ReplyService] = None,
        resolve_service: Optional[ResolveService] = None,
    ) -> None:
        """Initialize the composite rollback handler.

        Args:
            reply_service: Optional ReplyService instance.
            resolve_service: Optional ResolveService instance.
        """
        self.reply_handler = ReplyRollbackHandler(reply_service)
        self.resolve_handler = ResolveRollbackHandler(resolve_service)
        self.logger = logging.getLogger(__name__)

    def can_rollback(self, operation: OperationRecord) -> bool:
        """Check if an operation can be rolled back.

        Args:
            operation: The operation record to check.

        Returns:
            True if the operation can be rolled back.
        """
        if operation.operation_type == OperationType.REPLY_POST:
            return self.reply_handler.can_rollback(operation)
        elif operation.operation_type in (
            OperationType.THREAD_RESOLVE,
            OperationType.THREAD_UNRESOLVE,
        ):
            return self.resolve_handler.can_rollback(operation)
        else:
            self.logger.warning(f"Unknown operation type: {operation.operation_type}")
            return False

    def rollback(self, operation: OperationRecord) -> bool:
        """Rollback an operation.

        Args:
            operation: The operation record to rollback.

        Returns:
            True if rollback was successful, False otherwise.
        """
        if operation.operation_type == OperationType.REPLY_POST:
            return self.reply_handler.rollback(operation)
        elif operation.operation_type in (
            OperationType.THREAD_RESOLVE,
            OperationType.THREAD_UNRESOLVE,
        ):
            return self.resolve_handler.rollback(operation)
        else:
            self.logger.error(f"Unknown operation type: {operation.operation_type}")
            return False


def create_default_rollback_handler(
    reply_service: Optional[ReplyService] = None,
    resolve_service: Optional[ResolveService] = None,
) -> CompositeRollbackHandler:
    """Create a default rollback handler with all standard handlers.

    Args:
        reply_service: Optional ReplyService instance.
        resolve_service: Optional ResolveService instance.

    Returns:
        Configured CompositeRollbackHandler.
    """
    return CompositeRollbackHandler(
        reply_service=reply_service,
        resolve_service=resolve_service,
    )
