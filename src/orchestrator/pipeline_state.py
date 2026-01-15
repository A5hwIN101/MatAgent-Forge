# Purpose: Define the explicit state that flows through all nodes
# ============================================================================

from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    """
    Explicit state passed through all nodes in the analysis pipeline.
    
    This is the single source of truth for what data exists at each step.
    Every node receives this state, modifies it, and returns it.
    """
    
    # ===== INPUT =====
    formula: str  # Material formula entered by user (e.g., "NaCl", "Fe2O3")
    
    # ===== AFTER LOOKUP NODE =====
    material_data: Optional[Dict[str, Any]]  # Raw data from Materials Project API
    lookup_error: Optional[str]  # Error message if lookup failed
    material_found: bool  # True if material exists in database
    
    # ===== AFTER VALIDATION NODE =====
    chemistry_valid: bool  # True if chemistry guardrails passed
    validation_errors: List[str]  # List of validation violations
    
    # ===== AFTER ANALYSIS NODE =====
    analysis: Optional[Dict[str, Any]]  # Analyzed properties (electronic, mechanical, thermal)
    analysis_error: Optional[str]  # Error message if analysis failed
    
    # ===== AFTER HYPOTHESIS NODE =====
    hypotheses: List[Dict[str, Any]]  # Generated application hypotheses
    hypotheses_error: Optional[str]  # Error message if hypothesis generation failed
    
    # ===== AFTER FORMAT NODE =====
    formatted_output: Optional[str]  # Final markdown output
    
    # ===== ERROR TRACKING (GLOBAL) =====
    pipeline_status: str  # "running" | "success" | "error"
    error_messages: List[str]  # All errors that occurred during execution


def create_initial_state(formula: str) -> PipelineState:
    """
    Create initial state for a new pipeline run.
    
    Args:
        formula: Material formula (e.g., "NaCl")
    
    Returns:
        Initialized PipelineState
    """
    return {
        "formula": formula,
        "material_data": None,
        "lookup_error": None,
        "material_found": False,
        "chemistry_valid": False,
        "validation_errors": [],
        "analysis": None,
        "analysis_error": None,
        "hypotheses": [],
        "hypotheses_error": None,
        "formatted_output": None,
        "pipeline_status": "running",
        "error_messages": []
    }