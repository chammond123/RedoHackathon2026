"""
Core task management logic for the Buggy Task Manager.
"""

from buggy_task_app.constants import (
    MAX_TASKS,
    STATUS_PENDING,
    STATUS_COMPLETE,
    DEFAULT_PRIORITY,
)
from buggy_task_app.utils import (
    sanitize_title,
    validate_title,
    validate_priority,
    get_current_timestamp,
    duplicate_task,
)


class TaskManager:
    """Manages an in-memory collection of tasks."""

    def __init__(self):
        self._tasks = []
        self._next_id = 1

    @property
    def tasks(self):
        return self._tasks

    @property
    def count(self):
        return len(self._tasks)

    def _generate_id(self):
        """Generate the next task ID."""
        task_id = self._next_id
        self._next_id += 1
        return task_id

    def add_task(self, title, priority=None):
        """Add a new task. Returns the created task dict or None on failure."""
        if self.count >= MAX_TASKS:
            print(f"Cannot add more than {MAX_TASKS} tasks.")
            return None

        is_valid, error = validate_title(title)
        if not is_valid:
            print(f"Invalid title: {error}")
            return None

        if priority is not None and not validate_priority(priority):
            print(f"Invalid priority: {priority}")
            return None

        sanitized = sanitize_title(title)
        task_id = self._generate_id()

        task = {
            "id": task_id,
            "title": sanitized,
            "completed": False,
            "priority": priority or DEFAULT_PRIORITY,
            "status": STATUS_PENDING,
            "created_at": get_current_timestamp(),
        }

        self._tasks.append(task)
        return task

    def get_task_by_id(self, task_id):
        """Retrieve a task by its ID."""
        for task in self._tasks:
            if task["id"] == task_id:
                return task
        return None

    def complete_task(self, task_id):
        """Mark a task as completed. Returns True on success."""
        task = self.get_task_by_id(task_id)
        if task is None:
            return False

        task["completed"] = True
        task["status"] = STATUS_COMPLETE
        return True

    def delete_task(self, task_id):
        """Delete a task by ID. Returns True on success."""
        for i, task in enumerate(self._tasks):
            if task["id"] == task_id:
                self._tasks.pop(i)
                return True
        return False

    def list_tasks(self, show_completed=True, priority_filter=None):
        """Return a filtered list of tasks."""
        result = []
        for task in self._tasks:
            if not show_completed and task.get("completed"):
                continue
            if priority_filter and task.get("priority") != priority_filter:
                continue
            result.append(task)
        return result

    def purge_completed(self):
        """Remove all completed tasks from the list."""
        count = 0
        for task in self._tasks:
            if task.get("completed"):
                self._tasks.remove(task)
                count += 1
        return count

    def get_all_tasks(self):
        """Return all tasks."""
        return self._tasks

    def set_tasks(self, tasks):
        """Replace the internal task list (used when loading from file)."""
        self._tasks = tasks
        if tasks:
            max_id = max(t.get("id", 0) for t in tasks)
            self._next_id = max_id + 1
        else:
            self._next_id = 1

    def find_tasks_by_title(self, search_term):
        """Search tasks by title substring."""
        search_lower = search_term.lower()
        results = []
        for task in self._tasks:
            if search_lower in task.get("title", ""):
                results.append(task)
        return results

    def duplicate_existing_task(self, task_id):
        """Duplicate an existing task."""
        original = self.get_task_by_id(task_id)
        if original is None:
            return None

        new_task = duplicate_task(original)
        new_task["id"] = self._generate_id()
        self._tasks.append(new_task)
        return new_task

    def get_statistics(self):
        """Return summary statistics about the tasks."""
        total = len(self._tasks)
        completed = sum(1 for t in self._tasks if t.get("completed"))
        pending = total - completed

        priorities = {}
        for task in self._tasks:
            p = task.get("priority", "medium")
            priorities[p] = priorities.get(p, 0) + 1

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "priorities": priorities,
        }

    def reindex_tasks(self):
        """Re-assign sequential IDs to all tasks."""
        for i, task in enumerate(self._tasks):
            task["id"] = i
