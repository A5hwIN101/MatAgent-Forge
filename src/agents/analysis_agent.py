"""
Analysis Agent Module

Analyzes material properties from parsed data and enhances analysis with 
extracted rules from literature. Integrates quantitative rules to provide 
evidence-backed insights about material properties and potential applications.
"""

from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Import rule loader
try:
    from src.data_sources.rule_loader import RuleLoader
    RULE_LOADER_AVAILABLE = True
except ImportError as e:
    RULE_LOADER_AVAILABLE = False
    logging.warning(f"RuleLoader not available: {e}. Analysis will continue without rules.")

load_dotenv()

# Heavy model for deep reasoning
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile"
)

# Initialize rule loader at module level (cached for performance)
rule_loader: Optional[RuleLoader] = None
rules_cache: List[Dict] = []

if RULE_LOADER_AVAILABLE:
    try:
        rule_loader = RuleLoader()
        rules_cache = rule_loader.load_rules()
        logger.info(f"Loaded {len(rules_cache)} rules into cache for analysis agent")
    except Exception as e:
        logger.warning(f"Failed to load rules in analysis agent: {e}. Continuing without rules.")
        rule_loader = None
        rules_cache = []


def get_relevant_rules(material_properties: dict) -> List[Dict]:
    """
    Get rules relevant to the material's properties.
    
    Searches for rules matching property keywords (band_gap, formation_energy,
    bulk_modulus, energy_above_hull, etc.) and returns relevant rules sorted
    by confidence and category.
    
    Args:
        material_properties: Dictionary of material properties from parsed data
        
    Returns:
        List of relevant rule dictionaries, sorted by confidence (highest first)
    """
    if not rule_loader or not rules_cache:
        return []
    
    try:
        # Use RuleLoader's built-in method to get relevant rules
        relevant_rules = rule_loader.get_rules_for_analysis(material_properties)
        
        # Filter out rules with very low confidence (already filtered in rule_extractor)
        # but we can add an additional filter here if needed
        relevant_rules = [r for r in relevant_rules if r.get('confidence', 0) >= 0.7]
        
        logger.debug(f"Found {len(relevant_rules)} relevant rules for material properties")
        return relevant_rules
        
    except Exception as e:
        logger.warning(f"Error retrieving relevant rules: {e}")
        return []


def format_rules_for_analysis(rules: List[Dict], max_rules: int = 5) -> str:
    """
    Format rules into a readable string for inclusion in analysis.
    
    Args:
        rules: List of rule dictionaries
        max_rules: Maximum number of rules to include (default: 5)
        
    Returns:
        Formatted string with rule information
    """
    if not rules:
        return ""
    
    # Take top N rules by confidence
    top_rules = sorted(rules, key=lambda r: r.get('confidence', 0), reverse=True)[:max_rules]
    
    formatted = []
    for rule in top_rules:
        rule_text = rule.get('rule_text', '')
        category = rule.get('category', 'unknown')
        confidence = rule.get('confidence', 0.0)
        
        formatted.append(f"  • {rule_text} (category: {category}, confidence: {confidence:.2f})")
    
    if len(rules) > max_rules:
        formatted.append(f"  ... and {len(rules) - max_rules} more rules")
    
    return "\n".join(formatted)


def analyze_material_properties(parsed: dict) -> dict:
    """
    Analyze material properties and enhance with rule-based insights.
    
    Analyzes material properties (band gap, formation energy, bulk modulus,
    energy above hull, etc.) and incorporates relevant extracted rules from
    literature to provide evidence-backed insights.
    
    Args:
        parsed: Dictionary of parsed material data from Materials Project
        
    Returns:
        Dictionary with analysis results, including:
        - Thermal Behavior
        - Mechanical Behavior (with rule-based insights if available)
        - Electronic Behavior (with rule-based insights if available)
        - Stability / Limitations (with rule-based insights if available)
        - Rule-Based Insights (new section with relevant rules)
    """
    analysis = {}
    
    # Get relevant rules for this material's properties
    relevant_rules = get_relevant_rules(parsed)
    rules_by_category = {}
    if relevant_rules:
        # Group rules by category for easier reference
        for rule in relevant_rules:
            category = rule.get('category', 'unknown')
            if category not in rules_by_category:
                rules_by_category[category] = []
            rules_by_category[category].append(rule)
        logger.info(f"Using {len(relevant_rules)} rules in analysis across {len(rules_by_category)} categories")

    # Thermal Behavior (no thermal props yet, so placeholder)
    analysis["Thermal Behavior"] = "No thermal data available in this query."

    # Mechanical Behavior (check if bulk/shear modulus exist)
    if "bulk_modulus" in parsed and parsed["bulk_modulus"]:
        bulk_mod = parsed["bulk_modulus"]
        analysis["Mechanical Behavior"] = f"Bulk modulus: {bulk_mod} GPa"
        
        # Add rule-based insights for bulk modulus
        mechanical_rules = [
            r for r in relevant_rules 
            if 'bulk modulus' in r.get('rule_text', '').lower() or 
               r.get('category') == 'property_application'
        ]
        if mechanical_rules:
            # Look for bulk modulus specific rules
            bulk_rules = [r for r in mechanical_rules if 'bulk modulus' in r.get('rule_text', '').lower()]
            if bulk_rules:
                top_rule = max(bulk_rules, key=lambda r: r.get('confidence', 0))
                analysis["Mechanical Behavior"] += f"\n  Rule: {top_rule.get('rule_text', '')}"
    else:
        analysis["Mechanical Behavior"] = "No mechanical signals identified."

    # Electronic Behavior (band gap, metallicity)
    band_gap = parsed.get("band_gap")
    if band_gap is not None:
        if band_gap > 0.1:
            analysis["Electronic Behavior"] = f"Semiconductor with band gap {band_gap:.2f} eV"
        else:
            analysis["Electronic Behavior"] = "Likely metallic (very small band gap)"
        
        # Add rule-based insights for band gap
        electronic_rules = [
            r for r in relevant_rules 
            if 'band gap' in r.get('rule_text', '').lower() or
               (r.get('category') == 'property_application' and 'band' in r.get('rule_text', '').lower())
        ]
        if electronic_rules:
            # Sort by relevance (band gap specific first)
            band_gap_rules = [r for r in electronic_rules if 'band gap' in r.get('rule_text', '').lower()]
            if band_gap_rules:
                top_rule = max(band_gap_rules, key=lambda r: r.get('confidence', 0))
                analysis["Electronic Behavior"] += f"\n  Rule: {top_rule.get('rule_text', '')}"
    else:
        analysis["Electronic Behavior"] = "No band gap data available."

    # Stability / Limitations (energy above hull)
    e_hull = parsed.get("energy_above_hull")
    formation_energy = parsed.get("formation_energy_per_atom") or parsed.get("formation_energy")
    
    if e_hull is not None:
        if e_hull < 0.05:
            analysis["Limitations"] = f"Stable phase (energy above hull {e_hull:.3f} eV/atom)"
        else:
            analysis["Limitations"] = f"Metastable (energy above hull {e_hull:.3f} eV/atom)"
        
        # Add rule-based insights for stability
        stability_rules = [
            r for r in relevant_rules 
            if r.get('category') in ['stability', 'synthesis'] or
               'energy above hull' in r.get('rule_text', '').lower() or
               'formation energy' in r.get('rule_text', '').lower()
        ]
        if stability_rules:
            # Prefer rules that match the actual e_hull value
            e_hull_rules = [r for r in stability_rules if 'energy above hull' in r.get('rule_text', '').lower()]
            if e_hull_rules:
                top_rule = max(e_hull_rules, key=lambda r: r.get('confidence', 0))
                analysis["Limitations"] += f"\n  Rule: {top_rule.get('rule_text', '')}"
            elif formation_energy is not None:
                # Try formation energy rules
                fe_rules = [r for r in stability_rules if 'formation energy' in r.get('rule_text', '').lower()]
                if fe_rules:
                    top_rule = max(fe_rules, key=lambda r: r.get('confidence', 0))
                    analysis["Limitations"] += f"\n  Rule: {top_rule.get('rule_text', '')}"
    elif formation_energy is not None:
        analysis["Limitations"] = f"Formation energy: {formation_energy:.3f} eV/atom"
        
        # Add rule-based insights for formation energy
        fe_rules = [
            r for r in relevant_rules 
            if 'formation energy' in r.get('rule_text', '').lower() or
               r.get('category') == 'stability'
        ]
        if fe_rules:
            top_rule = max(fe_rules, key=lambda r: r.get('confidence', 0))
            analysis["Limitations"] += f"\n  Rule: {top_rule.get('rule_text', '')}"
    else:
        analysis["Limitations"] = "No stability data available."

    # Add a dedicated section for rule-based insights
    if relevant_rules:
        # Get top rules across all categories
        top_rules = sorted(relevant_rules, key=lambda r: r.get('confidence', 0), reverse=True)[:5]
        rules_text = format_rules_for_analysis(top_rules, max_rules=5)
        if rules_text:
            analysis["Rule-Based Insights"] = f"Found {len(relevant_rules)} relevant rules from literature:\n{rules_text}"
        else:
            analysis["Rule-Based Insights"] = f"Found {len(relevant_rules)} relevant rules (see category-specific insights above)"
    else:
        # Only add this section if rules are available but none matched
        if rule_loader and rules_cache:
            analysis["Rule-Based Insights"] = "No matching rules found in literature for this material's properties."

    return analysis


# ============================================================================
# ANALYSIS AGENT CLASS - For LangGraph Integration
# ============================================================================

class AnalysisAgent:
    """
    AnalysisAgent analyzes material properties and generates insights.
    
    This agent is designed to work with the LangGraph pipeline.
    """
    
    def __init__(self):
        """Initialize the AnalysisAgent."""
        self.llm = llm
    
    async def run(
        self,
        properties: Dict[str, Any],
        formula: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Analyze material properties.
        
        Args:
            properties: Dictionary of material properties from lookup
            formula: Material formula (for logging)
        
        Returns:
            Dictionary with analysis results
        """
        try:
            print(f"[AnalysisAgent.run] Analyzing {formula}")
            
            # Analyze material properties
            analysis = analyze_material_properties(properties)
            
            print(f"[AnalysisAgent.run] ✓ Analysis complete for {formula}")
            return analysis
        
        except Exception as e:
            print(f"[AnalysisAgent.run] ✗ Error: {e}")
            raise