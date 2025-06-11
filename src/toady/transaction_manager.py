"""Transaction management system for bulk operations with rollback capabilities."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from .exceptions import (
    ErrorCode,
    ErrorSeverity,
    ToadyError,
)


class TransactionStatus(Enum):
    """Status of a transaction."""

    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class OperationType(Enum):
    """Types of operations that can be tracked."""

    REPLY_POST = "reply_post"
    THREAD_RESOLVE = "thread_resolve"
    THREAD_UNRESOLVE = "thread_unresolve"
    CHECKPOINT = "checkpoint"


class RollbackStrategy(Enum):
    """Strategies for handling rollback operations."""

    IMMEDIATE = "immediate"  # Rollback immediately on any failure
    BEST_EFFORT = "best_effort"  # Try to rollback as much as possible
    CHECKPOINT_BASED = "checkpoint_based"  # Rollback to last checkpoint


@dataclass
class OperationRecord:
    """Record of a single operation in a transaction."""

    operation_id: str
    operation_type: OperationType
    timestamp: datetime
    thread_id: str
    data: Dict[str, Any]
    rollback_data: Optional[Dict[str, Any]] = None
    rollback_attempted: bool = False
    rollback_success: bool = False
    rollback_error: Optional[str] = None


@dataclass
class Checkpoint:
    """Represents a checkpoint in a transaction."""

    checkpoint_id: str
    timestamp: datetime
    operation_count: int
    description: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionLog:
    """Complete log of a transaction."""

    transaction_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: TransactionStatus
    operations: List[OperationRecord]
    checkpoints: List[Checkpoint]
    rollback_strategy: RollbackStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class RollbackHandler(Protocol):
    """Protocol for rollback handlers."""

    def can_rollback(self, operation: OperationRecord) -> bool:
        """Check if the operation can be rolled back."""
        ...

    def rollback(self, operation: OperationRecord) -> bool:
        """Perform the rollback operation."""
        ...


class TransactionError(ToadyError):
    """Raised when transaction operations fail."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize a TransactionError."""
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", ErrorCode.UNKNOWN_ERROR),
            severity=kwargs.pop("severity", ErrorSeverity.HIGH),
            suggestions=kwargs.pop(
                "suggestions",
                [
                    "Check transaction logs for detailed error information",
                    "Verify rollback handlers are properly configured",
                    "Consider using checkpoint-based recovery",
                    "Review operation sequence for potential conflicts",
                ],
            ),
            **kwargs,
        )


class TransactionManager:
    """Comprehensive transaction manager with rollback capabilities."""

    def __init__(
        self,
        rollback_strategy: RollbackStrategy = RollbackStrategy.IMMEDIATE,
        enable_checkpoints: bool = True,
        max_operation_history: int = 1000,
    ) -> None:
        """Initialize the transaction manager.

        Args:
            rollback_strategy: Strategy for handling rollbacks.
            enable_checkpoints: Whether to enable checkpoint functionality.
            max_operation_history: Maximum number of operations to keep in history.
        """
        self.rollback_strategy = rollback_strategy
        self.enable_checkpoints = enable_checkpoints
        self.max_operation_history = max_operation_history
        self.logger = logging.getLogger(__name__)

        # Current transaction state
        self._current_transaction: Optional[TransactionLog] = None
        self._rollback_handlers: Dict[OperationType, RollbackHandler] = {}

        # Transaction history
        self._transaction_history: List[TransactionLog] = []

    def register_rollback_handler(
        self, operation_type: OperationType, handler: RollbackHandler
    ) -> None:
        """Register a rollback handler for specific operation types.

        Args:
            operation_type: Type of operation the handler can rollback.
            handler: The rollback handler implementation.
        """
        self._rollback_handlers[operation_type] = handler
        self.logger.debug(f"Registered rollback handler for {operation_type.value}")

    def begin_transaction(
        self,
        rollback_strategy: Optional[RollbackStrategy] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Begin a new transaction.

        Args:
            rollback_strategy: Override default rollback strategy for this transaction.
            metadata: Additional metadata to store with the transaction.

        Returns:
            The transaction ID.

        Raises:
            TransactionError: If a transaction is already active.
        """
        if self._current_transaction is not None:
            raise TransactionError(
                "Cannot begin new transaction: another transaction is already active",
                context={
                    "current_transaction_id": self._current_transaction.transaction_id,
                    "current_status": self._current_transaction.status.value,
                },
            )

        transaction_id = str(uuid.uuid4())
        strategy = rollback_strategy or self.rollback_strategy

        self._current_transaction = TransactionLog(
            transaction_id=transaction_id,
            start_time=datetime.now(),
            end_time=None,
            status=TransactionStatus.ACTIVE,
            operations=[],
            checkpoints=[],
            rollback_strategy=strategy,
            metadata=metadata or {},
        )

        self.logger.info(
            f"Started transaction {transaction_id} with strategy {strategy.value}"
        )
        return transaction_id

    def record_operation(
        self,
        operation_type: OperationType,
        thread_id: str,
        data: Dict[str, Any],
        rollback_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an operation in the current transaction.

        Args:
            operation_type: Type of operation being performed.
            thread_id: ID of the thread being operated on.
            data: Data associated with the operation.
            rollback_data: Data needed to rollback the operation.

        Returns:
            The operation ID.

        Raises:
            TransactionError: If no transaction is active.
        """
        if self._current_transaction is None:
            raise TransactionError("No active transaction to record operation")

        operation_id = str(uuid.uuid4())
        operation = OperationRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            thread_id=thread_id,
            data=data.copy(),
            rollback_data=rollback_data.copy() if rollback_data else None,
        )

        self._current_transaction.operations.append(operation)

        # Trim operation history if needed
        if len(self._current_transaction.operations) > self.max_operation_history:
            self._current_transaction.operations = self._current_transaction.operations[
                -self.max_operation_history :
            ]
            self.logger.warning(
                f"Trimmed operation history to {self.max_operation_history} entries"
            )

        self.logger.debug(
            f"Recorded {operation_type.value} operation {operation_id} "
            f"for thread {thread_id}"
        )
        return operation_id

    def create_checkpoint(
        self, description: str, data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a checkpoint in the current transaction.

        Args:
            description: Description of the checkpoint.
            data: Additional data to store with the checkpoint.

        Returns:
            The checkpoint ID.

        Raises:
            TransactionError: If no transaction is active or checkpoints are disabled.
        """
        if self._current_transaction is None:
            raise TransactionError("No active transaction to create checkpoint")

        if not self.enable_checkpoints:
            raise TransactionError("Checkpoints are disabled")

        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            operation_count=len(self._current_transaction.operations),
            description=description,
            data=data.copy() if data else {},
        )

        self._current_transaction.checkpoints.append(checkpoint)
        self.logger.info(f"Created checkpoint {checkpoint_id}: {description}")
        return checkpoint_id

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Rollback the transaction to a specific checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to rollback to.

        Returns:
            True if rollback was successful, False otherwise.

        Raises:
            TransactionError: If no transaction is active or checkpoint not found.
        """
        if self._current_transaction is None:
            raise TransactionError("No active transaction to rollback")

        # Find the checkpoint
        checkpoint = None
        for cp in self._current_transaction.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                checkpoint = cp
                break

        if checkpoint is None:
            raise TransactionError(
                f"Checkpoint {checkpoint_id} not found",
                context={
                    "available_checkpoints": [
                        cp.checkpoint_id for cp in self._current_transaction.checkpoints
                    ]
                },
            )

        # Rollback operations after the checkpoint
        operations_to_rollback = self._current_transaction.operations[
            checkpoint.operation_count :
        ]
        success = self._perform_rollback(operations_to_rollback)

        if success:
            # Trim operations back to checkpoint
            self._current_transaction.operations = self._current_transaction.operations[
                : checkpoint.operation_count
            ]
            # Remove checkpoints after this one
            self._current_transaction.checkpoints = [
                cp
                for cp in self._current_transaction.checkpoints
                if cp.timestamp <= checkpoint.timestamp
            ]

        self.logger.info(
            f"Rollback to checkpoint {checkpoint_id}: "
            f"{'successful' if success else 'failed'}"
        )
        return success

    def rollback_transaction(self) -> bool:
        """Rollback the entire current transaction.

        Returns:
            True if rollback was successful, False otherwise.

        Raises:
            TransactionError: If no transaction is active.
        """
        if self._current_transaction is None:
            raise TransactionError("No active transaction to rollback")

        operations_to_rollback = list(reversed(self._current_transaction.operations))
        success = self._perform_rollback(operations_to_rollback)

        self._current_transaction.status = (
            TransactionStatus.ROLLED_BACK if success else TransactionStatus.FAILED
        )
        self._current_transaction.end_time = datetime.now()

        self.logger.info(
            f"Transaction {self._current_transaction.transaction_id} rollback: "
            f"{'successful' if success else 'failed'}"
        )
        return success

    def commit_transaction(self) -> bool:
        """Commit the current transaction.

        Returns:
            True if commit was successful, False otherwise.

        Raises:
            TransactionError: If no transaction is active.
        """
        if self._current_transaction is None:
            raise TransactionError("No active transaction to commit")

        self._current_transaction.status = TransactionStatus.COMMITTED
        self._current_transaction.end_time = datetime.now()

        # Move to history
        self._transaction_history.append(self._current_transaction)
        if len(self._transaction_history) > self.max_operation_history:
            self._transaction_history = self._transaction_history[
                -self.max_operation_history :
            ]

        transaction_id = self._current_transaction.transaction_id
        self._current_transaction = None

        self.logger.info(f"Committed transaction {transaction_id}")
        return True

    def abort_transaction(self, error_message: Optional[str] = None) -> bool:
        """Abort the current transaction with optional rollback.

        Args:
            error_message: Optional error message describing the failure.

        Returns:
            True if abort (including any rollback) was successful, False otherwise.

        Raises:
            TransactionError: If no transaction is active.
        """
        if self._current_transaction is None:
            raise TransactionError("No active transaction to abort")

        # Attempt rollback based on strategy
        rollback_success = True
        if self._current_transaction.rollback_strategy != RollbackStrategy.BEST_EFFORT:
            rollback_success = self.rollback_transaction()
        else:
            # For best effort, try rollback but don't fail if it doesn't work
            try:
                operations_to_rollback = list(
                    reversed(self._current_transaction.operations)
                )
                rollback_success = self._perform_rollback(operations_to_rollback)
            except Exception as e:
                self.logger.warning(f"Best effort rollback failed: {e}")
                rollback_success = False

        # Mark as FAILED only if we are still ACTIVE; preserve ROLLED_BACK when
        # rollback succeeded.
        if self._current_transaction.status == TransactionStatus.ACTIVE:
            self._current_transaction.status = TransactionStatus.FAILED
        self._current_transaction.error_message = error_message
        if self._current_transaction.end_time is None:
            self._current_transaction.end_time = datetime.now()

        # Move to history
        self._transaction_history.append(self._current_transaction)
        transaction_id = self._current_transaction.transaction_id
        self._current_transaction = None

        self.logger.error(
            f"Aborted transaction {transaction_id}: {error_message or 'Unknown error'}"
        )
        return rollback_success

    def get_current_transaction(self) -> Optional[TransactionLog]:
        """Get the current active transaction.

        Returns:
            The current transaction log or None if no transaction is active.
        """
        return self._current_transaction

    def get_transaction_history(self) -> List[TransactionLog]:
        """Get the transaction history.

        Returns:
            List of completed transaction logs.
        """
        return self._transaction_history.copy()

    def _perform_rollback(self, operations: List[OperationRecord]) -> bool:
        """Perform rollback of a list of operations.

        Args:
            operations: List of operations to rollback (should be in reverse order).

        Returns:
            True if all rollbacks were successful, False otherwise.
        """
        all_successful = True

        for operation in operations:
            if operation.rollback_attempted:
                continue  # Skip already attempted rollbacks

            operation.rollback_attempted = True

            # Check if we have a handler for this operation type
            handler = self._rollback_handlers.get(operation.operation_type)
            if handler is None:
                self.logger.warning(
                    f"No rollback handler for operation type "
                    f"{operation.operation_type.value}"
                )
                operation.rollback_success = False
                operation.rollback_error = "No rollback handler available"
                all_successful = False
                continue

            try:
                # Check if rollback is possible
                if not handler.can_rollback(operation):
                    self.logger.warning(
                        f"Operation {operation.operation_id} cannot be rolled back"
                    )
                    operation.rollback_success = False
                    operation.rollback_error = "Operation cannot be rolled back"
                    all_successful = False
                    continue

                # Perform the rollback
                success = handler.rollback(operation)
                operation.rollback_success = success

                if not success:
                    self.logger.error(
                        f"Failed to rollback operation {operation.operation_id}"
                    )
                    all_successful = False
                else:
                    self.logger.debug(
                        f"Successfully rolled back operation {operation.operation_id}"
                    )

            except Exception as e:
                self.logger.error(
                    f"Exception during rollback of operation "
                    f"{operation.operation_id}: {e}"
                )
                operation.rollback_success = False
                operation.rollback_error = str(e)
                all_successful = False

        return all_successful

    def generate_audit_report(
        self, transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate an audit report for a transaction.

        Args:
            transaction_id: ID of the transaction to report on. If None,
                reports on current transaction.

        Returns:
            Dictionary containing the audit report.

        Raises:
            TransactionError: If no transaction is found.
        """
        transaction = None

        if transaction_id is None:
            transaction = self._current_transaction
        else:
            # Look in history
            for tx in self._transaction_history:
                if tx.transaction_id == transaction_id:
                    transaction = tx
                    break

        if transaction is None:
            raise TransactionError(
                f"Transaction "
                f"{'(current)' if transaction_id is None else transaction_id} "
                f"not found"
            )

        duration = None
        if transaction.end_time:
            duration = (transaction.end_time - transaction.start_time).total_seconds()

        return {
            "transaction_id": transaction.transaction_id,
            "status": transaction.status.value,
            "start_time": transaction.start_time.isoformat(),
            "end_time": (
                transaction.end_time.isoformat() if transaction.end_time else None
            ),
            "duration_seconds": duration,
            "rollback_strategy": transaction.rollback_strategy.value,
            "total_operations": len(transaction.operations),
            "total_checkpoints": len(transaction.checkpoints),
            "operations_by_type": self._count_operations_by_type(
                transaction.operations
            ),
            "rollback_attempts": sum(
                1 for op in transaction.operations if op.rollback_attempted
            ),
            "successful_rollbacks": sum(
                1 for op in transaction.operations if op.rollback_success
            ),
            "failed_rollbacks": sum(
                1
                for op in transaction.operations
                if op.rollback_attempted and not op.rollback_success
            ),
            "error_message": transaction.error_message,
            "metadata": transaction.metadata,
        }

    def _count_operations_by_type(
        self, operations: List[OperationRecord]
    ) -> Dict[str, int]:
        """Count operations by type."""
        counts: Dict[str, int] = {}
        for op in operations:
            op_type = op.operation_type.value
            counts[op_type] = counts.get(op_type, 0) + 1
        return counts

    def get_rollback_handler_count(self) -> int:
        """Get the number of registered rollback handlers.

        Returns:
            The number of rollback handlers currently registered.
        """
        return len(self._rollback_handlers)
