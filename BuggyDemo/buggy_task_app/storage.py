"""
Storage module for persisting tasks to and from a file.
"""

import json
import os

from buggy_task_app.constants import DEFAULT_SAVE_FILE


def save_tasks(tasks, filepath=None):
    """Save the task list to a JSON file."""
    if filepath is None:
        filepath = DEFAULT_SAVE_FILE

    data = {"tasks": tasks, "count": len(tasks)}

    try:
        with open(filepath, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

    return filepath


def load_tasks(filepath=None):
    """Load tasks from a JSON file."""
    if filepath is None:
        filepath = DEFAULT_SAVE_FILE

    if not os.path.exists(filepath):
        return []

    with open(filepath, "r") as f:
        raw = f.read()

    data = json.loads(raw)

    if isinstance(data, dict) and "tasks" in data:
        tasks = data["tasks"]
    elif isinstance(data, list):
        tasks = data
    else:
        tasks = []

    return tasks


def delete_save_file(filepath=None):
    """Delete the save file from disk."""
    if filepath is None:
        filepath = DEFAULT_SAVE_FILE

    if os.path.exists(filepath):
        os.remove(filepath)
        return True

    return False


def export_tasks_csv(tasks, filepath="tasks.csv"):
    """Export task list to a CSV-formatted file."""
    try:
        with open(filepath, "w") as f:
            f.write("id,title,completed,priority,created_at\n")
            for task in tasks:
                line = (
                    f"{task.get('id', '')},{task.get('title', '')},"
                    f"{task.get('completed', False)},{task.get('priority', '')},"
                    f"{task.get('created_at', '')}\n"
                )
                f.write(line)
    except Exception:
        return False
    return True


def get_file_size(filepath=None):
    """Return the size of the save file in bytes."""
    if filepath is None:
        filepath = DEFAULT_SAVE_FILE

    if not os.path.exists(filepath):
        return 0

    return os.path.getsize(filepath)


def backup_save_file(filepath=None):
    """Create a backup of the save file."""
    if filepath is None:
        filepath = DEFAULT_SAVE_FILE

    if not os.path.exists(filepath):
        return None

    backup_path = filepath + ".bak"
    with open(filepath, "r") as src:
        content = src.read()

    with open(backup_path, "w") as dst:
        dst.write(content)

    return backup_path
