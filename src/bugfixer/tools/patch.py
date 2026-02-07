"""Patch tools – generate unified diffs, apply patches, revert changes."""

from __future__ import annotations

import difflib
import subprocess
from pathlib import Path


def generate_unified_diff(
    original: str,
    modified: str,
    filename: str,
) -> str:
    """Produce a unified diff string between *original* and *modified*."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def apply_file_edit(
    repo_path: str,
    relative_path: str,
    new_content: str,
) -> str:
    """Overwrite a file and return the unified diff of the change."""
    full = Path(repo_path) / relative_path
    if not full.exists():
        # Creating a new file
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(new_content)
        return generate_unified_diff("", new_content, relative_path)

    original = full.read_text(errors="replace")
    full.write_text(new_content)
    return generate_unified_diff(original, new_content, relative_path)


def apply_patch_string(repo_path: str, patch: str) -> tuple[bool, str]:
    """Apply a unified diff patch using ``git apply``.

    Returns ``(success, message)``.
    """
    try:
        proc = subprocess.run(
            ["git", "apply", "--check", "-"],
            input=patch,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, f"Patch check failed:\n{proc.stderr}"

        proc = subprocess.run(
            ["git", "apply", "-"],
            input=patch,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, f"Patch apply failed:\n{proc.stderr}"
        return True, "Patch applied successfully."
    except Exception as exc:
        return False, f"Error applying patch: {exc}"


def revert_changes(repo_path: str) -> tuple[bool, str]:
    """Hard-reset working tree changes via ``git checkout .``."""
    try:
        proc = subprocess.run(
            ["git", "checkout", "."],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stderr or "Reverted."
    except Exception as exc:
        return False, str(exc)


def get_git_diff(repo_path: str) -> str:
    """Return the current ``git diff`` for the repo."""
    try:
        proc = subprocess.run(
            ["git", "diff"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return proc.stdout
    except Exception:
        return ""
