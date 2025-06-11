"""Unit tests for enhanced BulkReplyResolveService with transaction management."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from toady.bulk_reply_resolve_service import (
    BulkOperation,
    BulkReplyResolveService,
)
from toady.exceptions import (
    BulkOperationError,
    ValidationError,
)
from toady.fetch_service import FetchService
from toady.models import ReviewThread
from toady.reply_service import ReplyService
from toady.resolve_service import ResolveService
from toady.transaction_manager import (
    RollbackStrategy,
    TransactionManager,
    TransactionStatus,
)


class TestBulkReplyResolveServiceWithTransactions:
    """Test cases for BulkReplyResolveService with transaction management."""

    @pytest.fixture
    def mock_fetch_service(self):
        """Create a mock fetch service."""
        return Mock(spec=FetchService)

    @pytest.fixture
    def mock_reply_service(self):
        """Create a mock reply service."""
        return Mock(spec=ReplyService)

    @pytest.fixture
    def mock_resolve_service(self):
        """Create a mock resolve service."""
        return Mock(spec=ResolveService)

    @pytest.fixture
    def mock_transaction_manager(self):
        """Create a mock transaction manager."""
        mock = Mock(spec=TransactionManager)
        mock.enable_checkpoints = True
        return mock

    @pytest.fixture
    def bulk_service(
        self,
        mock_fetch_service,
        mock_reply_service,
        mock_resolve_service,
        mock_transaction_manager,
    ):
        """Create a BulkReplyResolveService with mocked dependencies."""
        return BulkReplyResolveService(
            fetch_service=mock_fetch_service,
            reply_service=mock_reply_service,
            resolve_service=mock_resolve_service,
            transaction_manager=mock_transaction_manager,
            enable_transaction_logging=True,
            checkpoint_interval=5,
        )

    @pytest.fixture
    def sample_threads(self):
        """Create sample review threads for testing."""
        return [
            ReviewThread(
                thread_id="thread_1",
                title="First thread",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user1",
                comments=[],
            ),
            ReviewThread(
                thread_id="thread_2",
                title="Second thread",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="UNRESOLVED",
                author="user2",
                comments=[],
            ),
        ]

    def test_init_with_transaction_manager(
        self,
        mock_fetch_service,
        mock_reply_service,
        mock_resolve_service,
        mock_transaction_manager,
    ):
        """Test initialization with custom transaction manager."""
        service = BulkReplyResolveService(
            fetch_service=mock_fetch_service,
            reply_service=mock_reply_service,
            resolve_service=mock_resolve_service,
            transaction_manager=mock_transaction_manager,
            enable_transaction_logging=True,
            checkpoint_interval=10,
        )

        assert service.transaction_manager is mock_transaction_manager
        assert service.enable_transaction_logging is True
        assert service.checkpoint_interval == 10

        # Verify rollback handlers were registered
        assert mock_transaction_manager.register_rollback_handler.call_count == 3

    def test_init_with_default_transaction_manager(self):
        """Test initialization creates default transaction manager."""
        service = BulkReplyResolveService()

        assert service.transaction_manager is not None
        assert isinstance(service.transaction_manager, TransactionManager)

    def test_bulk_reply_and_resolve_with_transaction_success(
        self, bulk_service, sample_threads, mock_transaction_manager
    ):
        """Test successful bulk operation with transaction management."""
        # Setup mocks
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.commit_transaction.return_value = True
        mock_transaction_manager.generate_audit_report.return_value = {
            "transaction_id": "tx_123",
            "status": "committed",
        }

        # Mock successful operations
        bulk_service.reply_service.post_reply.return_value = {"reply_id": "reply_123"}
        bulk_service.resolve_service.resolve_thread.return_value = {"success": True}

        # Execute
        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=True,
        )

        # Verify transaction was started
        mock_transaction_manager.begin_transaction.assert_called_once()
        call_args = mock_transaction_manager.begin_transaction.call_args
        assert call_args[1]["rollback_strategy"] is None
        assert call_args[1]["metadata"]["pr_number"] == 123
        assert call_args[1]["metadata"]["operation_count"] == 2

        # Verify transaction was committed
        mock_transaction_manager.commit_transaction.assert_called_once()

        # Verify operations were recorded
        assert (
            mock_transaction_manager.record_operation.call_count == 4
        )  # 2 replies + 2 resolves

        # Verify summary includes transaction info
        assert summary.transaction_id == "tx_123"
        assert summary.transaction_status == TransactionStatus.COMMITTED.value
        assert summary.audit_report is not None

    def test_bulk_reply_and_resolve_with_rollback_strategy(
        self, bulk_service, sample_threads, mock_transaction_manager
    ):
        """Test bulk operation with custom rollback strategy."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.commit_transaction.return_value = True
        bulk_service.reply_service.post_reply.return_value = {"reply_id": "reply_123"}
        bulk_service.resolve_service.resolve_thread.return_value = {"success": True}

        bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=True,
            rollback_strategy=RollbackStrategy.BEST_EFFORT,
        )

        # Verify rollback strategy was passed
        call_args = mock_transaction_manager.begin_transaction.call_args
        assert call_args[1]["rollback_strategy"] == RollbackStrategy.BEST_EFFORT

    def test_bulk_reply_and_resolve_dry_run_no_transaction(
        self, bulk_service, sample_threads, mock_transaction_manager
    ):
        """Test dry run mode does not start transaction."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            dry_run=True,
        )

        # Verify no transaction was started
        mock_transaction_manager.begin_transaction.assert_not_called()

        # Verify dry run results
        assert summary.total_operations == 2
        assert summary.successful_operations == 2
        assert summary.transaction_id is None

    def test_bulk_reply_and_resolve_atomic_failure_with_abort(
        self, bulk_service, sample_threads, mock_transaction_manager
    ):
        """Test atomic operation failure triggers transaction abort."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.abort_transaction.return_value = True
        mock_transaction_manager.generate_audit_report.return_value = {
            "transaction_id": "tx_123",
            "status": "failed",
        }

        # Mock first operation success, second failure
        bulk_service.reply_service.post_reply.side_effect = [
            {"reply_id": "reply_123"},
            Exception("Reply failed"),
        ]
        bulk_service.resolve_service.resolve_thread.return_value = {"success": True}

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=True,
        )

        # Verify transaction was aborted
        mock_transaction_manager.abort_transaction.assert_called_once()

        # Verify summary shows failure
        assert summary.atomic_failure is True
        assert summary.transaction_status == TransactionStatus.FAILED.value

    def test_bulk_reply_and_resolve_validation_error_aborts_transaction(
        self, bulk_service, mock_transaction_manager
    ):
        """Test validation error aborts transaction."""
        mock_transaction_manager.begin_transaction.return_value = "tx_123"

        with pytest.raises(ValidationError):
            bulk_service.bulk_reply_and_resolve(
                pr_number=0,  # Invalid PR number
                message="test",
                atomic=True,
            )

        # Verify transaction was not started due to early validation
        mock_transaction_manager.begin_transaction.assert_not_called()

    def test_bulk_reply_and_resolve_unexpected_error_aborts_transaction(
        self, bulk_service, sample_threads, mock_transaction_manager
    ):
        """Test unexpected error aborts transaction."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.abort_transaction.return_value = True
        mock_transaction_manager.generate_audit_report.return_value = {
            "transaction_id": "tx_123",
            "status": "failed",
        }

        # Mock unexpected error during operation execution
        bulk_service.reply_service.post_reply.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Execute and expect graceful handling rather than exception
        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=True,
        )

        # Verify transaction was aborted
        mock_transaction_manager.abort_transaction.assert_called_once()

        # Verify atomic failure is reported
        assert summary.atomic_failure is True
        assert summary.failed_operations == len(sample_threads)
        assert summary.successful_operations == 0

    def test_execute_single_operation_with_transaction_success(self, bulk_service):
        """Test single operation execution with transaction recording."""
        operation = BulkOperation(
            thread_id="thread_123",
            reply_body="test message",
            operation_id="op_456",
        )

        # Mock successful services
        bulk_service.reply_service.post_reply.return_value = {"reply_id": "reply_789"}
        bulk_service.resolve_service.resolve_thread.return_value = {"success": True}

        result = bulk_service._execute_single_operation_with_transaction(
            operation, "tx_123"
        )

        assert result.success is True
        assert result.reply_result == {"reply_id": "reply_789"}
        assert result.resolve_result == {"success": True}

        # Verify operations were recorded in transaction
        assert bulk_service.transaction_manager.record_operation.call_count == 2

    def test_execute_single_operation_with_transaction_failure(self, bulk_service):
        """Test single operation execution failure with transaction."""
        operation = BulkOperation(
            thread_id="thread_123",
            reply_body="test message",
            operation_id="op_456",
        )

        # Mock service failure
        bulk_service.reply_service.post_reply.side_effect = Exception("Reply failed")

        result = bulk_service._execute_single_operation_with_transaction(
            operation, "tx_123"
        )

        assert result.success is False
        assert result.error == "Reply failed"

        # Verify no operations were recorded due to early failure
        bulk_service.transaction_manager.record_operation.assert_not_called()

    def test_checkpoint_creation_at_intervals(
        self, bulk_service, mock_transaction_manager
    ):
        """Test checkpoint creation at specified intervals."""
        # Create service with checkpoint interval of 2
        service = BulkReplyResolveService(
            transaction_manager=mock_transaction_manager,
            checkpoint_interval=2,
        )
        service.fetch_service = Mock()
        service.reply_service = Mock()
        service.resolve_service = Mock()

        # Create 5 threads to trigger checkpoints
        threads = []
        for i in range(5):
            threads.append(
                ReviewThread(
                    thread_id=f"thread_{i}",
                    title=f"Thread {i}",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    status="UNRESOLVED",
                    author="user",
                    comments=[],
                )
            )

        service.fetch_service.fetch_review_threads_from_current_repo.return_value = (
            threads
        )
        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.commit_transaction.return_value = True
        mock_transaction_manager.enable_checkpoints = True

        # Mock successful operations
        service.reply_service.post_reply.return_value = {"reply_id": "reply_123"}
        service.resolve_service.resolve_thread.return_value = {"success": True}

        service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=False,  # Use non-atomic to continue on failures
        )

        # Verify checkpoints were created
        # Initial checkpoint + checkpoints at intervals 2 and 4
        expected_checkpoints = 3
        assert (
            mock_transaction_manager.create_checkpoint.call_count
            == expected_checkpoints
        )

    def test_non_atomic_operations_with_transaction_mixed_results(
        self, bulk_service, sample_threads, mock_transaction_manager
    ):
        """Test non-atomic operations with mixed success/failure results."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.commit_transaction.return_value = True
        mock_transaction_manager.generate_audit_report.return_value = {
            "transaction_id": "tx_123",
            "status": "committed",
        }

        # Mock first operation success, second failure
        bulk_service.reply_service.post_reply.side_effect = [
            {"reply_id": "reply_123"},
            Exception("Second reply failed"),
        ]
        bulk_service.resolve_service.resolve_thread.return_value = {"success": True}

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=False,
        )

        # Verify transaction was still committed (non-atomic)
        mock_transaction_manager.commit_transaction.assert_called_once()

        # Verify mixed results
        assert summary.total_operations == 2
        assert summary.successful_operations == 1
        assert summary.failed_operations == 1
        assert summary.transaction_status == TransactionStatus.COMMITTED.value

    def test_transaction_abort_failure_is_logged(
        self, bulk_service, sample_threads, mock_transaction_manager, caplog
    ):
        """Test that transaction abort failures are logged."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        mock_transaction_manager.begin_transaction.return_value = "tx_123"
        mock_transaction_manager.abort_transaction.side_effect = Exception(
            "Abort failed"
        )

        # Mock operation failure
        bulk_service.reply_service.post_reply.side_effect = Exception("Reply failed")

        with pytest.raises(BulkOperationError):
            bulk_service.bulk_reply_and_resolve(
                pr_number=123,
                message="test message",
                atomic=True,
            )

        # Verify abort failure was logged
        assert "Failed to abort transaction" in caplog.text

    def test_validate_bulk_operation_feasibility_with_transaction_info(
        self, bulk_service, sample_threads
    ):
        """Test feasibility validation includes transaction considerations."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        result = bulk_service.validate_bulk_operation_feasibility(123)

        assert result["feasible"] is True
        assert result["target_thread_count"] == 2
        assert result["estimated_operations"] == 4  # 2 replies + 2 resolves


class TestTransactionIntegration:
    """Integration tests for transaction management with real services."""

    def test_real_transaction_manager_integration(self):
        """Test integration with real transaction manager."""
        service = BulkReplyResolveService(
            enable_transaction_logging=True,
            checkpoint_interval=3,
        )

        # Verify transaction manager is properly configured
        assert service.transaction_manager is not None
        assert service.transaction_manager.enable_checkpoints is True
        assert (
            service.transaction_manager.rollback_strategy == RollbackStrategy.IMMEDIATE
        )

        # Verify rollback handlers are registered
        tm = service.transaction_manager
        assert len(tm._rollback_handlers) == 3

    def test_transaction_manager_rollback_strategy_configuration(self):
        """Test transaction manager configuration with different rollback strategies."""
        # Test immediate strategy
        service_immediate = BulkReplyResolveService()
        assert (
            service_immediate.transaction_manager.rollback_strategy
            == RollbackStrategy.IMMEDIATE
        )

        # Test custom transaction manager with different strategy
        custom_tm = TransactionManager(
            rollback_strategy=RollbackStrategy.BEST_EFFORT,
            enable_checkpoints=False,
        )
        service_custom = BulkReplyResolveService(transaction_manager=custom_tm)
        assert (
            service_custom.transaction_manager.rollback_strategy
            == RollbackStrategy.BEST_EFFORT
        )
        assert service_custom.transaction_manager.enable_checkpoints is False
