"""generate_repro_test node – generate a focused reproduction test based on hypothesis.

This replaces the old approach of:
1. Generating a shell command (fragile)
2. Having LLM interpret if reproduction succeeded (inconsistent)

New approach:
1. Generate a Python test that asserts CORRECT behavior
2. Run it - if it FAILS, bug is reproduced (deterministic)
3. Use the SAME test after patch to verify fix
"""

from __future__ import annotations

import os
import re

from bugfixer.config import get_llm
from bugfixer.state import AgentState
from bugfixer.tools.codebase import read_file, get_file_summary
from bugfixer.tools.runner import run_command


def generate_repro_test(state: AgentState) -> dict:
    """Generate a reproduction test based on the hypothesis.
    
    The test should:
    - Assert the CORRECT/EXPECTED behavior
    - FAIL when the bug is present
    - PASS when the bug is fixed
    
    This gives us deterministic reproduction (exit code) instead of
    relying on LLM interpretation.
    """
    logs: list[str] = ["[repro_test] Generating reproduction test …"]
    repo = state["repo_path"]
    attempt = state.get("attempt_count", 0) + 1
    logs.append(f"[repro_test] Attempt #{attempt}")

    # Gather context
    snippets: list[str] = []
    for fpath in state.get("suspected_files", [])[:6]:
        try:
            content = get_file_summary(repo, fpath, max_lines=150)
            snippets.append(f"=== {fpath} ===\n{content}\n")
        except FileNotFoundError:
            logs.append(f"[repro_test] WARNING: file not found: {fpath}")

    for fpath in state.get("suspected_tests", [])[:4]:
        try:
            content = get_file_summary(repo, fpath, max_lines=100)
            snippets.append(f"=== {fpath} (existing test) ===\n{content}\n")
        except FileNotFoundError:
            pass

    snippets_str = "\n".join(snippets) if snippets else "(no file contents available)"

    # Include previous failure info if this is a retry
    prev_section = ""
    prev_error = state.get("repro_test_error", "")
    if prev_error and attempt > 1:
        prev_section = f"""
PREVIOUS REPRODUCTION TEST FAILED TO RUN:
{prev_error[:2000]}

Please fix the issues above in your new test.
"""

    llm = get_llm()
    prompt = f"""You are a debugging expert. Write a REPRODUCTION TEST that will confirm the bug exists.

BUG REPORT:
{state['bug_report']}

CODEBASE CONTEXT:
{state.get('context', {}).get('llm_summary', 'N/A')}

SOURCE FILES:
{snippets_str}
{prev_section}
REQUIREMENTS FOR THE REPRODUCTION TEST:
1. It must be a valid Python file using pytest
2. It must import from the codebase correctly (check the imports in existing code)
3. It must assert the CORRECT/EXPECTED behavior
4. It will FAIL when the bug is present (because reality doesn't match expectations)
5. It will PASS when the bug is fixed
6. Keep it minimal and focused on reproducing the specific bug
7. Include clear comments explaining what behavior it's testing
8. Handle any setup/teardown needed (temp files, test data, etc.)

IMPORTANT: Study the existing imports in the source files to understand the correct import paths.

Respond in EXACTLY this format:

HYPOTHESIS: <brief explanation of what you think the bug is>

REPRO_TEST:
```python
<complete pytest-compatible test file>
```

WHY_IT_FAILS: <explain why this test will fail when the bug is present>"""

    response = llm.invoke(prompt)
    content = response.content

    hypothesis = _extract_line(content, "HYPOTHESIS:")
    test_code = _extract_code_block(content)
    why_fails = _extract_line(content, "WHY_IT_FAILS:")

    logs.append(f"[repro_test] Hypothesis: {hypothesis}")
    logs.append(f"[repro_test] Why test fails with bug: {why_fails}")

    if not test_code:
        logs.append("[repro_test] ERROR: Could not extract test code from response")
        return {
            "hypothesis": hypothesis or state.get("hypothesis", ""),
            "repro_test_code": "",
            "repro_test_file": "",
            "attempt_count": attempt,
            "status": "analyzing",
            "logs": logs,
        }

    # Write the reproduction test to a file
    test_file = os.path.join(repo, "_repro_test.py")
    try:
        with open(test_file, "w") as f:
            f.write(test_code)
        logs.append(f"[repro_test] Wrote test to: {test_file}")
    except Exception as e:
        logs.append(f"[repro_test] ERROR writing test file: {e}")
        return {
            "hypothesis": hypothesis,
            "repro_test_code": test_code,
            "repro_test_file": "",
            "repro_test_error": str(e),
            "attempt_count": attempt,
            "status": "analyzing",
            "logs": logs,
        }

    return {
        "hypothesis": hypothesis,
        "repro_test_code": test_code,
        "repro_test_file": test_file,
        "repro_command": f"python -m pytest {test_file} -v",
        "attempt_count": attempt,
        "status": "reproducing",
        "logs": logs,
    }


def run_repro_test(state: AgentState) -> dict:
    """Run the reproduction test and check if it fails (confirming the bug).
    
    This is deterministic - no LLM interpretation needed.
    - Test FAILS (exit != 0) → bug is reproduced ✓
    - Test PASSES (exit == 0) → bug not reproduced, retry
    - Test has errors (import errors, etc.) → need to fix test
    """
    logs: list[str] = ["[run_repro] Running reproduction test …"]
    repo = state["repo_path"]
    test_file = state.get("repro_test_file", "")
    attempt = state.get("attempt_count", 1)
    max_attempts = state.get("max_attempts", 5)

    if not test_file or not os.path.exists(test_file):
        logs.append("[run_repro] ERROR: No reproduction test file found")
        return {
            "repro_confirmed": False,
            "status": "hypothesizing",
            "logs": logs,
        }

    # Run the test
    cmd = f"python -m pytest {test_file} -v --tb=short"
    logs.append(f"[run_repro] Command: {cmd}")
    
    result = run_command(cmd, cwd=repo, timeout=60)
    
    logs.append(f"[run_repro] Exit code: {result.returncode}")
    logs.append(f"[run_repro] Output:\n{result.combined_output[:2000]}")

    # Analyze the result
    output = result.combined_output.lower()
    
    # Check for import/syntax errors (test itself is broken)
    has_import_error = "importerror" in output or "modulenotfounderror" in output
    has_syntax_error = "syntaxerror" in output
    has_name_error = "nameerror" in output and "not defined" in output
    
    if has_import_error or has_syntax_error or has_name_error:
        logs.append("[run_repro] ⚠️  Test has errors (import/syntax/name) - will regenerate")
        
        if attempt >= max_attempts:
            logs.append(f"[run_repro] Exhausted {max_attempts} attempts")
            return {
                "repro_confirmed": False,
                "repro_test_error": result.combined_output,
                "error_output": result.combined_output,
                "status": "failed",
                "logs": logs,
            }
        
        return {
            "repro_confirmed": False,
            "repro_test_error": result.combined_output,
            "error_output": result.combined_output,
            "status": "hypothesizing",  # Retry with error context
            "logs": logs,
        }

    # Test ran successfully - check if it passed or failed
    if result.returncode != 0:
        # Test FAILED = bug is reproduced! ✓
        logs.append("[run_repro] ✅ Test FAILED as expected - BUG REPRODUCED!")
        logs.append("[run_repro] The test asserts correct behavior, so failure confirms the bug.")
        
        # Extract failing test info
        failing_tests = _extract_failing_tests(result.combined_output)
        if failing_tests:
            logs.append(f"[run_repro] Failing tests: {failing_tests}")
        
        return {
            "repro_confirmed": True,
            "failing_tests": failing_tests,
            "error_output": result.combined_output,
            "status": "root_cause",
            "logs": logs,
        }
    else:
        # Test PASSED = bug not reproduced
        logs.append("[run_repro] ⚠️  Test PASSED - bug NOT reproduced")
        logs.append("[run_repro] Either the bug is already fixed, or the test doesn't exercise the bug correctly.")
        
        if attempt >= max_attempts:
            logs.append(f"[run_repro] Exhausted {max_attempts} attempts")
            return {
                "repro_confirmed": False,
                "error_output": result.combined_output,
                "status": "failed",
                "logs": logs,
            }
        
        return {
            "repro_confirmed": False,
            "error_output": result.combined_output,
            "repro_test_error": "Test passed but should have failed. The test may not exercise the bug correctly.",
            "status": "hypothesizing",
            "logs": logs,
        }


def cleanup_repro_test(repo_path: str) -> None:
    """Remove the temporary reproduction test file."""
    test_file = os.path.join(repo_path, "_repro_test.py")
    if os.path.exists(test_file):
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


def _extract_code_block(text: str) -> str:
    """Extract Python code block from response."""
    # Look for ```python ... ``` blocks
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    if match:
        code = match.group(1)
        # Ensure it ends with newline
        if not code.endswith("\n"):
            code += "\n"
        return code
    return ""


def _extract_failing_tests(output: str) -> list[str]:
    """Extract test names that failed from pytest output."""
    failing = []
    for line in output.splitlines():
        # pytest marks failures with FAILED
        if "FAILED" in line:
            # Extract test name (usually in format "path::test_name")
            match = re.search(r"FAILED\s+([^\s]+)", line)
            if match:
                failing.append(match.group(1))
        # Also check for "test_xxx" in error lines
        elif "::test_" in line:
            match = re.search(r"([^\s]*::test_[^\s]+)", line)
            if match:
                failing.append(match.group(1))
    return list(set(failing))  # Deduplicate
