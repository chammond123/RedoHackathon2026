"""LangGraph state machine – wires all nodes into the agent workflow.

Graph topology
--------------

    START
      │
      ▼
  intake_context
      │
      ▼
  generate_repro_test  ◄───────────────┐
      │                                │
      ▼                                │
  run_repro_test ──── (not reproduced) ┘
      │ (reproduced = test FAILS)
      ▼
  root_cause_analysis
      │
      ▼
  patch_generation
      │
      ▼
  validation ──────── (fix failed) ──► generate_repro_test
      │ (fix passed = repro test now PASSES)
      ▼
  completion
      │
      ▼
    END

Key insight: The reproduction test asserts CORRECT behavior, so:
- Test FAILS → bug exists (reproduced) ✓
- Test PASSES → bug fixed (validated) ✓
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from bugfixer.state import AgentState
from bugfixer.nodes.intake import intake_context
from bugfixer.nodes.generate_repro_test import generate_repro_test, run_repro_test
from bugfixer.nodes.root_cause import root_cause_analysis
from bugfixer.nodes.patch import patch_generation
from bugfixer.nodes.validate import validation
from bugfixer.nodes.complete import completion


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------

def _route_after_repro_test(state: AgentState) -> str:
    """After running repro test, decide whether bug is reproduced."""
    status = state.get("status", "")
    if status == "root_cause":
        return "root_cause_analysis"
    if status == "failed":
        return "abort"
    # Default: retry generating repro test
    return "generate_repro_test"


def _route_after_validation(state: AgentState) -> str:
    """After validation, decide whether the fix worked or needs retry."""
    status = state.get("status", "")
    if status == "complete":
        return "completion"
    if status == "failed":
        return "abort"
    # Default: retry from repro test generation
    return "generate_repro_test"


def _abort(state: AgentState) -> dict:
    """Terminal node for failed runs."""
    return {
        "status": "failed",
        "logs": ["[abort] Agent could not resolve the bug within the attempt budget."],
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct and compile the bugfixer LangGraph state machine."""
    graph = StateGraph(AgentState)

    # -- Add nodes --
    graph.add_node("intake_context", intake_context)
    graph.add_node("generate_repro_test", generate_repro_test)
    graph.add_node("run_repro_test", run_repro_test)
    graph.add_node("root_cause_analysis", root_cause_analysis)
    graph.add_node("patch_generation", patch_generation)
    graph.add_node("validation", validation)
    graph.add_node("completion", completion)
    graph.add_node("abort", _abort)

    # -- Entry point --
    graph.set_entry_point("intake_context")

    # -- Linear edges --
    graph.add_edge("intake_context", "generate_repro_test")
    graph.add_edge("generate_repro_test", "run_repro_test")

    # -- Conditional: after running repro test --
    graph.add_conditional_edges(
        "run_repro_test",
        _route_after_repro_test,
        {
            "root_cause_analysis": "root_cause_analysis",
            "generate_repro_test": "generate_repro_test",
            "abort": "abort",
        },
    )

    # -- Linear edges (post-reproduction) --
    graph.add_edge("root_cause_analysis", "patch_generation")
    graph.add_edge("patch_generation", "validation")

    # -- Conditional: after validation --
    graph.add_conditional_edges(
        "validation",
        _route_after_validation,
        {
            "completion": "completion",
            "generate_repro_test": "generate_repro_test",
            "abort": "abort",
        },
    )

    # -- Terminal edges --
    graph.add_edge("completion", END)
    graph.add_edge("abort", END)

    return graph


def compile_graph():
    """Build and compile the graph, returning a runnable."""
    return build_graph().compile()


def invoke_graph(state, **kwargs):
    """Invoke the graph with increased recursion limit."""
    graph = compile_graph()
    return graph.invoke(state, {"recursion_limit": 100}, **kwargs)
