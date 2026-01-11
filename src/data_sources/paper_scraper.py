"""
Paper Scraper Module

Scrapes research papers from arXiv and PubMed Central (PMC) APIs.
Implements rate limiting, error handling with exponential backoff, and
returns structured paper data.
"""

import requests
import feedparser
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to respect API limits (max 3 requests/second)."""

    def __init__(self, max_requests: float = 3.0, time_window: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times: List[float] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove old requests outside the time window
        self.request_times = [t for t in self.request_times if now - t < self.time_window]

        if len(self.request_times) >= self.max_requests:
            # Wait until the oldest request expires
            sleep_time = self.time_window - (now - self.request_times[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < self.time_window]

        self.request_times.append(now)


class PaperScraper:
    """Scraper for research papers from arXiv and PMC."""

    def __init__(self):
        """Initialize the paper scraper."""
        self.rate_limiter = RateLimiter(max_requests=3.0, time_window=1.0)
        self.arxiv_base_url = "http://export.arxiv.org/api/query"
        self.pmc_base_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0"

    def _make_request_with_retry(
        self, url: str, params: Optional[Dict] = None, max_retries: int = 3
    ) -> Optional[requests.Response]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: URL to request
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            Response object or None if all retries failed
        """
        self.rate_limiter.wait_if_needed()

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                wait_time = (2 ** attempt) + (time.time() % 1)  # Exponential backoff with jitter
                if attempt < max_retries - 1:
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    return None

        return None

    def scrape_arxiv(
        self,
        keywords: List[str],
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "relevance"
    ) -> List[Dict]:
        """
        Query arXiv API for materials science papers.

        Args:
            keywords: List of search keywords
            max_results: Maximum number of results to return
            start: Starting index for pagination
            sort_by: Sort order ("relevance", "lastUpdatedDate", "submittedDate")

        Returns:
            List of paper dictionaries with keys: title, authors, abstract, url, source, date_published
        """
        papers = []
        query = " OR ".join([f'all:"{kw}"' for kw in keywords])

        params = {
            "search_query": query,
            "start": start,
            "max_results": min(max_results, 100),  # arXiv limit is 100 per request
            "sortBy": sort_by,
            "sortOrder": "descending"
        }

        logger.info(f"Querying arXiv with keywords: {keywords}")

        response = self._make_request_with_retry(self.arxiv_base_url, params=params)
        if not response:
            logger.error("Failed to fetch papers from arXiv")
            return papers

        try:
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                # Parse authors
                authors = [author.name for author in entry.get("authors", [])]

                # Parse date
                published_date = entry.get("published", "")
                try:
                    if published_date:
                        date_obj = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%SZ")
                        date_str = date_obj.strftime("%Y-%m-%d")
                    else:
                        date_str = ""
                except (ValueError, AttributeError):
                    date_str = published_date if published_date else ""

                paper = {
                    "title": entry.get("title", "").strip(),
                    "authors": authors,
                    "abstract": entry.get("summary", "").strip()[:500],  # Limit abstract length
                    "url": entry.get("id", ""),
                    "source": "arxiv",
                    "date_published": date_str
                }
                papers.append(paper)

            logger.info(f"Successfully scraped {len(papers)} papers from arXiv")
        except Exception as e:
            logger.error(f"Error parsing arXiv feed: {e}")

        return papers

    def scrape_pmc(
        self,
        keywords: List[str],
        max_results: int = 10,
        retstart: int = 0
    ) -> List[Dict]:
        """
        Query PubMed Central (PMC) API for materials-related research.

        Args:
            keywords: List of search keywords
            max_results: Maximum number of results to return
            retstart: Starting index for pagination

        Returns:
            List of paper dictionaries with keys: title, authors, abstract, url, source, date_published
        """
        papers = []
        query = " OR ".join(keywords)

        # Use E-utilities API for searching
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pmc",
            "term": query,
            "retmax": min(max_results, 100),  # NCBI limit
            "retstart": retstart,
            "retmode": "json",
            "sort": "relevance"
        }

        logger.info(f"Querying PMC with keywords: {keywords}")

        search_response = self._make_request_with_retry(search_url, params=search_params)
        if not search_response:
            logger.error("Failed to search PMC")
            return papers

        try:
            search_data = search_response.json()
            pmc_ids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmc_ids:
                logger.info("No PMC papers found")
                return papers

            # Fetch summaries for the IDs
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {
                "db": "pmc",
                "id": ",".join(pmc_ids[:max_results]),
                "retmode": "json"
            }

            summary_response = self._make_request_with_retry(summary_url, params=summary_params)
            if not summary_response:
                logger.error("Failed to fetch PMC summaries")
                return papers

            summary_data = summary_response.json()
            results = summary_data.get("result", {})

            for pmc_id in pmc_ids[:max_results]:
                if pmc_id not in results:
                    continue

                result = results[pmc_id]

                # Parse authors
                authors_list = result.get("authors", [])
                authors = []
                if isinstance(authors_list, list):
                    for author in authors_list:
                        if isinstance(author, dict):
                            name = f"{author.get('name', '')}".strip()
                            if name:
                                authors.append(name)
                        elif isinstance(author, str):
                            authors.append(author)

                # Parse date
                pub_date = result.get("pubdate", "")
                date_str = pub_date[:10] if pub_date and len(pub_date) >= 10 else pub_date if pub_date else ""

                paper = {
                    "title": result.get("title", "").strip(),
                    "authors": authors,
                    "abstract": result.get("sources", [{}])[0].get("value", "")[:500] if result.get("sources") else "",  # Limit abstract
                    "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/",
                    "source": "pmc",
                    "date_published": date_str
                }
                papers.append(paper)

            logger.info(f"Successfully scraped {len(papers)} papers from PMC")
        except Exception as e:
            logger.error(f"Error parsing PMC response: {e}")

        return papers

    def scrape_papers(
        self,
        sources: List[str] = ["arxiv"],
        keywords: List[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> List[Dict]:
        """
        Scrape papers from specified sources.

        Args:
            sources: List of sources to scrape ("arxiv", "pmc", or both)
            keywords: List of search keywords. Defaults to materials science keywords.
            max_results: Maximum number of results per source
            **kwargs: Additional arguments passed to individual scraper methods

        Returns:
            Combined list of papers from all sources
        """
        if keywords is None:
            keywords = [
                "materials science",
                "inorganic materials",
                "crystal structure",
                "materials properties"
            ]

        all_papers = []

        if "arxiv" in sources:
            arxiv_papers = self.scrape_arxiv(keywords=keywords, max_results=max_results, **kwargs)
            all_papers.extend(arxiv_papers)

        if "pmc" in sources:
            pmc_papers = self.scrape_pmc(keywords=keywords, max_results=max_results, **kwargs)
            all_papers.extend(pmc_papers)

        return all_papers