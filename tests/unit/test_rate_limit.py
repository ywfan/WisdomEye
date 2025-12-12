"""Unit tests for rate limiter."""
import time
import pytest
from infra.rate_limit import RateLimiter


class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_basic_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(limit=3, window_seconds=1.0)
        
        # Should succeed for first 3 calls
        assert limiter.acquire("test_key") is True
        assert limiter.acquire("test_key") is True
        assert limiter.acquire("test_key") is True
        
        # 4th call should fail
        assert limiter.acquire("test_key") is False

    def test_window_reset(self):
        """Test that window resets after expiration."""
        limiter = RateLimiter(limit=2, window_seconds=0.1)
        
        # Use up limit
        assert limiter.acquire("test_key") is True
        assert limiter.acquire("test_key") is True
        assert limiter.acquire("test_key") is False
        
        # Wait for window to reset
        time.sleep(0.15)
        
        # Should work again
        assert limiter.acquire("test_key") is True

    def test_different_keys(self):
        """Test that different keys have independent limits."""
        limiter = RateLimiter(limit=2, window_seconds=1.0)
        
        # Key1 uses up its limit
        assert limiter.acquire("key1") is True
        assert limiter.acquire("key1") is True
        assert limiter.acquire("key1") is False
        
        # Key2 should still work
        assert limiter.acquire("key2") is True
        assert limiter.acquire("key2") is True

    def test_zero_limit(self):
        """Test that zero limit blocks all requests."""
        limiter = RateLimiter(limit=0, window_seconds=1.0)
        assert limiter.acquire("test_key") is False

    def test_high_limit(self):
        """Test with high limit."""
        limiter = RateLimiter(limit=100, window_seconds=1.0)
        for _ in range(100):
            assert limiter.acquire("test_key") is True
        assert limiter.acquire("test_key") is False
