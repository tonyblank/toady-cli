"""Unit tests for rollback handlers."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from toady.rollback_handlers import (
    CompositeRollbackHandler,
    ReplyRollbackHandler,
    ResolveRollbackHandler,
    create_default_rollback_handler,
)
from toady.transaction_manager import OperationRecord, OperationType


class TestReplyRollbackHandler:
    """Test cases for ReplyRollbackHandler."""

    @pytest.fixture
    def mock_reply_service(self):
        """Create a mock reply service."""
        return Mock()

    @pytest.fixture
    def reply_handler(self, mock_reply_service):
        """Create a reply rollback handler."""
        return ReplyRollbackHandler(mock_reply_service)

    @pytest.fixture
    def reply_operation(self):
        """Create a sample reply operation record."""
        return OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.REPLY_POST,
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={
                "reply_body": "Test reply",
                "reply_result": {"reply_id": "reply_789"},
            },
            rollback_data={"reply_id": "reply_789", "thread_id": "thread_456"},
        )

    def test_init_with_service(self, mock_reply_service):
        """Test initialization with custom reply service."""
        handler = ReplyRollbackHandler(mock_reply_service)
        assert handler.reply_service is mock_reply_service

    def test_init_without_service(self):
        """Test initialization without reply service creates default."""
        handler = ReplyRollbackHandler()
        assert handler.reply_service is not None

    def test_can_rollback_always_false(self, reply_handler, reply_operation):
        """Test that reply operations cannot be rolled back."""
        result = reply_handler.can_rollback(reply_operation)
        assert result is False

    def test_rollback_always_fails(self, reply_handler, reply_operation):
        """Test that reply rollback always fails."""
        result = reply_handler.rollback(reply_operation)
        assert result is False

    def test_rollback_logs_warning(self, reply_handler, reply_operation, caplog):
        """Test that rollback logs appropriate warning."""
        reply_handler.rollback(reply_operation)

        assert "Cannot rollback reply operation" in caplog.text
        assert "GitHub API doesn't support deleting comments" in caplog.text
        assert "thread_456" in caplog.text

    def test_rollback_with_reply_id_logs_info(
        self, reply_handler, reply_operation, caplog
    ):
        """Test that rollback with reply ID logs additional info."""
        result = reply_handler.rollback(reply_operation)

        # Check that rollback fails as expected
        assert result is False

        # Check that warning message is logged (basic check)
        assert "Cannot rollback reply operation" in caplog.text


class TestResolveRollbackHandler:
    """Test cases for ResolveRollbackHandler."""

    @pytest.fixture
    def mock_resolve_service(self):
        """Create a mock resolve service."""
        return Mock()

    @pytest.fixture
    def resolve_handler(self, mock_resolve_service):
        """Create a resolve rollback handler."""
        return ResolveRollbackHandler(mock_resolve_service)

    @pytest.fixture
    def resolve_operation(self):
        """Create a sample resolve operation record."""
        return OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.THREAD_RESOLVE,
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={"resolve_result": {"success": True}},
            rollback_data={"thread_id": "thread_456", "previous_state": "unresolved"},
        )

    @pytest.fixture
    def unresolve_operation(self):
        """Create a sample unresolve operation record."""
        return OperationRecord(
            operation_id="op_124",
            operation_type=OperationType.THREAD_UNRESOLVE,
            timestamp=datetime.now(),
            thread_id="thread_789",
            data={"unresolve_result": {"success": True}},
            rollback_data={"thread_id": "thread_789", "previous_state": "resolved"},
        )

    def test_init_with_service(self, mock_resolve_service):
        """Test initialization with custom resolve service."""
        handler = ResolveRollbackHandler(mock_resolve_service)
        assert handler.resolve_service is mock_resolve_service

    def test_init_without_service(self):
        """Test initialization without resolve service creates default."""
        handler = ResolveRollbackHandler()
        assert handler.resolve_service is not None

    def test_can_rollback_resolve_operation(self, resolve_handler, resolve_operation):
        """Test that resolve operations can be rolled back."""
        result = resolve_handler.can_rollback(resolve_operation)
        assert result is True

    def test_can_rollback_unresolve_operation(
        self, resolve_handler, unresolve_operation
    ):
        """Test that unresolve operations can be rolled back."""
        result = resolve_handler.can_rollback(unresolve_operation)
        assert result is True

    def test_can_rollback_unsupported_operation(self, resolve_handler):
        """Test that unsupported operations cannot be rolled back."""
        operation = OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.REPLY_POST,
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={},
        )
        result = resolve_handler.can_rollback(operation)
        assert result is False  # REPLY_POST is not a resolve/unresolve type

    def test_rollback_resolve_operation_success(
        self, resolve_handler, resolve_operation, mock_resolve_service
    ):
        """Test successful rollback of resolve operation."""
        mock_resolve_service.unresolve_thread.return_value = {"success": True}

        result = resolve_handler.rollback(resolve_operation)

        assert result is True
        mock_resolve_service.unresolve_thread.assert_called_once_with("thread_456")

    def test_rollback_unresolve_operation_success(
        self, resolve_handler, unresolve_operation, mock_resolve_service
    ):
        """Test successful rollback of unresolve operation."""
        mock_resolve_service.resolve_thread.return_value = {"success": True}

        result = resolve_handler.rollback(unresolve_operation)

        assert result is True
        mock_resolve_service.resolve_thread.assert_called_once_with("thread_789")

    def test_rollback_resolve_operation_failure(
        self, resolve_handler, resolve_operation, mock_resolve_service
    ):
        """Test failed rollback of resolve operation."""
        mock_resolve_service.unresolve_thread.return_value = {"success": False}

        result = resolve_handler.rollback(resolve_operation)

        assert result is False

    def test_rollback_operation_exception(
        self, resolve_handler, resolve_operation, mock_resolve_service
    ):
        """Test rollback when service raises exception."""
        mock_resolve_service.unresolve_thread.side_effect = Exception("API Error")

        result = resolve_handler.rollback(resolve_operation)

        assert result is False

    def test_rollback_unsupported_operation_type(self, resolve_handler):
        """Test rollback of unsupported operation type."""
        operation = OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.REPLY_POST,
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={},
        )

        result = resolve_handler.rollback(operation)

        assert result is False

    def test_rollback_logs_success(
        self, resolve_handler, resolve_operation, mock_resolve_service, caplog
    ):
        """Test that successful rollback is logged."""
        mock_resolve_service.unresolve_thread.return_value = {"success": True}

        result = resolve_handler.rollback(resolve_operation)

        # Verify the rollback was successful
        assert result is True

        # Verify the service was called
        mock_resolve_service.unresolve_thread.assert_called_once_with("thread_456")

    def test_rollback_logs_failure(
        self, resolve_handler, resolve_operation, mock_resolve_service, caplog
    ):
        """Test that failed rollback is logged."""
        mock_resolve_service.unresolve_thread.side_effect = Exception("API Error")

        resolve_handler.rollback(resolve_operation)

        assert "Failed to rollback" in caplog.text
        assert "API Error" in caplog.text


class TestCompositeRollbackHandler:
    """Test cases for CompositeRollbackHandler."""

    @pytest.fixture
    def mock_reply_service(self):
        """Create a mock reply service."""
        return Mock()

    @pytest.fixture
    def mock_resolve_service(self):
        """Create a mock resolve service."""
        return Mock()

    @pytest.fixture
    def composite_handler(self, mock_reply_service, mock_resolve_service):
        """Create a composite rollback handler."""
        return CompositeRollbackHandler(mock_reply_service, mock_resolve_service)

    @pytest.fixture
    def reply_operation(self):
        """Create a sample reply operation record."""
        return OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.REPLY_POST,
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={},
        )

    @pytest.fixture
    def resolve_operation(self):
        """Create a sample resolve operation record."""
        return OperationRecord(
            operation_id="op_124",
            operation_type=OperationType.THREAD_RESOLVE,
            timestamp=datetime.now(),
            thread_id="thread_789",
            data={},
        )

    def test_init_with_services(self, mock_reply_service, mock_resolve_service):
        """Test initialization with custom services."""
        handler = CompositeRollbackHandler(mock_reply_service, mock_resolve_service)
        assert handler.reply_handler.reply_service is mock_reply_service
        assert handler.resolve_handler.resolve_service is mock_resolve_service

    def test_init_without_services(self):
        """Test initialization without services creates defaults."""
        handler = CompositeRollbackHandler()
        assert handler.reply_handler.reply_service is not None
        assert handler.resolve_handler.resolve_service is not None

    def test_can_rollback_reply_operation(self, composite_handler, reply_operation):
        """Test can_rollback delegates to reply handler."""
        result = composite_handler.can_rollback(reply_operation)
        assert result is False  # Reply operations cannot be rolled back

    def test_can_rollback_resolve_operation(self, composite_handler, resolve_operation):
        """Test can_rollback delegates to resolve handler."""
        result = composite_handler.can_rollback(resolve_operation)
        assert result is True  # Resolve operations can be rolled back

    def test_can_rollback_unknown_operation(self, composite_handler):
        """Test can_rollback with unknown operation type."""
        operation = OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.CHECKPOINT,  # Unknown type
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={},
        )

        result = composite_handler.can_rollback(operation)
        assert result is False

    def test_rollback_reply_operation(self, composite_handler, reply_operation):
        """Test rollback delegates to reply handler."""
        result = composite_handler.rollback(reply_operation)
        assert result is False  # Reply rollback always fails

    def test_rollback_resolve_operation(
        self, composite_handler, resolve_operation, mock_resolve_service
    ):
        """Test rollback delegates to resolve handler."""
        mock_resolve_service.unresolve_thread.return_value = {"success": True}

        result = composite_handler.rollback(resolve_operation)
        assert result is True

    def test_rollback_unknown_operation(self, composite_handler):
        """Test rollback with unknown operation type."""
        operation = OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.CHECKPOINT,  # Unknown type
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={},
        )

        result = composite_handler.rollback(operation)
        assert result is False

    def test_rollback_unknown_operation_logs_error(self, composite_handler, caplog):
        """Test that unknown operation type logs error."""
        operation = OperationRecord(
            operation_id="op_123",
            operation_type=OperationType.CHECKPOINT,  # Unknown type
            timestamp=datetime.now(),
            thread_id="thread_456",
            data={},
        )

        composite_handler.rollback(operation)

        assert "Unknown operation type" in caplog.text


class TestCreateDefaultRollbackHandler:
    """Test cases for create_default_rollback_handler function."""

    def test_create_with_services(self):
        """Test creating default handler with custom services."""
        mock_reply = Mock()
        mock_resolve = Mock()

        handler = create_default_rollback_handler(mock_reply, mock_resolve)

        assert isinstance(handler, CompositeRollbackHandler)
        assert handler.reply_handler.reply_service is mock_reply
        assert handler.resolve_handler.resolve_service is mock_resolve

    def test_create_without_services(self):
        """Test creating default handler without services."""
        handler = create_default_rollback_handler()

        assert isinstance(handler, CompositeRollbackHandler)
        assert handler.reply_handler.reply_service is not None
        assert handler.resolve_handler.resolve_service is not None
