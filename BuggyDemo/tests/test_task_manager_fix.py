import pytest
from buggy_task_app.tasks import TaskManager

def test_task_id_uniqueness_after_deletion():
    manager = TaskManager()

    # Add a task and check its ID
    task1 = manager.add_task("Task 1")
    assert task1["id"] == 1

    # Add another task and check its ID
    task2 = manager.add_task("Task 2")
    assert task2["id"] == 2

    # Delete the first task
    manager.delete_task(task1["id"])

    # Add a new task and check its ID
    task3 = manager.add_task("Task 3")
    assert task3["id"] == 3  # Should not reuse ID 1
