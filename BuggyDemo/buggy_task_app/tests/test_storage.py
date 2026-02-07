"""
Tests for the storage module.
"""

import os
import json
import pytest
from buggy_task_app.storage import (
    save_tasks,
    load_tasks,
    delete_save_file,
    export_tasks_csv,
    get_file_size,
    backup_save_file,
)


TEST_FILE = "test_tasks_temp.dat"
TEST_CSV = "test_tasks_temp.csv"


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test files after each test."""
    yield
    for f in [TEST_FILE, TEST_CSV, TEST_FILE + ".bak"]:
        if os.path.exists(f):
            os.remove(f)


def _sample_tasks():
    return [
        {"id": 1, "title": "Task A", "completed": False, "priority": "low", "created_at": "01-01-2026 10:00:00"},
        {"id": 2, "title": "Task B", "completed": True, "priority": "high", "created_at": "01-01-2026 11:00:00"},
    ]


class TestSaveTasks:
    def test_save_creates_file(self):
        tasks = _sample_tasks()
        save_tasks(tasks, TEST_FILE)
        assert os.path.exists(TEST_FILE)

    def test_save_file_contains_json(self):
        tasks = _sample_tasks()
        save_tasks(tasks, TEST_FILE)
        with open(TEST_FILE, "r") as f:
            data = json.load(f)
        assert "tasks" in data
        assert len(data["tasks"]) == 2

    def test_save_empty_list(self):
        save_tasks([], TEST_FILE)
        with open(TEST_FILE, "r") as f:
            data = json.load(f)
        assert data["tasks"] == []

    def test_save_returns_filepath(self):
        result = save_tasks([], TEST_FILE)
        assert result == TEST_FILE


class TestLoadTasks:
    def test_load_saved_tasks(self):
        tasks = _sample_tasks()
        save_tasks(tasks, TEST_FILE)
        loaded = load_tasks(TEST_FILE)
        assert len(loaded) == 2
        assert loaded[0]["title"] == "Task A"

    def test_load_nonexistent_file(self):
        result = load_tasks("nonexistent_file.dat")
        assert result == []

    def test_load_preserves_completed_status(self):
        tasks = _sample_tasks()
        save_tasks(tasks, TEST_FILE)
        loaded = load_tasks(TEST_FILE)
        assert loaded[1]["completed"] is True


class TestDeleteSaveFile:
    def test_delete_existing_file(self):
        save_tasks([], TEST_FILE)
        result = delete_save_file(TEST_FILE)
        assert result is True
        assert not os.path.exists(TEST_FILE)

    def test_delete_nonexistent_file(self):
        result = delete_save_file("no_such_file.dat")
        assert result is False


class TestExportCSV:
    def test_export_creates_csv(self):
        tasks = _sample_tasks()
        result = export_tasks_csv(tasks, TEST_CSV)
        assert result is True
        assert os.path.exists(TEST_CSV)

    def test_csv_has_header(self):
        tasks = _sample_tasks()
        export_tasks_csv(tasks, TEST_CSV)
        with open(TEST_CSV, "r") as f:
            header = f.readline().strip()
        assert "id" in header
        assert "title" in header


class TestGetFileSize:
    def test_size_of_existing_file(self):
        save_tasks(_sample_tasks(), TEST_FILE)
        size = get_file_size(TEST_FILE)
        assert size > 0

    def test_size_of_nonexistent_file(self):
        size = get_file_size("nonexistent.dat")
        assert size == 0


class TestBackup:
    def test_backup_creates_bak_file(self):
        save_tasks(_sample_tasks(), TEST_FILE)
        backup_path = backup_save_file(TEST_FILE)
        assert backup_path is not None
        assert os.path.exists(backup_path)

    def test_backup_nonexistent_file(self):
        result = backup_save_file("nonexistent.dat")
        assert result is None
