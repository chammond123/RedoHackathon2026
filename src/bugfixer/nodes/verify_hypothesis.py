"""verify_hypothesis node – generate and run a secondary test to verify the hypothesis.

This node creates a targeted test that should:
1. FAIL when the bug is present (before patch)
2. PASS when the bug is fixed (after patch)

This helps catch cases where:
- The original test is incorrect or doesn't properly exercise the bug
- The fix passes the original test but doesn't actually address the root cause
"""

from __future__ import annotations

import os
import tempfile

from bugfixer.config import get_llm, get_skip_verification
from bugfixer.state import AgentState
from bugfixer.tools.runner import run_command
from bugfixer.tools.codebase import read_file


def verify_hypothesis(state: AgentState) -> dict:
    """Generate a secondary verification test based on the hypothesis.

    This test is designed to specifically exercise the suspected bug behavior.
    """
    logs: list[str] = ["[verify_hypothesis] Generating verification test …"]
    
    # Check if verification is skipped
    if get_skip_verification():
        logs.append("[verify_hypothesis] Skipping verification (BUGFIXER_SKIP_VERIFICATION=true)")
        return {
            "verification_test": "",
            "verification_test_name": "",
            "verification_test_file": "",
            "verification_passed_before_patch": None,
            "logs": logs,
        }
    
    repo = state["repo_path"]
    hypothesis = state.get("hypothesis", "")
    root_cause = state.get("root_cause", "")
    bug_report = state["bug_report"]

    # Collect source snippets for context
    file_snippets: list[str] = []
    for fpath in state.get("suspected_files", [])[:4]:
        try:
            content = read_file(repo, fpath)
            if len(content) > 4000:
                content = content[:4000] + "\n... (truncated)"
            file_snippets.append(f"=== {fpath} ===\n{content}\n")
        except FileNotFoundError:
            pass

    llm = get_llm()
    prompt = f"""You are a testing expert. Your job is to write a VERIFICATION TEST
that will confirm or deny the hypothesis about a bug.

This test must:
1. FAIL when the bug is present (before any fix is applied)
2. PASS only when the bug is correctly fixed
3. Be focused and minimal - test ONLY the hypothesized bug behavior
4. Be independent of existing tests (it should work even if existing tests are wrong)

BUG REPORT:
{bug_report}

HYPOTHESIS:
{hypothesis}

ROOT CAUSE (if identified):
{root_cause or "Not yet determined"}

SOURCE CODE:
{"".join(file_snippets) if file_snippets else "(not available)"}

PREVIOUS ERROR OUTPUT:
{state.get('error_output', '')[:2000]}

Write a Python test that will verify the hypothesis. The test should:
- Import the relevant modules from the codebase
- Set up a minimal test case that triggers the bug
- Assert the CORRECT behavior (so it fails when the bug exists)
- Include clear comments explaining what it's testing

Respond in exactly this format:
VERIFICATION_TEST_NAME: <descriptive_test_name>
VERIFICATION_TEST:
```python
<complete test code>
```
EXPECTED_FAILURE_REASON: <why this test should fail with the bug present>"""

    response = llm.invoke(prompt)
    content = response.content

    test_name = _extract_line(content, "VERIFICATION_TEST_NAME:")
    test_code = _extract_code_block(content, "VERIFICATION_TEST:")
    expected_failure = _extract_line(content, "EXPECTED_FAILURE_REASON:")

    if not test_code:
        logs.append("[verify_hypothesis] ERROR: Could not parse verification test from LLM")
        return {
            "verification_test": "",
            "verification_test_name": "",
            "verification_passed_before_patch": None,
            "logs": logs,
        }

    logs.append(f"[verify_hypothesis] Generated test: {test_name}")
    logs.append(f"[verify_hypothesis] Expected failure reason: {expected_failure}")

    # Write the verification test to a temporary file in the repo
    test_file = os.path.join(repo, f"_verification_test_{test_name or 'hypothesis'}.py")
    try:
        with open(test_file, "w") as f:
            f.write(test_code)
        logs.append(f"[verify_hypothesis] Wrote verification test to: {test_file}")
    except Exception as e:
        logs.append(f"[verify_hypothesis] ERROR writing test file: {e}")
        return {
            "verification_test": test_code,
            "verification_test_name": test_name,
            "verification_test_file": "",
            "verification_passed_before_patch": None,
            "logs": logs,
        }

    # Run the verification test BEFORE any patch is applied
    # It SHOULD fail if our hypothesis is correct
    logs.append("[verify_hypothesis] Running verification test (should FAIL if hypothesis is correct) …")
    result = run_command(f"python -m pytest {test_file} -v", cwd=repo, timeout=60)
    
    passed_before = result.success
    logs.append(f"[verify_hypothesis] Verification test exit code: {result.returncode}")
    logs.append(f"[verify_hypothesis] Test passed before patch: {passed_before}")
    
    if passed_before:
        logs.append("[verify_hypothesis] ⚠️  WARNING: Verification test PASSED before patch!")
        logs.append("[verify_hypothesis] This suggests either:")
        logs.append("  1. The hypothesis may be incorrect")
        logs.append("  2. The verification test doesn't properly exercise the bug")
        logs.append("  3. The bug may have already been fixed")
    else:
        logs.append("[verify_hypothesis] ✓ Verification test FAILED as expected (bug is present)")
        logs.append(f"[verify_hypothesis] Failure output: {result.combined_output[:1500]}")

    return {
        "verification_test": test_code,
        "verification_test_name": test_name,
        "verification_test_file": test_file,
        "verification_passed_before_patch": passed_before,
        "verification_failure_output": result.combined_output if not passed_before else "",
        "expected_failure_reason": expected_failure,
        "logs": logs,
    }


def run_verification_after_patch(state: AgentState) -> dict:
    """Re-run the verification test after the patch is applied.
    
    This should be called during validation to ensure:
    1. The verification test now PASSES (fix addresses the root cause)
    2. If it still fails, the fix may be incomplete or incorrect
    """
    logs: list[str] = ["[verify_after_patch] Re-running verification test after patch …"]
    repo = state["repo_path"]
    test_file = state.get("verification_test_file", "")
    
    if not test_file or not os.path.exists(test_file):
        logs.append("[verify_after_patch] No verification test file found, skipping")
        return {
            "verification_passed_after_patch": None,
            "logs": logs,
        }
    
    result = run_command(f"python -m pytest {test_file} -v", cwd=repo, timeout=60)
    passed_after = result.success
    
    logs.append(f"[verify_after_patch] Verification test exit code: {result.returncode}")
    logs.append(f"[verify_after_patch] Test passed after patch: {passed_after}")
    
    passed_before = state.get("verification_passed_before_patch")
    
    if passed_before is False and passed_after is True:
        logs.append("[verify_after_patch] ✅ EXCELLENT: Test failed before → passed after")
        logs.append("[verify_after_patch] This strongly suggests the fix addresses the root cause!")
    elif passed_before is False and passed_after is False:
        logs.append("[verify_after_patch] ❌ Test still fails after patch")
        logs.append("[verify_after_patch] The fix may be incomplete or incorrect")
        logs.append(f"[verify_after_patch] Output: {result.combined_output[:1500]}")
    elif passed_before is True and passed_after is True:
        logs.append("[verify_after_patch] ⚠️  Test passed both before and after")
        logs.append("[verify_after_patch] Cannot confirm fix validity via verification test")
    else:
        logs.append(f"[verify_after_patch] Unexpected state: before={passed_before}, after={passed_after}")
    
    return {
        "verification_passed_after_patch": passed_after,
        "verification_confirms_fix": (passed_before is False and passed_after is True),
        "logs": logs,
    }


def cleanup_verification_test(state: AgentState) -> None:
    """Remove the temporary verification test file."""
    test_file = state.get("verification_test_file", "")
    if test_file and os.path.exists(test_file):
        try:
            os.remove(test_file)
        except Exception:
            pass


def _extract_line(text: str, prefix: str) -> str:
    """Extract a single-line value after the prefix."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith(prefix.upper()):
            return stripped.split(":", 1)[1].strip()
    return ""


def _extract_code_block(text: str, prefix: str) -> str:
    """Extract Python code block after the given prefix."""
    import re
    
    # Find the prefix location
    prefix_idx = text.upper().find(prefix.upper())
    if prefix_idx == -1:
        # Try finding just the code block
        match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    # Look for code block after the prefix
    rest = text[prefix_idx:]
    match = re.search(r"```python\n(.*?)```", rest, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    return ""
