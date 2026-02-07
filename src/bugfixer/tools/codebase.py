"""Codebase inspection tools – file reading, listing, and searching."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path


def list_files(
    repo_path: str,
    extensions: list[str] | None = None,
    ignore_dirs: list[str] | None = None,
    max_files: int = 500,
) -> list[str]:
    """Return relative paths of files in *repo_path*.

    Parameters
    ----------
    extensions : list[str] | None
        If given, only include files whose suffix is in this list
        (e.g. ``[".py", ".js"]``).
    ignore_dirs : list[str] | None
        Directory basenames to skip (defaults to common noise).
    max_files : int
        Safety cap to avoid overwhelming the context window.
    """
    ignore_dirs = ignore_dirs or [
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
        ".eggs", "*.egg-info",
    ]
    results: list[str] = []
    root = Path(repo_path).resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place
        dirnames[:] = [
            d for d in dirnames
            if not any(fnmatch.fnmatch(d, pat) for pat in ignore_dirs)
        ]
        for fname in filenames:
            if extensions and not any(fname.endswith(ext) for ext in extensions):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fname), root)
            results.append(rel)
            if len(results) >= max_files:
                return results
    return results


def read_file(repo_path: str, relative_path: str) -> str:
    """Read and return the full text content of a file."""
    full = Path(repo_path) / relative_path
    if not full.is_file():
        raise FileNotFoundError(f"File not found: {full}")
    return full.read_text(errors="replace")


def read_file_lines(
    repo_path: str,
    relative_path: str,
    start: int = 1,
    end: int | None = None,
) -> str:
    """Read a specific line range (1-indexed, inclusive)."""
    text = read_file(repo_path, relative_path)
    lines = text.splitlines(keepends=True)
    end = end or len(lines)
    return "".join(lines[start - 1 : end])


def search_files(
    repo_path: str,
    pattern: str,
    extensions: list[str] | None = None,
    max_results: int = 50,
) -> list[dict]:
    """Grep-like search: return matching lines across the repo.

    Returns a list of ``{"file": str, "line": int, "text": str}`` dicts.
    """
    results: list[dict] = []
    for rel in list_files(repo_path, extensions=extensions):
        try:
            content = read_file(repo_path, rel)
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if pattern.lower() in line.lower():
                results.append({"file": rel, "line": i, "text": line.strip()})
                if len(results) >= max_results:
                    return results
    return results


def get_file_summary(repo_path: str, relative_path: str, max_lines: int = 80) -> str:
    """Return the first *max_lines* lines of a file for quick inspection."""
    text = read_file(repo_path, relative_path)
    lines = text.splitlines()
    truncated = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        truncated += f"\n... ({len(lines) - max_lines} more lines)"
    return truncated
