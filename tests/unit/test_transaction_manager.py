"""Unit tests for TransactionManager."""

from uuid import UUID

import pytest

from toady.transaction_manager import (
    OperationType,
    RollbackStrategy,
    TransactionError,
    TransactionManager,
    TransactionStatus,
)


class MockRollbackHandler:
    """Mock rollback handler for testing."""

    def __init__(self, can_rollback: bool = True, rollback_success: bool = True):
        self.can_rollback_value = can_rollback
        self.rollback_success_value = rollback_success
        self.can_rollback_calls = []
        self.rollback_calls = []

    def can_rollback(self, operation):
        self.can_rollback_calls.append(operation)
        return self.can_rollback_value

    def rollback(self, operation):
        self.rollback_calls.append(operation)
        return self.rollback_success_value


class TestTransactionManager:
    """Test cases for TransactionManager."""

    @pytest.fixture
    def transaction_manager(self):
        """Create a transaction manager for testing."""
        return TransactionManager(
            rollback_strategy=RollbackStrategy.IMMEDIATE,
            enable_checkpoints=True,
            max_operation_history=100,
        )

    @pytest.fixture
    def mock_rollback_handler(self):
        """Create a mock rollback handler."""
        return MockRollbackHandler()

    def test_init_default(self):
        """Test transaction manager initialization with defaults."""
        tm = TransactionManager()
        assert tm.rollback_strategy == RollbackStrategy.IMMEDIATE
        assert tm.enable_checkpoints is True
        assert tm.max_operation_history == 1000
        assert tm._current_transaction is None
        assert len(tm._rollback_handlers) == 0

    def test_init_custom(self):
        """Test transaction manager initialization with custom values."""
        tm = TransactionManager(
            rollback_strategy=RollbackStrategy.BEST_EFFORT,
            enable_checkpoints=False,
            max_operation_history=500,
        )
        assert tm.rollback_strategy == RollbackStrategy.BEST_EFFORT
        assert tm.enable_checkpoints is False
        assert tm.max_operation_history == 500

    def test_register_rollback_handler(
        self, transaction_manager, mock_rollback_handler
    ):
        """Test registering rollback handlers."""
        transaction_manager.register_rollback_handler(
            OperationType.REPLY_POST, mock_rollback_handler
        )

        assert OperationType.REPLY_POST in transaction_manager._rollback_handlers
        assert (
            transaction_manager._rollback_handlers[OperationType.REPLY_POST]
            is mock_rollback_handler
        )

    def test_begin_transaction_success(self, transaction_manager):
        """Test successful transaction beginning."""
        metadata = {"test": "data"}
        transaction_id = transaction_manager.begin_transaction(
            rollback_strategy=RollbackStrategy.CHECKPOINT_BASED,
            metadata=metadata,
        )

        # Verify transaction ID is a valid UUID
        UUID(transaction_id)

        # Verify transaction state
        current_tx = transaction_manager.get_current_transaction()
        assert current_tx is not None
        assert current_tx.transaction_id == transaction_id
        assert current_tx.status == TransactionStatus.ACTIVE
        assert current_tx.rollback_strategy == RollbackStrategy.CHECKPOINT_BASED
        assert current_tx.metadata == metadata
        assert current_tx.start_time is not None
        assert current_tx.end_time is None

    def test_begin_transaction_already_active(self, transaction_manager):
        """Test beginning a transaction when one is already active."""
        transaction_manager.begin_transaction()

        with pytest.raises(
            TransactionError, match="another transaction is already active"
        ):
            transaction_manager.begin_transaction()

    def test_record_operation_success(self, transaction_manager):
        """Test recording an operation successfully."""
        transaction_manager.begin_transaction()

        operation_id = transaction_manager.record_operation(
            operation_type=OperationType.REPLY_POST,
            thread_id="thread_123",
            data={"message": "test"},
            rollback_data={"reply_id": "reply_456"},
        )

        # Verify operation ID is a valid UUID
        UUID(operation_id)

        # Verify operation is recorded
        current_tx = transaction_manager.get_current_transaction()
        assert len(current_tx.operations) == 1

        operation = current_tx.operations[0]
        assert operation.operation_id == operation_id
        assert operation.operation_type == OperationType.REPLY_POST
        assert operation.thread_id == "thread_123"
        assert operation.data == {"message": "test"}
        assert operation.rollback_data == {"reply_id": "reply_456"}

    def test_record_operation_no_active_transaction(self, transaction_manager):
        """Test recording an operation with no active transaction."""
        with pytest.raises(TransactionError, match="No active transaction"):
            transaction_manager.record_operation(
                operation_type=OperationType.REPLY_POST,
                thread_id="thread_123",
                data={"message": "test"},
            )

    def test_create_checkpoint_success(self, transaction_manager):
        """Test creating a checkpoint successfully."""
        transaction_manager.begin_transaction()

        checkpoint_id = transaction_manager.create_checkpoint(
            description="Test checkpoint",
            data={"progress": "50%"},
        )

        # Verify checkpoint ID is a valid UUID
        UUID(checkpoint_id)

        # Verify checkpoint is created
        current_tx = transaction_manager.get_current_transaction()
        assert len(current_tx.checkpoints) == 1

        checkpoint = current_tx.checkpoints[0]
        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.description == "Test checkpoint"
        assert checkpoint.data == {"progress": "50%"}
        assert checkpoint.operation_count == 0

    def test_create_checkpoint_disabled(self, transaction_manager):
        """Test creating a checkpoint when checkpoints are disabled."""
        tm = TransactionManager(enable_checkpoints=False)
        tm.begin_transaction()

        with pytest.raises(TransactionError, match="Checkpoints are disabled"):
            tm.create_checkpoint("Test checkpoint")

    def test_create_checkpoint_no_active_transaction(self, transaction_manager):
        """Test creating a checkpoint with no active transaction."""
        with pytest.raises(TransactionError, match="No active transaction"):
            transaction_manager.create_checkpoint("Test checkpoint")

    def test_commit_transaction_success(self, transaction_manager):
        """Test committing a transaction successfully."""
        transaction_id = transaction_manager.begin_transaction()

        # Add some operations
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test1"}
        )
        transaction_manager.record_operation(
            OperationType.THREAD_RESOLVE, "thread_1", {"resolved": True}
        )

        success = transaction_manager.commit_transaction()
        assert success is True

        # Verify transaction state
        assert transaction_manager.get_current_transaction() is None

        # Verify transaction is in history
        history = transaction_manager.get_transaction_history()
        assert len(history) == 1

        committed_tx = history[0]
        assert committed_tx.transaction_id == transaction_id
        assert committed_tx.status == TransactionStatus.COMMITTED
        assert committed_tx.end_time is not None
        assert len(committed_tx.operations) == 2

    def test_commit_transaction_no_active_transaction(self, transaction_manager):
        """Test committing with no active transaction."""
        with pytest.raises(TransactionError, match="No active transaction"):
            transaction_manager.commit_transaction()

    def test_rollback_transaction_success(
        self, transaction_manager, mock_rollback_handler
    ):
        """Test rolling back a transaction successfully."""
        # Set up rollback handler
        transaction_manager.register_rollback_handler(
            OperationType.REPLY_POST, mock_rollback_handler
        )

        transaction_manager.begin_transaction()

        # Add operation
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test"}
        )

        success = transaction_manager.rollback_transaction()
        assert success is True

        # Verify rollback was called
        assert len(mock_rollback_handler.rollback_calls) == 1

        # Verify transaction state
        current_tx = transaction_manager.get_current_transaction()
        assert current_tx.status == TransactionStatus.ROLLED_BACK
        assert current_tx.end_time is not None

    def test_rollback_transaction_handler_failure(self, transaction_manager):
        """Test rollback when handler fails."""
        # Set up failing rollback handler
        failing_handler = MockRollbackHandler(rollback_success=False)
        transaction_manager.register_rollback_handler(
            OperationType.REPLY_POST, failing_handler
        )

        transaction_manager.begin_transaction()
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test"}
        )

        success = transaction_manager.rollback_transaction()
        assert success is False

        # Verify transaction state
        current_tx = transaction_manager.get_current_transaction()
        assert current_tx.status == TransactionStatus.FAILED

    def test_abort_transaction_with_rollback(
        self, transaction_manager, mock_rollback_handler
    ):
        """Test aborting a transaction with rollback."""
        transaction_manager.register_rollback_handler(
            OperationType.REPLY_POST, mock_rollback_handler
        )

        transaction_manager.begin_transaction()
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test"}
        )

        success = transaction_manager.abort_transaction("Test abort")
        assert success is True

        # Verify transaction is in history with failed status
        history = transaction_manager.get_transaction_history()
        assert len(history) == 1

        aborted_tx = history[0]
        assert aborted_tx.status == TransactionStatus.FAILED
        assert aborted_tx.error_message == "Test abort"

    def test_rollback_to_checkpoint_success(
        self, transaction_manager, mock_rollback_handler
    ):
        """Test rolling back to a specific checkpoint."""
        transaction_manager.register_rollback_handler(
            OperationType.REPLY_POST, mock_rollback_handler
        )
        transaction_manager.register_rollback_handler(
            OperationType.THREAD_RESOLVE, mock_rollback_handler
        )

        transaction_manager.begin_transaction()

        # Add operation and checkpoint
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test1"}
        )
        checkpoint_id = transaction_manager.create_checkpoint("Checkpoint 1")

        # Add more operations
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_2", {"msg": "test2"}
        )
        transaction_manager.record_operation(
            OperationType.THREAD_RESOLVE, "thread_2", {"resolved": True}
        )

        # Rollback to checkpoint
        success = transaction_manager.rollback_to_checkpoint(checkpoint_id)
        assert success is True

        # Verify operations after checkpoint were rolled back
        current_tx = transaction_manager.get_current_transaction()
        assert (
            len(current_tx.operations) == 1
        )  # Only operation before checkpoint remains
        assert len(current_tx.checkpoints) == 1

    def test_rollback_to_checkpoint_not_found(self, transaction_manager):
        """Test rolling back to a non-existent checkpoint."""
        transaction_manager.begin_transaction()

        with pytest.raises(TransactionError, match="Checkpoint .* not found"):
            transaction_manager.rollback_to_checkpoint("nonexistent_checkpoint")

    def test_generate_audit_report_current_transaction(self, transaction_manager):
        """Test generating audit report for current transaction."""
        transaction_id = transaction_manager.begin_transaction(
            metadata={"test": "metadata"}
        )

        # Add operations and checkpoint
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test"}
        )
        transaction_manager.create_checkpoint("Test checkpoint")

        report = transaction_manager.generate_audit_report()

        assert report["transaction_id"] == transaction_id
        assert report["status"] == TransactionStatus.ACTIVE.value
        assert report["start_time"] is not None
        assert report["end_time"] is None
        assert report["duration_seconds"] is None
        assert report["total_operations"] == 1
        assert report["total_checkpoints"] == 1
        assert report["operations_by_type"]["reply_post"] == 1
        assert report["metadata"] == {"test": "metadata"}

    def test_generate_audit_report_historical_transaction(self, transaction_manager):
        """Test generating audit report for historical transaction."""
        transaction_id = transaction_manager.begin_transaction()
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test"}
        )
        transaction_manager.commit_transaction()

        report = transaction_manager.generate_audit_report(transaction_id)

        assert report["transaction_id"] == transaction_id
        assert report["status"] == TransactionStatus.COMMITTED.value
        assert report["duration_seconds"] is not None
        assert report["duration_seconds"] >= 0

    def test_generate_audit_report_not_found(self, transaction_manager):
        """Test generating audit report for non-existent transaction."""
        with pytest.raises(TransactionError, match="Transaction .* not found"):
            transaction_manager.generate_audit_report("nonexistent_id")

    def test_operation_history_trimming(self):
        """Test that operation history is trimmed when it exceeds max size."""
        tm = TransactionManager(max_operation_history=3)
        tm.begin_transaction()

        # Add more operations than the limit
        for i in range(5):
            tm.record_operation(
                OperationType.REPLY_POST, f"thread_{i}", {"msg": f"test{i}"}
            )

        current_tx = tm.get_current_transaction()
        assert len(current_tx.operations) == 3  # Trimmed to max size

        # Verify the last 3 operations are kept
        operation_data = [op.data["msg"] for op in current_tx.operations]
        assert operation_data == ["test2", "test3", "test4"]

    def test_transaction_history_trimming(self):
        """Test that transaction history is trimmed when it exceeds max size."""
        tm = TransactionManager(max_operation_history=2)

        # Create more transactions than the limit
        for i in range(4):
            tm.begin_transaction(metadata={"index": i})
            tm.record_operation(
                OperationType.REPLY_POST, f"thread_{i}", {"msg": f"test{i}"}
            )
            tm.commit_transaction()

        history = tm.get_transaction_history()
        assert len(history) == 2  # Trimmed to max size

        # Verify the last 2 transactions are kept
        metadata_indices = [tx.metadata["index"] for tx in history]
        assert metadata_indices == [2, 3]

    def test_best_effort_rollback_strategy(self, transaction_manager):
        """Test best effort rollback strategy continues on rollback failures."""
        # Set up failing rollback handler
        failing_handler = MockRollbackHandler(rollback_success=False)
        transaction_manager.register_rollback_handler(
            OperationType.REPLY_POST, failing_handler
        )

        transaction_manager.begin_transaction(
            rollback_strategy=RollbackStrategy.BEST_EFFORT
        )
        transaction_manager.record_operation(
            OperationType.REPLY_POST, "thread_1", {"msg": "test"}
        )

        # Abort should succeed even if rollback fails
        success = transaction_manager.abort_transaction("Test abort")
        assert success is False  # Rollback failed, but abort didn't raise exception

        # Verify transaction is in history
        history = transaction_manager.get_transaction_history()
        assert len(history) == 1
        assert history[0].status == TransactionStatus.FAILED


class TestTransactionManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_rollback_without_handler(self):
        """Test rollback when no handler is registered."""
        tm = TransactionManager()
        tm.begin_transaction()
        tm.record_operation(OperationType.REPLY_POST, "thread_1", {"msg": "test"})

        # Should handle missing handler gracefully
        success = tm.rollback_transaction()
        assert success is False

    def test_rollback_handler_exception(self):
        """Test rollback when handler raises exception."""

        class ExceptionHandler:
            def can_rollback(self, operation):
                return True

            def rollback(self, operation):
                raise Exception("Handler error")

        tm = TransactionManager()
        tm.register_rollback_handler(OperationType.REPLY_POST, ExceptionHandler())
        tm.begin_transaction()
        tm.record_operation(OperationType.REPLY_POST, "thread_1", {"msg": "test"})

        success = tm.rollback_transaction()
        assert success is False

        # Verify operation has rollback error recorded
        current_tx = tm.get_current_transaction()
        operation = current_tx.operations[0]
        assert operation.rollback_attempted is True
        assert operation.rollback_success is False
        assert operation.rollback_error == "Handler error"

    def test_can_rollback_false(self):
        """Test rollback when handler says operation cannot be rolled back."""
        handler = MockRollbackHandler(can_rollback=False)

        tm = TransactionManager()
        tm.register_rollback_handler(OperationType.REPLY_POST, handler)
        tm.begin_transaction()
        tm.record_operation(OperationType.REPLY_POST, "thread_1", {"msg": "test"})

        success = tm.rollback_transaction()
        assert success is False

        # Verify rollback was not attempted
        assert len(handler.rollback_calls) == 0

        current_tx = tm.get_current_transaction()
        operation = current_tx.operations[0]
        assert operation.rollback_attempted is True
        assert operation.rollback_success is False
        assert "cannot be rolled back" in operation.rollback_error
