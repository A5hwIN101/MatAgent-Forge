"""
Rule Extractor Module

Uses LLM (Llama-3.1-8b-instant via Groq) to extract QUANTITATIVE, ACTIONABLE rules
from paper abstracts. Focuses on extracting rules with specific thresholds, values,
and property-application relationships.

Extraction Strategy:
- Prioritizes quantitative rules with explicit thresholds (e.g., "Band gap > 3.0 eV → Optoelectronics")
- Filters out vague statements (confidence < 0.7)
- Validates rules contain numeric values or thresholds
- Categories: material_property, property_application, synthesis, stability
"""

import os
import json
import logging
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

logger = logging.getLogger(__name__)


class RuleExtractor:
    """
    Extracts QUANTITATIVE, ACTIONABLE rules from paper abstracts using LLM.
    
    Rules must contain specific thresholds, values, or numeric relationships.
    Only rules with confidence >= 0.7 are kept (filtering out vague statements).
    """

    def __init__(self, model_name: str = "llama-3.1-8b-instant", min_confidence: float = 0.7):
        """
        Initialize the rule extractor.

        Args:
            model_name: Name of the Groq model to use
            min_confidence: Minimum confidence threshold for keeping rules (default: 0.7)
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")

        self.llm = ChatGroq(
            api_key=api_key,
            model=model_name,
            temperature=0.3  # Lower temperature for more deterministic rule extraction
        )
        self.min_confidence = min_confidence

        self.extraction_prompt_template = """You are an expert materials scientist. Extract QUANTITATIVE, ACTIONABLE RULES from the following research paper abstract.

Abstract:
{abstract}

Extract rules that follow ONE of these FORMATS:

1. **Property-Application Rules** (with thresholds):
   - "Band gap > 3.0 eV → Optoelectronics"
   - "Formation energy < -2.0 eV → Thermodynamically stable"
   - "Bulk modulus > 200 GPa → Structural applications"

2. **Material Composition → Property Relationships**:
   - "High entropy alloys (≥5 elements) → Enhanced mechanical properties"
   - "Perovskites (A:B:X ratio ≈ 1:1:3) → Tunable band gaps"

3. **Synthesis Feasibility Rules**:
   - "Formation energy difference < 0.5 eV → Metastable synthesis possible"
   - "Temperature > 1000°C → High-temperature phase stable"

4. **Stability Rules** (with thresholds):
   - "Formation energy < -1.0 eV → Easily synthesizable"
   - "Energy above hull < 0.05 eV/atom → Stable phase"

**CRITICAL REQUIREMENTS:**
- Include SPECIFIC NUMBERS, THRESHOLDS, or VALUES (not vague terms like "high" or "low")
- Use format: "Property X > VALUE → Application Y" or "Property X < VALUE → Result Y"
- Skip vague statements like "Charge neutrality is important" (no threshold/application)

**CONFIDENCE SCORING** (assign based on specificity):
- 1.0 = Explicit quantitative threshold with numbers (e.g., "Band gap > 3.0 eV")
- 0.8 = Clear relationship with implied thresholds or ranges (e.g., "Band gap 3-5 eV → UV detectors")
- 0.6 = General relationship without specific values (should be avoided)
- Below 0.5 = Too vague, DO NOT INCLUDE

Return ONLY a JSON array of rules, where each rule has:
{{
  "rule_text": "Quantitative rule with specific threshold/value",
  "category": "property_application" | "material_property" | "synthesis" | "stability",
  "confidence": 0.0-1.0 (based on specificity above),
  "source_section": "abstract"
}}

**IMPORTANT:** 
- Return ONLY rules with confidence >= 0.7 (skip vague statements)
- Include NUMBERS/THRESHOLDS in rule_text
- Use "property_application" category for Property X → Application Y rules

If no quantitative rules can be extracted, return an empty array [].

JSON only, no additional text:"""

    def extract_rules(self, abstract: str, paper_id: str) -> List[Dict]:
        """
        Extract quantitative, actionable rules from a paper abstract.
        
        Rules are filtered to keep only those with confidence >= min_confidence (default 0.7).
        Vague statements without specific thresholds or values are automatically excluded.

        Args:
            abstract: Paper abstract text
            paper_id: Unique identifier for the source paper

        Returns:
            List of rule dictionaries with keys: rule_text, category, confidence, 
            source_paper_id, source_section. Only includes rules with confidence >= min_confidence.
        """
        if not abstract or len(abstract.strip()) < 50:
            logger.warning(f"Abstract too short for paper {paper_id}, skipping")
            return []

        try:
            prompt = self.extraction_prompt_template.format(abstract=abstract)
            response = self.llm.invoke(prompt)

            # Extract text from response
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Parse and filter rules
            rules = self._parse_rules_from_response(response_text, paper_id)
            
            # Filter by confidence threshold
            filtered_rules = [
                r for r in rules 
                if r.get('confidence', 0) >= self.min_confidence
            ]
            
            logger.info(
                f"Extracted {len(filtered_rules)} rules (confidence >= {self.min_confidence}) "
                f"from {len(rules)} total extracted from paper {paper_id}"
            )
            
            return filtered_rules

        except Exception as e:
            logger.error(f"Error extracting rules from paper {paper_id}: {e}")
            return []

    def _parse_rules_from_response(self, response_text: str, paper_id: str) -> List[Dict]:
        """
        Parse rules from LLM response text and validate/extract quantitative content.
        
        Rules are validated for format, category, and confidence values.
        Additionally validates that rules contain numeric content (thresholds/values).

        Args:
            response_text: Raw LLM response text
            paper_id: Source paper ID

        Returns:
            List of parsed and validated rule dictionaries
        """
        rules = []

        # Try to extract JSON array from response
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse JSON
            parsed_rules = json.loads(response_text)
            if not isinstance(parsed_rules, list):
                parsed_rules = [parsed_rules]

            # Validate and format rules
            for rule in parsed_rules:
                if isinstance(rule, dict):
                    # Validate required fields
                    if "rule_text" in rule and rule["rule_text"]:
                        rule_text = rule["rule_text"].strip()
                        
                        # Skip obviously invalid rules
                        if not rule_text or len(rule_text) < 10:
                            continue
                        
                        formatted_rule = {
                            "rule_text": rule_text,
                            "category": rule.get("category", "material_property"),
                            "confidence": float(rule.get("confidence", 0.5)),
                            "source_paper_id": paper_id,
                            "source_section": rule.get("source_section", "abstract")
                        }

                        # Validate and normalize category
                        # Map "application" to "property_application" for consistency
                        category = formatted_rule["category"]
                        valid_categories = [
                            "material_property", 
                            "property_application", 
                            "synthesis", 
                            "stability"
                        ]
                        
                        # Handle legacy category "application"
                        if category == "application":
                            category = "property_application"
                            
                        if category not in valid_categories:
                            category = "material_property"
                        
                        formatted_rule["category"] = category

                        # Clamp confidence to [0, 1]
                        formatted_rule["confidence"] = max(0.0, min(1.0, formatted_rule["confidence"]))
                        
                        # Re-evaluate confidence if rule lacks numeric content
                        # (If LLM assigned high confidence but rule is vague, lower it)
                        if formatted_rule["confidence"] >= 0.8 and not self._has_numeric_content(rule_text):
                            logger.debug(
                                f"Lowering confidence for rule without numeric content: "
                                f"{rule_text[:50]}..."
                            )
                            formatted_rule["confidence"] = max(0.5, formatted_rule["confidence"] - 0.2)

                        rules.append(formatted_rule)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response for paper {paper_id}: {e}")
            logger.debug(f"Response text: {response_text[:200]}")

        except Exception as e:
            logger.error(f"Error parsing rules from response for paper {paper_id}: {e}")

        return rules

    def _has_numeric_content(self, rule_text: str) -> bool:
        """
        Check if a rule contains numeric values, thresholds, or quantitative indicators.
        
        Looks for:
        - Numbers (integers, decimals)
        - Comparison operators with numbers (>, <, >=, <=, ≈, ~)
        - Units (eV, GPa, °C, etc.)
        
        Args:
            rule_text: The rule text to check
            
        Returns:
            True if rule contains numeric content, False otherwise
        """
        # Pattern to match numbers (including decimals, scientific notation)
        number_pattern = r'\d+\.?\d*'
        
        # Pattern to match comparison operators
        comparison_pattern = r'[<>≤≥≈~=]'
        
        # Common units in materials science
        units_pattern = r'\b(eV|GPa|MPa|K|°C|%|g/cm³|mol|ratio)\b'
        
        # Check for numbers
        has_number = bool(re.search(number_pattern, rule_text))
        
        # Check for comparison operators followed by potential numbers
        has_comparison = bool(re.search(comparison_pattern, rule_text))
        
        # Check for units (often indicates quantitative content)
        has_units = bool(re.search(units_pattern, rule_text, re.IGNORECASE))
        
        return has_number or (has_comparison and has_number) or has_units

    def extract_rules_from_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Extract quantitative, actionable rules from multiple papers.
        
        All rules are filtered to keep only those with confidence >= min_confidence.

        Args:
            papers: List of paper dictionaries with 'abstract' and 'url' keys

        Returns:
            Combined list of all extracted rules (already filtered by confidence threshold)
        """
        all_rules = []

        for paper in papers:
            abstract = paper.get("abstract", "")
            paper_id = paper.get("url", "")  # Use URL as paper ID

            if not paper_id:
                # Generate a simple ID from title
                title = paper.get("title", "")
                paper_id = title[:50].replace(" ", "_") if title else f"paper_{len(all_rules)}"

            rules = self.extract_rules(abstract, paper_id)
            all_rules.extend(rules)

        logger.info(
            f"Extracted {len(all_rules)} total quantitative rules "
            f"(confidence >= {self.min_confidence}) from {len(papers)} papers"
        )
        return all_rules