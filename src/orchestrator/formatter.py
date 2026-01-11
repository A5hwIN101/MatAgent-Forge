import re
from typing import List, Dict, Optional, Tuple


def parse_rule_from_text(text: str) -> Optional[Dict]:
    """
    Parse rule information from text string.
    Looks for patterns like:
    - "• {rule_text} (confidence: {confidence})"
    - Rule text with confidence in parentheses
    
    Returns:
        Dict with 'rule_text', 'confidence', 'category' if found, else None
    """
    if not isinstance(text, str):
        return None
    
    # Pattern 1: "• {text} (confidence: {number})"
    pattern1 = r'•\s*(.+?)\s*\(confidence:\s*([\d.]+)\)'
    match1 = re.search(pattern1, text)
    if match1:
        rule_text = match1.group(1).strip()
        confidence = float(match1.group(2))
        return {'rule_text': rule_text, 'confidence': confidence, 'category': None}
    
    # Pattern 2: "{text} (confidence: {number})"
    pattern2 = r'(.+?)\s*\(confidence:\s*([\d.]+)\)'
    match2 = re.search(pattern2, text)
    if match2:
        rule_text = match2.group(1).strip()
        confidence = float(match2.group(2))
        return {'rule_text': rule_text, 'confidence': confidence, 'category': None}
    
    return None


def format_rules_section(rules: List[Dict], max_rules: int = 5) -> str:
    """
    Format a list of rules into markdown.
    
    Args:
        rules: List of rule dicts with 'rule_text', 'confidence', optional 'category'
        max_rules: Maximum number of rules to display
    
    Returns:
        Formatted markdown string
    """
    if not rules:
        return ""
    
    formatted = "\n  **Supporting Rules:**"
    for rule in rules[:max_rules]:
        rule_text = rule.get('rule_text', 'Unknown rule')
        confidence = rule.get('confidence', 0.0)
        confidence_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
        category = rule.get('category', '')
        
        rule_line = f"\n  • {rule_text} (confidence: {confidence_pct}%)"
        if category:
            rule_line += f" [{category}]"
        formatted += rule_line
    
    if len(rules) > max_rules:
        formatted += f"\n  • ... and {len(rules) - max_rules} more rule(s)"
    
    return formatted


def format_analysis_value(value, key: str = "") -> str:
    """
    Format an analysis value, detecting and formatting rules if present.
    
    Args:
        value: The analysis value (string, dict, list, etc.)
        key: The analysis key (for context)
    
    Returns:
        Formatted markdown string
    """
    if isinstance(value, dict):
        # Check if it's a rule dict
        if 'rule_text' in value or 'supporting_rules' in value:
            if 'supporting_rules' in value:
                rules = value['supporting_rules']
                if isinstance(rules, list) and rules:
                    main_text = value.get('text', key)
                    rules_section = format_rules_section(rules)
                    return f"{main_text}{rules_section}"
            elif 'rule_text' in value:
                # Single rule dict
                rules_section = format_rules_section([value])
                main_text = value.get('text', key)
                return f"{main_text}{rules_section}"
        
        # Regular dict - convert to string representation
        return str(value)
    
    elif isinstance(value, str):
        # Check if string contains rule patterns
        if 'confidence:' in value.lower() or 'supported by' in value.lower():
            # Try to parse rules from text
            lines = value.split('\n')
            main_lines = []
            rules_found = []
            
            for line in lines:
                rule_info = parse_rule_from_text(line)
                if rule_info:
                    rules_found.append(rule_info)
                elif line.strip() and not line.strip().startswith('**Supported by'):
                    # Keep non-rule lines
                    main_lines.append(line.strip())
            
            result = '\n'.join(main_lines) if main_lines else value.split('\n')[0] if value.split('\n') else value
            if rules_found:
                rules_section = format_rules_section(rules_found)
                return f"{result}{rules_section}"
        
        # Check for multi-line rule sections
        if '**Supported by literature rules' in value:
            # Split the text and format rules separately
            parts = value.split('**Supported by literature rules')
            if len(parts) == 2:
                main_text = parts[0].strip()
                rules_text = parts[1]
                
                # Parse rules from the rules section
                rules_found = []
                for line in rules_text.split('\n'):
                    if '•' in line:
                        rule_info = parse_rule_from_text(line)
                        if rule_info:
                            rules_found.append(rule_info)
                
                if rules_found:
                    rules_section = format_rules_section(rules_found)
                    return f"{main_text}{rules_section}"
        
        return value
    
    elif isinstance(value, list):
        # If list of rule dicts
        if value and isinstance(value[0], dict) and 'rule_text' in value[0]:
            return format_rules_section(value)
        # Otherwise join as string
        return ', '.join(str(v) for v in value)
    
    else:
        return str(value)


def assemble_markdown(parsed: dict, analysis: dict, hypothesis: dict) -> str:
    # Material Summary
    formula = parsed.get("formula_pretty", "Unknown")
    symmetry = parsed.get("symmetry", {})
    space_group = symmetry.get("symbol", "Unknown")
    crystal_system = symmetry.get("crystal_system", "Unknown")

    lattice = parsed.get("structure", {}).get("lattice", {})
    a = lattice.get("a", "—")
    b = lattice.get("b", "—")
    c = lattice.get("c", "—")

    summary = f"""## 🧪 Material Summary
| Property    | Value        |
|-------------|--------------|
| Formula     | {formula}    |
| Structure   | {crystal_system} |
| Space Group | {space_group} |
| a           | {a} |
| b           | {b} |
| c           | {c} |
"""

    # ✅ Change 1: Computed Properties (only simple scalars, skip nested dicts/lists)
    props_table = "## 📊 Computed / Parsed Properties\n"
    props_table += "| Property | Value |\n|----------|-------|\n"
    for k, v in parsed.items():
        if isinstance(v, (int, float, str)):   # only include simple values
            props_table += f"| {k} | {v} |\n"

    # Analysis
    analysis_md = "## 🧩 Analysis\n"
    for k, v in analysis.items():
        formatted_value = format_analysis_value(v, k)
        analysis_md += f"- **{k}**: {formatted_value}\n"

    # ✅ Change 3: Hypotheses (always clean bullet points)
    hypothesis_md = "## 🔭 Hypotheses\n"
    if isinstance(hypothesis, dict):
        for k, v in hypothesis.items():
            hypothesis_md += f"- **{k}**: {v}\n"
    elif isinstance(hypothesis, list):
        for h in hypothesis:
            hypothesis_md += f"- {h}\n"
    elif isinstance(hypothesis, str):
        # split into lines and bullets
        lines = [l.strip("-• ").strip() for l in hypothesis.splitlines() if l.strip()]
        for l in lines:
            hypothesis_md += f"- {l}\n"
    else:
        hypothesis_md += "- No hypotheses generated.\n"

    return "\n".join([summary, props_table, analysis_md, hypothesis_md])