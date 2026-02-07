"""validation node – re-run tests to confirm the fix works."""

from __future__ import annotations

from bugfixer.state import AgentState
from bugfixer.config import get_strict_verification
from bugfixer.tools.runner import run_command, run_tests
from bugfixer.tools.patch import revert_changes
from bugfixer.nodes.verify_hypothesis import run_verification_after_patch, cleanup_verification_test


def validation(state: AgentState) -> dict:
    """Run the reproduction command again; if it passes, the fix is valid.

    Strategy
    --------
    1. Re-run the exact reproduction command.
       - If it now exits 0 → fix is validated.
    2. Re-run the verification test (should now PASS).
       - If it passes, we have strong confidence the fix is correct.
    3. Optionally run the broader test suite to check for regressions.
    4. If validation fails → revert changes and signal retry.
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

    # --- Step 2: Re-run verification test (should now PASS) ---
    verification_result = run_verification_after_patch(state)
    logs.extend(verification_result.get("logs", []))
    
    verification_passed_after = verification_result.get("verification_passed_after_patch")
    verification_confirms = verification_result.get("verification_confirms_fix", False)
    
    # If the verification test existed and still fails, the fix may be incomplete
    passed_before = state.get("verification_passed_before_patch")
    if passed_before is False and verification_passed_after is False:
        logs.append("[validate] ⚠️  Verification test still fails – fix may be incomplete!")
        logs.append("[validate] The fix passes the original test but not our verification test.")
        logs.append("[validate] This suggests the root cause may not be fully addressed.")
        
        # In strict mode, treat this as a validation failure
        if get_strict_verification():
            logs.append("[validate] STRICT MODE: Failing validation due to verification test failure.")
            ok, msg = revert_changes(repo)
            logs.append(f"[validate] Revert: {msg}")
            if attempt >= max_attempts:
                return {"fix_validated": False, "status": "failed", "logs": logs}
            return {"fix_validated": False, "status": "hypothesizing", "logs": logs}
    
    if verification_confirms:
        logs.append("[validate] 🎯 STRONG CONFIRMATION: Verification test failed before → passed after fix!")

    # --- Step 3: run broader test suite (best-effort) ---
    logs.append("[validate] Running broader test suite …")
    suite_result = run_tests(repo, timeout=180)
    logs.append(f"[validate] Suite exit code: {suite_result.returncode}")

    if not suite_result.success:
        logs.append("[validate] ⚠️  Some tests failed (may be pre-existing).")
        logs.append(f"[validate] Suite output (tail): …{suite_result.combined_output[-800:]}")
    else:
        logs.append("[validate] Full test suite passes.")

    # --- Cleanup verification test file ---
    cleanup_verification_test(state)

    return {
        "fix_validated": True,
        "status": "complete",
        "verification_passed_after_patch": verification_passed_after,
        "verification_confirms_fix": verification_confirms,
        "logs": logs,
    }
