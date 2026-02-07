"""reproduction_attempt node – actually run the repro command and capture output."""

from __future__ import annotations

from bugfixer.state import AgentState
from bugfixer.tools.runner import run_command


def reproduction_attempt(state: AgentState) -> dict:
    """Execute the proposed reproduction command.

    This node is *deterministic* – no LLM call, just shell execution.
    """
    repo = state["repo_path"]
    cmd = state.get("repro_command", "")
    logs: list[str] = [f"[repro] Running: {cmd}"]

    if not cmd:
        logs.append("[repro] ERROR: no repro command provided")
        return {
            "error_output": "No reproduction command was generated.",
            "repro_confirmed": False,
            "status": "analyzing",
            "logs": logs,
        }

    result = run_command(cmd, cwd=repo, timeout=120)

    logs.append(f"[repro] Exit code: {result.returncode}")
    if result.stdout.strip():
        logs.append(f"[repro] stdout (last 500 chars): …{result.stdout.strip()[-500:]}")
    if result.stderr.strip():
        logs.append(f"[repro] stderr (last 500 chars): …{result.stderr.strip()[-500:]}")

    return {
        "error_output": result.combined_output,
        "status": "analyzing",
        "logs": logs,
    }
