"""Unit tests for TTL cache."""
import time
import pytest
from infra.cache import TTLCache


class TestTTLCache:
    """Test TTL cache functionality."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a non-existent key returns None."""
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = TTLCache()
        cache.set("key1", "value1", ttl=0.1)  # 100ms TTL
        assert cache.get("key1") == "value1"
        time.sleep(0.15)  # Wait for expiration
        assert cache.get("key1") is None

    def test_no_ttl(self):
        """Test entries without TTL don't expire."""
        cache = TTLCache()
        cache.set("key1", "value1")
        time.sleep(0.1)
        assert cache.get("key1") == "value1"

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = TTLCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_invalidate_nonexistent(self):
        """Test invalidating non-existent key doesn't raise error."""
        cache = TTLCache()
        cache.invalidate("nonexistent")  # Should not raise

    def test_overwrite_value(self):
        """Test overwriting existing value."""
        cache = TTLCache()
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_different_types(self):
        """Test caching different data types."""
        cache = TTLCache()
        cache.set("int", 123)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        assert cache.get("int") == 123
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}
