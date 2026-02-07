"""
Tests for the TaskManager class.
"""

import pytest
from buggy_task_app.tasks import TaskManager


@pytest.fixture
def manager():
    """Provide a fresh TaskManager for each test."""
    return TaskManager()


class TestAddTask:
    def test_add_single_task(self, manager):
        task = manager.add_task("Buy groceries")
        assert task is not None
        assert task["title"] == "Buy groceries"
        assert task["completed"] is False
        assert manager.count == 1

    def test_add_multiple_tasks_have_unique_ids(self, manager):
        t1 = manager.add_task("Task A")
        t2 = manager.add_task("Task B")
        t3 = manager.add_task("Task C")
        assert t1["id"] != t2["id"]
        assert t2["id"] != t3["id"]

    def test_add_task_with_priority(self, manager):
        task = manager.add_task("Urgent fix", priority="high")
        assert task["priority"] == "high"

    def test_add_task_invalid_priority(self, manager):
        task = manager.add_task("Bad priority", priority="ultra")
        assert task is None

    def test_add_task_default_priority(self, manager):
        task = manager.add_task("Normal task")
        assert task["priority"] == "medium"

    def test_add_task_increments_count(self, manager):
        manager.add_task("One")
        manager.add_task("Two")
        assert manager.count == 2


class TestGetTask:
    def test_get_existing_task(self, manager):
        added = manager.add_task("Find me")
        found = manager.get_task_by_id(added["id"])
        assert found is not None
        assert found["title"] == "Find me"

    def test_get_nonexistent_task(self, manager):
        found = manager.get_task_by_id(999)
        assert found is None


class TestCompleteTask:
    def test_complete_existing_task(self, manager):
        task = manager.add_task("Finish report")
        result = manager.complete_task(task["id"])
        assert result is True

    def test_complete_nonexistent_task(self, manager):
        result = manager.complete_task(42)
        assert result is False

    def test_completed_task_has_status(self, manager):
        task = manager.add_task("Check status")
        manager.complete_task(task["id"])
        updated = manager.get_task_by_id(task["id"])
        assert updated["status"] == "complete"


class TestDeleteTask:
    def test_delete_existing_task(self, manager):
        task = manager.add_task("Remove me")
        result = manager.delete_task(task["id"])
        assert result is True
        assert manager.count == 0

    def test_delete_nonexistent_task(self, manager):
        result = manager.delete_task(999)
        assert result is False

    def test_delete_then_add_has_correct_ids(self, manager):
        t1 = manager.add_task("First")
        t2 = manager.add_task("Second")
        manager.delete_task(t1["id"])
        t3 = manager.add_task("Third")
        assert t3["id"] == 2


class TestListTasks:
    def test_list_all_tasks(self, manager):
        manager.add_task("A")
        manager.add_task("B")
        result = manager.list_tasks()
        assert len(result) == 2

    def test_list_pending_only(self, manager):
        manager.add_task("Pending")
        t = manager.add_task("Done")
        manager.complete_task(t["id"])
        result = manager.list_tasks(show_completed=False)
        assert len(result) == 1

    def test_list_filter_by_priority(self, manager):
        manager.add_task("Low task", priority="low")
        manager.add_task("High task", priority="high")
        result = manager.list_tasks(priority_filter="high")
        assert len(result) == 1
        assert result[0]["priority"] == "high"


class TestPurgeCompleted:
    def test_purge_removes_completed(self, manager):
        manager.add_task("Keep")
        t = manager.add_task("Remove")
        manager.complete_task(t["id"])
        purged = manager.purge_completed()
        assert purged >= 1
        assert manager.count == 1

    def test_purge_with_no_completed(self, manager):
        manager.add_task("Stay")
        purged = manager.purge_completed()
        assert purged == 0


class TestStatistics:
    def test_statistics_counts(self, manager):
        manager.add_task("A")
        manager.add_task("B")
        t = manager.add_task("C")
        manager.complete_task(t["id"])
        stats = manager.get_statistics()
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["pending"] == 2


class TestFindTasks:
    def test_find_by_title(self, manager):
        manager.add_task("Buy milk")
        manager.add_task("Buy bread")
        manager.add_task("Read book")
        results = manager.find_tasks_by_title("Buy")
        assert len(results) == 2

    def test_find_case_insensitive(self, manager):
        manager.add_task("Important Meeting")
        results = manager.find_tasks_by_title("important")
        assert len(results) == 1


class TestReindex:
    def test_reindex_sequential(self, manager):
        manager.add_task("A")
        manager.add_task("B")
        manager.add_task("C")
        manager.reindex_tasks()
        ids = [t["id"] for t in manager.tasks]
        assert ids == [1, 2, 3]
