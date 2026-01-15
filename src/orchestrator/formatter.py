# ============================================================================
# FORMATTER
# File: src/orchestrator/formatter.py
# Purpose: Format analysis results into markdown output
# ============================================================================

from typing import Dict, List, Optional, Tuple, Any
import re


# ============================================================================
# HELPER FUNCTIONS (Original)
# ============================================================================

def format_analysis_value(value: Any) -> str:
    """
    Format an analysis value for display.
    
    Args:
        value: Value to format (can be str, float, dict, list, etc.)
    
    Returns:
        Formatted string
    """
    if isinstance(value, dict):
        # Format dictionary as key: value pairs
        items = [f"  - {k}: {v}" for k, v in value.items()]
        return "\n".join(items)
    elif isinstance(value, list):
        # Format list as bullet points
        items = [f"  - {item}" for item in value]
        return "\n".join(items)
    elif isinstance(value, float):
        return f"{value:.4f}"
    else:
        return str(value)


def format_rules_section(rules: List[Dict[str, Any]]) -> str:
    """
    Format rules into a readable section.
    
    Args:
        rules: List of rule dictionaries
    
    Returns:
        Formatted markdown string
    """
    if not rules:
        return ""
    
    lines = ["### Rule-Based Insights\n"]
    
    for rule in rules:
        rule_text = rule.get("rule_text", "")
        confidence = rule.get("confidence", 0.0)
        category = rule.get("category", "unknown")
        
        lines.append(f"- **{rule_text}**")
        lines.append(f"  - Category: {category}")
        lines.append(f"  - Confidence: {confidence:.2%}")
    
    return "\n".join(lines)


def parse_rule_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse rule information from text.
    
    Args:
        text: Text containing rule information
    
    Returns:
        Rule dictionary or None
    """
    # Simple regex-based parsing
    rule_pattern = r"Rule:\s*(.+?)(?:\n|$)"
    match = re.search(rule_pattern, text)
    
    if match:
        return {
            "rule_text": match.group(1),
            "confidence": 0.8,
            "category": "general"
        }
    return None


def assemble_markdown(
    formula: str,
    material_data: Optional[Dict[str, Any]] = None,
    analysis: Optional[Dict[str, Any]] = None,
    hypotheses: Optional[List[Dict[str, str]]] = None,
    errors: Optional[List[str]] = None,
    validation_errors: Optional[List[str]] = None
) -> str:
    """
    Assemble analysis results into markdown format.
    
    Args:
        formula: Material formula
        material_data: Raw material properties
        analysis: Analyzed properties
        hypotheses: Generated hypotheses
        errors: Pipeline errors
        validation_errors: Validation errors
    
    Returns:
        Markdown formatted string
    """
    lines = []
    
    # Header
    lines.append(f"# Material Analysis: {formula}\n")
    
    # Material Properties
    if material_data:
        lines.append("## Material Properties\n")
        
        # Key properties table
        key_props = {
            "Band Gap (eV)": material_data.get("band_gap"),
            "Energy Above Hull (eV/atom)": material_data.get("energy_above_hull"),
            "Density (g/cm³)": material_data.get("density"),
            "Bulk Modulus (GPa)": material_data.get("bulk_modulus"),
            "Shear Modulus (GPa)": material_data.get("shear_modulus"),
            "Crystal System": material_data.get("symmetry", {}).get("crystal_system"),
            "Space Group": material_data.get("symmetry", {}).get("space_group_number")
        }
        
        lines.append("| Property | Value |")
        lines.append("|----------|-------|")
        
        for prop_name, prop_value in key_props.items():
            if prop_value is not None:
                if isinstance(prop_value, float):
                    lines.append(f"| {prop_name} | {prop_value:.4f} |")
                else:
                    lines.append(f"| {prop_name} | {prop_value} |")
        
        lines.append("")
    
    # Analysis Results
    if analysis:
        lines.append("## Property Analysis\n")
        
        for section, content in analysis.items():
            if section != "Rule-Based Insights":  # Handle separately
                lines.append(f"### {section}\n")
                lines.append(f"{content}\n")
        
        # Add rule-based insights if present
        if "Rule-Based Insights" in analysis:
            lines.append(f"### Rule-Based Insights\n")
            lines.append(f"{analysis['Rule-Based Insights']}\n")
    
    # Hypotheses
    if hypotheses and len(hypotheses) > 0:
        lines.append("## Generated Hypotheses\n")
        
        for i, hyp in enumerate(hypotheses, 1):
            if isinstance(hyp, dict):
                hyp_text = hyp.get("hypothesis", str(hyp))
            else:
                hyp_text = str(hyp)
            
            lines.append(f"{i}. {hyp_text}\n")
    
    # Errors (if any)
    if errors or validation_errors:
        lines.append("## Notes\n")
        
        if validation_errors:
            lines.append("**Validation Notes:**\n")
            for error in validation_errors:
                lines.append(f"- {error}")
            lines.append("")
        
        if errors:
            lines.append("**Pipeline Notices:**\n")
            for error in errors:
                lines.append(f"- {error}")
            lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# FORMATTER CLASS - For LangGraph Integration
# ============================================================================

class Formatter:
    """
    Formatter converts analysis results into formatted markdown output.
    
    This class is designed to work with the LangGraph pipeline.
    """
    
    def __init__(self):
        """Initialize the Formatter."""
        pass
    
    def format(
        self,
        formula: str,
        material_data: Optional[Dict[str, Any]] = None,
        analysis: Optional[Dict[str, Any]] = None,
        hypotheses: Optional[List[Dict[str, str]]] = None,
        errors: Optional[List[str]] = None,
        validation_errors: Optional[List[str]] = None
    ) -> str:
        """
        Format analysis results into markdown.
        
        Args:
            formula: Material formula
            material_data: Raw material properties
            analysis: Analyzed properties
            hypotheses: Generated hypotheses
            errors: Pipeline errors
            validation_errors: Validation errors
        
        Returns:
            Formatted markdown string
        """
        try:
            output = assemble_markdown(
                formula=formula,
                material_data=material_data,
                analysis=analysis,
                hypotheses=hypotheses,
                errors=errors,
                validation_errors=validation_errors
            )
            
            print(f"[Formatter.format] ✓ Formatted output for {formula}")
            return output
        
        except Exception as e:
            print(f"[Formatter.format] ✗ Error: {e}")
            raise