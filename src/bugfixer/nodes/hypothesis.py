"""hypothesis_generation node – form a hypothesis about how to reproduce the bug."""

from __future__ import annotations

from bugfixer.config import get_llm
from bugfixer.state import AgentState
from bugfixer.tools.codebase import read_file, get_file_summary


def hypothesis_generation(state: AgentState) -> dict:
    """Use gathered context + LLM to propose a reproduction strategy.

    Outputs
    -------
    - ``hypothesis``: natural-language explanation of what we think is wrong.
    - ``repro_command``: shell command to reproduce the bug.
    """
    logs: list[str] = ["[hypothesis] Generating reproduction hypothesis …"]
    repo = state["repo_path"]
    attempt = state.get("attempt_count", 0) + 1
    logs.append(f"[hypothesis] Attempt #{attempt}")

    # Gather source snippets for suspected files
    snippets: list[str] = []
    for fpath in state.get("suspected_files", [])[:8]:
        try:
            content = get_file_summary(repo, fpath, max_lines=120)
            snippets.append(f"=== {fpath} ===\n{content}\n")
        except FileNotFoundError:
            logs.append(f"[hypothesis] WARNING: suspected file not found: {fpath}")

    # Also grab suspected test files
    for fpath in state.get("suspected_tests", [])[:5]:
        try:
            content = get_file_summary(repo, fpath, max_lines=120)
            snippets.append(f"=== {fpath} (test) ===\n{content}\n")
        except FileNotFoundError:
            pass

    snippets_str = "\n".join(snippets) if snippets else "(no file contents available)"

    # Include previous error output if this is a retry
    prev_error = state.get("error_output", "")
    prev_section = ""
    if prev_error and attempt > 1:
        prev_section = f"""
PREVIOUS REPRODUCTION ATTEMPT (failed):
Command: {state.get('repro_command', 'N/A')}
Output:
{prev_error[:3000]}
"""

    llm = get_llm()
    prompt = f"""You are a debugging assistant.  Based on the information below,
propose a HYPOTHESIS about the root cause and a SINGLE shell command to
reproduce the bug.

BUG REPORT:
{state['bug_report']}

CODEBASE CONTEXT:
{state.get('context', {}).get('llm_summary', 'N/A')}

SOURCE FILES:
{snippets_str}
{prev_section}
RULES:
- The reproduction command must be runnable from the repo root.
- Prefer running existing tests (e.g. ``pytest tests/test_foo.py::test_bar -x``).
- If no relevant test exists, write a minimal Python one-liner or short script.
- The command should EXIT NON-ZERO when the bug is present.

Respond in exactly this format:
HYPOTHESIS: <your hypothesis>
REPRO_COMMAND: <single shell command>"""

    response = llm.invoke(prompt)
    content = response.content

    hypothesis = _extract(content, "HYPOTHESIS:")
    repro_command = _extract(content, "REPRO_COMMAND:")

    logs.append(f"[hypothesis] Hypothesis: {hypothesis}")
    logs.append(f"[hypothesis] Repro command: {repro_command}")

    return {
        "hypothesis": hypothesis,
        "repro_command": repro_command,
        "attempt_count": attempt,
        "status": "reproducing",
        "logs": logs,
    }


def _extract(text: str, prefix: str) -> str:
    """Extract a single-line value after *prefix*."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith(prefix.upper()):
            return stripped.split(":", 1)[1].strip()
    # Fallback: return everything after the prefix marker
    if prefix.rstrip(":").upper() in text.upper():
        idx = text.upper().index(prefix.rstrip(":").upper())
        rest = text[idx:].split("\n", 1)
        if len(rest) > 0:
            return rest[0].split(":", 1)[-1].strip()
    return text.strip()
