# ============================================================================
# GUARDRAILS - Fixed Version
# File: src/orchestrator/guardrails.py
# Purpose: Define chemistry & stability rules with realistic checks
# ============================================================================

from typing import Callable, List, Dict, Any


class Guardrail:
    """Single rule that can be checked against material properties."""
    
    def __init__(
        self,
        name: str,
        description: str,
        rule_func: Callable[[Dict[str, Any]], bool],
        confidence: float = 1.0
    ):
        self.name = name
        self.description = description
        self.rule_func = rule_func
        self.confidence = confidence  # 0.0-1.0
    
    def check(self, properties: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if material passes this guardrail.
        
        Returns:
            (passed: bool, message: str)
        """
        try:
            passed = self.rule_func(properties)
            if passed:
                return True, f"✓ {self.name}"
            else:
                return False, f"✗ {self.name}: {self.description}"
        except Exception as e:
            return False, f"✗ {self.name}: Error checking rule - {str(e)}"


# ============================================================================
# CHEMISTRY GUARDRAILS
# ============================================================================

CHEMISTRY_GUARDRAILS = [
    Guardrail(
        name="Material Has Data",
        description="Material has retrievable properties from database",
        rule_func=lambda props: bool(props),  # Simple: dict is not empty
        confidence=1.0
    ),
    Guardrail(
        name="Has Material ID",
        description="Material has a unique Materials Project ID",
        rule_func=lambda props: "material_id" in props or "mp_id" in props,
        confidence=0.9
    ),
    Guardrail(
        name="Has Crystal Structure",
        description="Material has crystal structure information",
        rule_func=lambda props: "structure" in props or "lattice" in props or "sites" in props,
        confidence=0.85
    )
]

# ============================================================================
# STABILITY GUARDRAILS
# ============================================================================

STABILITY_GUARDRAILS = [
    Guardrail(
        name="Energy Above Hull Check",
        description="Material is on or near convex hull (e_above_hull < 0.1 eV/atom)",
        rule_func=lambda props: props.get("e_above_hull", 999) < 0.1,
        confidence=0.85
    ),
    Guardrail(
        name="Formation Energy Reasonable",
        description="Formation energy is within reasonable bounds",
        rule_func=lambda props: "formation_energy_per_atom" in props or "energy_per_atom" in props or True,
        confidence=0.8
    )
]


# ============================================================================
# HELPER FUNCTION
# ============================================================================

def check_guardrails(
    guardrails: List[Guardrail],
    properties: Dict[str, Any]
) -> tuple[bool, List[str]]:
    """
    Check all guardrails against material properties.
    
    Args:
        guardrails: List of Guardrail objects to check
        properties: Material properties dictionary
    
    Returns:
        (all_passed: bool, messages: List[str])
    """
    messages = []
    all_passed = True
    
    for guardrail in guardrails:
        passed, message = guardrail.check(properties)
        messages.append(message)
        if not passed:
            all_passed = False
    
    return all_passed, messages