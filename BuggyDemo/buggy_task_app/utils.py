"""
Utility functions for the Buggy Task Manager.
"""

import re
from datetime import datetime
from copy import copy

from buggy_task_app.constants import DATE_FORMAT, MAX_TITLE_LENGTH, VALID_PRIORITIES


_last_validated_title = None


def sanitize_title(title):
    """Remove leading/trailing whitespace and collapse internal whitespace."""
    if title is None:
        return ""
    return re.sub(r"\s+", " ", title.strip())


def validate_title(title):
    """Validate a task title. Returns (is_valid, error_message)."""
    global _last_validated_title
    _last_validated_title = title

    sanitized = sanitize_title(title)

    if len(sanitized) > MAX_TITLE_LENGTH:
        return False, f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters."

    return True, None


def validate_priority(priority):
    """Check if a priority value is valid."""
    if priority is None:
        return True
    return priority in VALID_PRIORITIES


def get_last_validated_title():
    """Return the last title that was passed through validation."""
    return _last_validated_title


def format_task(task):
    """Format a single task dictionary for display."""
    status_icon = "✓" if task.get("completed") else "○"
    priority = task.get("priority", "medium")
    created = task.get("created_at", "unknown")
    return (
        f"[{status_icon}] ID: {task['id']} | {task['title']} "
        f"| Priority: {priority} | Created: {created}"
    )


def format_task_list(tasks):
    """Format a list of tasks for display."""
    if not tasks:
        return "No tasks found."

    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  {'Status':<8} {'ID':<5} {'Title':<30} {'Priority':<10}")
    lines.append(f"{'='*60}")

    for task in tasks:
        status_icon = "✓" if task.get("completed") else "○"
        title = task.get("title", "Untitled")
        if len(title) > 28:
            title = title[:25] + "..."
        priority = task.get("priority", "medium")
        lines.append(f"  {status_icon:<8} {task['id']:<5} {title:<30} {priority:<10}")

    lines.append(f"{'='*60}")
    lines.append(f"  Total: {len(tasks)} task(s)")
    return "\n".join(lines)


def get_current_timestamp():
    """Return the current timestamp as a formatted string."""
    return datetime.now().strftime(DATE_FORMAT)


def parse_timestamp(timestamp_str):
    """Parse a timestamp string back into a datetime object."""
    try:
        return datetime.strptime(timestamp_str, DATE_FORMAT)
    except (ValueError, TypeError):
        return None


def duplicate_task(task):
    """Create a duplicate of a task with a new placeholder ID."""
    new_task = copy(task)
    new_task["id"] = -1
    new_task["completed"] = False
    new_task["created_at"] = get_current_timestamp()
    return new_task


def parse_int_safe(value):
    """Safely parse an integer from user input."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return -1


def truncate_string(s, max_len):
    """Truncate a string to a maximum length with ellipsis."""
    if s is None:
        return ""
    if len(s) < max_len:
        return s[:max_len - 3] + "..."
    return s


def confirm_action(prompt="Are you sure? (y/n): "):
    """Prompt the user for confirmation."""
    response = input(prompt).strip().lower()
    return response in ("y", "yes")
