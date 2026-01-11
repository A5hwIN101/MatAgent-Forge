"""
Rule Loader Module

Loads rules at application startup and provides helper functions
for retrieving relevant rules based on material properties.
"""

import logging
from typing import List, Dict, Optional
from src.data_sources.rule_storage import RuleStorage

logger = logging.getLogger(__name__)


class RuleLoader:
    """Loads and caches rules for fast access."""

    def __init__(self, rules_dir: str = "rules"):
        """
        Initialize rule loader.

        Args:
            rules_dir: Directory path for rule JSON files
        """
        self.storage = RuleStorage(rules_dir)
        self._cached_rules: Optional[List[Dict]] = None
        self._cache_loaded = False

    def load_rules(self, force_reload: bool = False) -> List[Dict]:
        """
        Load all rules from storage (with caching).

        Args:
            force_reload: If True, reload from disk even if cached

        Returns:
            List of all rule dictionaries
        """
        if not self._cache_loaded or force_reload:
            self._cached_rules = self.storage.load_rules()
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._cached_rules)} rules into cache")

        return self._cached_rules or []

    def get_rules_for_analysis(self, material_properties: Dict) -> List[Dict]:
        """
        Get relevant rules based on material properties.

        Args:
            material_properties: Dictionary of material properties (e.g., band_gap, density, etc.)

        Returns:
            List of relevant rule dictionaries
        """
        # Load rules if not cached
        if not self._cache_loaded:
            self.load_rules()

        all_rules = self._cached_rules or []
        relevant_rules = []

        # Extract key terms from material properties
        property_terms = []
        for key, value in material_properties.items():
            if value is not None:
                # Add property name as keyword
                property_terms.append(key.lower())

                # Add value-based keywords if value is numeric
                if isinstance(value, (int, float)):
                    # For band gap, add relevant categories
                    if "band_gap" in key.lower() or "bandgap" in key.lower():
                        if value > 3.0:
                            property_terms.append("high band gap")
                            property_terms.append("optoelectronics")
                        elif value > 0:
                            property_terms.append("semiconductor")
                    # For stability indicators
                    if "formation_energy" in key.lower() or "energy_above_hull" in key.lower():
                        if value < 0:
                            property_terms.append("stable")
                            property_terms.append("negative formation energy")
                elif isinstance(value, str):
                    # Add string values as keywords
                    property_terms.append(value.lower())

        # Search for relevant rules using keywords
        for term in property_terms:
            matching_rules = self.storage.search_rules(term)
            relevant_rules.extend(matching_rules)

        # Remove duplicates (by rule_id if available, otherwise by rule_text)
        seen = set()
        unique_rules = []
        for rule in relevant_rules:
            rule_id = rule.get("rule_id")
            if rule_id is not None:
                if rule_id not in seen:
                    seen.add(rule_id)
                    unique_rules.append(rule)
            else:
                rule_text = rule.get("rule_text", "")
                if rule_text and rule_text not in seen:
                    seen.add(rule_text)
                    unique_rules.append(rule)

        # Sort by relevance (could be improved with scoring)
        # For now, sort by confidence
        unique_rules.sort(key=lambda r: r.get("confidence", 0.0), reverse=True)

        logger.info(f"Found {len(unique_rules)} relevant rules for material properties")
        return unique_rules

    def get_rules_by_category(self, category: str) -> List[Dict]:
        """
        Get rules by category.

        Args:
            category: Rule category ("material_property", "synthesis", "stability", "application")

        Returns:
            List of rules in the specified category
        """
        if not self._cache_loaded:
            self.load_rules()

        # Filter cached rules by category
        if self._cached_rules:
            return [r for r in self._cached_rules if r.get("category") == category]
        else:
            return self.storage.load_rules(category=category)

    def get_rule_stats(self) -> Dict:
        """
        Get statistics about loaded rules.

        Returns:
            Dictionary with rule statistics
        """
        return self.storage.get_rule_stats()

    def reload_cache(self) -> None:
        """Reload rules from storage into cache."""
        self.load_rules(force_reload=True)