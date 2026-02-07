"""FastAPI server – wraps the LangGraph agent with HTTP and SSE endpoints.

Every event emitted carries a ``visibility`` label:
  - ``PUBLIC``  → safe for external chat clients (progress, questions, completion)
  - ``INTERNAL`` → developer-only (state diffs, logs, root cause, patch, PR)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bugfixer.config import configure_langsmith, get_llm
from bugfixer.graph import compile_graph
from bugfixer.state import AgentState, initial_state

load_dotenv()

# ── Visibility enum ────────────────────────────────────────

class Visibility(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"


# ── Phase → human-friendly message mapping ────────────────

_PUBLIC_PHASE_MSG: dict[str, str] = {
    "intake": "Analysing the bug report …",
    "hypothesizing": "Forming a hypothesis about what went wrong …",
    "reproducing": "Trying to reproduce the bug …",
    "analyzing": "Checking reproduction results …",
    "root_cause": "Investigating root cause …",
    "patching": "Working on a fix …",
    "validating": "Validating the fix …",
    "complete": "Done — the bug has been fixed!",
    "failed": "Unable to fix the bug after multiple attempts.",
}


# ── Request / response models ────────────────────────────

class StartRequest(BaseModel):
    bug_report: str
    repo_path: str = "."
    max_attempts: int = 5
    model: str | None = None
    agent_mode: str = "fix_and_pr"


class ChatMessage(BaseModel):
    content: str


class RunRecord(BaseModel):
    id: str
    bug_report: str
    repo_path: str
    status: str
    agent_mode: str
    created_at: str
    updated_at: str
    agent_state: dict[str, Any] | None = None
    messages: list[dict[str, Any]] = []


# ── In-memory store ──────────────────────────────────────

_runs: dict[str, dict[str, Any]] = {}
_events: dict[str, list[dict[str, Any]]] = {}
_locks: dict[str, asyncio.Lock] = {}

# ── Metrics ──────────────────────────────────────────────

_metrics = {
    "active_runs": 0,
    "total_requests": 0,
    "success_count": 0,
    "failure_count": 0,
    "avg_repro_time_seconds": 0,
    "prs_created": 0,
    "tickets_created": 0,
}

# ── App ──────────────────────────────────────────────────

app = FastAPI(title="BugFixer Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(run_id: str, event_type: str, visibility: Visibility, data: dict[str, Any]):
    """Append a structured event to the run's event log."""
    evt: dict[str, Any] = {
        "type": event_type,
        "visibility": visibility.value,
        "request_id": run_id,
        "timestamp": _ts(),
        **data,
    }
    _events.setdefault(run_id, []).append(evt)


def _public_state_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Extract only the PUBLIC-safe fields from agent state."""
    return {
        "status": state.get("status", ""),
        "attempt_count": state.get("attempt_count", 0),
        "max_attempts": state.get("max_attempts", 5),
        "repro_confirmed": state.get("repro_confirmed", False),
        "fix_validated": state.get("fix_validated", False),
    }


async def _run_agent(run_id: str, run_data: dict[str, Any]):
    """Execute the LangGraph agent and emit events."""
    configure_langsmith()
    if run_data.get("model"):
        os.environ["BUGFIXER_MODEL"] = run_data["model"]

    graph = compile_graph()
    state = initial_state(
        bug_report=run_data["bug_report"],
        repo_path=run_data["repo_path"],
        max_attempts=run_data["max_attempts"],
    )

    _metrics["active_runs"] += 1
    prev_log_count = 0
    prev_status = ""
    last_state = state.copy()  # Start with initial state

    try:
        for event in graph.stream(state, {"recursion_limit": 100}):
            # event is dict like {"node_name": node_output}
            if not isinstance(event, dict):
                continue
            
            # Merge node outputs into our tracked state
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    last_state.update(node_output)
                
            # Detect phase transitions
            cur_status = last_state.get("status", "")
            if cur_status and cur_status != prev_status:
                # PUBLIC: user-friendly phase message
                _emit(run_id, "phase_change", Visibility.PUBLIC, {
                    "phase": cur_status,
                    "message": _PUBLIC_PHASE_MSG.get(cur_status, f"Phase: {cur_status}"),
                })
                # INTERNAL: full state diff
                _emit(run_id, "state_update", Visibility.INTERNAL, {
                    "state": last_state,
                })
                prev_status = cur_status

            # New log entries
            all_logs = last_state.get("logs", [])
            new_logs = all_logs[prev_log_count:]
            prev_log_count = len(all_logs)
            for entry in new_logs:
                _emit(run_id, "log", Visibility.INTERNAL, {
                    "entry": {
                        "id": str(uuid.uuid4()),
                        "timestamp": _ts(),
                        "phase": cur_status,
                        "message": entry,
                        "level": "info",
                    },
                })

        # Final state - use last_state if step isn't a dict
        final_state = last_state if last_state else {}
        final_status = final_state.get("status", "unknown")
        _runs[run_id]["status"] = final_status
        _runs[run_id]["updated_at"] = _ts()
        _runs[run_id]["agent_state"] = final_state

        if final_status == "complete":
            _metrics["success_count"] += 1
            _emit(run_id, "run_complete", Visibility.PUBLIC, {
                "status": "complete",
                "message": "Bug fixed successfully!",
            })
            # Internal: PR artefacts
            _emit(run_id, "pr_artifacts", Visibility.INTERNAL, {
                "pr_title": final_state.get("pr_title", ""),
                "pr_summary": final_state.get("pr_summary", ""),
                "patch": final_state.get("patch", ""),
            })
        else:
            _metrics["failure_count"] += 1
            _emit(run_id, "run_complete", Visibility.PUBLIC, {
                "status": "failed",
                "message": "Agent could not fix the bug.",
            })

    except Exception as exc:
        logger.error(f"Agent run {run_id} failed with error: {exc}")
        logger.error(traceback.format_exc())
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["updated_at"] = _ts()
        _runs[run_id]["agent_state"] = {"error": str(exc), "traceback": traceback.format_exc()}
        _metrics["failure_count"] += 1
        _emit(run_id, "run_complete", Visibility.PUBLIC, {
            "status": "failed",
            "message": f"Agent error: {exc}",
        })
        _emit(run_id, "error", Visibility.INTERNAL, {
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })
    finally:
        _metrics["active_runs"] = max(0, _metrics["active_runs"] - 1)


# ── Routes ───────────────────────────────────────────────

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ── Run management ───────────────────────────────────────

@app.post("/api/runs", status_code=201)
async def start_run(req: StartRequest):
    """Start a new agent run. Returns immediately with run ID."""
    run_id = str(uuid.uuid4())
    now = _ts()
    run_data = {
        "id": run_id,
        "bug_report": req.bug_report,
        "repo_path": req.repo_path,
        "status": "pending",
        "agent_mode": req.agent_mode,
        "created_at": now,
        "updated_at": now,
        "max_attempts": req.max_attempts,
        "model": req.model,
        "agent_state": None,
        "messages": [],
    }
    _runs[run_id] = run_data
    _events[run_id] = []
    _metrics["total_requests"] += 1

    # Fire and forget the agent
    asyncio.create_task(_run_agent(run_id, run_data))

    return {"id": run_id, "status": "pending"}


@app.get("/api/runs")
async def list_runs():
    return list(_runs.values())


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    if run_id not in _runs:
        raise HTTPException(404, "Run not found")
    return _runs[run_id]


@app.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    if run_id not in _runs:
        raise HTTPException(404, "Run not found")
    _runs[run_id]["status"] = "failed"
    _runs[run_id]["updated_at"] = _ts()
    return {"status": "cancelled"}


# ── Events (SSE) ────────────────────────────────────────

@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    """SSE stream of all events for a run (visibility filtering done by gateway)."""
    if run_id not in _runs:
        raise HTTPException(404, "Run not found")

    async def generate():
        seen = 0
        while True:
            if await request.is_disconnected():
                break
            events = _events.get(run_id, [])
            for evt in events[seen:]:
                yield f"data: {json.dumps(evt)}\n\n"
            seen = len(events)
            # Stop streaming once run completes
            status = _runs.get(run_id, {}).get("status", "")
            if status in ("complete", "failed") and seen >= len(events):
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Metrics ──────────────────────────────────────────────

@app.get("/api/metrics")
async def get_metrics():
    return _metrics


# ── Logs ─────────────────────────────────────────────────

@app.get("/api/logs")
async def get_logs(request_id: str | None = None):
    """Return log entries. Optionally filter by request_id."""
    if request_id:
        events = _events.get(request_id, [])
    else:
        events = [e for evts in _events.values() for e in evts]
    return [e["entry"] for e in events if e["type"] == "log"]


# ── Config ───────────────────────────────────────────────

_config = {
    "repository": {"local_path": ".", "branch": "main", "validated": False},
    "agent": {
        "mode": "fix_and_pr",
        "max_retries": 5,
        "patch_aggressiveness": "moderate",
        "allow_test_execution": True,
        "model": os.getenv("BUGFIXER_MODEL", "gpt-4o"),
    },
    "integrations": {"github_token": "", "jira_token": "", "slack_webhook": ""},
}


@app.get("/api/config")
async def get_config():
    return _config


@app.put("/api/config")
async def update_config(new_config: dict[str, Any]):
    _config.update(new_config)
    return _config


@app.post("/api/config/validate-repo")
async def validate_repo(body: dict[str, str]):
    path = body.get("path", "")
    valid = os.path.isdir(path)
    return {"valid": valid, "message": "OK" if valid else f"Not a directory: {path}"}


# ── Requests aliases (frontend expects /api/requests) ────

@app.get("/api/requests")
async def list_requests():
    return list(_runs.values())


@app.get("/api/requests/recent")
async def recent_requests():
    runs = sorted(_runs.values(), key=lambda r: r["updated_at"], reverse=True)
    return runs[:10]


@app.get("/api/requests/{request_id}")
async def get_request(request_id: str):
    if request_id not in _runs:
        raise HTTPException(404, "Run not found")
    return _runs[request_id]


@app.post("/api/requests")
async def submit_request(req: StartRequest):
    return await start_run(req)


@app.post("/api/requests/{request_id}/cancel")
async def cancel_request(request_id: str):
    return await cancel_run(request_id)


@app.get("/api/requests/{request_id}/tools")
async def get_tool_invocations(request_id: str):
    # Placeholder – would be populated by tool-call hooks
    return []


@app.get("/api/telemetry/llm")
async def get_llm_usage(request_id: str | None = None):
    return {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_calls": 0,
        "total_cost_usd": 0,
    }
