import time
import threading

class RateLimiter:
    """Thread-safe fixed-window limiter per key.

    acquire(key) returns True if within limit for current window,
    otherwise False without sleeping.
    """
    def __init__(self, limit: int = 60, window_seconds: float = 60.0):
        self.limit = int(limit)
        self.window = float(window_seconds)
        self._state: dict[str, tuple[float, int]] = {}
        self._lock = threading.RLock()

    def acquire(self, key: str) -> bool:
        """Consume one token for key; start/reset window when expired. Thread-safe."""
        with self._lock:
            now = time.time()
            start, count = self._state.get(key, (now, 0))
            if now - start >= self.window:
                start, count = now, 0
            if count >= self.limit:
                self._state[key] = (start, count)
                return False
            count += 1
            self._state[key] = (start, count)
            return True
"""Token-based rate limiter over a sliding window per key."""
