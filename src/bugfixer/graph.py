"""LangGraph state machine – wires all nodes into the agent workflow.

Graph topology
--------------

    START
      │
      ▼
  intake_context
      │
      ▼
  hypothesis_generation  ◄──────────────┐
      │                                 │
      ▼                                 │
  reproduction_attempt                  │
      │                                 │
      ▼                                 │
  reproduction_analysis ── (not reproduced) ─┘
      │ (reproduced)
      ▼
  root_cause_analysis
      │
      ▼
  verify_hypothesis  ◄─── NEW: generates secondary test
      │                   (should FAIL before fix)
      ▼
  patch_generation
      │
      ▼
  validation ──────── (fix failed) ──► hypothesis_generation
      │ (fix passed)    │
      │       verifies secondary test passes after fix
      ▼
  completion
      │
      ▼
    END
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from bugfixer.state import AgentState
from bugfixer.nodes.intake import intake_context
from bugfixer.nodes.hypothesis import hypothesis_generation
from bugfixer.nodes.reproduce import reproduction_attempt
from bugfixer.nodes.analyze import reproduction_analysis
from bugfixer.nodes.root_cause import root_cause_analysis
from bugfixer.nodes.verify_hypothesis import verify_hypothesis
from bugfixer.nodes.patch import patch_generation
from bugfixer.nodes.validate import validation
from bugfixer.nodes.complete import completion


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------

def _route_after_analysis(state: AgentState) -> str:
    """After reproduction analysis, decide whether to proceed or retry."""
    status = state.get("status", "")
    if status == "root_cause":
        return "root_cause_analysis"
    if status == "failed":
        return "abort"
    # Default: retry hypothesis
    return "hypothesis_generation"


def _route_after_validation(state: AgentState) -> str:
    """After validation, decide whether the fix worked or needs retry."""
    status = state.get("status", "")
    if status == "complete":
        return "completion"
    if status == "failed":
        return "abort"
    # Default: retry from hypothesis
    return "hypothesis_generation"


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
    graph.add_node("hypothesis_generation", hypothesis_generation)
    graph.add_node("reproduction_attempt", reproduction_attempt)
    graph.add_node("reproduction_analysis", reproduction_analysis)
    graph.add_node("root_cause_analysis", root_cause_analysis)
    graph.add_node("verify_hypothesis", verify_hypothesis)
    graph.add_node("patch_generation", patch_generation)
    graph.add_node("validation", validation)
    graph.add_node("completion", completion)
    graph.add_node("abort", _abort)

    # -- Entry point --
    graph.set_entry_point("intake_context")

    # -- Linear edges --
    graph.add_edge("intake_context", "hypothesis_generation")
    graph.add_edge("hypothesis_generation", "reproduction_attempt")
    graph.add_edge("reproduction_attempt", "reproduction_analysis")

    # -- Conditional: after reproduction analysis --
    graph.add_conditional_edges(
        "reproduction_analysis",
        _route_after_analysis,
        {
            "root_cause_analysis": "root_cause_analysis",
            "hypothesis_generation": "hypothesis_generation",
            "abort": "abort",
        },
    )

    # -- Linear edges (post-reproduction) --
    graph.add_edge("root_cause_analysis", "verify_hypothesis")
    graph.add_edge("verify_hypothesis", "patch_generation")
    graph.add_edge("patch_generation", "validation")

    # -- Conditional: after validation --
    graph.add_conditional_edges(
        "validation",
        _route_after_validation,
        {
            "completion": "completion",
            "hypothesis_generation": "hypothesis_generation",
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
