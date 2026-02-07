"""Runner tools – execute shell commands, run tests, capture output."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class RunResult:
    """Structured result of a shell command."""

    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0

    @property
    def combined_output(self) -> str:
        parts: list[str] = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        return "\n".join(parts)


def run_command(
    command: str,
    cwd: str | None = None,
    timeout: int = 120,
    env: dict | None = None,
) -> RunResult:
    """Run a shell command and capture output.

    Parameters
    ----------
    command : str
        Shell command string (executed via ``bash -c``).
    cwd : str | None
        Working directory.  Defaults to current directory.
    timeout : int
        Max seconds before the process is killed.
    env : dict | None
        Extra environment variables merged with ``os.environ``.
    """
    import os

    full_env = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )
        return RunResult(
            command=command,
            returncode=proc.returncode,
            stdout=_truncate(proc.stdout),
            stderr=_truncate(proc.stderr),
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
        )
    except Exception as exc:
        return RunResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Failed to execute command: {exc}",
        )


def run_tests(
    repo_path: str,
    test_paths: list[str] | None = None,
    framework: str = "pytest",
    timeout: int = 180,
) -> RunResult:
    """Run tests in the target repo and return the result.

    Parameters
    ----------
    test_paths : list[str] | None
        Specific test files or node IDs to run.  If ``None`` the whole
        suite is executed.
    framework : str
        Test framework command (default ``pytest``).
    """
    parts = [framework, "-v", "--tb=short"]
    if test_paths:
        parts.extend(test_paths)
    cmd = " ".join(parts)
    return run_command(cmd, cwd=repo_path, timeout=timeout)


def detect_test_framework(repo_path: str) -> str:
    """Heuristic to guess the test framework used in a repo."""
    from pathlib import Path

    root = Path(repo_path)
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
        return "pytest"
    if (root / "setup.cfg").exists():
        return "pytest"  # common default
    if (root / "tox.ini").exists():
        return "pytest"
    return "pytest"


def _truncate(text: str, max_chars: int = 15_000) -> str:
    """Truncate output to stay within context window budgets."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + f"\n\n... [truncated {len(text) - max_chars} chars] ...\n\n"
        + text[-half:]
    )
