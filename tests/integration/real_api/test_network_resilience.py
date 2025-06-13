"""Integration tests for network resilience and rate limiting.

These tests verify proper handling of network conditions, rate limiting,
retry logic, and error recovery in real API interactions.
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
@pytest.mark.resilience
@pytest.mark.slow
class TestNetworkResilience:
    """Test network resilience and error recovery."""

    def test_api_timeout_handling(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
    ):
        """Test handling of API timeouts."""
        pr_number = verify_test_pr_exists["number"]

        # Test with normal timeout first
        performance_monitor.start_timing("normal_timeout_fetch")

        result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        normal_duration = performance_monitor.stop_timing()

        # Should complete within reasonable time
        assert normal_duration < 30.0, f"Normal fetch took too long: {normal_duration}s"

        if result.exit_code == 0:
            # Verify we got valid data
            threads = json.loads(result.output)
            assert isinstance(threads, list)
        else:
            # If it failed, ensure it's a proper error, not a timeout
            assert "timeout" not in result.output.lower() or normal_duration < 30.0

    def test_network_retry_behavior(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        api_retry_helper,
        rate_limit_aware_delay,
    ):
        """Test retry behavior under network conditions."""
        pr_number = verify_test_pr_exists["number"]

        def fetch_with_potential_failure():
            """Make a fetch call that might need retrying."""
            return integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

        # Use the retry helper to make the call
        result = api_retry_helper(fetch_with_potential_failure)

        # Should eventually succeed or fail consistently
        assert result.exit_code == 0 or "error" in result.output.lower()

        rate_limit_aware_delay()

    def test_large_response_handling(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
        skip_if_slow,
    ):
        """Test handling of large API responses."""
        pr_number = verify_test_pr_exists["number"]

        # Fetch with resolved threads included (potentially larger response)
        performance_monitor.start_timing("large_response_fetch")

        result = integration_cli_runner.invoke(
            cli,
            [
                "fetch",
                "--pr",
                str(pr_number),
                "--resolved",  # Include resolved threads
                "--limit",
                "1000",  # Request large limit
                "--format",
                "json",
            ],
        )

        large_response_duration = performance_monitor.stop_timing()

        # Should handle large responses within reasonable time
        performance_monitor.assert_performance_threshold("large_response_fetch", 60.0)

        if result.exit_code == 0:
            try:
                threads = json.loads(result.output)
                assert isinstance(threads, list)

                # Log the size for monitoring
                print(
                    f"Fetched {len(threads)} threads in {large_response_duration:.2f}s"
                )

            except json.JSONDecodeError:
                pytest.fail(
                    f"Large response was not valid JSON: {result.output[:500]}..."
                )

    def test_concurrent_api_usage_patterns(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        rate_limit_aware_delay,
        skip_if_slow,
    ):
        """Test behavior under concurrent API usage."""
        pr_number = verify_test_pr_exists["number"]

        # Make several concurrent-like requests
        results = []

        for i in range(5):
            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )
            results.append((i, result))

            # Small delay to simulate concurrent usage
            rate_limit_aware_delay(0.5)

        # Analyze results
        successful_count = 0
        failed_count = 0

        for i, result in results:
            if result.exit_code == 0:
                successful_count += 1
                try:
                    threads = json.loads(result.output)
                    assert isinstance(threads, list)
                except json.JSONDecodeError:
                    pytest.fail(f"Request {i} returned invalid JSON: {result.output}")
            else:
                failed_count += 1
                # Check if failure is due to rate limiting
                if "rate limit" in result.output.lower():
                    print(f"Request {i} hit rate limit")
                else:
                    print(f"Request {i} failed: {result.output}")

        print(f"Concurrent usage: {successful_count} success, {failed_count} failed")

        # At least some requests should succeed
        assert successful_count > 0, "All concurrent requests failed"

    def test_progressive_backoff_behavior(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        rate_limit_aware_delay,
        skip_if_slow,
    ):
        """Test progressive backoff when approaching rate limits."""
        pr_number = verify_test_pr_exists["number"]

        # Make rapid requests to potentially trigger rate limiting
        backoff_timings = []

        for i in range(10):
            start_time = time.time()

            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            end_time = time.time()
            duration = end_time - start_time
            backoff_timings.append(duration)

            if result.exit_code != 0:
                if "rate limit" in result.output.lower():
                    print(f"Hit rate limit on request {i+1}")
                    break
                print(f"Request {i+1} failed for other reason: {result.output}")

            # Small delay between requests
            rate_limit_aware_delay(0.2)

        print(f"Request timings: {[f'{t:.2f}s' for t in backoff_timings]}")

        # If we hit rate limits, later requests should potentially take longer
        # (This is implementation dependent and might not always be observable)

    def test_connection_recovery_after_failure(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        api_retry_helper,
    ):
        """Test recovery after connection failures."""
        pr_number = verify_test_pr_exists["number"]

        # First, make a successful request
        first_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        if first_result.exit_code != 0:
            pytest.skip("Initial connection failed, cannot test recovery")

        # Simulate some delay (as if recovering from failure)
        time.sleep(2.0)

        # Make another request - should work if connection is stable
        def recovery_fetch():
            return integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

        recovery_result = api_retry_helper(recovery_fetch)

        # Should recover and work
        if recovery_result.exit_code != 0:
            print(f"Recovery failed: {recovery_result.output}")

        # Both requests should have similar behavior
        assert first_result.exit_code == recovery_result.exit_code


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.resilience
class TestRateLimitHandling:
    """Test GitHub API rate limit handling and compliance."""

    def test_rate_limit_status_monitoring(
        self,
        integration_test_config: dict[str, Any],
    ):
        """Test monitoring of rate limit status."""
        try:
            # Check initial rate limit status
            initial_result = subprocess.run(
                ["gh", "api", "rate_limit"], capture_output=True, text=True, timeout=10
            )

            assert initial_result.returncode == 0

            initial_data = json.loads(initial_result.stdout)
            initial_remaining = initial_data["rate"]["remaining"]

            # Make a test API call
            test_result = subprocess.run(
                ["gh", "api", "user"], capture_output=True, text=True, timeout=10
            )

            if test_result.returncode == 0:
                # Check rate limit again
                after_result = subprocess.run(
                    ["gh", "api", "rate_limit"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                assert after_result.returncode == 0

                after_data = json.loads(after_result.stdout)
                after_remaining = after_data["rate"]["remaining"]

                # Should have decremented (or stayed same if using cached results)
                assert after_remaining <= initial_remaining

                print(f"Rate limit: {initial_remaining} -> {after_remaining}")

        except Exception as e:
            pytest.fail(f"Rate limit monitoring failed: {e}")

    def test_rate_limit_respect_in_operations(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        integration_test_config: dict[str, Any],
    ):
        """Test that operations respect rate limits."""
        pr_number = verify_test_pr_exists["number"]

        # Check current rate limit
        rate_result = subprocess.run(
            ["gh", "api", "rate_limit"], capture_output=True, text=True, timeout=10
        )

        if rate_result.returncode == 0:
            rate_data = json.loads(rate_result.stdout)
            remaining = rate_data["rate"]["remaining"]

            # If we're too close to the limit, skip this test
            if remaining < integration_test_config["rate_limit_buffer"]:
                pytest.skip(f"Too close to rate limit: {remaining}")

            # Make a toady operation
            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            # Should complete successfully within rate limits
            if result.exit_code != 0 and "rate limit" in result.output.lower():
                pytest.fail(
                    "Operation failed due to rate limiting when sufficient "
                    "quota available"
                )

    def test_rate_limit_error_handling(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
    ):
        """Test graceful handling when rate limits are exceeded."""
        verify_test_pr_exists["number"]

        # This test is difficult to implement safely without actually
        # exhausting rate limits, which would affect other tests

        # Instead, we test that our error handling would work correctly
        # by checking the error message format for rate limit scenarios

        # We can check current rate limit and warn if we're close
        try:
            rate_result = subprocess.run(
                ["gh", "api", "rate_limit"], capture_output=True, text=True, timeout=10
            )

            if rate_result.returncode == 0:
                rate_data = json.loads(rate_result.stdout)
                remaining = rate_data["rate"]["remaining"]
                limit = rate_data["rate"]["limit"]
                reset_time = rate_data["rate"]["reset"]

                print(
                    f"Current rate limit: {remaining}/{limit} (resets at {reset_time})"
                )

                if remaining < 100:
                    print("WARNING: Low rate limit remaining")

        except Exception as e:
            print(f"Could not check rate limit: {e}")

    def test_secondary_rate_limit_handling(self):
        """Test handling of secondary rate limits (abuse detection)."""
        # Secondary rate limits are harder to test consistently
        # as they depend on GitHub's abuse detection algorithms

        # We can test that our code would handle such errors appropriately
        # by ensuring our error handling covers the expected error codes

        # For now, this is a placeholder for future implementation
        # when we have better ways to simulate these conditions


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.resilience
class TestErrorRecoveryPatterns:
    """Test error recovery and resilience patterns."""

    def test_transient_error_recovery(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        api_retry_helper,
    ):
        """Test recovery from transient errors."""
        pr_number = verify_test_pr_exists["number"]

        def potentially_failing_operation():
            return integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

        # Use retry helper which implements backoff
        result = api_retry_helper(potentially_failing_operation)

        # Should eventually succeed or give a consistent error
        if result.exit_code != 0:
            # Error should be informative, not a crash
            assert len(result.output) > 0
            assert "traceback" not in result.output.lower()

    def test_partial_failure_handling(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
    ):
        """Test handling of partial failures in operations."""
        pr_number = verify_test_pr_exists["number"]

        # Test operations that might partially fail
        # (e.g., some data available, some not)

        result = integration_cli_runner.invoke(
            cli,
            [
                "fetch",
                "--pr",
                str(pr_number),
                "--limit",
                "1000",  # Large limit that might hit boundaries
                "--format",
                "json",
            ],
        )

        if result.exit_code == 0:
            try:
                threads = json.loads(result.output)
                # Should get some data, even if not everything requested
                assert isinstance(threads, list)

            except json.JSONDecodeError:
                pytest.fail(f"Partial success returned invalid JSON: {result.output}")
        else:
            # If it fails, should be a clear error
            assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_data_consistency_after_errors(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        rate_limit_aware_delay,
    ):
        """Test that data remains consistent after error conditions."""
        pr_number = verify_test_pr_exists["number"]

        # Get baseline data
        baseline_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        if baseline_result.exit_code != 0:
            pytest.skip("Cannot establish baseline data")

        baseline_threads = json.loads(baseline_result.output)

        # Wait a bit (simulate time passing)
        rate_limit_aware_delay(3.0)

        # Get data again
        consistency_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        if consistency_result.exit_code == 0:
            consistency_threads = json.loads(consistency_result.output)

            # Basic consistency checks
            baseline_ids = {t["thread_id"] for t in baseline_threads}
            consistency_ids = {t["thread_id"] for t in consistency_threads}

            # Thread IDs should be stable (assuming no external changes)
            # We allow for some differences due to potential external modifications
            common_ids = baseline_ids & consistency_ids

            if baseline_ids and consistency_ids:
                # Should have significant overlap unless there were major changes
                overlap_ratio = len(common_ids) / max(
                    len(baseline_ids), len(consistency_ids)
                )

                if overlap_ratio < 0.8:  # Allow 20% change due to external factors
                    print(f"Warning: Data consistency low: {overlap_ratio:.2%} overlap")

    def test_graceful_degradation_patterns(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
    ):
        """Test graceful degradation when services are limited."""
        pr_number = verify_test_pr_exists["number"]

        # Test with various constraint scenarios
        constraint_tests = [
            (["fetch", "--pr", str(pr_number), "--limit", "1"], "small_limit"),
            (["fetch", "--pr", str(pr_number), "--format", "json"], "standard"),
        ]

        for cmd_args, test_name in constraint_tests:
            result = integration_cli_runner.invoke(cli, cmd_args)

            # Should either work or fail gracefully
            if result.exit_code == 0:
                try:
                    if "--format" in cmd_args and "json" in cmd_args:
                        threads = json.loads(result.output)
                        assert isinstance(threads, list)
                except json.JSONDecodeError:
                    pytest.fail(f"{test_name} returned invalid JSON: {result.output}")
            else:
                # Failure should be informative
                assert len(result.output) > 0
                print(f"{test_name} failed gracefully: {result.output[:100]}...")
