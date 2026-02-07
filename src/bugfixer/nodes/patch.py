"""patch_generation node – generate and apply a minimal fix."""

from __future__ import annotations

from bugfixer.config import get_llm
from bugfixer.state import AgentState
from bugfixer.tools.codebase import read_file
from bugfixer.tools.patch import apply_file_edit


def patch_generation(state: AgentState) -> dict:
    """Ask the LLM to generate fixed file contents, then apply them.

    Strategy
    --------
    - For each affected file the LLM returns the complete corrected source.
    - We compute a unified diff and store it in ``AgentState["patch"]``.
    - The files are written to disk so validation can run immediately.
    """
    logs: list[str] = ["[patch] Generating fix …"]
    repo = state["repo_path"]
    root_cause = state.get("root_cause", "")
    suspected = state.get("suspected_files", [])

    # Read current contents of affected files
    file_map: dict[str, str] = {}
    for fpath in suspected[:6]:
        try:
            file_map[fpath] = read_file(repo, fpath)
        except FileNotFoundError:
            logs.append(f"[patch] Skipping missing file: {fpath}")

    if not file_map:
        logs.append("[patch] ERROR: no source files available to patch")
        return {"status": "failed", "logs": logs}

    files_block = "\n".join(
        f"=== {fp} ===\n{src}\n" for fp, src in file_map.items()
    )

    llm = get_llm()
    prompt = f"""You are a senior engineer writing a minimal patch to fix a bug.

BUG REPORT:
{state['bug_report']}

ROOT CAUSE:
{root_cause}

CURRENT SOURCE FILES:
{files_block}

INSTRUCTIONS:
1. Fix ONLY the code that causes the bug.  Do not refactor unrelated code.
2. If a test should be added or updated, include it.
3. For each file you modify, output the COMPLETE corrected file contents.

Respond using EXACTLY this format (repeat the FILE block for each file):

FILE: <relative/path.py>
```python
<full corrected file content>
```
END_FILE"""

    response = llm.invoke(prompt)
    content = response.content

    # Parse the response into file edits
    edits = _parse_file_blocks(content)
    logs.append(f"[patch] LLM proposed changes to {len(edits)} file(s): {list(edits.keys())}")

    if not edits:
        logs.append("[patch] ERROR: could not parse any file edits from LLM response")
        return {"status": "failed", "logs": logs}

    # Apply edits and accumulate the unified diff
    all_diffs: list[str] = []
    patch_files: list[str] = []
    for fpath, new_content in edits.items():
        diff = apply_file_edit(repo, fpath, new_content)
        if diff:
            all_diffs.append(diff)
            patch_files.append(fpath)
            logs.append(f"[patch] Applied edit to {fpath} ({len(diff)} chars of diff)")
        else:
            logs.append(f"[patch] No diff for {fpath} (content unchanged?)")

    combined_patch = "\n".join(all_diffs)

    return {
        "patch": combined_patch,
        "patch_files": patch_files,
        "status": "validating",
        "logs": logs,
    }


def _parse_file_blocks(text: str) -> dict[str, str]:
    """Parse ``FILE: <path> ... END_FILE`` blocks from LLM output."""
    import re

    edits: dict[str, str] = {}
    # Pattern: FILE: <path>\n```<lang>\n<content>\n```\nEND_FILE
    # Allow flexible whitespace and optional language tag
    pattern = re.compile(
        r"FILE:\s*(.+?)\s*\n"
        r"```[a-z]*\n"
        r"(.*?)\n```"
        r"(?:\s*\nEND_FILE)?",
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        fpath = m.group(1).strip()
        content = m.group(2)
        # Ensure file ends with newline
        if not content.endswith("\n"):
            content += "\n"
        edits[fpath] = content

    return edits
