"""
Tests for the CLI app module.
"""

import pytest
from unittest.mock import patch
from buggy_task_app.app import manager, handle_add_task, handle_save, handle_load


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the global manager before each test."""
    manager._tasks.clear()
    manager._next_id = 1
    yield


class TestHandleAddTask:
    @patch("builtins.input", side_effect=["Test task", ""])
    def test_add_task_via_cli(self, mock_input):
        handle_add_task()
        assert manager.count == 1
        assert manager.tasks[0]["title"] == "Test task"

    @patch("builtins.input", side_effect=["", ""])
    def test_add_empty_title(self, mock_input):
        handle_add_task()
        assert manager.count == 1

    @patch("builtins.input", side_effect=["Priority task", "high"])
    def test_add_with_priority(self, mock_input):
        handle_add_task()
        assert manager.tasks[0]["priority"] == "high"


class TestHandleSaveLoad:
    @patch("builtins.input", return_value="test_cli_save.dat")
    def test_save_and_load_roundtrip(self, mock_input):
        manager.add_task("Saved task")
        handle_save()

        manager._tasks.clear()
        assert manager.count == 0

        with patch("builtins.input", return_value="test_cli_save.dat"):
            handle_load()

        assert manager.count == 1

    @patch("builtins.input", return_value="")
    def test_save_default_file(self, mock_input):
        manager.add_task("Default save")
        handle_save()

    @patch("builtins.input", return_value="nonexistent_cli.dat")
    def test_load_missing_file(self, mock_input):
        handle_load()
        assert manager.count == 0


class TestGlobalManagerState:
    def test_manager_is_shared(self):
        from buggy_task_app.app import manager as m1
        from buggy_task_app.app import manager as m2
        assert m1 is m2

    def test_manager_starts_empty(self):
        assert manager.count == 0
