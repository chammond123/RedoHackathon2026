"""
Simple Flask web interface for the Buggy Task Manager.
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from buggy_task_app.tasks import TaskManager
from buggy_task_app.utils import format_task, sanitize_title

app = Flask(__name__)
app.secret_key = "buggy-task-manager-secret"

manager = TaskManager()

BUG_REPORTS_FILE = "bug_reports.json"

# ── BugFixer gateway config (injected into templates) ──
BUGFIXER_GATEWAY_URL = os.environ.get("BUGFIXER_GATEWAY_URL", "http://localhost:3001")
BUGFIXER_API_KEY     = os.environ.get("BUGFIXER_API_KEY", "")
BUGFIXER_REPO_PATH   = os.environ.get("BUGFIXER_REPO_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@app.context_processor
def inject_bugfixer_config():
    """Make gateway config available in all templates."""
    return {
        "bugfixer_gateway_url": BUGFIXER_GATEWAY_URL,
        "bugfixer_api_key": BUGFIXER_API_KEY,
        "bugfixer_repo_path": BUGFIXER_REPO_PATH,
    }


def _load_bug_reports():
    if not os.path.exists(BUG_REPORTS_FILE):
        return []
    with open(BUG_REPORTS_FILE, "r") as f:
        return json.load(f)


def _save_bug_report(report):
    reports = _load_bug_reports()
    reports.append(report)
    with open(BUG_REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=2)


@app.route("/")
def index():
    filter_type = request.args.get("filter", "all")
    if filter_type == "pending":
        tasks = manager.list_tasks(show_completed=False)
    elif filter_type == "completed":
        tasks = [t for t in manager.get_all_tasks() if t.get("completed")]
    else:
        tasks = manager.get_all_tasks()

    stats = manager.get_statistics()
    return render_template("index.html", tasks=tasks, stats=stats, filter_type=filter_type)


@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    priority = request.form.get("priority", "medium").strip()

    if not priority:
        priority = "medium"

    task = manager.add_task(title, priority if priority else None)
    if task:
        flash(f"Task added: {task['title']}", "success")
    else:
        flash("Failed to add task.", "error")
    return redirect(url_for("index"))


@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    success = manager.complete_task(task_id)
    if success:
        flash(f"Task {task_id} completed.", "success")
    else:
        flash(f"Task {task_id} not found.", "error")
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    success = manager.delete_task(task_id)
    if success:
        flash(f"Task {task_id} deleted.", "success")
    else:
        flash(f"Task {task_id} not found.", "error")
    return redirect(url_for("index"))


@app.route("/purge", methods=["POST"])
def purge_completed():
    count = manager.purge_completed()
    flash(f"Purged {count} completed task(s).", "success")
    return redirect(url_for("index"))


@app.route("/bug-reports")
def bug_reports_page():
    """View all submitted bug reports."""
    reports = _load_bug_reports()
    return render_template("bug_reports.html", reports=reports)


@app.route("/api/bug-report", methods=["POST"])
def api_submit_bug_report():
    """JSON endpoint: save a bug report from the chat bubble."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    report = {
        "reporter": data.get("reporter", "Chat User"),
        "module": data.get("module", ""),
        "severity": data.get("severity", "medium"),
        "title": data.get("title", "Untitled"),
        "description": data.get("description", ""),
        "steps": data.get("steps", ""),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_bug_report(report)
    return jsonify({"status": "ok", "report": report})


def run_web():
    """Entry point for the web interface."""
    app.run(debug=False, port=5000)


if __name__ == "__main__":
    run_web()
