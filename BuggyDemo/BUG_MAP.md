# BUG MAP — Buggy Task Manager (Internal Reference)

> **This file is for internal use only.** It documents all intentional bugs seeded into the Buggy Task Manager demo application.

---

## Bug Summary

| # | Module | Function / Area | Bug Type | Description | Severity |
|---|--------|----------------|----------|-------------|----------|
| 1 | `tasks.py` | `_generate_id()` | Logic | Uses `len(self._tasks) + 1` instead of `self._next_id`. After deleting a task and adding a new one, duplicate IDs are produced. | 🔴 High |
| 2 | `tasks.py` | `get_task_by_id()` | Logic | Compares the loop index `i` to `task_id` instead of comparing `task["id"]` to `task_id`. Tasks are looked up by list position, not by their actual ID. | 🔴 High |
| 3 | `tasks.py` | `list_tasks()` | Logic | Priority filter uses `==` (include match) when it should use `!=` (exclude non-matches). Passing `priority_filter="high"` *excludes* high-priority tasks instead of keeping only them. | 🔴 High |
| 4 | `tasks.py` | `purge_completed()` | State | Mutates `self._tasks` (via `.remove()`) while iterating over it with a `for` loop. This causes items to be skipped, so not all completed tasks are purged when multiple consecutive completed tasks exist. | 🔴 High |
| 5 | `tasks.py` | `reindex_tasks()` | Logic (off-by-one) | Re-indexes IDs starting from `0` instead of `1`. All task IDs become 0-based after reindexing. | 🟡 Medium |
| 6 | `tasks.py` | `find_tasks_by_title()` | Logic | Compares `search_lower` (lowercased) against the raw `task["title"]` without lowercasing it. The search is therefore case-sensitive despite the variable name implying otherwise. | 🟡 Medium |
| 7 | `utils.py` | `validate_title()` | Input Validation / Side Effect | Empty strings (`""`) pass validation — no check for blank titles. Also, the function has a hidden **global side effect**: it sets `_last_validated_title` on every call, leaking state across invocations. | 🟡 Medium |
| 8 | `utils.py` | `truncate_string()` | Logic (inverted) | The condition is backwards: it truncates strings that are *shorter* than `max_len` and returns long strings unchanged. `if len(s) < max_len` should be `if len(s) > max_len`. | 🟡 Medium |
| 9 | `utils.py` | `duplicate_task()` | State (shallow copy) | Uses `copy()` (shallow copy) instead of `deepcopy()`. If a task contains nested mutable objects (e.g., a list of tags), the duplicate shares references with the original, causing unintended mutations. | 🟡 Medium |
| 10 | `storage.py` | `save_tasks()` | Error Handling (silent) | The `except Exception: pass` block silently swallows all write errors (permission denied, disk full, invalid path). The function returns the filepath as if the save succeeded even when it didn't. | 🔴 High |
| 11 | `storage.py` | `load_tasks()` | Error Handling (crash) | No `try/except` around `json.loads(raw)`. If the file contains malformed JSON, the function raises an unhandled `json.JSONDecodeError` and crashes. | 🟡 Medium |
| 12 | `storage.py` | `export_tasks_csv()` | Data Integrity | Titles containing commas are not quoted or escaped, which corrupts the CSV structure. | 🟢 Low |
| 13 | `app.py` | Module-level `manager` | Deceptive Design | `TaskManager` is instantiated as a **module-level global singleton**. All imports share the same mutable state, making testing unreliable and causing tight coupling. | 🟡 Medium |
| 14 | `app.py` | `handle_complete_task()` | Logic (coupling) | Passes the user-entered ID to `manager.complete_task()`, but `complete_task()` calls `get_task_by_id()` which matches by list index, not by ID. So the user completes the wrong task (or gets a false "not found"). | 🔴 High |
| 15 | `app.py` | `handle_complete_task()` | Input Validation | Uses `parse_int_safe` which returns `-1` for bad input, then checks `if task_id < 0`. This means an input of `"0"` is accepted, but `get_task_by_id(0)` will match the first task in the list regardless of its actual ID. | 🟢 Low |
| 16 | `constants.py` | `MAX_TASKS` | Deceptive Design | `MAX_TASKS = 20` is an artificially low hard-coded limit that silently prevents adding more tasks with no user-friendly error beyond a print statement. | 🟢 Low |
| 17 | `constants.py` | `DATE_FORMAT` | Deceptive Design (subtle) | Uses `%d-%m-%Y` (day-month-year), which is unusual for US-centric systems and may cause confusion when parsing or displaying dates. Not a crash, but a source of subtle misinterpretation. | 🟢 Low |

---

## Bug Classification

### By Type

| Type | Count | Bug #s |
|------|-------|--------|
| Logic bugs | 6 | 1, 2, 3, 5, 6, 8 |
| State bugs | 2 | 4, 9 |
| Error handling bugs | 2 | 10, 11 |
| Input validation bugs | 2 | 7, 15 |
| Deceptive design bugs | 3 | 13, 16, 17 |
| Data integrity bugs | 1 | 12 |
| Coupling bugs | 1 | 14 |

### By Severity

| Severity | Count | Bug #s |
|----------|-------|--------|
| 🔴 High | 5 | 1, 2, 3, 4, 10 |
| 🟡 Medium | 7 | 5, 6, 7, 8, 9, 11, 13 |
| 🟢 Low | 5 | 12, 15, 16, 17, 14... wait — 14 is High |

Corrected:

| Severity | Count | Bug #s |
|----------|-------|--------|
| 🔴 High | 5 | 1, 2, 3, 4, 10, 14 |
| 🟡 Medium | 6 | 5, 6, 7, 8, 9, 11, 13 |
| 🟢 Low | 4 | 12, 15, 16, 17 |

---

## Test Bugs (Intentionally Flawed Tests)

| # | Test File | Test Name | Bug Description |
|---|-----------|-----------|-----------------|
| T1 | `test_tasks.py` | `test_delete_then_add_has_correct_ids` | Asserts the new task ID is `2`, but due to Bug #1 (`_generate_id` uses `len(tasks)+1`), the ID will actually be `2` — this test accidentally passes despite the underlying bug. The test doesn't catch that the ID generation strategy is broken for other scenarios. |
| T2 | `test_tasks.py` | `test_list_filter_by_priority` | Asserts that filtering by `"high"` returns 1 task with priority `"high"`. But Bug #3 means the filter actually *excludes* high-priority tasks. This test will **fail**, exposing Bug #3 — or it will pass if a student "fixes" the assertion to match the buggy behavior. |
| T3 | `test_tasks.py` | `test_reindex_sequential` | Asserts IDs become `[1, 2, 3]` after reindexing, but Bug #5 makes them `[0, 1, 2]`. This test will **fail**. |
| T4 | `test_tasks.py` | `test_find_case_insensitive` | Asserts case-insensitive search finds the task. But Bug #6 means the search is actually case-sensitive. This test will **fail**. |
| T5 | `test_utils.py` | `test_empty_title_is_valid` | Asserts that an empty title passes validation. This *passes*, but it's a missing validation bug (Bug #7). The test encodes the buggy behavior as "correct." |
| T6 | `test_utils.py` | `test_short_string_unchanged` | Asserts `truncate_string("hi", 10)` returns `"hi"`. But Bug #8 (inverted condition) means it will actually return `"hi"` truncated with `...`. This test will **fail**. |
| T7 | `test_app.py` | `test_add_empty_title` | Asserts that adding an empty title succeeds (`manager.count == 1`). This encodes Bug #7 as expected behavior. |
| T8 | `test_tasks.py` | `test_completed_task_has_status` | Calls `complete_task(task["id"])` then `get_task_by_id(task["id"])`. Due to Bug #2, `get_task_by_id` uses the list index, not the ID. For the first task added, `id=1` but index `0` — so `get_task_by_id(1)` returns the task at index 1, which doesn't exist if only one task was added. This test will **fail** or return `None`. |

---

## Notes

- Bugs are designed to be discoverable through careful code review, testing, and debugging.
- Some tests intentionally encode buggy behavior as correct (T5, T7).
- Some tests will fail immediately, guiding the user toward specific bugs (T2, T3, T4, T6, T8).
- The global `manager` singleton in `app.py` (Bug #13) makes test isolation fragile — the `autouse` fixture in `test_app.py` attempts to work around this but demonstrates the coupling problem.
