"""AgentState – shared structured state threaded through every graph node.

This module uses TypedDict so LangGraph can manage the state natively.
Every node receives the full state and returns a *partial* update dict.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state for the bugfixer agent graph.

    Fields
    ------
    bug_report : str
        The original bug description provided by the user.
    repo_path : str
        Absolute path to the target repository.
    context : dict
        Gathered information about the codebase, environment, deps, etc.
    suspected_files : list[str]
        File paths the agent believes are relevant.
    suspected_tests : list[str]
        Test files / test IDs that may exercise the buggy code.
    failing_tests : list[str]
        Tests that actually fail during reproduction.
    repro_command : str
        The shell command or script used to reproduce the bug.
    error_output : str
        Captured stdout + stderr from the reproduction attempt.
    hypothesis : str
        Current hypothesis about the root cause.
    root_cause : str
        Confirmed root-cause explanation.
    patch : str
        Unified diff string representing the fix.
    patch_files : list[str]
        Files modified by the patch.
    status : str
        Current high-level status – one of:
        "intake", "hypothesizing", "reproducing", "analyzing",
        "root_cause", "patching", "validating", "complete", "failed"
    repro_confirmed : bool
        Whether the bug was successfully reproduced.
    fix_validated : bool
        Whether the fix passed validation.
    attempt_count : int
        Number of reproduction / fix attempts so far (guards infinite loops).
    max_attempts : int
        Upper bound on retries before the agent gives up.
    logs : list[str]
        Human-readable log entries appended at every step.
    pr_summary : str
        Markdown summary suitable for a pull-request description.
    pr_title : str
        One-line title suitable for a pull-request.
    verification_test : str
        Generated test code to verify the hypothesis.
    verification_test_name : str
        Name of the verification test.
    verification_test_file : str
        Path to the temporary verification test file.
    verification_passed_before_patch : bool | None
        Whether the verification test passed before applying the patch.
        Should be False if hypothesis is correct.
    verification_passed_after_patch : bool | None
        Whether the verification test passed after applying the patch.
        Should be True if fix is correct.
    verification_confirms_fix : bool
        True if verification test failed before patch and passed after.
    """

    bug_report: str
    repo_path: str
    context: dict
    suspected_files: list[str]
    suspected_tests: list[str]
    failing_tests: list[str]
    repro_command: str
    error_output: str
    hypothesis: str
    root_cause: str
    patch: str
    patch_files: list[str]
    status: str
    repro_confirmed: bool
    fix_validated: bool
    attempt_count: int
    max_attempts: int
    # `logs` uses the Annotated[list, operator.add] pattern so that
    # every node can *append* entries without overwriting previous ones.
    logs: Annotated[list[str], operator.add]
    pr_summary: str
    pr_title: str
    # Verification test fields
    verification_test: str
    verification_test_name: str
    verification_test_file: str
    verification_passed_before_patch: bool | None
    verification_passed_after_patch: bool | None
    verification_confirms_fix: bool
    expected_failure_reason: str
    verification_failure_output: str


def initial_state(bug_report: str, repo_path: str, max_attempts: int = 5) -> AgentState:
    """Create a fresh AgentState with sensible defaults."""
    return AgentState(
        bug_report=bug_report,
        repo_path=repo_path,
        context={},
        suspected_files=[],
        suspected_tests=[],
        failing_tests=[],
        repro_command="",
        error_output="",
        hypothesis="",
        root_cause="",
        patch="",
        patch_files=[],
        status="intake",
        repro_confirmed=False,
        fix_validated=False,
        attempt_count=0,
        max_attempts=max_attempts,
        logs=[f"[init] Bug report received. Target repo: {repo_path}"],
        pr_summary="",
        pr_title="",
        # Verification test defaults
        verification_test="",
        verification_test_name="",
        verification_test_file="",
        verification_passed_before_patch=None,
        verification_passed_after_patch=None,
        verification_confirms_fix=False,
        expected_failure_reason="",
        verification_failure_output="",
    )
