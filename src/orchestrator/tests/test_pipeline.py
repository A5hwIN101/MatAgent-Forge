# Purpose: Test each node and the full graph
# ============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest
import asyncio
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
    route_after_analysis
)
from src.orchestrator.pipeline_graph import get_pipeline_graph, run_pipeline


# ===== TEST: STATE CREATION =====

def test_create_initial_state():
    """Test that initial state is created correctly."""
    formula = "NaCl"
    state = create_initial_state(formula)
    
    # Check required fields
    assert state["formula"] == "NaCl"
    assert state["material_found"] is False
    assert state["chemistry_valid"] is False
    assert state["pipeline_status"] == "running"
    assert state["error_messages"] == []
    assert state["hypotheses"] == []
    
    print("✓ test_create_initial_state passed")


# ===== TEST: CONDITIONAL EDGES =====

def test_route_after_lookup_material_found():
    """Test routing when material is found."""
    state = create_initial_state("NaCl")
    state["material_found"] = True
    
    next_node = route_after_lookup(state)
    assert next_node == "validate_chemistry"
    
    print("✓ test_route_after_lookup_material_found passed")


def test_route_after_lookup_material_not_found():
    """Test routing when material is not found."""
    state = create_initial_state("UnknownMaterial123")
    state["material_found"] = False
    
    next_node = route_after_lookup(state)
    assert next_node == "error"
    assert len(state["error_messages"]) > 0
    
    print("✓ test_route_after_lookup_material_not_found passed")


def test_route_after_validation_valid():
    """Test routing when chemistry is valid."""
    state = create_initial_state("NaCl")
    state["chemistry_valid"] = True
    
    next_node = route_after_validation(state)
    assert next_node == "analyze"
    
    print("✓ test_route_after_validation_valid passed")


def test_route_after_validation_invalid():
    """Test routing when chemistry is invalid."""
    state = create_initial_state("NaCl")
    state["chemistry_valid"] = False
    state["validation_errors"] = ["Charge neutrality failed"]
    
    next_node = route_after_validation(state)
    assert next_node == "error"
    assert len(state["error_messages"]) > 0
    
    print("✓ test_route_after_validation_invalid passed")


def test_route_after_analysis_success():
    """Test routing after successful analysis."""
    state = create_initial_state("NaCl")
    state["analysis"] = {"electronic": "semiconductor"}
    state["analysis_error"] = None
    
    next_node = route_after_analysis(state)
    assert next_node == "hypothesize"
    
    print("✓ test_route_after_analysis_success passed")


def test_route_after_analysis_failure():
    """Test routing after failed analysis."""
    state = create_initial_state("NaCl")
    state["analysis"] = None
    state["analysis_error"] = "Analysis failed"
    
    next_node = route_after_analysis(state)
    assert next_node == "error"
    
    print("✓ test_route_after_analysis_failure passed")


# ===== TEST: NODES (INDIVIDUAL) =====

@pytest.mark.asyncio
async def test_lookup_node_not_found():
    """Test lookup node when material is not found."""
    state = create_initial_state("UnknownMaterial123")
    
    # This will fail because DataAgent doesn't have the material
    # We expect it to set material_found = False
    result = await lookup_node(state)
    
    # Should set material_found to False
    assert result["material_found"] is False
    
    print("✓ test_lookup_node_not_found passed")


@pytest.mark.asyncio
async def test_validate_chemistry_node_no_material():
    """Test validation node when material is not found."""
    state = create_initial_state("Test")
    state["material_found"] = False
    
    result = await validate_chemistry_node(state)
    
    assert result["chemistry_valid"] is False
    assert len(result["validation_errors"]) > 0
    
    print("✓ test_validate_chemistry_node_no_material passed")


@pytest.mark.asyncio
async def test_error_node():
    """Test error handler node."""
    state = create_initial_state("NaCl")
    state["error_messages"] = ["Test error 1", "Test error 2"]
    
    result = await error_node(state)
    
    assert result["pipeline_status"] == "error"
    assert result["formatted_output"] is not None
    assert "Test error 1" in result["formatted_output"]
    assert "Test error 2" in result["formatted_output"]
    
    print("✓ test_error_node passed")


# ===== TEST: FULL PIPELINE =====

@pytest.mark.asyncio
async def test_full_pipeline_graph_creation():
    """Test that the graph compiles without errors."""
    graph = get_pipeline_graph()
    assert graph is not None
    
    print("✓ test_full_pipeline_graph_creation passed")


@pytest.mark.asyncio
async def test_full_pipeline_execution():
    """Test full pipeline execution (will fail lookup but completes)."""
    formula = "UnknownMaterial123"
    final_state = await run_pipeline(formula)
    
    # Should have completed (either success or error)
    assert final_state["pipeline_status"] in ["success", "error"]
    
    # Should have formatted output
    assert final_state["formatted_output"] is not None
    
    print("✓ test_full_pipeline_execution passed")


# ===== MANUAL TEST RUNNER =====

async def run_all_tests():
    """Run all tests manually (without pytest)."""
    print("\n" + "="*60)
    print("RUNNING MANUAL TESTS")
    print("="*60 + "\n")
    
    # State tests
    test_create_initial_state()
    
    # Edge routing tests
    test_route_after_lookup_material_found()
    test_route_after_lookup_material_not_found()
    test_route_after_validation_valid()
    test_route_after_validation_invalid()
    test_route_after_analysis_success()
    test_route_after_analysis_failure()
    
    # Node tests
    print("\nTesting individual nodes...")
    await test_lookup_node_not_found()
    await test_validate_chemistry_node_no_material()
    await test_error_node()
    
    # Full pipeline tests
    print("\nTesting full pipeline...")
    await test_full_pipeline_graph_creation()
    await test_full_pipeline_execution()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run manual tests if executed directly
    asyncio.run(run_all_tests())