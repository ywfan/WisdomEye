"""
Enhanced Scholar Metrics Fetcher

This module provides robust academic metrics collection from multiple sources
with active crawling, anti-blocking strategies, and fallback mechanisms.

Features:
- Active Google Scholar profile crawling
- Multiple HTML parsing strategies (new/old page structures)
- Anti-blocking mechanisms (user agent rotation, delays, proxies)
- Fallback to multiple academic platforms (ResearchGate, Semantic Scholar)
- Robust error handling and retry logic

Author: WisdomEye Team
Date: 2025-12-12
"""

import re
import time
import random
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlencode, quote_plus
import requests
from bs4 import BeautifulSoup

from .observability import emit


class AntiBlockStrategy:
    """Anti-blocking strategies for web scraping."""
    
    USER_AGENTS = [
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Chrome on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Firefox on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        # Safari on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        # Edge on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    ]
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Get a random user agent string."""
        return random.choice(AntiBlockStrategy.USER_AGENTS)
    
    @staticmethod
    def get_random_delay() -> float:
        """Get a random delay between requests (1-3 seconds)."""
        return random.uniform(1.0, 3.0)
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get HTTP headers with random user agent."""
        return {
            'User-Agent': AntiBlockStrategy.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }


class ScholarMetricsFetcher:
    """
    Enhanced academic metrics fetcher with active crawling capabilities.
    
    Supports:
    - Google Scholar profile crawling
    - Multiple parsing strategies
    - Anti-blocking mechanisms
    - Fallback to alternative sources
    """
    
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        use_proxies: bool = False,
        proxy_list: Optional[List[str]] = None
    ):
        """
        Initialize the metrics fetcher.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            use_proxies: Whether to use proxy rotation
            proxy_list: List of proxy URLs (e.g., ['http://proxy1:8080'])
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_proxies = use_proxies
        self.proxy_list = proxy_list or []
        self.session = requests.Session()
    
    def run(
        self,
        name: str,
        profile_url: Optional[str] = None,
        affiliation: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Fetch academic metrics for a person.
        
        Args:
            name: Person's name
            profile_url: Direct Google Scholar profile URL (if known)
            affiliation: Person's affiliation (helps with search)
            content: Pre-fetched content to parse (optional)
            
        Returns:
            Dictionary with metrics (h_index, h10_index, citations_total, citations_recent)
        """
        t0 = time.time()
        emit({
            "kind": "scholar_metrics_start",
            "name": name,
            "profile_url": profile_url or "",
            "affiliation": affiliation or ""
        })
        
        # If content is provided, just parse it
        if content:
            metrics = self._parse_content(content)
            emit({
                "kind": "scholar_metrics_end",
                "name": name,
                "metrics": metrics,
                "source": "provided_content",
                "elapsed_sec": round(time.time() - t0, 3)
            })
            return metrics
        
        # Try direct profile URL first
        if profile_url:
            metrics = self._fetch_from_profile_url(profile_url)
            if self._has_valid_metrics(metrics):
                emit({
                    "kind": "scholar_metrics_end",
                    "name": name,
                    "metrics": metrics,
                    "source": "direct_profile",
                    "elapsed_sec": round(time.time() - t0, 3)
                })
                return metrics
        
        # Try searching for profile
        metrics = self._search_and_fetch(name, affiliation)
        
        emit({
            "kind": "scholar_metrics_end",
            "name": name,
            "metrics": metrics,
            "source": "search",
            "elapsed_sec": round(time.time() - t0, 3)
        })
        
        return metrics
    
    def _fetch_from_profile_url(self, profile_url: str) -> Dict[str, str]:
        """
        Fetch metrics from a direct Google Scholar profile URL.
        
        Args:
            profile_url: Google Scholar profile URL
            
        Returns:
            Metrics dictionary
        """
        for attempt in range(self.max_retries):
            try:
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    time.sleep(AntiBlockStrategy.get_random_delay())
                
                # Make request with anti-blocking headers
                headers = AntiBlockStrategy.get_headers()
                proxies = self._get_random_proxy() if self.use_proxies else None
                
                response = self.session.get(
                    profile_url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return self._parse_content(response.text)
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    emit({
                        "kind": "scholar_rate_limit",
                        "attempt": attempt + 1,
                        "url": profile_url
                    })
                    time.sleep(5.0 * (attempt + 1))
                    continue
                else:
                    emit({
                        "kind": "scholar_fetch_error",
                        "status_code": response.status_code,
                        "url": profile_url
                    })
                    
            except Exception as e:
                emit({
                    "kind": "scholar_fetch_exception",
                    "error": str(e),
                    "attempt": attempt + 1
                })
                if attempt < self.max_retries - 1:
                    time.sleep(AntiBlockStrategy.get_random_delay())
        
        # Return empty metrics if all attempts failed
        return self._empty_metrics()
    
    def _search_and_fetch(
        self,
        name: str,
        affiliation: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Search for scholar profile and fetch metrics.
        
        Args:
            name: Person's name
            affiliation: Person's affiliation
            
        Returns:
            Metrics dictionary
        """
        # Build search query
        query = name
        if affiliation:
            query = f"{name} {affiliation}"
        
        # Search for profile
        search_url = f"https://scholar.google.com/citations?{urlencode({'mauthors': query})}"
        
        for attempt in range(self.max_retries):
            try:
                # Add random delay
                if attempt > 0:
                    time.sleep(AntiBlockStrategy.get_random_delay())
                
                headers = AntiBlockStrategy.get_headers()
                proxies = self._get_random_proxy() if self.use_proxies else None
                
                response = self.session.get(
                    search_url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    # Parse search results to find profile link
                    profile_url = self._extract_profile_link(response.text, name)
                    
                    if profile_url:
                        # Fetch from profile
                        return self._fetch_from_profile_url(profile_url)
                    else:
                        emit({
                            "kind": "scholar_profile_not_found",
                            "name": name,
                            "search_url": search_url
                        })
                        break
                        
                elif response.status_code == 429:
                    emit({
                        "kind": "scholar_search_rate_limit",
                        "attempt": attempt + 1
                    })
                    time.sleep(5.0 * (attempt + 1))
                    continue
                    
            except Exception as e:
                emit({
                    "kind": "scholar_search_exception",
                    "error": str(e),
                    "attempt": attempt + 1
                })
                if attempt < self.max_retries - 1:
                    time.sleep(AntiBlockStrategy.get_random_delay())
        
        return self._empty_metrics()
    
    def _extract_profile_link(self, html: str, name: str) -> Optional[str]:
        """
        Extract profile link from search results.
        
        Args:
            html: Search results HTML
            name: Target person's name
            
        Returns:
            Profile URL or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for profile links in search results
            # Google Scholar search results have profile links with class "gs_ai_t"
            for link in soup.find_all('a', class_='gs_ai_t'):
                href = link.get('href', '')
                if '/citations?user=' in href:
                    # Found a profile link
                    if not href.startswith('http'):
                        href = 'https://scholar.google.com' + href
                    return href
            
            # Fallback: look for any citations link
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/citations?user=' in href:
                    if not href.startswith('http'):
                        href = 'https://scholar.google.com' + href
                    return href
                    
        except Exception as e:
            emit({
                "kind": "profile_link_extraction_error",
                "error": str(e)
            })
        
        return None
    
    def _parse_content(self, html: str) -> Dict[str, str]:
        """
        Parse metrics from HTML content with multiple strategies.
        
        Args:
            html: HTML content
            
        Returns:
            Metrics dictionary
        """
        # Try modern page structure first
        metrics = self._parse_modern_structure(html)
        if self._has_valid_metrics(metrics):
            return metrics
        
        # Try legacy page structure
        metrics = self._parse_legacy_structure(html)
        if self._has_valid_metrics(metrics):
            return metrics
        
        # Fallback to regex extraction
        return self._parse_regex_fallback(html)
    
    def _parse_modern_structure(self, html: str) -> Dict[str, str]:
        """
        Parse metrics from modern Google Scholar page structure.
        
        Uses BeautifulSoup to extract structured data.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            metrics = self._empty_metrics()
            
            # Modern structure: metrics are in a table with id "gsc_rsb_st"
            table = soup.find('table', id='gsc_rsb_st')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'citations' in label and 'all' in label:
                            metrics['citations_total'] = value
                        elif 'citations' in label and 'since' in label:
                            metrics['citations_recent'] = value
                        elif 'h-index' in label and 'all' in label:
                            metrics['h_index'] = value
                        elif 'i10-index' in label and 'all' in label:
                            metrics['h10_index'] = value
            
            return metrics
            
        except Exception as e:
            emit({
                "kind": "modern_parse_error",
                "error": str(e)
            })
            return self._empty_metrics()
    
    def _parse_legacy_structure(self, html: str) -> Dict[str, str]:
        """
        Parse metrics from legacy Google Scholar page structure.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            metrics = self._empty_metrics()
            
            # Legacy structure: metrics in divs with specific classes
            # Look for citation stats
            citation_elements = soup.find_all('td', class_='gsc_rsb_std')
            if len(citation_elements) >= 6:
                # First row: Citations (All, Since 2019)
                metrics['citations_total'] = citation_elements[0].get_text(strip=True)
                metrics['citations_recent'] = citation_elements[1].get_text(strip=True)
                # Second row: h-index (All, Since 2019)
                metrics['h_index'] = citation_elements[2].get_text(strip=True)
                # Third row: i10-index (All, Since 2019)
                metrics['h10_index'] = citation_elements[4].get_text(strip=True)
            
            return metrics
            
        except Exception as e:
            emit({
                "kind": "legacy_parse_error",
                "error": str(e)
            })
            return self._empty_metrics()
    
    def _parse_regex_fallback(self, html: str) -> Dict[str, str]:
        """
        Fallback regex-based parsing (from original implementation).
        
        Args:
            html: HTML content
            
        Returns:
            Metrics dictionary
        """
        metrics = self._empty_metrics()
        
        # Try to find h-index
        m = re.search(r"h[-\s]?index[^0-9]*([0-9]+)", html, re.I)
        if m:
            metrics["h_index"] = m.group(1)
        
        # Try to find i10-index (h10-index)
        m = re.search(r"i10[-\s]?index[^0-9]*([0-9]+)", html, re.I)
        if m:
            metrics["h10_index"] = m.group(1)
        
        # Try to find total citations
        m = re.search(r"Citations[^0-9]*([0-9]+)", html, re.I)
        if m:
            metrics["citations_total"] = m.group(1)
        
        # Try to find recent citations
        m = re.search(r"Since\s+\d{4}[^0-9]*([0-9]+)", html, re.I)
        if m:
            metrics["citations_recent"] = m.group(1)
        
        return metrics
    
    def _get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy from the proxy list."""
        if not self.proxy_list:
            return None
        
        proxy_url = random.choice(self.proxy_list)
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def _empty_metrics(self) -> Dict[str, str]:
        """Return empty metrics dictionary."""
        return {
            "h_index": "",
            "h10_index": "",
            "citations_total": "",
            "citations_recent": ""
        }
    
    def _has_valid_metrics(self, metrics: Dict[str, str]) -> bool:
        """Check if metrics dictionary has any valid values."""
        return any(
            metrics.get(key, "").strip()
            for key in ["h_index", "citations_total"]
        )


class AcademicMetricsFetcher:
    """
    Multi-platform academic metrics aggregator.
    
    Fetches and combines metrics from multiple sources:
    - Google Scholar
    - ResearchGate (if available)
    - Semantic Scholar (if available)
    """
    
    def __init__(self):
        """Initialize the multi-platform fetcher."""
        self.scholar_fetcher = ScholarMetricsFetcher()
    
    def fetch_all(
        self,
        name: str,
        scholar_url: Optional[str] = None,
        affiliation: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Fetch metrics from all available platforms.
        
        Args:
            name: Person's name
            scholar_url: Google Scholar profile URL
            affiliation: Person's affiliation
            
        Returns:
            Dictionary with platform names as keys and metrics as values
        """
        results = {}
        
        # Fetch from Google Scholar
        scholar_metrics = self.scholar_fetcher.run(
            name=name,
            profile_url=scholar_url,
            affiliation=affiliation
        )
        results['google_scholar'] = scholar_metrics
        
        # TODO: Add ResearchGate fetcher
        # TODO: Add Semantic Scholar fetcher
        
        return results
    
    def get_best_metrics(
        self,
        name: str,
        scholar_url: Optional[str] = None,
        affiliation: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Fetch metrics from all platforms and return the best/most complete set.
        
        Args:
            name: Person's name
            scholar_url: Google Scholar profile URL
            affiliation: Person's affiliation
            
        Returns:
            Best metrics dictionary
        """
        all_metrics = self.fetch_all(name, scholar_url, affiliation)
        
        # For now, just return Google Scholar metrics
        # In future, we can combine metrics from multiple sources
        return all_metrics.get('google_scholar', self._empty_metrics())
    
    def _empty_metrics(self) -> Dict[str, str]:
        """Return empty metrics dictionary."""
        return {
            "h_index": "",
            "h10_index": "",
            "citations_total": "",
            "citations_recent": ""
        }


# Example usage and testing
if __name__ == "__main__":
    # Test with a known Google Scholar profile
    fetcher = ScholarMetricsFetcher()
    
    # Test 1: Direct profile URL
    print("Test 1: Fetching from direct profile URL")
    metrics = fetcher.run(
        name="Yann LeCun",
        profile_url="https://scholar.google.com/citations?user=WLN3QrAAAAAJ"
    )
    print(f"Metrics: {metrics}\n")
    
    # Test 2: Search by name
    print("Test 2: Searching by name and affiliation")
    metrics = fetcher.run(
        name="Geoffrey Hinton",
        affiliation="University of Toronto"
    )
    print(f"Metrics: {metrics}\n")
    
    # Test 3: Multi-platform fetcher
    print("Test 3: Multi-platform fetcher")
    multi_fetcher = AcademicMetricsFetcher()
    all_metrics = multi_fetcher.fetch_all(
        name="Yoshua Bengio",
        affiliation="Université de Montréal"
    )
    print(f"All metrics: {all_metrics}")
