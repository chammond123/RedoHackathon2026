"""Tests for the bugfixer graph structure and state management."""

from __future__ import annotations

import pytest

from bugfixer.state import AgentState, initial_state


class TestAgentState:
    """Verify the state schema and defaults."""

    def test_initial_state_fields(self):
        s = initial_state("something is broken", "/tmp/repo")
        assert s["bug_report"] == "something is broken"
        assert s["repo_path"] == "/tmp/repo"
        assert s["status"] == "intake"
        assert s["attempt_count"] == 0
        assert s["max_attempts"] == 5
        assert isinstance(s["logs"], list)
        assert len(s["logs"]) == 1

    def test_initial_state_custom_max(self):
        s = initial_state("bug", "/tmp", max_attempts=3)
        assert s["max_attempts"] == 3

    def test_empty_collections(self):
        s = initial_state("bug", "/tmp")
        assert s["suspected_files"] == []
        assert s["suspected_tests"] == []
        assert s["failing_tests"] == []
        assert s["patch_files"] == []
        assert s["context"] == {}


class TestGraphConstruction:
    """Verify the graph compiles and has expected nodes."""

    def test_graph_compiles(self):
        from bugfixer.graph import compile_graph
        app = compile_graph()
        assert app is not None

    def test_graph_has_expected_nodes(self):
        from bugfixer.graph import build_graph
        g = build_graph()
        node_names = set(g.nodes.keys())
        expected = {
            "intake_context",
            "hypothesis_generation",
            "reproduction_attempt",
            "reproduction_analysis",
            "root_cause_analysis",
            "patch_generation",
            "validation",
            "completion",
            "abort",
        }
        # LangGraph may add __start__ / __end__ internally
        assert expected.issubset(node_names), f"Missing nodes: {expected - node_names}"


class TestTools:
    """Verify deterministic tool functions."""

    def test_list_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.txt").write_text("hello")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.py").write_text("y = 2")

        from bugfixer.tools.codebase import list_files
        result = list_files(str(tmp_path))
        assert "a.py" in result
        assert "b.txt" in result
        assert any("c.py" in f for f in result)

    def test_list_files_extension_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.txt").write_text("hello")

        from bugfixer.tools.codebase import list_files
        result = list_files(str(tmp_path), extensions=[".py"])
        assert "a.py" in result
        assert "b.txt" not in result

    def test_read_file(self, tmp_path):
        (tmp_path / "test.py").write_text("hello world")
        from bugfixer.tools.codebase import read_file
        assert read_file(str(tmp_path), "test.py") == "hello world"

    def test_read_file_not_found(self, tmp_path):
        from bugfixer.tools.codebase import read_file
        with pytest.raises(FileNotFoundError):
            read_file(str(tmp_path), "nope.py")

    def test_search_files(self, tmp_path):
        (tmp_path / "a.py").write_text("def foo():\n    return 42\n")
        from bugfixer.tools.codebase import search_files
        hits = search_files(str(tmp_path), "foo")
        assert len(hits) >= 1
        assert hits[0]["file"] == "a.py"

    def test_run_command(self):
        from bugfixer.tools.runner import run_command
        result = run_command("echo hello")
        assert result.success
        assert "hello" in result.stdout

    def test_run_command_failure(self):
        from bugfixer.tools.runner import run_command
        result = run_command("exit 1")
        assert not result.success

    def test_run_command_timeout(self):
        from bugfixer.tools.runner import run_command
        result = run_command("sleep 10", timeout=1)
        assert not result.success
        assert "timed out" in result.stderr.lower()

    def test_generate_unified_diff(self):
        from bugfixer.tools.patch import generate_unified_diff
        diff = generate_unified_diff("a = 1\n", "a = 2\n", "file.py")
        assert "---" in diff
        assert "+++" in diff
        assert "-a = 1" in diff
        assert "+a = 2" in diff

    def test_apply_file_edit(self, tmp_path):
        (tmp_path / "x.py").write_text("old\n")
        from bugfixer.tools.patch import apply_file_edit
        diff = apply_file_edit(str(tmp_path), "x.py", "new\n")
        assert "-old" in diff
        assert "+new" in diff
        assert (tmp_path / "x.py").read_text() == "new\n"


class TestRouting:
    """Verify conditional routing functions."""

    def test_route_after_analysis_to_root_cause(self):
        from bugfixer.graph import _route_after_analysis
        assert _route_after_analysis({"status": "root_cause"}) == "root_cause_analysis"

    def test_route_after_analysis_to_retry(self):
        from bugfixer.graph import _route_after_analysis
        assert _route_after_analysis({"status": "hypothesizing"}) == "hypothesis_generation"

    def test_route_after_analysis_to_abort(self):
        from bugfixer.graph import _route_after_analysis
        assert _route_after_analysis({"status": "failed"}) == "abort"

    def test_route_after_validation_to_complete(self):
        from bugfixer.graph import _route_after_validation
        assert _route_after_validation({"status": "complete"}) == "completion"

    def test_route_after_validation_to_retry(self):
        from bugfixer.graph import _route_after_validation
        assert _route_after_validation({"status": "hypothesizing"}) == "hypothesis_generation"

    def test_route_after_validation_to_abort(self):
        from bugfixer.graph import _route_after_validation
        assert _route_after_validation({"status": "failed"}) == "abort"
