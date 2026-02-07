"""validation node – re-run the reproduction test to confirm the fix works."""

from __future__ import annotations

import os

from bugfixer.state import AgentState
from bugfixer.tools.runner import run_command, run_tests
from bugfixer.tools.patch import revert_changes
from bugfixer.nodes.generate_repro_test import cleanup_repro_test


def validation(state: AgentState) -> dict:
    """Re-run the reproduction test; if it NOW PASSES, the fix is valid.

    The reproduction test asserts CORRECT behavior, so:
    - Before fix: test FAILS (bug exists)
    - After fix: test PASSES (bug fixed) ✓

    Strategy
    --------
    1. Re-run the reproduction test (should now PASS)
    2. Optionally run the broader test suite to check for regressions.
    3. If validation fails → revert changes and signal retry.
    """
    logs: list[str] = ["[validate] Running validation …"]
    repo = state["repo_path"]
    repro_test_file = state.get("repro_test_file", "")
    attempt = state.get("attempt_count", 1)
    max_attempts = state.get("max_attempts", 5)

    # --- Step 1: Re-run the reproduction test (should now PASS) ---
    if repro_test_file and os.path.exists(repro_test_file):
        cmd = f"python -m pytest {repro_test_file} -v --tb=short"
        logs.append(f"[validate] Re-running reproduction test: {cmd}")
        result = run_command(cmd, cwd=repo, timeout=60)
        logs.append(f"[validate] Repro test exit code: {result.returncode}")

        if not result.success:
            logs.append("[validate] ❌ Reproduction test still FAILS – fix did NOT work!")
            logs.append(f"[validate] Output:\n{result.combined_output[:1500]}")

            # Revert changes so the next attempt starts clean
            ok, msg = revert_changes(repo)
            logs.append(f"[validate] Revert: {msg}")

            if attempt >= max_attempts:
                logs.append(f"[validate] Exhausted {max_attempts} attempts.")
                return {
                    "fix_validated": False,
                    "error_output": result.combined_output,
                    "status": "failed",
                    "logs": logs,
                }

            return {
                "fix_validated": False,
                "error_output": result.combined_output,
                "status": "hypothesizing",  # Retry
                "logs": logs,
            }

        logs.append("[validate] ✅ Reproduction test now PASSES – bug appears fixed!")
    else:
        logs.append("[validate] WARNING: no reproduction test file – skipping repro validation")

    # --- Step 2: run broader test suite (best-effort) ---
    logs.append("[validate] Running broader test suite …")
    suite_result = run_tests(repo, timeout=180)
    logs.append(f"[validate] Suite exit code: {suite_result.returncode}")

    if not suite_result.success:
        logs.append("[validate] ⚠️  Some tests failed (may be pre-existing).")
        logs.append(f"[validate] Suite output (tail): …{suite_result.combined_output[-800:]}")
    else:
        logs.append("[validate] ✅ Full test suite passes.")

    # --- Cleanup reproduction test file ---
    cleanup_repro_test(repo)

    return {
        "fix_validated": True,
        "status": "complete",
        "logs": logs,
    }
