"""
Application-wide constants for the Buggy Task Manager.
"""

APP_NAME = "Buggy Task Manager"
APP_VERSION = "1.0.0"

MAX_TASKS = 20
MAX_TITLE_LENGTH = 50

DEFAULT_SAVE_FILE = "tasks.dat"

DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

VALID_PRIORITIES = ["low", "medium", "high", "critical"]

DEFAULT_PRIORITY = "medium"

MENU_OPTIONS = {
    1: "Add Task",
    2: "List Tasks",
    3: "Complete Task",
    4: "Delete Task",
    5: "Save Tasks",
    6: "Load Tasks",
    7: "Purge Completed",
    8: "Exit",
}

STATUS_PENDING = "pending"
STATUS_COMPLETE = "complete"

ID_START = 1
