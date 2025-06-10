"""Service for bulk reply and resolve operations with atomic transaction handling."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .exceptions import (
    BulkOperationError,
    GitHubServiceError,
    ValidationError,
    create_validation_error,
)
from .fetch_service import FetchService
from .models import ReviewThread
from .reply_service import ReplyRequest, ReplyService
from .resolve_service import ResolveService


@dataclass
class BulkOperation:
    """Represents a single operation in a bulk workflow."""

    thread_id: str
    reply_body: str
    operation_id: str
    thread: Optional[ReviewThread] = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation."""

    operation_id: str
    thread_id: str
    success: bool
    reply_result: Optional[Dict[str, Any]] = None
    resolve_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    rollback_attempted: bool = False
    rollback_success: bool = False


@dataclass
class BulkOperationSummary:
    """Summary of all bulk operations."""

    total_operations: int
    successful_operations: int
    failed_operations: int
    results: List[BulkOperationResult]
    atomic_failure: bool = False
    rollback_performed: bool = False


class BulkReplyResolveService:
    """Service for bulk reply and resolve operations with atomic semantics."""

    def __init__(
        self,
        fetch_service: Optional[FetchService] = None,
        reply_service: Optional[ReplyService] = None,
        resolve_service: Optional[ResolveService] = None,
    ) -> None:
        """Initialize the bulk reply resolve service.

        Args:
            fetch_service: Optional FetchService instance. If None, creates a new one.
            reply_service: Optional ReplyService instance. If None, creates a new one.
            resolve_service: Optional ResolveService. If None, creates new.
        """
        self.fetch_service = fetch_service or FetchService()
        self.reply_service = reply_service or ReplyService()
        self.resolve_service = resolve_service or ResolveService()
        self.logger = logging.getLogger(__name__)

    def bulk_reply_and_resolve(
        self,
        pr_number: int,
        message: str,
        thread_ids: Optional[List[str]] = None,
        atomic: bool = True,
        dry_run: bool = False,
    ) -> BulkOperationSummary:
        """Perform bulk reply and resolve operations on review threads.

        Args:
            pr_number: Pull request number to operate on.
            message: Reply message to post to each thread.
            thread_ids: Optional list of specific thread IDs. If None, operates on all
                       unresolved threads.
            atomic: If True, all operations must succeed or all will be rolled back.
            dry_run: If True, simulate operations without making actual changes.

        Returns:
            BulkOperationSummary with details of all operations performed.

        Raises:
            ValidationError: If input parameters are invalid.
            BulkOperationError: If atomic operations fail and cannot be rolled back.
            GitHubServiceError: If GitHub API calls fail preventing recovery.
        """
        try:
            # Validate input parameters
            self._validate_bulk_operation_params(pr_number, message, thread_ids)

            # Get target threads
            target_threads = self._get_target_threads(pr_number, thread_ids)

            if not target_threads:
                return BulkOperationSummary(
                    total_operations=0,
                    successful_operations=0,
                    failed_operations=0,
                    results=[],
                )

            # Create bulk operations
            operations = self._create_bulk_operations(target_threads, message)

            # Execute operations
            if dry_run:
                return self._perform_dry_run(operations)
            elif atomic:
                return self._perform_atomic_operations(operations)
            else:
                return self._perform_non_atomic_operations(operations)

        except (ValidationError, BulkOperationError, GitHubServiceError):
            raise
        except Exception as e:
            raise BulkOperationError(
                message=f"Unexpected error during bulk operations: {str(e)}",
                context={
                    "pr_number": pr_number,
                    "thread_ids": thread_ids,
                    "atomic": atomic,
                    "dry_run": dry_run,
                },
            ) from e

    def _validate_bulk_operation_params(
        self,
        pr_number: int,
        message: str,
        thread_ids: Optional[List[str]],
    ) -> None:
        """Validate parameters for bulk operations."""
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise create_validation_error(
                field_name="pr_number",
                invalid_value=pr_number,
                expected_format="positive integer",
                message="PR number must be a positive integer",
            )

        if not isinstance(message, str) or not message.strip():
            raise create_validation_error(
                field_name="message",
                invalid_value=message,
                expected_format="non-empty string",
                message="Reply message must be a non-empty string",
            )

        if thread_ids is not None:
            if not isinstance(thread_ids, list):
                raise create_validation_error(
                    field_name="thread_ids",
                    invalid_value=type(thread_ids).__name__,
                    expected_format="list of strings or None",
                    message="thread_ids must be a list of strings or None",
                )

            for i, thread_id in enumerate(thread_ids):
                if not isinstance(thread_id, str) or not thread_id.strip():
                    raise create_validation_error(
                        field_name=f"thread_ids[{i}]",
                        invalid_value=thread_id,
                        expected_format="non-empty string",
                        message=f"Thread ID at index {i} must be a non-empty string",
                    )

    def _get_target_threads(
        self, pr_number: int, thread_ids: Optional[List[str]]
    ) -> List[ReviewThread]:
        """Get the threads to operate on."""
        try:
            # Fetch all unresolved threads from the PR
            all_threads = self.fetch_service.fetch_review_threads_from_current_repo(
                pr_number=pr_number,
                include_resolved=False,
            )

            if thread_ids is None:
                # Use all unresolved threads
                return all_threads

            # Filter to specific thread IDs
            thread_id_set = set(thread_ids)
            target_threads = []

            for thread in all_threads:
                if thread.thread_id in thread_id_set:
                    target_threads.append(thread)
                    thread_id_set.discard(thread.thread_id)

            # Check for thread IDs that weren't found
            if thread_id_set:
                missing_threads = list(thread_id_set)
                raise BulkOperationError(
                    message=f"Thread IDs not found or resolved: {missing_threads}",
                    context={
                        "pr_number": pr_number,
                        "missing_thread_ids": missing_threads,
                        "available_thread_ids": [t.thread_id for t in all_threads],
                    },
                )

            return target_threads

        except Exception as e:
            if isinstance(e, (BulkOperationError, GitHubServiceError)):
                raise
            raise BulkOperationError(
                message=f"Failed to fetch target threads: {str(e)}",
                context={"pr_number": pr_number, "thread_ids": thread_ids},
            ) from e

    def _create_bulk_operations(
        self, threads: List[ReviewThread], message: str
    ) -> List[BulkOperation]:
        """Create bulk operation objects from threads."""
        operations = []
        for i, thread in enumerate(threads):
            operation = BulkOperation(
                thread_id=thread.thread_id,
                reply_body=message,
                operation_id=f"bulk_op_{i:03d}",
                thread=thread,
            )
            operations.append(operation)
        return operations

    def _perform_dry_run(self, operations: List[BulkOperation]) -> BulkOperationSummary:
        """Simulate bulk operations without making actual changes."""
        results = []
        for operation in operations:
            result = BulkOperationResult(
                operation_id=operation.operation_id,
                thread_id=operation.thread_id,
                success=True,
                reply_result={"dry_run": True, "message": "Would post reply"},
                resolve_result={"dry_run": True, "message": "Would resolve thread"},
            )
            results.append(result)

        return BulkOperationSummary(
            total_operations=len(operations),
            successful_operations=len(operations),
            failed_operations=0,
            results=results,
        )

    def _perform_atomic_operations(
        self, operations: List[BulkOperation]
    ) -> BulkOperationSummary:
        """Perform operations atomically - all succeed or all are rolled back."""
        successful_results: List[BulkOperationResult] = []
        failed_result: Optional[BulkOperationResult] = None

        try:
            # Execute all operations
            for operation in operations:
                try:
                    result = self._execute_single_operation(operation)
                    if result.success:
                        successful_results.append(result)
                    else:
                        # First failure in atomic mode triggers rollback
                        failed_result = result
                        break
                except Exception as e:
                    # Create failed result for exception
                    failed_result = BulkOperationResult(
                        operation_id=operation.operation_id,
                        thread_id=operation.thread_id,
                        success=False,
                        error=str(e),
                    )
                    break

            # If any operation failed, rollback all successful ones
            if failed_result:
                self.logger.warning(
                    "Atomic failure, attempting rollback of %d operations",
                    len(successful_results),
                )
                rollback_results = self._rollback_operations(successful_results)

                # Update successful results with rollback status
                for i, rollback_result in enumerate(rollback_results):
                    if i < len(successful_results):
                        successful_results[i].rollback_attempted = True
                        successful_results[i].rollback_success = rollback_result.success

                # Mark all operations as failed due to atomic constraint
                all_results = successful_results + [failed_result]
                return BulkOperationSummary(
                    total_operations=len(operations),
                    successful_operations=0,
                    failed_operations=len(operations),
                    results=all_results,
                    atomic_failure=True,
                    rollback_performed=True,
                )

            # All operations succeeded
            return BulkOperationSummary(
                total_operations=len(operations),
                successful_operations=len(successful_results),
                failed_operations=0,
                results=successful_results,
            )

        except Exception as e:
            # Unexpected error during atomic operations
            raise BulkOperationError(
                message=f"Critical error during atomic operations: {str(e)}",
                context={
                    "completed_operations": len(successful_results),
                    "total_operations": len(operations),
                },
            ) from e

    def _perform_non_atomic_operations(
        self, operations: List[BulkOperation]
    ) -> BulkOperationSummary:
        """Perform operations non-atomically - continue on failures."""
        results = []
        successful_count = 0

        for operation in operations:
            try:
                result = self._execute_single_operation(operation)
                results.append(result)
                if result.success:
                    successful_count += 1
            except Exception as e:
                # Create failed result for exception
                result = BulkOperationResult(
                    operation_id=operation.operation_id,
                    thread_id=operation.thread_id,
                    success=False,
                    error=str(e),
                )
                results.append(result)

        return BulkOperationSummary(
            total_operations=len(operations),
            successful_operations=successful_count,
            failed_operations=len(operations) - successful_count,
            results=results,
        )

    def _execute_single_operation(
        self, operation: BulkOperation
    ) -> BulkOperationResult:
        """Execute a single reply and resolve operation."""
        try:
            # Step 1: Post reply
            reply_request = ReplyRequest(
                comment_id=operation.thread_id,
                reply_body=operation.reply_body,
            )

            reply_result = self.reply_service.post_reply(reply_request)

            # Step 2: Resolve thread
            resolve_result = self.resolve_service.resolve_thread(operation.thread_id)

            return BulkOperationResult(
                operation_id=operation.operation_id,
                thread_id=operation.thread_id,
                success=True,
                reply_result=reply_result,
                resolve_result=resolve_result,
            )

        except Exception as e:
            return BulkOperationResult(
                operation_id=operation.operation_id,
                thread_id=operation.thread_id,
                success=False,
                error=str(e),
            )

    def _rollback_operations(
        self, successful_results: List[BulkOperationResult]
    ) -> List[BulkOperationResult]:
        """Attempt to rollback successful operations by unresolving threads."""
        rollback_results = []

        for result in successful_results:
            try:
                # Only unresolve - we cannot "unpost" replies
                unresolve_result = self.resolve_service.unresolve_thread(
                    result.thread_id
                )
                rollback_results.append(
                    BulkOperationResult(
                        operation_id=f"rollback_{result.operation_id}",
                        thread_id=result.thread_id,
                        success=True,
                        resolve_result=unresolve_result,
                    )
                )
            except Exception as e:
                rollback_results.append(
                    BulkOperationResult(
                        operation_id=f"rollback_{result.operation_id}",
                        thread_id=result.thread_id,
                        success=False,
                        error=f"Rollback failed: {str(e)}",
                    )
                )

        return rollback_results

    def validate_bulk_operation_feasibility(
        self, pr_number: int, thread_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate that a bulk operation can be performed.

        Args:
            pr_number: Pull request number.
            thread_ids: Optional list of specific thread IDs.

        Returns:
            Dictionary with validation results including thread count and any issues.

        Raises:
            ValidationError: If parameters are invalid.
            BulkOperationError: If validation cannot be performed.
        """
        try:
            # Validate parameters
            self._validate_bulk_operation_params(pr_number, "test", thread_ids)

            # Get target threads
            target_threads = self._get_target_threads(pr_number, thread_ids)

            return {
                "feasible": True,
                "target_thread_count": len(target_threads),
                "thread_ids": [t.thread_id for t in target_threads],
                "estimated_operations": len(target_threads) * 2,  # reply + resolve
            }

        except Exception as e:
            return {
                "feasible": False,
                "error": str(e),
                "target_thread_count": 0,
                "thread_ids": [],
                "estimated_operations": 0,
            }
