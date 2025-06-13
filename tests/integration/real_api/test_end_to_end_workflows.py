"""End-to-end integration tests for complete GitHub review workflows.

These tests verify complete user workflows against real GitHub repositories,
testing the integration between fetch, reply, and resolve commands.
"""

import json
import subprocess
import time
from typing import Any

from click.testing import CliRunner
import pytest

from toady.cli import cli


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.slow
class TestEndToEndWorkflows:
    """Test complete end-to-end review workflows against real GitHub API."""

    def test_complete_review_cycle_workflow(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        test_repository_info: dict[str, Any],
        rate_limit_aware_delay,
        performance_monitor,
        integration_test_cleanup,
    ):
        """Test a complete review cycle: fetch -> reply -> resolve workflow.

        This test verifies that a user can:
        1. Fetch unresolved review threads from a PR
        2. Reply to a review comment
        3. Resolve the review thread
        4. Verify the thread is marked as resolved
        """
        pr_number = verify_test_pr_exists["number"]
        repo_full_name = test_repository_info["full_name"]

        # Step 1: Fetch unresolved review threads
        performance_monitor.start_timing("fetch_unresolved_threads")

        result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        performance_monitor.stop_timing()

        raw_out = getattr(result, "stdout", result.output)
        assert result.exit_code == 0, f"Fetch command failed: {raw_out}"

        try:
            threads_data = json.loads(raw_out)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response from fetch: {raw_out}")

        assert isinstance(threads_data, list), "Expected list of threads"

        # If no unresolved threads, create a test comment first
        if not threads_data:
            # Create a test review comment for this test
            test_comment_body = f"Integration test comment - {int(time.time())}"

            create_result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "comment",
                    str(pr_number),
                    "--repo",
                    repo_full_name,
                    "--body",
                    test_comment_body,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if create_result.returncode != 0:
                pytest.skip("Could not create test comment for workflow test")

            # Add cleanup for the test comment
            integration_test_cleanup(
                self._cleanup_comment, create_result.stdout.strip()
            )

            # Wait for comment to be processed
            rate_limit_aware_delay(2.0)

            # Re-fetch to get the new comment
            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            raw_out = getattr(result, "stdout", result.output)
            assert result.exit_code == 0
            threads_data = json.loads(raw_out)

        if not threads_data:
            pytest.skip("No review threads available for end-to-end testing")

        # Get the first thread for testing
        test_thread = threads_data[0]

        # Verify thread structure
        assert "thread_id" in test_thread
        assert "comments" in test_thread
        assert len(test_thread["comments"]) > 0

        thread_id = test_thread["thread_id"]
        first_comment = test_thread["comments"][0]
        comment_id = first_comment["comment_id"]

        # Step 2: Reply to the review comment
        performance_monitor.start_timing("post_reply")

        reply_body = f"Integration test reply - {int(time.time())}"

        reply_result = integration_cli_runner.invoke(
            cli,
            [
                "reply",
                "--comment-id",
                comment_id,
                "--body",
                reply_body,
                "--format",
                "json",
            ],
        )

        performance_monitor.stop_timing()
        rate_limit_aware_delay()

        assert (
            reply_result.exit_code == 0
        ), f"Reply command failed: {reply_result.output}"

        try:
            reply_data = json.loads(reply_result.output)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response from reply: {reply_result.output}")

        assert reply_data.get("success") is True
        assert "comment_id" in reply_data

        # Step 3: Resolve the review thread
        performance_monitor.start_timing("resolve_thread")

        resolve_result = integration_cli_runner.invoke(
            cli, ["resolve", "--thread-id", thread_id, "--format", "json"]
        )

        performance_monitor.stop_timing()
        rate_limit_aware_delay()

        assert (
            resolve_result.exit_code == 0
        ), f"Resolve command failed: {resolve_result.output}"

        try:
            resolve_data = json.loads(resolve_result.output)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response from resolve: {resolve_result.output}")

        assert resolve_data.get("success") is True
        assert resolve_data.get("thread_id") == thread_id
        assert resolve_data.get("resolved") is True

        # Step 4: Verify thread is resolved by fetching again
        performance_monitor.start_timing("verify_resolution")

        verify_result = integration_cli_runner.invoke(
            cli,
            [
                "fetch",
                "--pr",
                str(pr_number),
                "--resolved",  # Include resolved threads
                "--format",
                "json",
            ],
        )

        performance_monitor.stop_timing()

        assert verify_result.exit_code == 0

        resolved_threads = json.loads(verify_result.output)
        resolved_thread = next(
            (t for t in resolved_threads if t["thread_id"] == thread_id), None
        )

        assert resolved_thread is not None, "Resolved thread not found in results"
        assert resolved_thread.get("status") == "RESOLVED"

        # Performance assertions
        performance_monitor.assert_performance_threshold(
            "fetch_unresolved_threads", 10.0
        )
        performance_monitor.assert_performance_threshold("post_reply", 15.0)
        performance_monitor.assert_performance_threshold("resolve_thread", 10.0)
        performance_monitor.assert_performance_threshold("verify_resolution", 10.0)

    def test_bulk_thread_resolution_workflow(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        test_repository_info: dict[str, Any],
        rate_limit_aware_delay,
        performance_monitor,
        skip_if_slow,
    ):
        """Test bulk resolution of all threads in a PR."""
        pr_number = verify_test_pr_exists["number"]

        # First, fetch all unresolved threads
        performance_monitor.start_timing("fetch_for_bulk_resolve")

        result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        performance_monitor.stop_timing()

        assert result.exit_code == 0

        threads_data = json.loads(result.output)
        unresolved_count = len(threads_data)

        if unresolved_count == 0:
            pytest.skip("No unresolved threads available for bulk resolution test")

        # Perform bulk resolution
        performance_monitor.start_timing("bulk_resolve_all")

        bulk_result = integration_cli_runner.invoke(
            cli, ["resolve", "--all", "--pr", str(pr_number), "--format", "json"]
        )

        performance_monitor.stop_timing()
        rate_limit_aware_delay(2.0)  # Allow more time for bulk operations

        assert bulk_result.exit_code == 0, f"Bulk resolve failed: {bulk_result.output}"

        bulk_data = json.loads(bulk_result.output)
        assert bulk_data.get("success") is True
        assert bulk_data.get("resolved_count") == unresolved_count

        # Verify all threads are now resolved
        verify_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        assert verify_result.exit_code == 0
        remaining_unresolved = json.loads(verify_result.output)

        # Should be no unresolved threads remaining
        assert len(remaining_unresolved) == 0, (
            f"Expected 0 unresolved threads after bulk resolve, "
            f"but found {len(remaining_unresolved)}"
        )

        # Performance assertion for bulk operations
        performance_monitor.assert_performance_threshold("bulk_resolve_all", 30.0)

    def test_error_recovery_workflow(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        test_repository_info: dict[str, Any],
        rate_limit_aware_delay,
    ):
        """Test error recovery in workflows (invalid IDs, network issues, etc.)."""
        verify_test_pr_exists["number"]

        # Test 1: Invalid comment ID handling
        invalid_reply_result = integration_cli_runner.invoke(
            cli,
            [
                "reply",
                "--comment-id",
                "INVALID_COMMENT_ID_12345",
                "--body",
                "Test reply",
                "--format",
                "json",
            ],
        )

        # Should fail gracefully with proper error message
        assert invalid_reply_result.exit_code != 0

        # Test 2: Invalid thread ID handling
        invalid_resolve_result = integration_cli_runner.invoke(
            cli,
            ["resolve", "--thread-id", "INVALID_THREAD_ID_12345", "--format", "json"],
        )

        # Should fail gracefully with proper error message
        assert invalid_resolve_result.exit_code != 0

        # Test 3: Invalid PR number handling
        invalid_fetch_result = integration_cli_runner.invoke(
            cli,
            ["fetch", "--pr", "999999", "--format", "json"],  # Very unlikely to exist
        )

        # Should fail gracefully with proper error message
        assert invalid_fetch_result.exit_code != 0

    def test_interactive_workflow_with_multiple_prs(
        self,
        integration_cli_runner: CliRunner,
        test_repository_info: dict[str, Any],
        rate_limit_aware_delay,
        skip_if_slow,
    ):
        """Test interactive workflow that handles multiple PRs."""
        test_repository_info["full_name"]

        # Fetch without specifying PR (interactive mode)
        result = integration_cli_runner.invoke(
            cli, ["fetch", "--format", "json"], input="\n"
        )  # Just press enter to select first PR

        # Should either work with available PRs or skip gracefully
        if result.exit_code == 0:
            # Verify we got valid thread data
            # For JSON format, check stdout only (stderr contains interactive messages)
            try:
                raw_out = getattr(result, "stdout", result.output)
                threads_data = json.loads(raw_out)
                assert isinstance(threads_data, list)
            except json.JSONDecodeError:
                raw_out = getattr(result, "stdout", result.output)
                pytest.fail(f"Invalid JSON response in output: {raw_out}")
        else:
            # Interactive mode might fail if no PRs available - that's okay
            assert (
                "No pull requests found" in result.output
                or "error" in result.output.lower()
            )

    def test_format_consistency_across_workflow(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        rate_limit_aware_delay,
    ):
        """Test that output formats are consistent across all commands in a workflow."""
        pr_number = verify_test_pr_exists["number"]

        # Test JSON format consistency
        json_commands = [
            (["fetch", "--pr", str(pr_number), "--format", "json"], "fetch"),
            (
                ["fetch", "--pr", str(pr_number), "--resolved", "--format", "json"],
                "fetch_resolved",
            ),
        ]

        for cmd_args, cmd_name in json_commands:
            result = integration_cli_runner.invoke(cli, cmd_args)

            assert result.exit_code == 0, f"{cmd_name} failed: {result.output}"

            try:
                data = json.loads(result.output)
                assert isinstance(data, list), f"{cmd_name} should return a list"
            except json.JSONDecodeError:
                pytest.fail(f"{cmd_name} returned invalid JSON: {result.output}")

            rate_limit_aware_delay()

        # Test pretty format consistency
        pretty_commands = [
            (["fetch", "--pr", str(pr_number), "--format", "pretty"], "fetch_pretty"),
        ]

        for cmd_args, cmd_name in pretty_commands:
            result = integration_cli_runner.invoke(cli, cmd_args)

            assert result.exit_code == 0, f"{cmd_name} failed: {result.output}"

            # Pretty format should contain human-readable content
            assert len(result.output.strip()) > 0
            # Should not be JSON
            assert not result.output.strip().startswith("[")
            assert not result.output.strip().startswith("{")

            rate_limit_aware_delay()

    def _cleanup_comment(self, comment_url: str):
        """Clean up a test comment after the test.

        Args:
            comment_url: URL of the comment to delete.
        """
        import contextlib

        with contextlib.suppress(Exception):
            # Extract comment ID from URL and delete
            # This is a best-effort cleanup - if it fails, it's not critical
            subprocess.run(
                ["gh", "api", "--method", "DELETE", comment_url],
                capture_output=True,
                timeout=10,
            )


@pytest.mark.integration
@pytest.mark.real_api
class TestWorkflowEdgeCases:
    """Test edge cases and boundary conditions in workflows."""

    def test_workflow_with_empty_pr(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
    ):
        """Test workflow behavior with a PR that has no review comments."""
        pr_number = verify_test_pr_exists["number"]

        # Fetch from PR (might have no comments)
        result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        assert result.exit_code == 0

        threads_data = json.loads(result.output)

        # Should return empty list if no comments
        assert isinstance(threads_data, list)
        # Length can be 0 or more - both are valid states

    def test_workflow_state_persistence(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        rate_limit_aware_delay,
    ):
        """Test that workflow state changes persist across multiple commands."""
        pr_number = verify_test_pr_exists["number"]

        # Fetch current state
        initial_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        assert initial_result.exit_code == 0
        initial_threads = json.loads(initial_result.output)

        rate_limit_aware_delay()

        # Fetch again - should get same results (assuming no external changes)
        second_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        assert second_result.exit_code == 0
        second_threads = json.loads(second_result.output)

        # Thread count should be stable
        assert len(initial_threads) == len(second_threads)

        # Thread IDs should be consistent
        initial_ids = {t["thread_id"] for t in initial_threads}
        second_ids = {t["thread_id"] for t in second_threads}
        assert initial_ids == second_ids

    def test_concurrent_workflow_operations(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        rate_limit_aware_delay,
        skip_if_slow,
    ):
        """Test behavior when multiple operations might be happening concurrently."""
        pr_number = verify_test_pr_exists["number"]

        # Perform multiple fetch operations in quick succession
        results = []

        for _i in range(3):
            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )
            results.append(result)
            rate_limit_aware_delay(0.5)  # Small delay between requests

        # All should succeed
        for i, result in enumerate(results):
            assert result.exit_code == 0, f"Fetch {i+1} failed: {result.output}"

            # Should return valid JSON
            try:
                threads = json.loads(result.output)
                assert isinstance(threads, list)
            except json.JSONDecodeError:
                pytest.fail(f"Fetch {i+1} returned invalid JSON: {result.output}")
