"""
Rule Extractor Module

Uses LLM (Llama-3.1-8b-instant via Groq) to extract rules from paper abstracts.
Identifies material-property relationships, synthesis heuristics, stability indicators,
and application predictions.
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

logger = logging.getLogger(__name__)


class RuleExtractor:
    """Extracts rules from paper abstracts using LLM."""

    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        """
        Initialize the rule extractor.

        Args:
            model_name: Name of the Groq model to use
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")

        self.llm = ChatGroq(
            api_key=api_key,
            model=model_name,
            temperature=0.3  # Lower temperature for more deterministic rule extraction
        )

        self.extraction_prompt_template = """You are an expert materials scientist. Extract actionable rules and heuristics from the following research paper abstract.

Abstract:
{abstract}

Extract specific rules and heuristics related to:
1. Material-property relationships (e.g., "High band gap → optoelectronics")
2. Synthesis feasibility heuristics (e.g., "Perovskites require specific ratios")
3. Stability indicators (e.g., "Materials with negative formation energy are stable")
4. Application predictions (e.g., "Semiconductors with Eg 3-5eV are suitable for UV detectors")

Return ONLY a JSON array of rules, where each rule has the following structure:
{{
  "rule_text": "The actual rule statement",
  "category": "material_property" | "synthesis" | "stability" | "application",
  "confidence": 0.0-1.0,
  "source_section": "abstract"
}}

Be specific and actionable. Avoid generic statements. Focus on quantifiable relationships when possible.
If no clear rules can be extracted, return an empty array [].

JSON only, no additional text:"""

    def extract_rules(self, abstract: str, paper_id: str) -> List[Dict]:
        """
        Extract rules from a paper abstract.

        Args:
            abstract: Paper abstract text
            paper_id: Unique identifier for the source paper

        Returns:
            List of rule dictionaries with keys: rule_text, category, confidence, source_paper_id, source_section
        """
        if not abstract or len(abstract.strip()) < 50:
            logger.warning(f"Abstract too short for paper {paper_id}, skipping")
            return []

        try:
            prompt = self.extraction_prompt_template.format(abstract=abstract)
            response = self.llm.invoke(prompt)

            # Extract text from response
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Try to parse JSON from response
            rules = self._parse_rules_from_response(response_text, paper_id)
            logger.info(f"Extracted {len(rules)} rules from paper {paper_id}")
            return rules

        except Exception as e:
            logger.error(f"Error extracting rules from paper {paper_id}: {e}")
            return []

    def _parse_rules_from_response(self, response_text: str, paper_id: str) -> List[Dict]:
        """
        Parse rules from LLM response text.

        Args:
            response_text: Raw LLM response text
            paper_id: Source paper ID

        Returns:
            List of parsed rule dictionaries
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
                        formatted_rule = {
                            "rule_text": rule["rule_text"].strip(),
                            "category": rule.get("category", "material_property"),
                            "confidence": float(rule.get("confidence", 0.5)),
                            "source_paper_id": paper_id,
                            "source_section": rule.get("source_section", "abstract")
                        }

                        # Validate category
                        valid_categories = ["material_property", "synthesis", "stability", "application"]
                        if formatted_rule["category"] not in valid_categories:
                            formatted_rule["category"] = "material_property"

                        # Clamp confidence to [0, 1]
                        formatted_rule["confidence"] = max(0.0, min(1.0, formatted_rule["confidence"]))

                        rules.append(formatted_rule)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response for paper {paper_id}: {e}")
            logger.debug(f"Response text: {response_text[:200]}")

        except Exception as e:
            logger.error(f"Error parsing rules from response for paper {paper_id}: {e}")

        return rules

    def extract_rules_from_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Extract rules from multiple papers.

        Args:
            papers: List of paper dictionaries with 'abstract' and 'url' keys

        Returns:
            Combined list of all extracted rules
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

        logger.info(f"Extracted {len(all_rules)} total rules from {len(papers)} papers")
        return all_rules