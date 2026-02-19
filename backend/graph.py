from langgraph.graph import StateGraph, END
from backend.state import AgentState
from backend.nodes.discovery import discovery_node
from backend.nodes.tester import tester_node
from backend.nodes.debugger import debugger_node
from backend.nodes.fixer import fixer_node
from backend.nodes.git_node import git_node
from backend.scoring import scoring_node

MAX_RETRIES = 5

# ── Short-circuit if clone/discovery failed ───────────────────────
def check_discovery_status(state: AgentState):
    if state.get('current_step') == 'DISCOVERY_FAILED':
        return 'failed'
    return 'ok'

# ── Conditional Logic (after tester) ─────────────────────────────
def check_test_status(state: AgentState):
    if state.get('final_status') == "PASSED":
        return "passed"
    # retry_count is already incremented by tester_node after each failure
    retry_count = state.get('retry_count', 0)
    max_retries = state.get('max_iterations', 5)
    if retry_count >= max_retries:
        return "max_retries"
    return "failed"

def create_workflow():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("discovery", discovery_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("debugger", debugger_node)
    workflow.add_node("fixer", fixer_node)
    workflow.add_node("git", git_node)
    workflow.add_node("scoring", scoring_node)

    # Add Edges
    workflow.set_entry_point("discovery")

    # Short-circuit: if discovery failed (zombie dir / empty clone), skip straight to scoring
    workflow.add_conditional_edges(
        "discovery",
        check_discovery_status,
        {
            "ok": "tester",
            "failed": "scoring",
        }
    )

    # Conditional Edge from Tester
    workflow.add_conditional_edges(
        "tester",
        check_test_status,
        {
            "passed": "scoring",
            "failed": "debugger",
            "max_retries": "scoring",  # End if max retries reached
        }
    )

    # Conditional Edge from Debugger (Guardrail: prevent fixing if no bugs found)
    def check_debugger_status(state: AgentState):
        if state.get('current_step') == "NO_BUGS_FOUND":
            return "stop"
        return "continue"

    workflow.add_conditional_edges(
        "debugger",
        check_debugger_status,
        {
            "continue": "fixer",
            "stop": "scoring",
        }
    )
    workflow.add_edge("fixer", "git")
    workflow.add_edge("git", "tester")
    workflow.add_edge("scoring", END)

    # Compile with a safe recursion limit:
    # Each iteration = 4 nodes (debugger->fixer->git->tester) + 2 (discovery, scoring) = 4*MAX_RETRIES + 2
    recursion_limit = MAX_RETRIES * 6 + 10
    return workflow.compile()

def get_workflow_config():
    """Returns the config dict for ainvoke with a safe recursion limit."""
    recursion_limit = MAX_RETRIES * 6 + 10
    return {"recursion_limit": recursion_limit}
