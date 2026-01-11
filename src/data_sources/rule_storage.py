"""
Rule Storage System

Manages persistent storage of extracted rules using JSON files.
Implements deduplication, indexing, and search functionality.
"""

import json
import hashlib
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RuleStorage:
    """Manages storage and retrieval of extracted rules."""

    def __init__(self, rules_dir: str = "rules"):
        """
        Initialize rule storage.

        Args:
            rules_dir: Directory path for storing rule JSON files
        """
        self.rules_dir = rules_dir
        self.rules_file = os.path.join(rules_dir, "extracted_rules.json")
        self.metadata_file = os.path.join(rules_dir, "rule_metadata.json")
        self.index_file = os.path.join(rules_dir, "rule_index.json")

        # Create directory if it doesn't exist
        os.makedirs(rules_dir, exist_ok=True)

        # Initialize files if they don't exist
        self._initialize_files()

    def _initialize_files(self) -> None:
        """Initialize JSON files if they don't exist."""
        if not os.path.exists(self.rules_file):
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _hash_rule_text(self, rule_text: str) -> str:
        """
        Generate hash for rule text (for deduplication).

        Args:
            rule_text: Rule text to hash

        Returns:
            SHA256 hash of the normalized rule text
        """
        normalized = rule_text.lower().strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _load_rules(self) -> List[Dict]:
        """Load all rules from JSON file."""
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading rules file: {e}. Initializing empty list.")
            return []

    def _save_rules(self, rules: List[Dict]) -> None:
        """Save rules to JSON file."""
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving rules file: {e}")
            raise

    def _load_metadata(self) -> Dict:
        """Load metadata from JSON file."""
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading metadata file: {e}. Initializing empty dict.")
            return {}

    def _save_metadata(self, metadata: Dict) -> None:
        """Save metadata to JSON file."""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata file: {e}")
            raise

    def _load_index(self) -> Dict:
        """Load index from JSON file."""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading index file: {e}. Initializing empty dict.")
            return {}

    def _save_index(self, index: Dict) -> None:
        """Save index to JSON file."""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving index file: {e}")
            raise

    def _build_index(self, rules: List[Dict]) -> Dict:
        """
        Build searchable index from rules.

        Args:
            rules: List of rule dictionaries

        Returns:
            Index dictionary with category and keyword mappings
        """
        index: Dict = {
            "category": {},
            "keyword": {}
        }

        for i, rule in enumerate(rules):
            rule_id = i  # Use index as ID

            # Index by category
            category = rule.get("category", "material_property")
            if category not in index["category"]:
                index["category"][category] = []
            index["category"][category].append(rule_id)

            # Index by keywords (simple word-based indexing)
            rule_text = rule.get("rule_text", "").lower()
            words = set(rule_text.split())
            # Filter out common stop words and short words
            stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
            keywords = [w for w in words if len(w) > 3 and w not in stop_words]

            for keyword in keywords[:10]:  # Limit keywords per rule
                if keyword not in index["keyword"]:
                    index["keyword"][keyword] = []
                if rule_id not in index["keyword"][keyword]:
                    index["keyword"][keyword].append(rule_id)

        return index

    def save_rules(self, rules_list: List[Dict], paper_metadata: Optional[Dict] = None) -> int:
        """
        Save new rules, avoiding duplicates.

        Args:
            rules_list: List of rule dictionaries to save
            paper_metadata: Optional metadata about the source paper (title, authors, url, etc.)

        Returns:
            Number of new rules added (after deduplication)
        """
        existing_rules = self._load_rules()
        existing_hashes = {self._hash_rule_text(r.get("rule_text", "")) for r in existing_rules}

        new_rules = []
        for rule in rules_list:
            rule_text = rule.get("rule_text", "")
            if not rule_text:
                continue

            rule_hash = self._hash_rule_text(rule_text)
            if rule_hash not in existing_hashes:
                # Add unique rule ID
                rule_with_id = rule.copy()
                rule_with_id["rule_id"] = len(existing_rules) + len(new_rules)
                new_rules.append(rule_with_id)
                existing_hashes.add(rule_hash)

        if not new_rules:
            logger.info("No new rules to save (all duplicates)")
            return 0

        # Append new rules
        all_rules = existing_rules + new_rules
        self._save_rules(all_rules)

        # Update metadata
        if paper_metadata:
            metadata = self._load_metadata()
            paper_id = paper_metadata.get("url", paper_metadata.get("title", "unknown"))
            metadata[paper_id] = {
                "title": paper_metadata.get("title", ""),
                "authors": paper_metadata.get("authors", []),
                "url": paper_metadata.get("url", ""),
                "extraction_date": datetime.now().isoformat(),
                "rules_count": len(new_rules)
            }
            self._save_metadata(metadata)

        # Rebuild index
        index = self._build_index(all_rules)
        self._save_index(index)

        logger.info(f"Saved {len(new_rules)} new rules (skipped {len(rules_list) - len(new_rules)} duplicates)")
        return len(new_rules)

    def load_rules(self, category: Optional[str] = None) -> List[Dict]:
        """
        Load all rules or filter by category.

        Args:
            category: Optional category filter ("material_property", "synthesis", "stability", "application")

        Returns:
            List of rule dictionaries
        """
        all_rules = self._load_rules()

        if category:
            filtered_rules = [r for r in all_rules if r.get("category") == category]
            logger.info(f"Loaded {len(filtered_rules)} rules for category '{category}'")
            return filtered_rules

        logger.info(f"Loaded {len(all_rules)} total rules")
        return all_rules

    def search_rules(self, keyword: str) -> List[Dict]:
        """
        Search rules by keyword.

        Args:
            keyword: Search keyword

        Returns:
            List of matching rule dictionaries
        """
        keyword_lower = keyword.lower().strip()
        index = self._load_index()
        all_rules = self._load_rules()

        matching_rule_ids = set()

        # Search in keyword index
        keyword_index = index.get("keyword", {})
        if keyword_lower in keyword_index:
            matching_rule_ids.update(keyword_index[keyword_lower])

        # Also search in rule text directly (for partial matches)
        for i, rule in enumerate(all_rules):
            rule_text = rule.get("rule_text", "").lower()
            if keyword_lower in rule_text:
                matching_rule_ids.add(i)

        # Return matching rules
        matching_rules = [all_rules[i] for i in matching_rule_ids if i < len(all_rules)]

        logger.info(f"Found {len(matching_rules)} rules matching keyword '{keyword}'")
        return matching_rules

    def get_rule_stats(self) -> Dict:
        """
        Get statistics about stored rules.

        Returns:
            Dictionary with count by category, total papers, last update time
        """
        rules = self._load_rules()
        metadata = self._load_metadata()

        stats = {
            "total_rules": len(rules),
            "categories": {},
            "total_papers": len(metadata),
            "last_update": None
        }

        # Count by category
        for rule in rules:
            category = rule.get("category", "unknown")
            stats["categories"][category] = stats["categories"].get(category, 0) + 1

        # Get last update time from metadata
        if metadata:
            dates = [m.get("extraction_date", "") for m in metadata.values() if m.get("extraction_date")]
            if dates:
                stats["last_update"] = max(dates)

        return stats