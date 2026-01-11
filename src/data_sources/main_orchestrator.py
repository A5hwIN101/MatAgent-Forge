"""
Main Orchestrator Module

Orchestrates the full paper scraping and rule extraction pipeline.
Includes CLI interface for manual execution.
"""

import argparse
import logging
import sys
from typing import List, Dict
from src.data_sources.paper_scraper import PaperScraper
from src.data_sources.rule_extractor import RuleExtractor
from src.data_sources.rule_storage import RuleStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PaperScraperOrchestrator:
    """Orchestrates the paper scraping and rule extraction pipeline."""

    def __init__(self, rules_dir: str = "rules"):
        """
        Initialize the orchestrator.

        Args:
            rules_dir: Directory path for storing rule JSON files
        """
        self.scraper = PaperScraper()
        self.extractor = RuleExtractor()
        self.storage = RuleStorage(rules_dir)

    def run_pipeline(
        self,
        sources: List[str] = ["arxiv"],
        keywords: List[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Run the full pipeline: scrape papers → extract rules → store rules.

        Args:
            sources: List of sources to scrape ("arxiv", "pmc", or both)
            keywords: List of search keywords. Defaults to materials science keywords.
            limit: Maximum number of papers to process per source
            **kwargs: Additional arguments passed to scraper

        Returns:
            Dictionary with pipeline execution results
        """
        logger.info("=" * 60)
        logger.info("Starting Paper Scraper Pipeline")
        logger.info("=" * 60)

        # Step 1: Scrape papers
        logger.info(f"\n[Step 1/3] Scraping papers from {sources}...")
        papers = self.scraper.scrape_papers(
            sources=sources,
            keywords=keywords,
            max_results=limit,
            **kwargs
        )

        if not papers:
            logger.warning("No papers found. Exiting pipeline.")
            return {
                "papers_scraped": 0,
                "rules_extracted": 0,
                "rules_saved": 0,
                "papers": []
            }

        logger.info(f"Successfully scraped {len(papers)} papers")

        # Step 2: Extract rules
        logger.info(f"\n[Step 2/3] Extracting rules from {len(papers)} papers...")
        all_rules = []

        for i, paper in enumerate(papers, 1):
            logger.info(f"Processing paper {i}/{len(papers)}: {paper.get('title', 'Unknown')[:60]}...")
            abstract = paper.get("abstract", "")
            paper_id = paper.get("url", paper.get("title", f"paper_{i}"))

            rules = self.extractor.extract_rules(abstract, paper_id)
            all_rules.extend(rules)

            # Store rules for this paper
            if rules:
                paper_metadata = {
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "url": paper.get("url", ""),
                    "date_published": paper.get("date_published", "")
                }
                saved_count = self.storage.save_rules(rules, paper_metadata)
                logger.info(f"  → Extracted {len(rules)} rules, saved {saved_count} new rules")

        logger.info(f"Successfully extracted {len(all_rules)} total rules")

        # Step 3: Final statistics
        logger.info(f"\n[Step 3/3] Pipeline complete!")
        stats = self.storage.get_rule_stats()
        logger.info(f"\nRule Statistics:")
        logger.info(f"  Total rules: {stats['total_rules']}")
        logger.info(f"  Total papers: {stats['total_papers']}")
        logger.info(f"  Categories: {stats['categories']}")
        if stats['last_update']:
            logger.info(f"  Last update: {stats['last_update']}")

        logger.info("=" * 60)

        return {
            "papers_scraped": len(papers),
            "rules_extracted": len(all_rules),
            "rules_saved": stats['total_rules'],
            "papers": papers,
            "stats": stats
        }

    def print_sample_rules(self, num_samples: int = 5) -> None:
        """
        Print sample rules to console for review.

        Args:
            num_samples: Number of sample rules to print
        """
        rules = self.storage.load_rules()
        if not rules:
            logger.info("No rules found in storage.")
            return

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Sample Rules (showing {min(num_samples, len(rules))} of {len(rules)}):")
        logger.info(f"{'=' * 60}")

        for i, rule in enumerate(rules[:num_samples], 1):
            logger.info(f"\nRule {i}:")
            logger.info(f"  Category: {rule.get('category', 'N/A')}")
            logger.info(f"  Confidence: {rule.get('confidence', 0.0):.2f}")
            logger.info(f"  Text: {rule.get('rule_text', 'N/A')}")
            logger.info(f"  Source: {rule.get('source_paper_id', 'N/A')[:80]}")


def main():
    """CLI entry point for the orchestrator."""
    parser = argparse.ArgumentParser(
        description="Paper Scraper Pipeline: Extract rules from research papers"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of papers to process per source (default: 10)"
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["arxiv", "pmc", "both"],
        default="arxiv",
        help="Source to scrape: arxiv, pmc, or both (default: arxiv)"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        default=None,
        help="Custom search keywords (default: materials science keywords)"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of sample rules to display after extraction (default: 5)"
    )

    args = parser.parse_args()

    # Parse source argument
    if args.source == "both":
        sources = ["arxiv", "pmc"]
    else:
        sources = [args.source]

    # Initialize orchestrator
    orchestrator = PaperScraperOrchestrator()

    # Run pipeline
    try:
        results = orchestrator.run_pipeline(
            sources=sources,
            keywords=args.keywords,
            limit=args.limit
        )

        # Print sample rules
        orchestrator.print_sample_rules(num_samples=args.samples)

        # Exit with success
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()