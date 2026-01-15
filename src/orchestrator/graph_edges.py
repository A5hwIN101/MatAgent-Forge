# Purpose: Define routing logic between nodes
# ============================================================================

from src.orchestrator.pipeline_state import PipelineState


def route_after_lookup(state: PipelineState) -> str:
    """
    After lookup, decide next step.
    
    If material found → validate chemistry
    If not found → error handler
    """
    if state.get("material_found"):
        return "validate_chemistry"
    else:
        state["error_messages"].append(
            f"Material '{state['formula']}' not found in Materials Project database"
        )
        return "error"


def route_after_validation(state: PipelineState) -> str:
    """
    After validation, decide next step.
    
    If chemistry valid → analyze
    If invalid → error handler
    """
    if state.get("chemistry_valid"):
        return "analyze"
    else:
        errors = state.get("validation_errors", [])
        for error in errors:
            state["error_messages"].append(f"Validation failed: {error}")
        return "error"


def route_after_analysis(state: PipelineState) -> str:
    """
    After analysis, decide next step.
    
    If analysis succeeded → hypothesize
    If error → error handler
    """
    if state.get("analysis") and not state.get("analysis_error"):
        return "hypothesize"
    else:
        error = state.get("analysis_error")
        if error:
            state["error_messages"].append(f"Analysis error: {error}")
        return "error"


def route_after_hypothesis(state: PipelineState) -> str:
    """
    After hypothesis generation, decide next step.
    
    Always format (even if hypotheses are empty)
    """
    if state.get("hypotheses_error"):
        state["error_messages"].append(f"Hypothesis generation error: {state['hypotheses_error']}")
    
    return "format"