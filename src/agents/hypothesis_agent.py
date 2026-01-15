# ============================================================================
# HYPOTHESIS AGENT
# File: src/agents/hypothesis_agent.py
# Purpose: Generate application hypotheses from analyzed material properties
# ============================================================================

from typing import List, Dict, Any, Optional


def safe_float(val: Any) -> Optional[float]:
    """
    Safely convert a value to float.
    
    Args:
        val: Value to convert
    
    Returns:
        Float value or None if conversion fails
    """
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def generate_hypothesis(parsed: Dict[str, Any]) -> List[str]:
    """
    Generate application hypotheses from material properties.
    
    Args:
        parsed: Dictionary of material properties
    
    Returns:
        List of hypothesis strings
    """
    print("DEBUG parsed keys:", list(parsed.keys()))
    hypotheses = []

    band_gap = safe_float(parsed.get("band_gap"))
    e_hull = safe_float(parsed.get("energy_above_hull"))
    density = safe_float(parsed.get("density"))
    symmetry = parsed.get("symmetry", {}).get("crystal_system")

    # Electronic hypotheses
    if band_gap is not None:
        if band_gap > 2.0:
            hypotheses.append(f"Wide-bandgap semiconductor (~{band_gap:.2f} eV), potential for UV optoelectronics.")
        elif 0.5 < band_gap <= 2.0:
            hypotheses.append(f"Narrow-bandgap semiconductor (~{band_gap:.2f} eV), possible IR/thermoelectric applications.")
        elif band_gap <= 0.1:
            hypotheses.append("Likely metallic, useful for conductive layers or contacts.")

    # Stability hypotheses
    if e_hull is not None:
        if e_hull < 0.05:
            hypotheses.append(f"Stable phase (energy above hull {e_hull:.3f} eV/atom), synthesis feasible.")
        else:
            hypotheses.append(f"Metastable phase (energy above hull {e_hull:.3f} eV/atom), may need special synthesis routes.")

    # Density-based hypothesis
    if density is not None:
        if density > 7.0:
            hypotheses.append(f"High density ({density:.2f} g/cm³), potential for radiation shielding or heavy-metal applications.")
        elif density < 2.0:
            hypotheses.append(f"Low density ({density:.2f} g/cm³), lightweight material suitable for structural or aerospace uses.")

    # Symmetry-based hypothesis
    if symmetry:
        hypotheses.append(f"{symmetry} crystal system may enable anisotropic optical or electronic properties.")

    if not hypotheses:
        hypotheses.append("No specific hypotheses generated from available data.")

    return hypotheses


# ============================================================================
# HYPOTHESIS AGENT CLASS - For LangGraph Integration
# ============================================================================

class HypothesisAgent:
    """
    HypothesisAgent generates application hypotheses from material properties.
    
    This agent is designed to work with the LangGraph pipeline.
    """
    
    def __init__(self):
        """Initialize the HypothesisAgent."""
        pass
    
    async def run(
        self,
        analysis: Dict[str, Any],
        properties: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate hypotheses from analysis and properties.
        
        Args:
            analysis: Dictionary of analyzed properties
            properties: Dictionary of raw material properties
        
        Returns:
            List of hypothesis dictionaries with 'hypothesis' and 'reasoning' keys
        """
        try:
            print(f"[HypothesisAgent.run] Generating hypotheses")
            
            # Generate hypotheses from properties
            hypothesis_strings = generate_hypothesis(properties)
            
            # Convert to structured format
            hypotheses = [
                {
                    "hypothesis": h,
                    "reasoning": "Derived from material properties analysis"
                }
                for h in hypothesis_strings
            ]
            
            print(f"[HypothesisAgent.run] ✓ Generated {len(hypotheses)} hypotheses")
            return hypotheses
        
        except Exception as e:
            print(f"[HypothesisAgent.run] ✗ Error: {e}")
            raise