"""Performance and memory tests for formatters.

This module contains performance benchmarks and memory usage tests for all formatters
to ensure they can handle large datasets efficiently without memory leaks.
"""

import gc
import os
import time
from datetime import datetime

import pytest

from toady.format_interfaces import FormatterError
from toady.json_formatter import JSONFormatter
from toady.models import Comment, ReviewThread
from toady.pretty_formatter import PrettyFormatter

# Skip performance tests if running in CI or if psutil is not available
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

SKIP_PERFORMANCE = (
    os.environ.get("CI") == "true"
    or os.environ.get("SKIP_PERFORMANCE") == "true"
    or not PSUTIL_AVAILABLE
)


class TestFormatterPerformance:
    """Test performance characteristics of formatters."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance without colors for consistent performance."""
        return PrettyFormatter(use_colors=False)

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Performance tests skipped")
    def test_large_thread_collection_performance(
        self, json_formatter, pretty_formatter
    ):
        """Test performance with large collections of threads."""
        # Create large collection of threads
        threads = []
        for i in range(500):  # 500 threads
            comments = []
            for j in range(3):  # 3 comments per thread
                comment = Comment(
                    comment_id=f"IC_{i}_{j}",
                    content=f"Comment {j} in thread {i}. "
                    + "Lorem ipsum dolor sit amet. " * 10,
                    author=f"user_{j}",
                    created_at=datetime(2024, 1, 15, 10, j, 0),
                    updated_at=datetime(2024, 1, 15, 10, j, 0),
                    parent_id=None,
                    thread_id=f"RT_{i}",
                )
                comments.append(comment)

            thread = ReviewThread(
                thread_id=f"RT_{i}",
                title=f"Review thread {i} with some longer title content",
                created_at=datetime(2024, 1, 15, 9, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 30, 0),
                status="RESOLVED" if i % 2 == 0 else "UNRESOLVED",
                author=f"reviewer_{i % 10}",
                comments=comments,
                file_path=f"src/module_{i % 20}/file_{i}.py",
                line=i + 10,
                is_outdated=i % 10 == 0,
            )
            threads.append(thread)

        # Test JSON formatter performance
        start_time = time.time()
        json_result = json_formatter.format_threads(threads)
        json_time = time.time() - start_time

        print(f"JSON formatting {len(threads)} threads took {json_time:.3f} seconds")
        assert json_time < 10.0  # Should complete within 10 seconds
        assert len(json_result) > 0
        assert "RT_0" in json_result
        assert "RT_499" in json_result

        # Test pretty formatter performance
        start_time = time.time()
        pretty_result = pretty_formatter.format_threads(threads)
        pretty_time = time.time() - start_time

        print(
            f"Pretty formatting {len(threads)} threads took {pretty_time:.3f} seconds"
        )
        assert pretty_time < 30.0  # Pretty formatting can take longer
        assert len(pretty_result) > 0
        assert "Review thread 0" in pretty_result
        assert "Review thread 499" in pretty_result

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Performance tests skipped")
    def test_large_comment_collection_performance(
        self, json_formatter, pretty_formatter
    ):
        """Test performance with large collections of comments."""
        # Create large collection of comments
        comments = []
        for i in range(1000):  # 1000 comments
            comment = Comment(
                comment_id=f"IC_{i}",
                content=f"Comment {i}. " + "Some content text. " * 20,
                author=f"user_{i % 50}",
                author_name=f"User {i % 50}",
                created_at=datetime(2024, 1, 15, 10, i % 60, 0),
                updated_at=datetime(2024, 1, 15, 10, i % 60, 0),
                parent_id=f"IC_{i-1}" if i > 0 and i % 10 != 0 else None,
                thread_id=f"RT_{i // 10}",
                url=f"https://github.com/test/repo/pull/1#issuecomment-{i}",
            )
            comments.append(comment)

        # Test JSON formatter performance
        start_time = time.time()
        json_result = json_formatter.format_comments(comments)
        json_time = time.time() - start_time

        print(f"JSON formatting {len(comments)} comments took {json_time:.3f} seconds")
        assert json_time < 5.0  # Should complete within 5 seconds
        assert len(json_result) > 0

        # Test pretty formatter performance
        start_time = time.time()
        pretty_result = pretty_formatter.format_comments(comments)
        pretty_time = time.time() - start_time

        print(
            f"Pretty formatting {len(comments)} comments took {pretty_time:.3f} seconds"
        )
        assert pretty_time < 15.0  # Pretty formatting can take longer
        assert len(pretty_result) > 0

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Performance tests skipped")
    def test_deep_nesting_performance(self, json_formatter, pretty_formatter):
        """Test performance with deeply nested structures."""
        # Create deeply nested dictionary
        deep_dict = {}
        current = deep_dict

        for i in range(100):  # 100 levels deep
            current[f"level_{i}"] = {
                "data": f"Level {i} data with some content",
                "index": i,
                "nested": {},
            }
            current = current[f"level_{i}"]["nested"]

        current["final"] = "reached the bottom"

        # Test JSON formatter performance
        start_time = time.time()
        json_result = json_formatter.format_object(deep_dict)
        json_time = time.time() - start_time

        print(f"JSON formatting deep structure took {json_time:.3f} seconds")
        assert json_time < 5.0
        assert "level_0" in json_result
        assert "final" in json_result

        # Test pretty formatter performance
        start_time = time.time()
        pretty_result = pretty_formatter.format_object(deep_dict)
        pretty_time = time.time() - start_time

        print(f"Pretty formatting deep structure took {pretty_time:.3f} seconds")
        assert pretty_time < 10.0
        assert "level_0" in pretty_result

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Performance tests skipped")
    def test_wide_table_performance(self, pretty_formatter):
        """Test performance with wide table formatting."""
        # Create wide table data
        wide_data = []
        for i in range(100):
            row = {}
            for j in range(20):  # 20 columns
                row[f"column_{j}"] = f"data_{i}_{j}_with_some_longer_content"
            wide_data.append(row)

        # Test pretty formatter table performance
        start_time = time.time()
        result = pretty_formatter.format_array(wide_data)
        format_time = time.time() - start_time

        print(f"Pretty formatting wide table took {format_time:.3f} seconds")
        assert format_time < 10.0
        assert "|" in result  # Should be formatted as table
        assert "column_0" in result
        assert "column_19" in result

    def test_repeated_formatting_performance(self, json_formatter, pretty_formatter):
        """Test performance when formatting repeatedly."""
        # Create test data
        thread = ReviewThread(
            thread_id="RT_PERF",
            title="Performance test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="UNRESOLVED",
            author="perf_user",
            comments=[],
            is_outdated=False,
        )

        # Test repeated JSON formatting
        start_time = time.time()
        for _ in range(1000):  # Format 1000 times
            json_formatter.format_threads([thread])
        json_time = time.time() - start_time

        print(f"JSON formatting 1000 times took {json_time:.3f} seconds")
        assert json_time < 5.0  # Should be fast for repeated operations

        # Test repeated pretty formatting
        start_time = time.time()
        for _ in range(100):  # Format 100 times (pretty is slower)
            pretty_formatter.format_threads([thread])
        pretty_time = time.time() - start_time

        print(f"Pretty formatting 100 times took {pretty_time:.3f} seconds")
        assert pretty_time < 10.0


class TestFormatterMemoryUsage:
    """Test memory usage characteristics of formatters."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False)

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_memory_usage_large_dataset(self, json_formatter, pretty_formatter):
        """Test memory usage with large datasets."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create large dataset
        large_threads = []
        for i in range(200):  # 200 threads
            comments = []
            for j in range(5):  # 5 comments each
                comment = Comment(
                    comment_id=f"IC_{i}_{j}",
                    content="Large comment content. " * 50,  # ~1KB per comment
                    author=f"user_{j}",
                    created_at=datetime(2024, 1, 15, 10, j, 0),
                    updated_at=datetime(2024, 1, 15, 10, j, 0),
                    parent_id=None,
                    thread_id=f"RT_{i}",
                )
                comments.append(comment)

            thread = ReviewThread(
                thread_id=f"RT_{i}",
                title=f"Thread {i}",
                created_at=datetime(2024, 1, 15, 9, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="UNRESOLVED",
                author=f"reviewer_{i}",
                comments=comments,
                is_outdated=False,
            )
            large_threads.append(thread)

        # Format with JSON formatter
        json_result = json_formatter.format_threads(large_threads)
        json_memory = process.memory_info().rss

        # Format with pretty formatter
        pretty_result = pretty_formatter.format_threads(large_threads)
        pretty_memory = process.memory_info().rss

        # Clean up
        del json_result, pretty_result, large_threads
        gc.collect()

        final_memory = process.memory_info().rss

        print(f"Initial memory: {initial_memory / 1024 / 1024:.1f} MB")
        print(f"After JSON: {json_memory / 1024 / 1024:.1f} MB")
        print(f"After Pretty: {pretty_memory / 1024 / 1024:.1f} MB")
        print(f"Final memory: {final_memory / 1024 / 1024:.1f} MB")

        # Memory usage should be reasonable
        max_increase = max(json_memory - initial_memory, pretty_memory - initial_memory)
        assert max_increase < 200 * 1024 * 1024  # Less than 200MB increase

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_memory_leak_detection(self, json_formatter, pretty_formatter):
        """Test for memory leaks in repeated operations."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create test data
        test_thread = ReviewThread(
            thread_id="RT_LEAK_TEST",
            title="Memory leak test thread",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="UNRESOLVED",
            author="leak_tester",
            comments=[],
            is_outdated=False,
        )

        # Perform many operations
        for i in range(100):
            # Create some data
            threads = [test_thread] * 10

            # Format with both formatters
            json_result = json_formatter.format_threads(threads)
            pretty_result = pretty_formatter.format_threads(threads)

            # Clean up explicitly
            del json_result, pretty_result, threads

            # Force garbage collection every 10 iterations
            if i % 10 == 0:
                gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        memory_mb = memory_increase / 1024 / 1024
        print(f"Memory increase after 100 iterations: {memory_mb:.1f} MB")

        # Should not have significant memory growth (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_memory_usage_circular_references(self, json_formatter, pretty_formatter):
        """Test memory usage when handling circular references."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create circular reference
        circular_data = {"key": "value"}
        circular_data["self"] = circular_data

        # Should handle circular references without memory explosion
        for _ in range(10):
            json_result = json_formatter.format_object(circular_data)
            pretty_result = pretty_formatter.format_object(circular_data)

            del json_result, pretty_result
            gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        memory_mb = memory_increase / 1024 / 1024
        print(f"Memory increase with circular refs: {memory_mb:.1f} MB")

        # Should not have excessive memory growth
        assert memory_increase < 10 * 1024 * 1024  # Less than 10MB


class TestFormatterStressTests:
    """Stress tests for formatters under extreme conditions."""

    @pytest.fixture
    def json_formatter(self):
        """JSON formatter instance."""
        return JSONFormatter()

    @pytest.fixture
    def pretty_formatter(self):
        """Pretty formatter instance."""
        return PrettyFormatter(use_colors=False)

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Stress tests skipped")
    def test_extremely_large_comment_content(self, json_formatter, pretty_formatter):
        """Test formatters with extremely large comment content."""
        # Create comment with very large content
        large_content = "This is a very long comment. " * 10000  # ~300KB

        comment = Comment(
            comment_id="IC_LARGE",
            content=large_content,
            author="large_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_LARGE",
        )

        thread = ReviewThread(
            thread_id="RT_LARGE",
            title="Thread with large comment",
            created_at=datetime(2024, 1, 15, 9, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="UNRESOLVED",
            author="large_reviewer",
            comments=[comment],
            is_outdated=False,
        )

        # Should handle large content without crashing
        start_time = time.time()
        json_result = json_formatter.format_threads([thread])
        json_time = time.time() - start_time

        assert json_time < 10.0
        assert len(json_result) > 0
        assert "IC_LARGE" in json_result

        start_time = time.time()
        pretty_result = pretty_formatter.format_threads([thread])
        pretty_time = time.time() - start_time

        assert pretty_time < 20.0
        assert len(pretty_result) > 0
        assert "Thread with large comment" in pretty_result

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Stress tests skipped")
    def test_many_small_objects(self, json_formatter, pretty_formatter):
        """Test formatters with many small objects."""
        # Create many small objects
        small_objects = []
        for i in range(10000):  # 10,000 small objects
            obj = {
                "id": i,
                "name": f"obj_{i}",
                "active": i % 2 == 0,
                "value": i * 1.5,
            }
            small_objects.append(obj)

        # Test formatting many small objects
        start_time = time.time()
        json_result = json_formatter.format_array(small_objects)
        json_time = time.time() - start_time

        print(f"JSON formatting 10,000 objects took {json_time:.3f} seconds")
        assert json_time < 15.0
        assert len(json_result) > 0

        # Pretty formatter might take longer with table formatting
        start_time = time.time()
        pretty_result = pretty_formatter.format_array(small_objects)
        pretty_time = time.time() - start_time

        print(f"Pretty formatting 10,000 objects took {pretty_time:.3f} seconds")
        assert pretty_time < 60.0  # Give more time for table formatting
        assert len(pretty_result) > 0

    def test_malformed_data_stress(self, json_formatter, pretty_formatter):
        """Test formatters with various malformed data under stress."""
        malformed_objects = []

        # Create various malformed objects
        class BadObject1:
            def to_dict(self):
                raise Exception("Failed to serialize")

        class BadObject2:
            def __init__(self):
                self.circular = self

        class BadObject3:
            def __str__(self):
                raise Exception("Failed to stringify")

        for i in range(100):
            if i % 3 == 0:
                malformed_objects.append(BadObject1())
            elif i % 3 == 1:
                malformed_objects.append(BadObject2())
            else:
                malformed_objects.append(BadObject3())

        # JSON formatter should raise FormatterError for bad objects
        with pytest.raises(FormatterError):
            json_formatter.format_array(malformed_objects)

        # Pretty formatter should handle malformed objects gracefully
        pretty_result = pretty_formatter.format_array(malformed_objects)
        assert isinstance(pretty_result, str)
        assert len(pretty_result) > 0

    @pytest.mark.skipif(SKIP_PERFORMANCE, reason="Stress tests skipped")
    def test_unicode_stress(self, json_formatter, pretty_formatter):
        """Test formatters with heavy Unicode content."""
        unicode_strings = [
            "🎉" * 1000,  # Many emojis
            "中文测试" * 500,  # Chinese characters
            "العربية" * 500,  # Arabic text
            "ñáéíóú" * 1000,  # Accented characters
            "🏳️‍🌈" * 100,  # Complex emojis with modifiers
        ]

        unicode_objects = []
        for i, unicode_str in enumerate(unicode_strings):
            obj = {
                "id": i,
                "content": unicode_str,
                "type": "unicode_test",
            }
            unicode_objects.append(obj)

        # Should handle Unicode content efficiently
        start_time = time.time()
        json_result = json_formatter.format_array(unicode_objects)
        json_time = time.time() - start_time

        assert json_time < 5.0
        assert len(json_result) > 0

        start_time = time.time()
        pretty_result = pretty_formatter.format_array(unicode_objects)
        pretty_time = time.time() - start_time

        assert pretty_time < 10.0
        assert len(pretty_result) > 0
