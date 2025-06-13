"""Integration tests for performance monitoring and benchmarking.

These tests measure and validate performance characteristics of real API
interactions, including response times, memory usage, and scalability.
"""

import json
import time
from typing import Any

from click.testing import CliRunner
import pytest

from toady.cli import cli

try:
    import psutil
except ImportError:
    psutil = None


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Test performance characteristics of API operations."""

    def test_fetch_performance_baseline(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
    ):
        """Establish performance baseline for fetch operations."""
        pr_number = verify_test_pr_exists["number"]

        # Warm-up call (exclude from timing)
        warmup_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        if warmup_result.exit_code != 0:
            pytest.skip(f"Warmup fetch failed: {warmup_result.output}")

        # Measure multiple fetch operations
        timings = []
        thread_counts = []

        for i in range(5):
            performance_monitor.start_timing(f"fetch_baseline_{i}")

            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            duration = performance_monitor.stop_timing()
            timings.append(duration)

            assert result.exit_code == 0, f"Fetch {i+1} failed: {result.output}"

            threads = json.loads(result.output)
            thread_counts.append(len(threads))

            # Small delay between calls
            time.sleep(1.0)

        # Calculate statistics
        avg_time = sum(timings) / len(timings)
        max_time = max(timings)
        min_time = min(timings)
        avg_threads = sum(thread_counts) / len(thread_counts)

        print("Fetch performance baseline:")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Min/Max time: {min_time:.2f}s / {max_time:.2f}s")
        print(f"  Average threads: {avg_threads:.1f}")

        # Performance assertions
        assert avg_time < 10.0, f"Average fetch time too slow: {avg_time:.2f}s"
        assert max_time < 20.0, f"Maximum fetch time too slow: {max_time:.2f}s"

        # Consistency check
        time_variance = max_time - min_time
        assert (
            time_variance < 15.0
        ), f"Timing too inconsistent: {time_variance:.2f}s variance"

    def test_memory_usage_patterns(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        skip_if_slow,
    ):
        """Monitor memory usage patterns during operations."""
        if psutil is None:
            pytest.skip("psutil not available for memory monitoring")

        pr_number = verify_test_pr_exists["number"]

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_measurements = [initial_memory]

        # Perform multiple operations while monitoring memory
        for i in range(10):
            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(current_memory)

            if result.exit_code != 0:
                print(f"Operation {i+1} failed: {result.output}")
                break

            time.sleep(0.5)

        # Analyze memory usage
        max_memory = max(memory_measurements)
        final_memory = memory_measurements[-1]
        memory_growth = final_memory - initial_memory

        print("Memory usage analysis:")
        print(f"  Initial: {initial_memory:.1f} MB")
        print(f"  Maximum: {max_memory:.1f} MB")
        print(f"  Final: {final_memory:.1f} MB")
        print(f"  Growth: {memory_growth:.1f} MB")

        # Memory usage assertions
        assert (
            max_memory < initial_memory + 500
        ), f"Memory usage too high: {max_memory:.1f} MB"
        assert (
            memory_growth < 100
        ), f"Memory leak detected: {memory_growth:.1f} MB growth"

    def test_large_pr_performance(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
        skip_if_slow,
    ):
        """Test performance with large PRs (high thread count)."""
        pr_number = verify_test_pr_exists["number"]

        # Test with maximum limit to stress test
        performance_monitor.start_timing("large_pr_fetch")

        result = integration_cli_runner.invoke(
            cli,
            [
                "fetch",
                "--pr",
                str(pr_number),
                "--resolved",  # Include resolved threads for larger dataset
                "--limit",
                "1000",
                "--format",
                "json",
            ],
        )

        duration = performance_monitor.stop_timing()

        if result.exit_code == 0:
            threads = json.loads(result.output)
            thread_count = len(threads)

            print("Large PR performance:")
            print(f"  Threads fetched: {thread_count}")
            print(f"  Time taken: {duration:.2f}s")

            if thread_count > 0:
                print(f"  Threads per second: {thread_count / duration:.1f}")

                # Performance assertions based on data size
                if thread_count > 100:
                    # For large datasets, allow more time
                    performance_monitor.assert_performance_threshold(
                        "large_pr_fetch", 60.0
                    )
                elif thread_count > 10:
                    # Medium datasets
                    performance_monitor.assert_performance_threshold(
                        "large_pr_fetch", 30.0
                    )
                else:
                    # Small datasets should be fast
                    performance_monitor.assert_performance_threshold(
                        "large_pr_fetch", 15.0
                    )
        else:
            # If fetch failed, still check that it failed quickly
            assert duration < 30.0, f"Failed fetch took too long: {duration:.2f}s"

    def test_concurrent_performance_impact(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
        skip_if_slow,
    ):
        """Test performance impact of concurrent operations."""
        pr_number = verify_test_pr_exists["number"]

        # Single operation baseline
        performance_monitor.start_timing("single_operation")

        single_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        single_duration = performance_monitor.stop_timing()

        if single_result.exit_code != 0:
            pytest.skip(f"Single operation failed: {single_result.output}")

        # Multiple rapid operations
        rapid_timings = []

        for i in range(5):
            performance_monitor.start_timing(f"rapid_operation_{i}")

            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            timing = performance_monitor.stop_timing()
            rapid_timings.append(timing)

            if result.exit_code != 0:
                print(f"Rapid operation {i+1} failed: {result.output}")

            # Minimal delay to simulate rapid usage
            time.sleep(0.2)

        # Analyze performance impact
        avg_rapid_time = sum(rapid_timings) / len(rapid_timings)
        slowdown_factor = (
            avg_rapid_time / single_duration if single_duration > 0 else 1.0
        )

        print("Concurrent performance analysis:")
        print(f"  Single operation: {single_duration:.2f}s")
        print(f"  Average rapid operation: {avg_rapid_time:.2f}s")
        print(f"  Slowdown factor: {slowdown_factor:.2f}x")

        # Performance should not degrade excessively
        assert (
            slowdown_factor < 3.0
        ), f"Excessive slowdown under load: {slowdown_factor:.2f}x"

    def test_cache_performance_impact(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
        temp_cache_dir,
    ):
        """Test performance impact of caching mechanisms."""
        pr_number = verify_test_pr_exists["number"]

        # First call (cold cache)
        performance_monitor.start_timing("cold_cache_fetch")

        first_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        cold_duration = performance_monitor.stop_timing()

        if first_result.exit_code != 0:
            pytest.skip(f"Cold cache fetch failed: {first_result.output}")

        # Wait a moment
        time.sleep(1.0)

        # Second call (potentially warm cache)
        performance_monitor.start_timing("warm_cache_fetch")

        second_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        warm_duration = performance_monitor.stop_timing()

        if second_result.exit_code == 0:
            # Compare results
            first_threads = json.loads(first_result.output)
            second_threads = json.loads(second_result.output)

            # Results should be consistent
            assert len(first_threads) == len(
                second_threads
            ), "Cache returned different data"

            # Performance analysis
            speedup = cold_duration / warm_duration if warm_duration > 0 else 1.0

            print("Cache performance analysis:")
            print(f"  Cold cache: {cold_duration:.2f}s")
            print(f"  Warm cache: {warm_duration:.2f}s")
            print(f"  Speedup: {speedup:.2f}x")

            # Cache should not significantly slow things down
            assert (
                warm_duration <= cold_duration * 2.0
            ), "Cache caused significant slowdown"

    def test_network_latency_impact(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
        network_simulation,
    ):
        """Test performance under various network conditions."""
        pr_number = verify_test_pr_exists["number"]

        # Baseline measurement
        performance_monitor.start_timing("baseline_fetch")

        baseline_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        baseline_duration = performance_monitor.stop_timing()

        if baseline_result.exit_code != 0:
            pytest.skip(f"Baseline fetch failed: {baseline_result.output}")

        # Test with simulated slow connection
        # (Note: This is limited simulation - real network testing would require
        # network manipulation tools)

        network_simulation.simulate_slow_connection(1.0)

        performance_monitor.start_timing("slow_network_fetch")

        slow_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        slow_duration = performance_monitor.stop_timing()

        if slow_result.exit_code == 0:
            print("Network latency impact:")
            print(f"  Baseline: {baseline_duration:.2f}s")
            print(f"  With simulated delay: {slow_duration:.2f}s")

            # Results should still be consistent
            baseline_threads = json.loads(baseline_result.output)
            slow_threads = json.loads(slow_result.output)

            assert len(baseline_threads) == len(
                slow_threads
            ), "Network delay affected data consistency"


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.performance
class TestScalabilityPatterns:
    """Test scalability characteristics and patterns."""

    def test_thread_count_scaling(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
    ):
        """Test performance scaling with different thread counts."""
        pr_number = verify_test_pr_exists["number"]

        # Test with different limits
        limits = [1, 5, 10, 50, 100]
        scaling_data = []

        for limit in limits:
            performance_monitor.start_timing(f"scaling_limit_{limit}")

            result = integration_cli_runner.invoke(
                cli,
                [
                    "fetch",
                    "--pr",
                    str(pr_number),
                    "--limit",
                    str(limit),
                    "--format",
                    "json",
                ],
            )

            duration = performance_monitor.stop_timing()

            if result.exit_code == 0:
                threads = json.loads(result.output)
                actual_count = len(threads)

                scaling_data.append(
                    {
                        "limit": limit,
                        "actual_count": actual_count,
                        "duration": duration,
                        "threads_per_second": (
                            actual_count / duration if duration > 0 else 0
                        ),
                    }
                )

                print(f"Limit {limit}: {actual_count} threads in {duration:.2f}s")
            else:
                print(f"Limit {limit} failed: {result.output}")

            time.sleep(1.0)  # Rate limiting courtesy

        # Analyze scaling patterns
        if len(scaling_data) >= 2:
            # Check if performance scales reasonably
            first = scaling_data[0]
            last = scaling_data[-1]

            if last["actual_count"] > first["actual_count"]:
                efficiency_ratio = (
                    last["threads_per_second"] / first["threads_per_second"]
                )

                print(f"Scaling efficiency: {efficiency_ratio:.2f}")

                # Performance should not degrade dramatically with scale
                assert (
                    efficiency_ratio > 0.1
                ), f"Poor scaling efficiency: {efficiency_ratio:.2f}"

    def test_data_processing_efficiency(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        performance_monitor,
    ):
        """Test efficiency of data processing operations."""
        pr_number = verify_test_pr_exists["number"]

        # Fetch data for processing analysis
        performance_monitor.start_timing("data_fetch_for_processing")

        result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        fetch_duration = performance_monitor.stop_timing()

        if result.exit_code != 0:
            pytest.skip(f"Data fetch failed: {result.output}")

        threads = json.loads(result.output)

        if not threads:
            pytest.skip("No threads available for processing analysis")

        # Analyze data structure complexity
        total_comments = sum(len(thread.get("comments", [])) for thread in threads)
        total_chars = sum(
            len(comment.get("content", ""))
            for thread in threads
            for comment in thread.get("comments", [])
        )

        print("Data processing analysis:")
        print(f"  Threads: {len(threads)}")
        print(f"  Comments: {total_comments}")
        print(f"  Characters: {total_chars}")
        print(f"  Processing time: {fetch_duration:.2f}s")

        if total_chars > 0:
            chars_per_second = total_chars / fetch_duration
            print(f"  Processing rate: {chars_per_second:.0f} chars/sec")

            # Reasonable processing efficiency
            assert (
                chars_per_second > 1000
            ), f"Processing too slow: {chars_per_second:.0f} chars/sec"

    def test_resource_utilization_patterns(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        skip_if_slow,
    ):
        """Test CPU and memory utilization patterns."""
        if psutil is None:
            pytest.skip("psutil not available for resource monitoring")

        pr_number = verify_test_pr_exists["number"]

        process = psutil.Process()

        # Baseline measurements
        initial_cpu_percent = process.cpu_percent()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform resource-intensive operation
        start_time = time.time()

        result = integration_cli_runner.invoke(
            cli,
            [
                "fetch",
                "--pr",
                str(pr_number),
                "--resolved",
                "--limit",
                "1000",
                "--format",
                "json",
            ],
        )

        operation_duration = time.time() - start_time

        # Measure resource usage during operation
        peak_cpu_percent = process.cpu_percent()
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB

        print("Resource utilization analysis:")
        print(f"  Operation duration: {operation_duration:.2f}s")
        print(f"  CPU usage: {initial_cpu_percent:.1f}% -> {peak_cpu_percent:.1f}%")
        print(f"  Memory usage: {initial_memory:.1f} MB -> {peak_memory:.1f} MB")

        if result.exit_code == 0:
            threads = json.loads(result.output)
            print(f"  Threads processed: {len(threads)}")

            # Resource efficiency checks
            memory_increase = peak_memory - initial_memory

            if len(threads) > 0:
                memory_per_thread = memory_increase / len(threads)
                print(f"  Memory per thread: {memory_per_thread:.2f} MB")

                # Memory usage should be reasonable
                assert (
                    memory_per_thread < 10
                ), f"Excessive memory per thread: {memory_per_thread:.2f} MB"

        # CPU usage should be reasonable (not constantly maxed out)
        # Note: This is environment-dependent
        if peak_cpu_percent > 90:
            print("Warning: High CPU usage detected")

    def test_long_running_stability(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        skip_if_slow,
    ):
        """Test stability over extended operation periods."""
        pr_number = verify_test_pr_exists["number"]

        # Run multiple operations over time to test stability
        operation_count = 20
        success_count = 0
        failure_count = 0
        timings = []

        for i in range(operation_count):
            start_time = time.time()

            result = integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

            duration = time.time() - start_time
            timings.append(duration)

            if result.exit_code == 0:
                success_count += 1
                try:
                    threads = json.loads(result.output)
                    assert isinstance(threads, list)
                except json.JSONDecodeError:
                    failure_count += 1
                    print(f"Operation {i+1}: JSON decode failed")
            else:
                failure_count += 1
                print(f"Operation {i+1}: Command failed")

            # Delay between operations
            time.sleep(2.0)

        # Analyze stability
        success_rate = success_count / operation_count
        avg_time = sum(timings) / len(timings)
        time_variance = max(timings) - min(timings)

        print("Long-running stability analysis:")
        print(f"  Operations: {operation_count}")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Time variance: {time_variance:.2f}s")

        # Stability assertions
        assert success_rate >= 0.8, f"Poor success rate: {success_rate:.1%}"
        assert time_variance < 30.0, f"Excessive timing variance: {time_variance:.2f}s"
