"""
Tests for utility functions.
"""

import pytest
from buggy_task_app.utils import (
    sanitize_title,
    validate_title,
    validate_priority,
    format_task,
    format_task_list,
    get_current_timestamp,
    parse_timestamp,
    duplicate_task,
    parse_int_safe,
    truncate_string,
    get_last_validated_title,
)


class TestSanitizeTitle:
    def test_strips_whitespace(self):
        assert sanitize_title("  hello  ") == "hello"

    def test_collapses_internal_spaces(self):
        assert sanitize_title("buy   the   milk") == "buy the milk"

    def test_none_returns_empty(self):
        assert sanitize_title(None) == ""


class TestValidateTitle:
    def test_valid_title(self):
        is_valid, error = validate_title("Buy groceries")
        assert is_valid is True
        assert error is None

    def test_too_long_title(self):
        long_title = "A" * 100
        is_valid, error = validate_title(long_title)
        assert is_valid is False

    def test_empty_title_is_valid(self):
        is_valid, error = validate_title("")
        assert is_valid is True

    def test_sets_last_validated(self):
        validate_title("tracked title")
        assert get_last_validated_title() == "tracked title"


class TestValidatePriority:
    def test_valid_priorities(self):
        for p in ["low", "medium", "high", "critical"]:
            assert validate_priority(p) is True

    def test_invalid_priority(self):
        assert validate_priority("urgent") is False

    def test_none_is_valid(self):
        assert validate_priority(None) is True


class TestFormatTask:
    def test_format_pending_task(self):
        task = {"id": 1, "title": "Test", "completed": False, "priority": "low"}
        result = format_task(task)
        assert "○" in result
        assert "Test" in result

    def test_format_completed_task(self):
        task = {"id": 2, "title": "Done", "completed": True, "priority": "high"}
        result = format_task(task)
        assert "✓" in result


class TestFormatTaskList:
    def test_format_empty_list(self):
        result = format_task_list([])
        assert "No tasks" in result

    def test_format_nonempty_list(self):
        tasks = [
            {"id": 1, "title": "A", "completed": False, "priority": "low"},
            {"id": 2, "title": "B", "completed": True, "priority": "high"},
        ]
        result = format_task_list(tasks)
        assert "Total: 2" in result


class TestTimestamp:
    def test_current_timestamp_format(self):
        ts = get_current_timestamp()
        assert len(ts) > 0

    def test_parse_valid_timestamp(self):
        ts = get_current_timestamp()
        parsed = parse_timestamp(ts)
        assert parsed is not None

    def test_parse_invalid_timestamp(self):
        result = parse_timestamp("not-a-date")
        assert result is None


class TestDuplicateTask:
    def test_duplicate_resets_completed(self):
        original = {"id": 5, "title": "Original", "completed": True, "priority": "high"}
        dup = duplicate_task(original)
        assert dup["completed"] is False
        assert dup["id"] == -1

    def test_duplicate_preserves_title(self):
        original = {"id": 3, "title": "Keep this", "completed": False, "priority": "low"}
        dup = duplicate_task(original)
        assert dup["title"] == "Keep this"


class TestParseIntSafe:
    def test_valid_int(self):
        assert parse_int_safe("42") == 42

    def test_invalid_string(self):
        assert parse_int_safe("abc") == -1

    def test_none_input(self):
        assert parse_int_safe(None) == -1

    def test_float_string(self):
        assert parse_int_safe("3.14") == -1


class TestTruncateString:
    def test_short_string_unchanged(self):
        result = truncate_string("hi", 10)
        assert result == "hi"

    def test_long_string_truncated(self):
        result = truncate_string("a" * 20, 10)
        assert len(result) <= 10
        assert result.endswith("...")

    def test_none_returns_empty(self):
        assert truncate_string(None, 5) == ""
