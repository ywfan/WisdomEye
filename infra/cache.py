import time
from typing import Any, Optional

class TTLCache:
    """Key-value store with optional per-entry expiry.

    - set: stores value and optional TTL (seconds)
    - get: returns value if not expired; removes expired entries
    - invalidate: removes a key if present
    """
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value with optional TTL (seconds)."""
        exp = time.time() + float(ttl or 0) if ttl else 0.0
        self._store[str(key)] = (value, exp)

    def get(self, key: str) -> Optional[Any]:
        """Get a value; return None if missing or expired."""
        k = str(key)
        if k not in self._store:
            return None
        v, exp = self._store[k]
        if exp and time.time() > exp:
            try:
                del self._store[k]
            except Exception:
                pass
            return None
        return v

    def invalidate(self, key: str) -> None:
        """Remove a key from the cache if present."""
        try:
            del self._store[str(key)]
        except Exception:
            pass
"""Simple in-memory TTL cache for small request-level memoization."""
