import pytest
from buggy_task_app.tasks import TaskManager

def test_purge_completed_tasks():
    # Setup: Create a TaskManager instance and add tasks
    manager = TaskManager()
    
    # Add tasks and mark some as completed
    task1 = manager.add_task("Task 1")
    task2 = manager.add_task("Task 2")
    task3 = manager.add_task("Task 3")
    
    manager.complete_task(task1["id"])
    manager.complete_task(task2["id"])
    
    # Ensure tasks are marked as completed
    assert manager.get_task_by_id(task1["id"])["completed"] is True
    assert manager.get_task_by_id(task2["id"])["completed"] is True
    assert manager.get_task_by_id(task3["id"])["completed"] is False
    
    # Act: Purge completed tasks
    manager.purge_completed()
    
    # Assert: Only the non-completed task should remain
    remaining_tasks = manager.get_all_tasks()
    assert len(remaining_tasks) == 1
    assert remaining_tasks[0]["id"] == task3["id"]
    assert remaining_tasks[0]["completed"] is False

    # Act: Purge again to ensure idempotency
    manager.purge_completed()
    
    # Assert: The state should remain unchanged
    remaining_tasks_after_second_purge = manager.get_all_tasks()
    assert len(remaining_tasks_after_second_purge) == 1
    assert remaining_tasks_after_second_purge[0]["id"] == task3["id"]
    assert remaining_tasks_after_second_purge[0]["completed"] is False
