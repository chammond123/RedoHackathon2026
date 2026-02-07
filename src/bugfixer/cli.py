"""CLI interface – ``bugfixer run`` command."""

from __future__ import annotations

import os
import sys
import time

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from bugfixer.config import configure_langsmith
from bugfixer.graph import compile_graph
from bugfixer.state import initial_state

# Load environment variables from .env file
load_dotenv()

console = Console()

# Status → emoji mapping for phase indicators
_PHASE_ICONS = {
    "intake": "🔍",
    "hypothesizing": "💡",
    "reproducing": "🔄",
    "analyzing": "🧪",
    "root_cause": "🎯",
    "patching": "🩹",
    "validating": "✅",
    "complete": "🎉",
    "failed": "❌",
}


@click.group()
@click.version_option(package_name="bugfixer")
def main():
    """BugFixer – an agentic debugging system."""
    pass


@main.command()
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to the target repository (default: current directory).",
)
@click.option(
    "--bug", "-b",
    default=None,
    help="Bug report text (if not provided, you will be prompted).",
)
@click.option(
    "--max-attempts",
    default=5,
    show_default=True,
    help="Maximum number of reproduction/fix attempts.",
)
@click.option(
    "--model",
    default=None,
    help="Override the LLM model (default: gpt-4o).",
)
def run(repo: str, bug: str | None, max_attempts: int, model: str | None):
    """Run the bugfixer agent on a bug report."""
    # --- Setup ---
    if model:
        os.environ["BUGFIXER_MODEL"] = model
    configure_langsmith()

    _check_api_key()

    # --- Get bug report ---
    if bug is None:
        console.print(
            Panel("Describe the bug you want to fix.\n"
                  "Include error messages, steps to reproduce, and any other details.",
                  title="Bug Report"),
        )
        bug = _multiline_input()

    if not bug.strip():
        console.print("[red]Error:[/red] Bug report cannot be empty.")
        sys.exit(1)

    console.print()
    console.print(Panel(bug, title="📋 Bug Report", border_style="cyan"))
    console.print(f"[dim]Target repo:[/dim] {repo}")
    console.print(f"[dim]Max attempts:[/dim] {max_attempts}")
    console.print()

    # --- Build and run the graph ---
    app = compile_graph()
    state = initial_state(bug_report=bug, repo_path=repo, max_attempts=max_attempts)

    prev_log_count = 0
    prev_status = ""
    start = time.time()

    console.print("[bold]Starting agent …[/bold]\n")

    # Stream execution – LangGraph yields state updates per node
    for step in app.stream(state, stream_mode="values"):
        # Print new log entries
        all_logs = step.get("logs", [])
        new_logs = all_logs[prev_log_count:]
        prev_log_count = len(all_logs)

        # Phase transition indicator
        current_status = step.get("status", "")
        if current_status and current_status != prev_status:
            icon = _PHASE_ICONS.get(current_status, "▶")
            console.print(
                f"\n[bold blue]─── {icon} Phase: {current_status.upper()} ───[/bold blue]"
            )
            prev_status = current_status

        for entry in new_logs:
            _print_log(entry)

    elapsed = time.time() - start

    # --- Final output ---
    console.print(f"\n[dim]Elapsed: {elapsed:.1f}s[/dim]\n")

    final_status = step.get("status", "unknown")
    if final_status == "complete":
        console.print(Panel("[bold green]✅ Bug fixed successfully![/bold green]"))
        _print_pr_artifacts(step)
        _print_patch(step)
    elif final_status == "failed":
        console.print(Panel("[bold red]❌ Agent could not fix the bug.[/bold red]"))
        console.print("[yellow]Review the logs above for details.[/yellow]")
    else:
        console.print(f"[yellow]Agent ended in unexpected status: {final_status}[/yellow]")

    sys.exit(0 if final_status == "complete" else 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]Error:[/red] OPENAI_API_KEY environment variable is not set.")
        console.print("Set it with:  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)


def _multiline_input() -> str:
    """Read multi-line input until an empty line or EOF."""
    console.print("[dim](Enter your bug report.  Press Enter twice or Ctrl-D to finish.)[/dim]")
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def _print_log(entry: str):
    """Pretty-print a single log entry."""
    if entry.startswith("["):
        bracket_end = entry.index("]") + 1
        tag = entry[:bracket_end]
        rest = entry[bracket_end:]
        console.print(f"[bold cyan]{tag}[/bold cyan]{rest}")
    else:
        console.print(entry)


def _print_pr_artifacts(state: dict):
    """Print the PR title and body."""
    title = state.get("pr_title", "")
    body = state.get("pr_summary", "")
    if title:
        console.print(f"\n[bold]PR Title:[/bold] {title}")
    if body:
        console.print(Panel(Markdown(body), title="PR Description", border_style="green"))


def _print_patch(state: dict):
    """Print the unified diff."""
    patch = state.get("patch", "")
    if patch:
        console.print(Panel(patch, title="Patch (unified diff)", border_style="yellow"))
