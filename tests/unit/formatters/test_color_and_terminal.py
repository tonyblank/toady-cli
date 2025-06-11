"""Tests for color support and terminal-specific formatting behavior.

This module tests color output in different terminal environments,
ANSI escape code handling, and terminal-specific edge cases.
"""

import os
import time
from datetime import datetime
from unittest.mock import patch

import pytest

from toady.models import Comment, ReviewThread
from toady.pretty_formatter import PrettyFormatter


class TestColorSupport:
    """Test color support in different environments."""

    def test_color_enabled_basic(self):
        """Test basic color functionality when enabled."""
        formatter = PrettyFormatter(use_colors=True)

        # Test style method directly
        styled_text = formatter._style("test", "red", bold=True)

        # Should be different from unstyled text
        assert styled_text != "test"

        # Should work without raising exceptions
        assert isinstance(styled_text, str)

    def test_color_disabled_basic(self):
        """Test color functionality when disabled."""
        formatter = PrettyFormatter(use_colors=False)

        # Test style method directly
        styled_text = formatter._style("test", "red", bold=True)

        # Should return original text unchanged
        assert styled_text == "test"

    @patch("click.style")
    def test_color_click_integration(self, mock_style):
        """Test integration with click.style."""
        mock_style.return_value = "\x1b[31mtest\x1b[0m"  # Red text

        formatter = PrettyFormatter(use_colors=True)
        result = formatter._style("test", "red", bold=True)

        # Should call click.style with correct parameters
        mock_style.assert_called_once_with("test", fg="red", bold=True)
        assert result == "\x1b[31mtest\x1b[0m"

    @patch("click.style")
    def test_color_disabled_no_click_call(self, mock_style):
        """Test that click.style is not called when colors are disabled."""
        formatter = PrettyFormatter(use_colors=False)
        result = formatter._style("test", "red", bold=True)

        # Should not call click.style
        mock_style.assert_not_called()
        assert result == "test"

    def test_status_colors(self):
        """Test status color mapping."""
        formatter = PrettyFormatter(use_colors=True)

        # Test all status colors
        status_color_map = {
            "RESOLVED": "green",
            "OUTDATED": "yellow",
            "PENDING": "red",
            "UNRESOLVED": "red",
            "UNKNOWN_STATUS": "white",
        }

        for status, expected_color in status_color_map.items():
            color = formatter._get_status_color(status)
            assert color == expected_color

    def test_status_emojis(self):
        """Test status emoji mapping."""
        formatter = PrettyFormatter()

        # Test emoji mapping
        assert formatter._get_status_emoji("RESOLVED") == "✅"
        assert formatter._get_status_emoji("OUTDATED") == "⏰"
        assert formatter._get_status_emoji("UNRESOLVED") == "❌"
        assert formatter._get_status_emoji("PENDING") == "❌"

        # Test outdated override
        assert formatter._get_status_emoji("RESOLVED", is_outdated=True) == "⏰"
        assert formatter._get_status_emoji("UNRESOLVED", is_outdated=True) == "⏰"


class TestAnsiCodeHandling:
    """Test ANSI escape code handling."""

    def test_strip_ansi_codes(self):
        """Test stripping ANSI escape codes."""
        formatter = PrettyFormatter()

        test_cases = [
            ("plain text", "plain text"),
            ("\x1b[31mred text\x1b[0m", "red text"),
            ("\x1b[1m\x1b[32mbold green\x1b[0m\x1b[0m", "bold green"),
            ("\x1b[38;5;196mvery red\x1b[0m", "very red"),
            ("\x1b[48;5;21mblue background\x1b[0m", "blue background"),
            (
                "mixed \x1b[31mred\x1b[0m and \x1b[32mgreen\x1b[0m text",
                "mixed red and green text",
            ),
            ("", ""),  # Empty string
        ]

        for input_text, expected_output in test_cases:
            result = formatter._strip_ansi_codes(input_text)
            assert result == expected_output

    def test_display_width_calculation(self):
        """Test display width calculation with ANSI codes."""
        formatter = PrettyFormatter()

        test_cases = [
            ("hello", 5),
            ("\x1b[31mhello\x1b[0m", 5),  # Red "hello"
            ("\x1b[1m\x1b[32mbold\x1b[0m\x1b[0m", 4),  # Bold green "bold"
            ("", 0),  # Empty string
            ("🎉", 2),  # Emoji (typically 2 display columns)
            ("\x1b[31m🎉\x1b[0m", 2),  # Colored emoji
        ]

        for text, expected_width in test_cases:
            width = formatter._display_width(text)
            # Allow some variance for emoji handling across different systems
            if "🎉" in text:
                assert width >= 1 and width <= 2
            else:
                assert width == expected_width

    def test_pad_to_width_with_ansi(self):
        """Test padding text with ANSI codes."""
        formatter = PrettyFormatter()

        # Test padding plain text
        result = formatter._pad_to_width("hello", 10)
        assert len(result) == 10
        assert result == "hello     "

        # Test padding text with ANSI codes
        styled_text = "\x1b[31mhello\x1b[0m"  # Red "hello"
        result = formatter._pad_to_width(styled_text, 10)

        # Should preserve ANSI codes and pad correctly
        assert styled_text in result
        assert formatter._display_width(result) == 10

        # Test text already at target width
        result = formatter._pad_to_width("hello", 5)
        assert result == "hello"

        # Test text longer than target (should not truncate)
        result = formatter._pad_to_width("hello world", 5)
        assert result == "hello world"

    def test_ansi_regex_pattern(self):
        """Test ANSI escape sequence regex pattern comprehensively."""
        formatter = PrettyFormatter()

        # Test various ANSI escape sequences
        ansi_sequences = [
            "\x1b[0m",  # Reset
            "\x1b[1m",  # Bold
            "\x1b[31m",  # Red foreground
            "\x1b[42m",  # Green background
            "\x1b[38;5;196m",  # 256-color foreground
            "\x1b[48;2;255;0;0m",  # True color background
            "\x1b[2J",  # Clear screen
            "\x1b[H",  # Cursor home
            "\x1b[?25h",  # Show cursor
            "\x1b[K",  # Clear line
        ]

        for sequence in ansi_sequences:
            text_with_ansi = f"before{sequence}after"
            result = formatter._strip_ansi_codes(text_with_ansi)
            assert result == "beforeafter"
            assert sequence not in result


class TestTerminalEnvironments:
    """Test behavior in different terminal environments."""

    def test_different_term_variables(self):
        """Test behavior with different TERM environment variables."""
        term_configs = [
            "xterm-256color",
            "xterm",
            "screen-256color",
            "tmux-256color",
            "dumb",
            "vt100",
            "",  # Empty TERM
        ]

        for term_value in term_configs:
            with patch.dict(os.environ, {"TERM": term_value}, clear=False):
                # Formatter should work regardless of TERM value
                formatter = PrettyFormatter(use_colors=True)

                # Should not raise exceptions
                result = formatter.format_primitive("test")
                assert isinstance(result, str)

                # Should handle styling
                styled = formatter._style("test", "red")
                assert isinstance(styled, str)

    def test_no_term_variable(self):
        """Test behavior when TERM variable is not set."""
        env_without_term = dict(os.environ)
        if "TERM" in env_without_term:
            del env_without_term["TERM"]

        with patch.dict(os.environ, env_without_term, clear=True):
            formatter = PrettyFormatter(use_colors=True)

            # Should still work without TERM
            result = formatter.format_primitive("test")
            assert isinstance(result, str)

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="TTY tests may not work in CI environment",
    )
    def test_tty_detection(self):
        """Test behavior with TTY detection."""
        formatter = PrettyFormatter(use_colors=True)

        # Should work regardless of TTY status
        result = formatter.format_primitive("test")
        assert isinstance(result, str)

    def test_color_in_pipes_and_redirects(self):
        """Test color behavior when output is piped or redirected."""
        # Simulate non-TTY environment
        with patch("sys.stdout.isatty", return_value=False):
            formatter = PrettyFormatter(use_colors=True)

            # Should still respect the use_colors setting
            styled = formatter._style("test", "red")
            assert isinstance(styled, str)

    def test_windows_terminal_compatibility(self):
        """Test Windows terminal compatibility."""
        with patch("sys.platform", "win32"):
            formatter = PrettyFormatter(use_colors=True)

            # Should work on Windows
            result = formatter.format_primitive("test")
            assert isinstance(result, str)

            styled = formatter._style("test", "blue")
            assert isinstance(styled, str)


class TestColorInComplexFormatting:
    """Test color support in complex formatting scenarios."""

    def test_colored_thread_formatting(self):
        """Test color support in thread formatting."""
        formatter = PrettyFormatter(use_colors=True)

        comment = Comment(
            comment_id="IC_COLOR",
            content="Colored comment content",
            author="color_user",
            author_name="Color User",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_COLOR",
            url="https://github.com/test/comment",
        )

        thread = ReviewThread(
            thread_id="RT_COLOR",
            title="Colored thread",
            created_at=datetime(2024, 1, 15, 9, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="RESOLVED",
            author="color_reviewer",
            comments=[comment],
            file_path="src/colored.py",
            line=42,
            is_outdated=False,
        )

        result = formatter.format_threads([thread])

        # Should contain the basic content
        assert "Colored thread" in result
        assert "Colored comment content" in result
        assert "color_reviewer" in result

        # Result should be formatted (might contain ANSI codes)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_colored_table_formatting(self):
        """Test color support in table formatting."""
        formatter = PrettyFormatter(use_colors=True)

        # Data that should be formatted as a table
        table_data = [
            {"id": 1, "status": "RESOLVED", "author": "user1"},
            {"id": 2, "status": "UNRESOLVED", "author": "user2"},
            {"id": 3, "status": "OUTDATED", "author": "user3"},
        ]

        result = formatter.format_array(table_data)

        # Should be formatted as table
        assert "|" in result
        assert "status" in result
        assert "author" in result
        assert "RESOLVED" in result

        # Should handle different status colors
        assert isinstance(result, str)

    def test_colored_error_formatting(self):
        """Test color support in error formatting."""
        formatter = PrettyFormatter(use_colors=True)

        error_data = {
            "message": "Something went wrong",
            "type": "ValidationError",
            "code": 500,
            "details": {"field": "value", "reason": "invalid"},
        }

        result = formatter.format_error(error_data)

        # Should contain error content
        assert "Something went wrong" in result
        assert "ValidationError" in result
        assert "❌ Error" in result

        # Should be properly formatted
        assert isinstance(result, str)
        assert len(result) > 0

    def test_color_consistency_across_methods(self):
        """Test that color settings are consistent across all formatting methods."""
        formatter_with_colors = PrettyFormatter(use_colors=True)
        formatter_without_colors = PrettyFormatter(use_colors=False)

        # Test data
        test_object = {"key": "value", "number": 42}
        test_array = [1, 2, 3]
        test_primitive = "test string"

        # With colors enabled
        obj_result = formatter_with_colors.format_object(test_object)
        array_result = formatter_with_colors.format_array(test_array)
        prim_result = formatter_with_colors.format_primitive(test_primitive)

        # Without colors
        obj_result_no_color = formatter_without_colors.format_object(test_object)
        array_result_no_color = formatter_without_colors.format_array(test_array)
        prim_result_no_color = formatter_without_colors.format_primitive(test_primitive)

        # All should produce valid output
        for result in [
            obj_result,
            array_result,
            prim_result,
            obj_result_no_color,
            array_result_no_color,
            prim_result_no_color,
        ]:
            assert isinstance(result, str)
            assert len(result) > 0

    def test_unicode_with_colors(self):
        """Test Unicode content with color formatting."""
        formatter = PrettyFormatter(use_colors=True)

        unicode_data = {
            "emoji": "🎉🚀🌟",
            "accented": "ñáéíóú",
            "chinese": "中文测试",
            "arabic": "العربية",
        }

        result = formatter.format_object(unicode_data)

        # Should handle Unicode content
        assert "🎉🚀🌟" in result
        assert "ñáéíóú" in result
        assert "中文测试" in result
        assert "العربية" in result

        # Should be valid output
        assert isinstance(result, str)

    def test_nested_color_formatting(self):
        """Test color formatting in nested structures."""
        formatter = PrettyFormatter(use_colors=True)

        nested_data = {
            "level1": {
                "level2": {
                    "status": "RESOLVED",
                    "items": [
                        {"id": 1, "active": True},
                        {"id": 2, "active": False},
                    ],
                }
            }
        }

        result = formatter.format_object(nested_data)

        # Should handle nested structures with colors
        assert "level1" in result
        assert "level2" in result
        assert "RESOLVED" in result
        assert isinstance(result, str)


class TestColorPerformance:
    """Test performance impact of color formatting."""

    def test_color_vs_no_color_performance(self):
        """Test performance difference between colored and non-colored output."""

        # Create test data
        threads = []
        for i in range(50):
            comment = Comment(
                comment_id=f"IC_{i}",
                content=f"Comment {i} content",
                author=f"user_{i}",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                parent_id=None,
                thread_id=f"RT_{i}",
            )

            thread = ReviewThread(
                thread_id=f"RT_{i}",
                title=f"Thread {i}",
                created_at=datetime(2024, 1, 15, 9, 0, 0),
                updated_at=datetime(2024, 1, 15, 10, 0, 0),
                status="RESOLVED" if i % 2 == 0 else "UNRESOLVED",
                author=f"reviewer_{i}",
                comments=[comment],
                is_outdated=False,
            )
            threads.append(thread)

        # Test with colors
        formatter_with_colors = PrettyFormatter(use_colors=True)
        start_time = time.time()
        result_with_colors = formatter_with_colors.format_threads(threads)
        time_with_colors = time.time() - start_time

        # Test without colors
        formatter_without_colors = PrettyFormatter(use_colors=False)
        start_time = time.time()
        result_without_colors = formatter_without_colors.format_threads(threads)
        time_without_colors = time.time() - start_time

        # Both should complete in reasonable time
        assert time_with_colors < 5.0
        assert time_without_colors < 5.0

        # Both should produce valid output
        assert isinstance(result_with_colors, str)
        assert isinstance(result_without_colors, str)
        assert len(result_with_colors) > 0
        assert len(result_without_colors) > 0

        print(f"With colors: {time_with_colors:.3f}s")
        print(f"Without colors: {time_without_colors:.3f}s")

    def test_color_with_large_content(self):
        """Test color formatting with large content."""
        formatter = PrettyFormatter(use_colors=True)

        # Create large content
        large_content = "Large content line. " * 1000

        large_comment = Comment(
            comment_id="IC_LARGE_COLOR",
            content=large_content,
            author="large_user",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            parent_id=None,
            thread_id="RT_LARGE_COLOR",
        )

        thread = ReviewThread(
            thread_id="RT_LARGE_COLOR",
            title="Thread with large colored content",
            created_at=datetime(2024, 1, 15, 9, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0),
            status="UNRESOLVED",
            author="large_reviewer",
            comments=[large_comment],
            is_outdated=False,
        )

        # Should handle large content with colors
        start_time = time.time()
        result = formatter.format_threads([thread])
        format_time = time.time() - start_time

        assert format_time < 10.0  # Should complete within 10 seconds
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Thread with large colored content" in result
