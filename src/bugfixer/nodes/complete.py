"""completion node – summarize findings and prepare PR artifacts."""

from __future__ import annotations

from bugfixer.config import get_llm
from bugfixer.state import AgentState


def completion(state: AgentState) -> dict:
    """Produce a pull-request title, summary, and final log entry.

    This is the terminal node for successful runs.
    """
    logs: list[str] = ["[complete] Preparing PR artifacts …"]

    llm = get_llm()
    prompt = f"""You are writing a pull-request description for a bug fix.

BUG REPORT:
{state['bug_report']}

ROOT CAUSE:
{state.get('root_cause', 'N/A')}

PATCH (unified diff):
{state.get('patch', 'N/A')[:6000]}

FILES CHANGED:
{state.get('patch_files', [])}

Write a concise, professional PR description.

Respond in exactly this format:
PR_TITLE: <one-line title>
PR_BODY:
<markdown body with sections: ## Summary, ## Root Cause, ## Changes, ## Testing>"""

    response = llm.invoke(prompt)
    content = response.content

    pr_title = _extract_line(content, "PR_TITLE:")
    pr_body = _extract_body(content, "PR_BODY:")

    logs.append(f"[complete] PR title: {pr_title}")
    logs.append("[complete] ✅ Done – artifacts ready for pull request.")

    return {
        "pr_title": pr_title,
        "pr_summary": pr_body,
        "status": "complete",
        "logs": logs,
    }


def _extract_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            return line.split(":", 1)[1].strip()
    return "Bug fix"


def _extract_body(text: str, prefix: str) -> str:
    lines = text.splitlines()
    collecting = False
    body_lines: list[str] = []
    for line in lines:
        if line.strip().upper().startswith(prefix.upper()):
            # grab anything after "PR_BODY:" on the same line
            rest = line.split(":", 1)[1].strip()
            if rest:
                body_lines.append(rest)
            collecting = True
            continue
        if collecting:
            body_lines.append(line)
    return "\n".join(body_lines).strip()
