"""Unit tests for BulkReplyResolveService."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from toady.bulk_reply_resolve_service import (
    BulkOperation,
    BulkOperationResult,
    BulkOperationSummary,
    BulkReplyResolveService,
)
from toady.exceptions import (
    BulkOperationError,
    GitHubServiceError,
    ValidationError,
)
from toady.fetch_service import FetchService
from toady.models import ReviewThread
from toady.reply_service import ReplyService
from toady.resolve_service import ResolveService


class TestBulkReplyResolveService:
    """Test cases for BulkReplyResolveService."""

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
    def bulk_service(
        self, mock_fetch_service, mock_reply_service, mock_resolve_service
    ):
        """Create a BulkReplyResolveService with mocked dependencies."""
        return BulkReplyResolveService(
            fetch_service=mock_fetch_service,
            reply_service=mock_reply_service,
            resolve_service=mock_resolve_service,
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

    def test_init_with_default_services(self):
        """Test initialization with default services."""
        service = BulkReplyResolveService()
        assert service.fetch_service is not None
        assert service.reply_service is not None
        assert service.resolve_service is not None

    def test_init_with_custom_services(
        self, mock_fetch_service, mock_reply_service, mock_resolve_service
    ):
        """Test initialization with custom services."""
        service = BulkReplyResolveService(
            fetch_service=mock_fetch_service,
            reply_service=mock_reply_service,
            resolve_service=mock_resolve_service,
        )
        assert service.fetch_service is mock_fetch_service
        assert service.reply_service is mock_reply_service
        assert service.resolve_service is mock_resolve_service

    def test_validate_bulk_operation_params_valid(self, bulk_service):
        """Test parameter validation with valid inputs."""
        # Should not raise any exceptions
        bulk_service._validate_bulk_operation_params(123, "test message", ["thread_1"])
        bulk_service._validate_bulk_operation_params(456, "another message", None)

    def test_validate_bulk_operation_params_invalid_pr_number(self, bulk_service):
        """Test parameter validation with invalid PR number."""
        with pytest.raises(
            ValidationError, match="PR number must be a positive integer"
        ):
            bulk_service._validate_bulk_operation_params(0, "test", None)

        with pytest.raises(
            ValidationError, match="PR number must be a positive integer"
        ):
            bulk_service._validate_bulk_operation_params(-1, "test", None)

        with pytest.raises(
            ValidationError, match="PR number must be a positive integer"
        ):
            bulk_service._validate_bulk_operation_params("123", "test", None)

    def test_validate_bulk_operation_params_invalid_message(self, bulk_service):
        """Test parameter validation with invalid message."""
        with pytest.raises(
            ValidationError, match="Reply message must be a non-empty string"
        ):
            bulk_service._validate_bulk_operation_params(123, "", None)

        with pytest.raises(
            ValidationError, match="Reply message must be a non-empty string"
        ):
            bulk_service._validate_bulk_operation_params(123, "   ", None)

        with pytest.raises(
            ValidationError, match="Reply message must be a non-empty string"
        ):
            bulk_service._validate_bulk_operation_params(123, 123, None)

    def test_validate_bulk_operation_params_invalid_thread_ids(self, bulk_service):
        """Test parameter validation with invalid thread IDs."""
        with pytest.raises(
            ValidationError, match="thread_ids must be a list of strings or None"
        ):
            bulk_service._validate_bulk_operation_params(123, "test", "not_a_list")

        with pytest.raises(
            ValidationError, match="Thread ID at index 0 must be a non-empty string"
        ):
            bulk_service._validate_bulk_operation_params(123, "test", [""])

        with pytest.raises(
            ValidationError, match="Thread ID at index 1 must be a non-empty string"
        ):
            bulk_service._validate_bulk_operation_params(123, "test", ["valid", 123])

    def test_get_target_threads_all_unresolved(self, bulk_service, sample_threads):
        """Test getting all unresolved threads."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        result = bulk_service._get_target_threads(123, None)

        assert result == sample_threads
        bulk_service.fetch_service.fetch_review_threads_from_current_repo.assert_called_once_with(
            pr_number=123,
            include_resolved=False,
        )

    def test_get_target_threads_specific_ids(self, bulk_service, sample_threads):
        """Test getting specific thread IDs."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        result = bulk_service._get_target_threads(123, ["thread_1"])

        assert len(result) == 1
        assert result[0].thread_id == "thread_1"

    def test_get_target_threads_missing_ids(self, bulk_service, sample_threads):
        """Test getting threads with some missing IDs."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        with pytest.raises(
            BulkOperationError, match="Thread IDs not found or resolved"
        ):
            bulk_service._get_target_threads(123, ["thread_1", "missing_thread"])

    def test_create_bulk_operations(self, bulk_service, sample_threads):
        """Test creating bulk operations from threads."""
        operations = bulk_service._create_bulk_operations(
            sample_threads, "test message"
        )

        assert len(operations) == 2
        assert operations[0].thread_id == "thread_1"
        assert operations[0].reply_body == "test message"
        assert operations[0].operation_id == "bulk_op_000"
        assert operations[1].thread_id == "thread_2"
        assert operations[1].operation_id == "bulk_op_001"

    def test_perform_dry_run(self, bulk_service, sample_threads):
        """Test dry run mode."""
        operations = bulk_service._create_bulk_operations(sample_threads, "test")
        result = bulk_service._perform_dry_run(operations)

        assert result.total_operations == 2
        assert result.successful_operations == 2
        assert result.failed_operations == 0
        assert len(result.results) == 2
        assert all(r.success for r in result.results)
        assert all(r.reply_result["dry_run"] for r in result.results)

    def test_execute_single_operation_success(self, bulk_service):
        """Test successful execution of a single operation."""
        operation = BulkOperation(
            thread_id="test_thread",
            reply_body="test message",
            operation_id="test_op",
        )

        mock_reply_result = {"reply_id": "reply_123"}
        mock_resolve_result = {"success": True}

        bulk_service.reply_service.post_reply.return_value = mock_reply_result
        bulk_service.resolve_service.resolve_thread.return_value = mock_resolve_result

        result = bulk_service._execute_single_operation(operation)

        assert result.success is True
        assert result.reply_result == mock_reply_result
        assert result.resolve_result == mock_resolve_result
        assert result.error is None

    def test_execute_single_operation_reply_failure(self, bulk_service):
        """Test single operation with reply failure."""
        operation = BulkOperation(
            thread_id="test_thread",
            reply_body="test message",
            operation_id="test_op",
        )

        bulk_service.reply_service.post_reply.side_effect = Exception("Reply failed")

        result = bulk_service._execute_single_operation(operation)

        assert result.success is False
        assert result.error == "Reply failed"
        assert result.reply_result is None
        assert result.resolve_result is None

    def test_execute_single_operation_resolve_failure(self, bulk_service):
        """Test single operation with resolve failure."""
        operation = BulkOperation(
            thread_id="test_thread",
            reply_body="test message",
            operation_id="test_op",
        )

        mock_reply_result = {"reply_id": "reply_123"}
        bulk_service.reply_service.post_reply.return_value = mock_reply_result
        bulk_service.resolve_service.resolve_thread.side_effect = Exception(
            "Resolve failed"
        )

        result = bulk_service._execute_single_operation(operation)

        assert result.success is False
        assert result.error == "Resolve failed"
        assert result.reply_result is None
        assert result.resolve_result is None

    def test_perform_non_atomic_operations_mixed_results(
        self, bulk_service, sample_threads
    ):
        """Test non-atomic operations with mixed success and failure."""
        operations = bulk_service._create_bulk_operations(sample_threads, "test")

        # Mock first operation to succeed, second to fail
        results = [
            BulkOperationResult(
                operation_id="bulk_op_000",
                thread_id="thread_1",
                success=True,
                reply_result={"reply_id": "reply_1"},
                resolve_result={"success": True},
            ),
            BulkOperationResult(
                operation_id="bulk_op_001",
                thread_id="thread_2",
                success=False,
                error="Operation failed",
            ),
        ]

        with patch.object(
            bulk_service, "_execute_single_operation", side_effect=results
        ):
            summary = bulk_service._perform_non_atomic_operations(operations)

        assert summary.total_operations == 2
        assert summary.successful_operations == 1
        assert summary.failed_operations == 1
        assert len(summary.results) == 2

    def test_perform_atomic_operations_all_success(self, bulk_service, sample_threads):
        """Test atomic operations where all succeed."""
        operations = bulk_service._create_bulk_operations(sample_threads, "test")

        # Mock all operations to succeed
        success_results = [
            BulkOperationResult(
                operation_id=f"bulk_op_{i:03d}",
                thread_id=f"thread_{i+1}",
                success=True,
                reply_result={"reply_id": f"reply_{i+1}"},
                resolve_result={"success": True},
            )
            for i in range(2)
        ]

        with patch.object(
            bulk_service, "_execute_single_operation", side_effect=success_results
        ):
            summary = bulk_service._perform_atomic_operations(operations)

        assert summary.total_operations == 2
        assert summary.successful_operations == 2
        assert summary.failed_operations == 0
        assert summary.atomic_failure is False
        assert summary.rollback_performed is False

    def test_perform_atomic_operations_with_failure_and_rollback(
        self, bulk_service, sample_threads
    ):
        """Test atomic operations with failure and rollback."""
        operations = bulk_service._create_bulk_operations(sample_threads, "test")

        # Mock first operation to succeed, second to fail
        results = [
            BulkOperationResult(
                operation_id="bulk_op_000",
                thread_id="thread_1",
                success=True,
                reply_result={"reply_id": "reply_1"},
                resolve_result={"success": True},
            ),
            BulkOperationResult(
                operation_id="bulk_op_001",
                thread_id="thread_2",
                success=False,
                error="Operation failed",
            ),
        ]

        # Mock rollback to succeed
        rollback_results = [
            BulkOperationResult(
                operation_id="rollback_bulk_op_000",
                thread_id="thread_1",
                success=True,
                resolve_result={"success": True},
            )
        ]

        with (
            patch.object(
                bulk_service, "_execute_single_operation", side_effect=results
            ),
            patch.object(
                bulk_service, "_rollback_operations", return_value=rollback_results
            ),
        ):
            summary = bulk_service._perform_atomic_operations(operations)

        assert summary.total_operations == 2
        assert (
            summary.successful_operations == 0
        )  # All marked as failed due to atomic constraint
        assert summary.failed_operations == 2
        assert summary.atomic_failure is True
        assert summary.rollback_performed is True

    def test_rollback_operations(self, bulk_service):
        """Test rollback operations."""
        successful_results = [
            BulkOperationResult(
                operation_id="bulk_op_000",
                thread_id="thread_1",
                success=True,
            ),
            BulkOperationResult(
                operation_id="bulk_op_001",
                thread_id="thread_2",
                success=True,
            ),
        ]

        # Mock unresolve calls
        mock_unresolve_results = [
            {"thread_id": "thread_1", "success": True},
            {"thread_id": "thread_2", "success": True},
        ]
        bulk_service.resolve_service.unresolve_thread.side_effect = (
            mock_unresolve_results
        )

        rollback_results = bulk_service._rollback_operations(successful_results)

        assert len(rollback_results) == 2
        assert all(r.success for r in rollback_results)
        assert bulk_service.resolve_service.unresolve_thread.call_count == 2

    def test_rollback_operations_with_failures(self, bulk_service):
        """Test rollback operations with some failures."""
        successful_results = [
            BulkOperationResult(
                operation_id="bulk_op_000",
                thread_id="thread_1",
                success=True,
            ),
            BulkOperationResult(
                operation_id="bulk_op_001",
                thread_id="thread_2",
                success=True,
            ),
        ]

        # Mock first unresolve to succeed, second to fail
        def unresolve_side_effect(thread_id):
            if thread_id == "thread_1":
                return {"thread_id": "thread_1", "success": True}
            else:
                raise Exception("Unresolve failed")

        bulk_service.resolve_service.unresolve_thread.side_effect = (
            unresolve_side_effect
        )

        rollback_results = bulk_service._rollback_operations(successful_results)

        assert len(rollback_results) == 2
        assert rollback_results[0].success is True
        assert rollback_results[1].success is False
        assert "Rollback failed" in rollback_results[1].error

    def test_bulk_reply_and_resolve_dry_run(self, bulk_service, sample_threads):
        """Test bulk reply and resolve in dry run mode."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            dry_run=True,
        )

        assert summary.total_operations == 2
        assert summary.successful_operations == 2
        assert summary.failed_operations == 0
        assert all(r.success for r in summary.results)

    def test_bulk_reply_and_resolve_atomic_success(self, bulk_service, sample_threads):
        """Test bulk reply and resolve with atomic operations (all succeed)."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        # Mock all operations to succeed
        mock_reply_result = {"reply_id": "reply_123"}
        mock_resolve_result = {"success": True}
        bulk_service.reply_service.post_reply.return_value = mock_reply_result
        bulk_service.resolve_service.resolve_thread.return_value = mock_resolve_result

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            atomic=True,
        )

        assert summary.total_operations == 2
        assert summary.successful_operations == 2
        assert summary.failed_operations == 0
        assert summary.atomic_failure is False

    def test_bulk_reply_and_resolve_no_threads(self, bulk_service):
        """Test bulk reply and resolve with no target threads."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = []

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
        )

        assert summary.total_operations == 0
        assert summary.successful_operations == 0
        assert summary.failed_operations == 0

    def test_validate_bulk_operation_feasibility_success(
        self, bulk_service, sample_threads
    ):
        """Test validation of bulk operation feasibility (success case)."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        result = bulk_service.validate_bulk_operation_feasibility(123)

        assert result["feasible"] is True
        assert result["target_thread_count"] == 2
        assert result["thread_ids"] == ["thread_1", "thread_2"]
        assert result["estimated_operations"] == 4

    def test_validate_bulk_operation_feasibility_failure(self, bulk_service):
        """Test validation of bulk operation feasibility (failure case)."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.side_effect = Exception(
            "API Error"
        )

        result = bulk_service.validate_bulk_operation_feasibility(123)

        assert result["feasible"] is False
        assert "API Error" in result["error"]
        assert result["target_thread_count"] == 0

    def test_bulk_reply_and_resolve_validation_error(self, bulk_service):
        """Test bulk reply and resolve with validation error."""
        with pytest.raises(ValidationError):
            bulk_service.bulk_reply_and_resolve(
                pr_number=0,  # Invalid PR number
                message="test",
            )

    def test_bulk_reply_and_resolve_fetch_error(self, bulk_service):
        """Test bulk reply and resolve with fetch error."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.side_effect = (
            GitHubServiceError("Fetch failed")
        )

        with pytest.raises(GitHubServiceError):
            bulk_service.bulk_reply_and_resolve(
                pr_number=123,
                message="test",
            )

    def test_bulk_reply_and_resolve_with_specific_thread_ids(
        self, bulk_service, sample_threads
    ):
        """Test bulk reply and resolve with specific thread IDs."""
        fetch_service = bulk_service.fetch_service
        fetch_service.fetch_review_threads_from_current_repo.return_value = (
            sample_threads
        )

        # Mock successful operations
        mock_reply_result = {"reply_id": "reply_123"}
        mock_resolve_result = {"success": True}
        bulk_service.reply_service.post_reply.return_value = mock_reply_result
        bulk_service.resolve_service.resolve_thread.return_value = mock_resolve_result

        summary = bulk_service.bulk_reply_and_resolve(
            pr_number=123,
            message="test message",
            thread_ids=["thread_1"],
            atomic=False,
        )

        assert summary.total_operations == 1
        assert summary.successful_operations == 1
        assert summary.results[0].thread_id == "thread_1"


class TestBulkOperationDataClasses:
    """Test cases for bulk operation data classes."""

    def test_bulk_operation_creation(self):
        """Test BulkOperation creation."""
        operation = BulkOperation(
            thread_id="test_thread",
            reply_body="test message",
            operation_id="test_op",
        )

        assert operation.thread_id == "test_thread"
        assert operation.reply_body == "test message"
        assert operation.operation_id == "test_op"
        assert operation.thread is None

    def test_bulk_operation_result_creation(self):
        """Test BulkOperationResult creation."""
        result = BulkOperationResult(
            operation_id="test_op",
            thread_id="test_thread",
            success=True,
            reply_result={"reply_id": "123"},
            resolve_result={"success": True},
        )

        assert result.operation_id == "test_op"
        assert result.thread_id == "test_thread"
        assert result.success is True
        assert result.reply_result == {"reply_id": "123"}
        assert result.resolve_result == {"success": True}
        assert result.error is None

    def test_bulk_operation_summary_creation(self):
        """Test BulkOperationSummary creation."""
        results = [
            BulkOperationResult(
                operation_id="op1",
                thread_id="thread1",
                success=True,
            ),
            BulkOperationResult(
                operation_id="op2",
                thread_id="thread2",
                success=False,
                error="Failed",
            ),
        ]

        summary = BulkOperationSummary(
            total_operations=2,
            successful_operations=1,
            failed_operations=1,
            results=results,
        )

        assert summary.total_operations == 2
        assert summary.successful_operations == 1
        assert summary.failed_operations == 1
        assert len(summary.results) == 2
        assert summary.atomic_failure is False
        assert summary.rollback_performed is False
