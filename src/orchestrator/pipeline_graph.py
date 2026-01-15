# Purpose: Create and compile the StateGraph
# ============================================================================

from langgraph.graph import StateGraph, END
from src.orchestrator.pipeline_state import PipelineState, create_initial_state
from src.orchestrator.graph_nodes import (
    lookup_node,
    validate_chemistry_node,
    analyze_node,
    hypothesize_node,
    format_node,
    error_node
)
from src.orchestrator.graph_edges import (
    route_after_lookup,
    route_after_validation,
    route_after_analysis,
    route_after_hypothesis
)


def create_pipeline_graph():
    """
    Create the analysis pipeline as a LangGraph StateGraph.
    
    Structure:
    lookup → validate_chemistry → analyze → hypothesize → format → END
                     ↓                                        ↓
                  error ──────────────────────────────────────→ END
    
    Returns:
        Compiled StateGraph ready for execution
    """
    
    # Initialize the graph with state schema
    graph = StateGraph(PipelineState)
    
    # ===== ADD NODES =====
    print("[create_pipeline_graph] Adding nodes...")
    
    graph.add_node("lookup", lookup_node)
    graph.add_node("validate_chemistry", validate_chemistry_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("hypothesize", hypothesize_node)
    graph.add_node("format", format_node)
    graph.add_node("error", error_node)
    
    print("[create_pipeline_graph] ✓ All 6 nodes added")
    
    # ===== ADD EDGES =====
    print("[create_pipeline_graph] Adding edges...")
    
    # lookup → validate_chemistry (direct edge, always goes to validation)
    graph.add_edge("lookup", "validate_chemistry")
    
    # validate_chemistry → (analyze OR error) based on chemistry_valid
    graph.add_conditional_edges(
        "validate_chemistry",
        route_after_validation,
        {
            "analyze": "analyze",
            "error": "error"
        }
    )
    
    # analyze → (hypothesize OR error) based on analysis success
    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "hypothesize": "hypothesize",
            "error": "error"
        }
    )
    
    # hypothesize → format (always goes to format, even if hypotheses are empty)
    graph.add_edge("hypothesize", "format")
    
    # format → END (success path)
    graph.add_edge("format", END)
    
    # error → END (error path)
    graph.add_edge("error", END)
    
    print("[create_pipeline_graph] ✓ All edges connected")
    
    # ===== SET ENTRY POINT =====
    graph.set_entry_point("lookup")
    print("[create_pipeline_graph] ✓ Entry point set to 'lookup'")
    
    # ===== COMPILE =====
    print("[create_pipeline_graph] Compiling graph...")
    compiled_graph = graph.compile()
    print("[create_pipeline_graph] ✓ Graph compiled successfully")
    
    return compiled_graph


# ===== SINGLETON PATTERN =====
_graph_instance = None


def get_pipeline_graph():
    """
    Get or create the singleton pipeline graph.
    
    This ensures we only compile the graph once and reuse it.
    
    Returns:
        Compiled StateGraph
    """
    global _graph_instance
    
    if _graph_instance is None:
        _graph_instance = create_pipeline_graph()
    
    return _graph_instance


# ===== HELPER FUNCTIONS FOR TESTING =====

async def run_pipeline(formula: str):
    """
    Run the pipeline for a given material formula.
    
    Args:
        formula: Material formula (e.g., "NaCl")
    
    Returns:
        Final state after pipeline execution
    """
    graph = get_pipeline_graph()
    initial_state = create_initial_state(formula)
    
    print(f"\n{'='*60}")
    print(f"RUNNING PIPELINE FOR: {formula}")
    print(f"{'='*60}\n")
    
    # Run the graph
    final_state = await graph.ainvoke(initial_state)
    
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE - Status: {final_state.get('pipeline_status')}")
    print(f"{'='*60}\n")
    
    return final_state


def visualize_graph():
    """
    Print the graph structure for debugging.
    
    Useful to verify connections and flow.
    """
    graph = get_pipeline_graph()
    
    print("\n" + "="*60)
    print("PIPELINE GRAPH STRUCTURE")
    print("="*60)
    
    # Print node connections
    print("\nNODES:")
    print("  1. lookup (Data Agent)")
    print("  2. validate_chemistry (Guardrail Checker)")
    print("  3. analyze (Analysis Agent)")
    print("  4. hypothesize (Hypothesis Agent)")
    print("  5. format (Output Formatter)")
    print("  6. error (Error Handler)")
    
    print("\nEDGES:")
    print("  lookup → validate_chemistry")
    print("  validate_chemistry → analyze (if chemistry_valid=True)")
    print("  validate_chemistry → error (if chemistry_valid=False)")
    print("  analyze → hypothesize (if analysis successful)")
    print("  analyze → error (if analysis failed)")
    print("  hypothesize → format")
    print("  format → END")
    print("  error → END")
    
    print("\nENTRY POINT: lookup")
    print("EXIT POINTS: END (via format or error)")
    print("="*60 + "\n")