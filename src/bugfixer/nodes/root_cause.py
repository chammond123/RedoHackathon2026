"""root_cause_analysis node – drill down to the minimal root cause."""

from __future__ import annotations

from bugfixer.config import get_llm
from bugfixer.state import AgentState
from bugfixer.tools.codebase import read_file


def root_cause_analysis(state: AgentState) -> dict:
    """Read the suspected source files and ask the LLM to pinpoint the root cause.

    This is where we move from "what fails" to "why it fails".
    """
    logs: list[str] = ["[root_cause] Performing root-cause analysis …"]
    repo = state["repo_path"]

    # Collect full content of suspected files (within budget)
    file_contents: list[str] = []
    for fpath in state.get("suspected_files", [])[:6]:
        try:
            src = read_file(repo, fpath)
            # Truncate very large files
            if len(src) > 8000:
                src = src[:8000] + "\n... (truncated)"
            file_contents.append(f"=== {fpath} ===\n{src}\n")
        except FileNotFoundError:
            logs.append(f"[root_cause] File not found: {fpath}")

    llm = get_llm()
    prompt = f"""You are a senior software engineer performing root-cause analysis.

BUG REPORT:
{state['bug_report']}

HYPOTHESIS:
{state.get('hypothesis', 'N/A')}

REPRODUCTION COMMAND:
{state.get('repro_command', 'N/A')}

ERROR OUTPUT:
{state.get('error_output', '')[:4000]}

SOURCE CODE:
{"".join(file_contents) if file_contents else "(not available)"}

FAILING TESTS:
{state.get('failing_tests', [])}

Identify the MINIMAL root cause.  Be specific: name the file, function, and
line range where the bug originates.  Explain WHY the code is wrong.

Respond in exactly this format:
ROOT_CAUSE: <detailed explanation>
AFFECTED_FILES: <comma-separated file paths>"""

    response = llm.invoke(prompt)
    content = response.content

    root_cause = _extract(content, "ROOT_CAUSE:")
    affected = _parse_csv(content, "AFFECTED_FILES:")

    logs.append(f"[root_cause] Root cause: {root_cause}")
    logs.append(f"[root_cause] Affected files: {affected}")

    # Merge affected files into suspected_files (dedup)
    existing = set(state.get("suspected_files", []))
    merged = list(existing | set(affected))

    return {
        "root_cause": root_cause,
        "suspected_files": merged,
        "status": "patching",
        "logs": logs,
    }


def _extract(text: str, prefix: str) -> str:
    collecting = False
    lines: list[str] = []
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            lines.append(line.split(":", 1)[1].strip())
            collecting = True
        elif collecting:
            if any(line.strip().upper().startswith(p) for p in ("ROOT_CAUSE:", "AFFECTED_FILES:")):
                break
            lines.append(line.strip())
    return " ".join(lines).strip()


def _parse_csv(text: str, prefix: str) -> list[str]:
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            rest = line.split(":", 1)[1].strip()
            return [s.strip() for s in rest.split(",") if s.strip()]
    return []
