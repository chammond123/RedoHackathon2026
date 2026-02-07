import unittest
from buggy_task_app.tasks import TaskManager

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.manager = TaskManager()

    def test_complete_task(self):
        # Add a task to complete
        task = self.manager.add_task("Test Task")
        task_id = task["id"]

        # Complete the task
        result = self.manager.complete_task(task_id)

        # Verify the task is marked as completed
        self.assertTrue(result)
        self.assertTrue(self.manager.get_task_by_id(task_id)["completed"])

    def test_complete_nonexistent_task(self):
        # Try to complete a task that doesn't exist
        result = self.manager.complete_task(999)

        # Verify the task completion fails
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
