"""intake_context node – gather codebase structure, environment info, and initial clues."""

from __future__ import annotations

from bugfixer.config import get_llm
from bugfixer.state import AgentState
from bugfixer.tools.codebase import list_files, search_files, read_file


def intake_context(state: AgentState) -> dict:
    """Scan the target repository and build a context dict.

    Deterministic steps
    -------------------
    1. List all source files.
    2. Detect language / framework / test setup.
    3. Search for keywords from the bug report.

    LLM step
    --------
    4. Ask the model to identify the most relevant files and tests.
    """
    repo = state["repo_path"]
    bug = state["bug_report"]
    logs: list[str] = ["[intake] Starting context gathering …"]

    # --- 1. file listing ---
    all_files = list_files(repo)
    py_files = [f for f in all_files if f.endswith(".py")]
    test_files = [f for f in py_files if "test" in f.lower()]
    logs.append(f"[intake] Found {len(all_files)} files ({len(py_files)} Python, {len(test_files)} test files)")

    # --- 2. environment detection ---
    config_files = [f for f in all_files if f in (
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
        "Pipfile", "poetry.lock", "tox.ini", "Makefile",
    )]
    config_contents: dict[str, str] = {}
    for cf in config_files:
        try:
            config_contents[cf] = read_file(repo, cf)[:3000]
        except Exception:
            pass
    logs.append(f"[intake] Config files found: {config_files or 'none'}")

    # --- 3. keyword search ---
    # Extract meaningful words from the bug report for searching
    keywords = _extract_search_terms(bug)
    search_hits: list[dict] = []
    for kw in keywords[:5]:  # limit to top 5 keywords
        hits = search_files(repo, kw, extensions=[".py"], max_results=10)
        search_hits.extend(hits)
    logs.append(f"[intake] Keyword search produced {len(search_hits)} hits")

    # --- 4. LLM-assisted file ranking ---
    llm = get_llm()
    file_list_str = "\n".join(py_files[:200])
    hits_str = "\n".join(
        f"  {h['file']}:{h['line']}  {h['text']}" for h in search_hits[:30]
    )

    prompt = f"""You are a debugging assistant.  Given the following bug report and
codebase information, identify the files most likely related to the bug and any
test files that could help reproduce it.

BUG REPORT:
{bug}

PYTHON FILES IN REPO:
{file_list_str}

KEYWORD SEARCH HITS:
{hits_str}

CONFIG FILES:
{list(config_contents.keys())}

Respond in this exact format (no extra text):
SUSPECTED_FILES: file1.py, file2.py
SUSPECTED_TESTS: test_file1.py, test_file2.py
SUMMARY: One-paragraph summary of what the bug is likely about."""

    response = llm.invoke(prompt)
    content = response.content

    suspected_files = _parse_csv_line(content, "SUSPECTED_FILES:")
    suspected_tests = _parse_csv_line(content, "SUSPECTED_TESTS:")
    summary = _parse_field(content, "SUMMARY:")
    logs.append(f"[intake] LLM suspects files: {suspected_files}")
    logs.append(f"[intake] LLM suspects tests: {suspected_tests}")
    logs.append(f"[intake] LLM summary: {summary}")

    context = {
        "all_files": all_files,
        "py_files": py_files,
        "test_files": test_files,
        "config_files": config_files,
        "config_contents": config_contents,
        "search_hits": search_hits[:30],
        "llm_summary": summary,
    }

    return {
        "context": context,
        "suspected_files": suspected_files,
        "suspected_tests": suspected_tests,
        "status": "hypothesizing",
        "logs": logs,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_search_terms(text: str) -> list[str]:
    """Pull plausible code identifiers out of free-form text."""
    import re
    # Match camelCase, snake_case, dotted paths, quoted strings
    tokens: list[str] = re.findall(r'[A-Za-z_]\w{2,}', text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        low = t.lower()
        if low not in seen and low not in _STOP_WORDS:
            seen.add(low)
            unique.append(t)
    return unique


def _parse_csv_line(text: str, prefix: str) -> list[str]:
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            rest = line.split(":", 1)[1].strip()
            return [s.strip() for s in rest.split(",") if s.strip()]
    return []


def _parse_field(text: str, prefix: str) -> str:
    collecting = False
    lines: list[str] = []
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            rest = line.split(":", 1)[1].strip()
            lines.append(rest)
            collecting = True
        elif collecting:
            if any(line.strip().upper().startswith(p) for p in ("SUSPECTED_FILES:", "SUSPECTED_TESTS:", "SUMMARY:")):
                break
            lines.append(line.strip())
    return " ".join(lines).strip()


_STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was",
    "but", "not", "you", "all", "can", "has", "when", "one", "our",
    "out", "also", "been", "have", "each", "make", "like", "into",
    "bug", "error", "issue", "fix", "should", "does", "file", "test",
    "def", "class", "import", "return", "none", "true", "false", "self",
}
