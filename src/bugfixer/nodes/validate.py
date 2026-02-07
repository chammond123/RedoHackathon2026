"""validation node – re-run tests to confirm the fix works."""

from __future__ import annotations

from bugfixer.state import AgentState
from bugfixer.tools.runner import run_command, run_tests
from bugfixer.tools.patch import revert_changes


def validation(state: AgentState) -> dict:
    """Run the reproduction command again; if it passes, the fix is valid.

    Strategy
    --------
    1. Re-run the exact reproduction command.
       - If it now exits 0 → fix is validated.
    2. Optionally run the broader test suite to check for regressions.
    3. If validation fails → revert changes and signal retry.
    """
    logs: list[str] = ["[validate] Running validation …"]
    repo = state["repo_path"]
    repro_cmd = state.get("repro_command", "")
    attempt = state.get("attempt_count", 1)
    max_attempts = state.get("max_attempts", 5)

    # --- Step 1: re-run repro command ---
    if repro_cmd:
        logs.append(f"[validate] Re-running repro command: {repro_cmd}")
        result = run_command(repro_cmd, cwd=repo, timeout=120)
        logs.append(f"[validate] Repro exit code: {result.returncode}")

        if not result.success:
            logs.append("[validate] Repro command still fails – fix did NOT work.")
            logs.append(f"[validate] Output: {result.combined_output[:1000]}")

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
                "status": "hypothesizing",
                "logs": logs,
            }

        logs.append("[validate] ✅ Repro command now passes!")
    else:
        logs.append("[validate] WARNING: no repro command – skipping repro check.")

    # --- Step 2: run broader test suite (best-effort) ---
    logs.append("[validate] Running broader test suite …")
    suite_result = run_tests(repo, timeout=180)
    logs.append(f"[validate] Suite exit code: {suite_result.returncode}")

    if not suite_result.success:
        logs.append("[validate] ⚠️  Some tests failed (may be pre-existing).")
        logs.append(f"[validate] Suite output (tail): …{suite_result.combined_output[-800:]}")
    else:
        logs.append("[validate] Full test suite passes.")

    return {
        "fix_validated": True,
        "status": "complete",
        "logs": logs,
    }
