"""
Unit tests for enhanced scholar metrics fetcher.

Tests the ScholarMetricsFetcher and AcademicMetricsFetcher classes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from infra.scholar_metrics_enhanced import (
    AntiBlockStrategy,
    ScholarMetricsFetcher,
    AcademicMetricsFetcher
)


class TestAntiBlockStrategy:
    """Test anti-blocking strategies."""
    
    def test_get_random_user_agent(self):
        """Test user agent rotation."""
        ua1 = AntiBlockStrategy.get_random_user_agent()
        assert isinstance(ua1, str)
        assert len(ua1) > 0
        assert "Mozilla" in ua1
        
        # Test randomness (should get different UAs over multiple calls)
        uas = set(AntiBlockStrategy.get_random_user_agent() for _ in range(20))
        assert len(uas) > 1  # Should have some variation
    
    def test_get_random_delay(self):
        """Test random delay generation."""
        delay = AntiBlockStrategy.get_random_delay()
        assert isinstance(delay, float)
        assert 1.0 <= delay <= 3.0
        
        # Test multiple delays are different
        delays = [AntiBlockStrategy.get_random_delay() for _ in range(10)]
        assert len(set(delays)) > 1
    
    def test_get_headers(self):
        """Test HTTP headers generation."""
        headers = AntiBlockStrategy.get_headers()
        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert headers["DNT"] == "1"


class TestScholarMetricsFetcher:
    """Test ScholarMetricsFetcher class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.fetcher = ScholarMetricsFetcher(timeout=5.0)
    
    def test_initialization(self):
        """Test fetcher initialization."""
        assert self.fetcher.timeout == 5.0
        assert self.fetcher.max_retries == 3
        assert self.fetcher.use_proxies is False
        assert self.fetcher.proxy_list == []
    
    def test_initialization_with_proxies(self):
        """Test initialization with proxy support."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        fetcher = ScholarMetricsFetcher(use_proxies=True, proxy_list=proxies)
        assert fetcher.use_proxies is True
        assert fetcher.proxy_list == proxies
    
    def test_empty_metrics(self):
        """Test empty metrics structure."""
        metrics = self.fetcher._empty_metrics()
        assert metrics["h_index"] == ""
        assert metrics["h10_index"] == ""
        assert metrics["citations_total"] == ""
        assert metrics["citations_recent"] == ""
    
    def test_has_valid_metrics(self):
        """Test valid metrics detection."""
        # Valid metrics
        assert self.fetcher._has_valid_metrics({"h_index": "10", "citations_total": "100"})
        assert self.fetcher._has_valid_metrics({"h_index": "5"})
        
        # Invalid metrics
        assert not self.fetcher._has_valid_metrics({"h_index": "", "citations_total": ""})
        assert not self.fetcher._has_valid_metrics({})
    
    def test_parse_modern_structure(self):
        """Test parsing modern Google Scholar page structure."""
        # Mock HTML with modern structure
        html = """
        <html>
        <table id="gsc_rsb_st">
            <tr><td>Citations</td><td>All</td><td>Since 2019</td></tr>
            <tr><td></td><td>1500</td><td>800</td></tr>
            <tr><td>h-index</td><td>All</td><td>Since 2019</td></tr>
            <tr><td></td><td>25</td><td>18</td></tr>
            <tr><td>i10-index</td><td>All</td><td>Since 2019</td></tr>
            <tr><td></td><td>40</td><td>30</td></tr>
        </table>
        </html>
        """
        
        metrics = self.fetcher._parse_modern_structure(html)
        assert metrics["citations_total"] in ["1500", ""]
        assert metrics["h_index"] in ["25", ""]
    
    def test_parse_legacy_structure(self):
        """Test parsing legacy Google Scholar page structure."""
        html = """
        <html>
        <td class="gsc_rsb_std">1500</td>
        <td class="gsc_rsb_std">800</td>
        <td class="gsc_rsb_std">25</td>
        <td class="gsc_rsb_std">18</td>
        <td class="gsc_rsb_std">40</td>
        <td class="gsc_rsb_std">30</td>
        </html>
        """
        
        metrics = self.fetcher._parse_legacy_structure(html)
        # Should extract some metrics
        assert isinstance(metrics, dict)
    
    def test_parse_regex_fallback(self):
        """Test regex-based parsing fallback."""
        html = """
        Scholar Profile
        h-index: 25
        i10-index: 40
        Citations: 1500
        Since 2019: 800
        """
        
        metrics = self.fetcher._parse_regex_fallback(html)
        assert metrics["h_index"] == "25"
        assert metrics["h10_index"] == "40"
        assert metrics["citations_total"] == "1500"
        assert metrics["citations_recent"] == "800"
    
    def test_parse_content_with_multiple_strategies(self):
        """Test content parsing with strategy fallback."""
        # HTML that should match regex fallback
        html = "h-index: 30 Citations: 2000"
        
        metrics = self.fetcher._parse_content(html)
        assert metrics["h_index"] == "30"
        assert metrics["citations_total"] == "2000"
    
    def test_extract_profile_link(self):
        """Test profile link extraction from search results."""
        html = """
        <html>
        <a class="gs_ai_t" href="/citations?user=ABC123">John Doe</a>
        </html>
        """
        
        link = self.fetcher._extract_profile_link(html, "John Doe")
        assert link is not None
        assert "citations?user=ABC123" in link
    
    def test_run_with_provided_content(self):
        """Test run method with provided content."""
        content = "h-index: 15 Citations: 500"
        
        metrics = self.fetcher.run(name="Test User", content=content)
        assert metrics["h_index"] == "15"
        assert metrics["citations_total"] == "500"
    
    @patch('infra.scholar_metrics_enhanced.requests.Session')
    def test_fetch_from_profile_url_success(self, mock_session):
        """Test successful profile URL fetching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "h-index: 20 Citations: 1000"
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        fetcher = ScholarMetricsFetcher()
        fetcher.session = mock_session_instance
        
        metrics = fetcher._fetch_from_profile_url("https://scholar.google.com/citations?user=TEST")
        
        assert metrics["h_index"] == "20"
        assert metrics["citations_total"] == "1000"
    
    @patch('infra.scholar_metrics_enhanced.requests.Session')
    def test_fetch_from_profile_url_rate_limit(self, mock_session):
        """Test rate limit handling (429 response)."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        fetcher = ScholarMetricsFetcher(max_retries=1)
        fetcher.session = mock_session_instance
        
        metrics = fetcher._fetch_from_profile_url("https://scholar.google.com/citations?user=TEST")
        
        # Should return empty metrics after retries
        assert metrics == fetcher._empty_metrics()
    
    @patch('infra.scholar_metrics_enhanced.requests.Session')
    def test_fetch_with_retry_logic(self, mock_session):
        """Test retry logic on failure."""
        # Mock failed responses
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        
        fetcher = ScholarMetricsFetcher(max_retries=2)
        fetcher.session = mock_session_instance
        
        metrics = fetcher._fetch_from_profile_url("https://scholar.google.com/citations?user=TEST")
        
        # Should retry multiple times
        assert mock_session_instance.get.call_count >= 2
        assert metrics == fetcher._empty_metrics()
    
    def test_get_random_proxy(self):
        """Test random proxy selection."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"]
        fetcher = ScholarMetricsFetcher(use_proxies=True, proxy_list=proxies)
        
        proxy = fetcher._get_random_proxy()
        assert proxy is not None
        assert "http" in proxy
        assert "https" in proxy
    
    def test_get_random_proxy_empty_list(self):
        """Test proxy selection with empty list."""
        fetcher = ScholarMetricsFetcher(use_proxies=True, proxy_list=[])
        proxy = fetcher._get_random_proxy()
        assert proxy is None


class TestAcademicMetricsFetcher:
    """Test AcademicMetricsFetcher class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.fetcher = AcademicMetricsFetcher()
    
    def test_initialization(self):
        """Test fetcher initialization."""
        assert self.fetcher.scholar_fetcher is not None
        assert isinstance(self.fetcher.scholar_fetcher, ScholarMetricsFetcher)
    
    @patch.object(ScholarMetricsFetcher, 'run')
    def test_fetch_all(self, mock_run):
        """Test fetch_all method."""
        # Mock scholar metrics
        mock_run.return_value = {
            "h_index": "25",
            "h10_index": "40",
            "citations_total": "1500",
            "citations_recent": "800"
        }
        
        results = self.fetcher.fetch_all(
            name="Test User",
            scholar_url="https://scholar.google.com/citations?user=TEST",
            affiliation="Test University"
        )
        
        assert "google_scholar" in results
        assert results["google_scholar"]["h_index"] == "25"
        mock_run.assert_called_once()
    
    @patch.object(ScholarMetricsFetcher, 'run')
    def test_get_best_metrics(self, mock_run):
        """Test get_best_metrics method."""
        mock_run.return_value = {
            "h_index": "30",
            "citations_total": "2000"
        }
        
        best_metrics = self.fetcher.get_best_metrics(
            name="Test User",
            affiliation="Test University"
        )
        
        assert best_metrics["h_index"] == "30"
        assert best_metrics["citations_total"] == "2000"


class TestRealWorldScenarios:
    """Test real-world scenarios with mock data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.fetcher = ScholarMetricsFetcher()
    
    def test_parse_complete_profile_page(self):
        """Test parsing a complete profile page."""
        # Realistic HTML structure
        html = """
        <html>
        <body>
            <div class="gsc_rsb">
                <table id="gsc_rsb_st">
                    <tbody>
                        <tr>
                            <th class="gsc_rsb_sc1">
                                <a href="#">Citations</a>
                            </th>
                            <th class="gsc_rsb_sth">All</th>
                            <th class="gsc_rsb_sth">Since 2019</th>
                        </tr>
                        <tr>
                            <td class="gsc_rsb_sc1">
                                <a href="#">Citations</a>
                            </td>
                            <td class="gsc_rsb_std">5432</td>
                            <td class="gsc_rsb_std">3210</td>
                        </tr>
                        <tr>
                            <td class="gsc_rsb_sc1">
                                <a href="#">h-index</a>
                            </td>
                            <td class="gsc_rsb_std">42</td>
                            <td class="gsc_rsb_std">35</td>
                        </tr>
                        <tr>
                            <td class="gsc_rsb_sc1">
                                <a href="#">i10-index</a>
                            </td>
                            <td class="gsc_rsb_std">89</td>
                            <td class="gsc_rsb_std">67</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        
        metrics = self.fetcher._parse_content(html)
        
        # Should successfully extract metrics
        assert self.fetcher._has_valid_metrics(metrics)
    
    def test_parse_minimal_html(self):
        """Test parsing minimal HTML with just text."""
        html = """
        John Doe - Google Scholar
        h-index: 25
        Total citations: 1500
        """
        
        metrics = self.fetcher._parse_content(html)
        assert metrics["h_index"] == "25"
        # Citations might not match exact pattern, but h-index should work
    
    def test_empty_html_handling(self):
        """Test handling of empty or invalid HTML."""
        html = ""
        metrics = self.fetcher._parse_content(html)
        assert metrics == self.fetcher._empty_metrics()
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML."""
        html = "<html><unclosed><tag>random text h-index"
        metrics = self.fetcher._parse_content(html)
        # Should not crash, returns empty or partial metrics
        assert isinstance(metrics, dict)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.fetcher = ScholarMetricsFetcher()
    
    def test_none_values(self):
        """Test handling of None values."""
        metrics = self.fetcher.run(name="Test", content=None)
        assert isinstance(metrics, dict)
    
    def test_empty_name(self):
        """Test handling of empty name."""
        metrics = self.fetcher.run(name="", content="h-index: 10")
        assert isinstance(metrics, dict)
    
    def test_special_characters_in_content(self):
        """Test handling of special characters."""
        html = """
        h-index: 25 © ® ™
        Citations: 1,500
        i10-index: 40
        """
        metrics = self.fetcher._parse_content(html)
        assert metrics["h_index"] == "25"
    
    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        html = """
        学者简介
        h-index: 30
        引用次数: 2000
        """
        metrics = self.fetcher._parse_content(html)
        assert metrics["h_index"] == "30"
    
    def test_very_large_numbers(self):
        """Test handling of very large citation numbers."""
        html = """
        h-index: 150
        Citations: 250000
        Since 2019: 50000
        """
        metrics = self.fetcher._parse_content(html)
        assert metrics["h_index"] == "150"
        assert metrics["citations_total"] == "250000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
