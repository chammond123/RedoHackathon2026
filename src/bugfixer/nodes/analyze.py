"""reproduction_analysis node – determine if the reproduction succeeded."""

from __future__ import annotations

from bugfixer.config import get_llm
from bugfixer.state import AgentState


def reproduction_analysis(state: AgentState) -> dict:
    """Ask the LLM whether the reproduction output confirms the bug.

    If confirmed, set ``repro_confirmed = True`` and move to root-cause.
    Otherwise, signal a retry.
    """
    logs: list[str] = ["[analysis] Analyzing reproduction output …"]

    error_output = state.get("error_output", "")
    repro_cmd = state.get("repro_command", "")
    bug = state["bug_report"]
    attempt = state.get("attempt_count", 1)
    max_attempts = state.get("max_attempts", 5)

    if not error_output.strip():
        logs.append("[analysis] No output captured – reproduction inconclusive.")
        if attempt >= max_attempts:
            logs.append("[analysis] Max attempts reached – aborting.")
            return {"repro_confirmed": False, "status": "failed", "logs": logs}
        return {"repro_confirmed": False, "status": "hypothesizing", "logs": logs}

    llm = get_llm()
    prompt = f"""You are a debugging assistant.  Determine whether the following
reproduction output confirms the bug described in the report.

BUG REPORT:
{bug}

REPRODUCTION COMMAND:
{repro_cmd}

OUTPUT:
{error_output[:6000]}

Answer in exactly this format:
REPRODUCED: YES or NO
FAILING_TESTS: comma-separated test names (or NONE)
REASONING: brief explanation"""

    response = llm.invoke(prompt)
    content = response.content

    reproduced = "YES" in _extract(content, "REPRODUCED:").upper()
    failing_tests = _parse_csv(content, "FAILING_TESTS:")
    reasoning = _extract(content, "REASONING:")

    logs.append(f"[analysis] Reproduced: {reproduced}")
    logs.append(f"[analysis] Failing tests: {failing_tests}")
    logs.append(f"[analysis] Reasoning: {reasoning}")

    if reproduced:
        return {
            "repro_confirmed": True,
            "failing_tests": failing_tests,
            "status": "root_cause",
            "logs": logs,
        }

    # Not reproduced – check attempt budget
    if attempt >= max_attempts:
        logs.append(f"[analysis] Exhausted {max_attempts} attempts – giving up.")
        return {
            "repro_confirmed": False,
            "status": "failed",
            "logs": logs,
        }

    logs.append(f"[analysis] Attempt {attempt}/{max_attempts} – will re-hypothesize.")
    return {
        "repro_confirmed": False,
        "status": "hypothesizing",
        "logs": logs,
    }


def _extract(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            return line.split(":", 1)[1].strip()
    return ""


def _parse_csv(text: str, prefix: str) -> list[str]:
    raw = _extract(text, prefix)
    if not raw or raw.upper() == "NONE":
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]
