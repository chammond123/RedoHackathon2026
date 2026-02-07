"""
CLI entry point for the Buggy Task Manager.
"""

import sys

from buggy_task_app.constants import APP_NAME, APP_VERSION, MENU_OPTIONS
from buggy_task_app.tasks import TaskManager
from buggy_task_app.storage import save_tasks, load_tasks
from buggy_task_app.utils import (
    format_task_list,
    parse_int_safe,
    validate_priority,
    confirm_action,
)


manager = TaskManager()


def print_banner():
    """Print the application banner."""
    print(f"\n{'='*50}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"{'='*50}")


def print_menu():
    """Print the main menu."""
    print("\nMain Menu:")
    for key, value in MENU_OPTIONS.items():
        print(f"  {key}. {value}")
    print()


def handle_add_task():
    """Handle adding a new task."""
    title = input("Enter task title: ")
    priority = input("Enter priority (low/medium/high/critical) [medium]: ").strip()

    if not priority:
        priority = None

    task = manager.add_task(title, priority)
    if task:
        print(f"Task added: ID={task['id']}, Title='{task['title']}'")
    else:
        print("Failed to add task.")


def handle_list_tasks():
    """Handle listing tasks with optional filters."""
    print("\nFilter options:")
    print("  1. Show all tasks")
    print("  2. Show pending only")
    print("  3. Filter by priority")

    choice = input("Select filter [1]: ").strip()

    if choice == "2":
        tasks = manager.list_tasks(show_completed=False)
    elif choice == "3":
        priority = input("Enter priority to filter: ").strip()
        tasks = manager.list_tasks(priority_filter=priority)
    else:
        tasks = manager.list_tasks()

    print(format_task_list(tasks))


def handle_complete_task():
    """Handle marking a task as completed."""
    id_str = input("Enter task ID to complete: ")
    task_id = parse_int_safe(id_str)

    if task_id < 0:
        print("Invalid task ID.")
        return

    success = manager.complete_task(task_id)
    if success:
        print(f"Task {task_id} marked as completed.")
    else:
        print(f"Task with ID {task_id} not found.")


def handle_delete_task():
    """Handle deleting a task."""
    id_str = input("Enter task ID to delete: ")
    task_id = parse_int_safe(id_str)

    if task_id < 0:
        print("Invalid task ID.")
        return

    if confirm_action(f"Delete task {task_id}? (y/n): "):
        success = manager.delete_task(task_id)
        if success:
            print(f"Task {task_id} deleted.")
        else:
            print(f"Task with ID {task_id} not found.")
    else:
        print("Delete cancelled.")


def handle_save():
    """Handle saving tasks to file."""
    filepath = input("Enter filename [tasks.dat]: ").strip()
    if not filepath:
        filepath = None

    all_tasks = manager.get_all_tasks()
    result = save_tasks(all_tasks, filepath)
    print(f"Tasks saved to {result}.")


def handle_load():
    """Handle loading tasks from file."""
    filepath = input("Enter filename [tasks.dat]: ").strip()
    if not filepath:
        filepath = None

    tasks = load_tasks(filepath)
    manager.set_tasks(tasks)
    print(f"Loaded {len(tasks)} task(s).")


def handle_purge():
    """Handle purging completed tasks."""
    if not confirm_action("Purge all completed tasks? (y/n): "):
        print("Purge cancelled.")
        return

    count = manager.purge_completed()
    print(f"Purged {count} completed task(s).")


def run():
    """Main CLI loop."""
    print_banner()

    while True:
        print_menu()
        choice_str = input("Select option: ")
        choice = parse_int_safe(choice_str)

        if choice == 1:
            handle_add_task()
        elif choice == 2:
            handle_list_tasks()
        elif choice == 3:
            handle_complete_task()
        elif choice == 4:
            handle_delete_task()
        elif choice == 5:
            handle_save()
        elif choice == 6:
            handle_load()
        elif choice == 7:
            handle_purge()
        elif choice == 8:
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    run()
