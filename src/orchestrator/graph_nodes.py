# Purpose: Implement each step of the pipeline as a node
# ============================================================================

import os
from src.orchestrator.pipeline_state import PipelineState
from src.orchestrator.guardrails import check_guardrails, CHEMISTRY_GUARDRAILS


async def lookup_node(state: PipelineState) -> PipelineState:
    """
    NODE 1: Lookup material in Materials Project API
    
    Input: formula (str)
    Output: material_data, material_found, lookup_error
    """
    print(f"\n[lookup_node] Starting lookup for: {state['formula']}")
    
    try:
        # Import inside function to avoid circular imports
        from src.agents.data_agent import DataAgent
        
        agent = DataAgent()
        material_data = await agent.run(state["formula"])
        
        if material_data:
            state["material_data"] = material_data
            state["material_found"] = True
            state["lookup_error"] = None
            print(f"[lookup_node] ✓ Found material data")
        else:
            state["material_data"] = None
            state["material_found"] = False
            state["lookup_error"] = "No data returned from API"
            print(f"[lookup_node] ✗ No data found")
    
    except Exception as e:
        state["lookup_error"] = str(e)
        state["material_found"] = False
        state["material_data"] = None
        print(f"[lookup_node] ✗ Exception: {e}")
    
    return state


async def validate_chemistry_node(state: PipelineState) -> PipelineState:
    """
    NODE 2: Validate chemistry guardrails
    
    Input: material_data (optional), material_found
    Output: chemistry_valid, validation_errors
    """
    print(f"\n[validate_chemistry_node] Validating chemistry rules")
    
    # If material not found, skip validation
    if not state.get("material_found"):
        state["chemistry_valid"] = False
        state["validation_errors"] = ["Cannot validate: material not found in database"]
        print(f"[validate_chemistry_node] ✗ Skipping: material not found")
        return state
    
    # Check guardrails
    material_data = state.get("material_data", {})
    all_passed, messages = check_guardrails(CHEMISTRY_GUARDRAILS, material_data)
    
    state["chemistry_valid"] = all_passed
    state["validation_errors"] = [msg for msg in messages if msg.startswith("✗")]
    
    print(f"[validate_chemistry_node] Valid: {all_passed}")
    for msg in messages:
        print(f"  {msg}")
    
    return state


async def analyze_node(state: PipelineState) -> PipelineState:
    """
    NODE 3: Analyze material properties
    
    Input: material_data, formula
    Output: analysis, analysis_error
    """
    print(f"\n[analyze_node] Analyzing material properties")
    
    if not state.get("material_found"):
        state["analysis"] = None
        state["analysis_error"] = "Cannot analyze: material not found"
        print(f"[analyze_node] ✗ Skipping: material not found")
        return state
    
    try:
        from src.agents.analysis_agent import AnalysisAgent
        
        agent = AnalysisAgent()
        material_data = state.get("material_data", {})
        
        analysis = await agent.run(
            properties=material_data,
            formula=state["formula"]
        )
        
        state["analysis"] = analysis
        state["analysis_error"] = None
        print(f"[analyze_node] ✓ Analysis complete")
    
    except Exception as e:
        state["analysis"] = None
        state["analysis_error"] = str(e)
        print(f"[analyze_node] ✗ Exception: {e}")
    
    return state


async def hypothesize_node(state: PipelineState) -> PipelineState:
    """
    NODE 4: Generate application hypotheses
    
    Input: analysis, material_data
    Output: hypotheses, hypotheses_error
    """
    print(f"\n[hypothesize_node] Generating hypotheses")
    
    if not state.get("analysis"):
        state["hypotheses"] = []
        state["hypotheses_error"] = "Cannot hypothesize: analysis did not complete"
        print(f"[hypothesize_node] ✗ Skipping: no analysis data")
        return state
    
    try:
        from src.agents.hypothesis_agent import HypothesisAgent
        
        agent = HypothesisAgent()
        
        hypotheses = await agent.run(
            analysis=state["analysis"],
            properties=state.get("material_data", {})
        )
        
        state["hypotheses"] = hypotheses if isinstance(hypotheses, list) else [hypotheses]
        state["hypotheses_error"] = None
        print(f"[hypothesize_node] ✓ Generated {len(state['hypotheses'])} hypotheses")
    
    except Exception as e:
        state["hypotheses"] = []
        state["hypotheses_error"] = str(e)
        print(f"[hypothesize_node] ✗ Exception: {e}")
    
    return state


async def format_node(state: PipelineState) -> PipelineState:
    """
    NODE 5: Format final output as markdown
    
    Input: formula, material_data, analysis, hypotheses, error_messages
    Output: formatted_output, pipeline_status
    """
    print(f"\n[format_node] Formatting output")
    
    try:
        from src.orchestrator.formatter import Formatter
        
        formatter = Formatter()
        
        output = formatter.format(
            formula=state.get("formula", "Unknown"),
            material_data=state.get("material_data"),
            analysis=state.get("analysis"),
            hypotheses=state.get("hypotheses", []),
            errors=state.get("error_messages", []),
            validation_errors=state.get("validation_errors", [])
        )
        
        state["formatted_output"] = output
        state["pipeline_status"] = "success"
        print(f"[format_node] ✓ Output formatted")
    
    except Exception as e:
        state["formatted_output"] = f"Error formatting output: {str(e)}"
        state["pipeline_status"] = "error"
        state["error_messages"].append(f"Formatting error: {e}")
        print(f"[format_node] ✗ Exception: {e}")
    
    return state


async def error_node(state: PipelineState) -> PipelineState:
    """
    NODE 6: Handle errors gracefully
    
    Input: error_messages, formula, pipeline_status
    Output: formatted_output, pipeline_status
    """
    print(f"\n[error_node] Handling pipeline error")
    
    error_report = f"""# Error Report: {state.get('formula', 'Unknown Material')}

## Status
Pipeline failed with the following error(s):

"""
    
    for i, error in enumerate(state.get("error_messages", []), 1):
        error_report += f"{i}. {error}\n"
    
    if state.get("validation_errors"):
        error_report += "\n## Validation Issues\n"
        for error in state.get("validation_errors", []):
            error_report += f"- {error}\n"
    
    error_report += """
## Next Steps
1. Check that the material formula is correct (e.g., "NaCl", "Fe2O3")
2. Verify the material exists in the Materials Project database
3. Try a different material and try again
"""
    
    state["formatted_output"] = error_report
    state["pipeline_status"] = "error"
    
    return state