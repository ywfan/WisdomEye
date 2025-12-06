import time
import random
from typing import Callable, TypeVar

T = TypeVar("T")

class RetryPolicy:
    """Run a callable with configurable attempts and backoff.

    Backoff grows exponentially from base_delay up to max_delay,
    with small jitter to avoid thundering herd.
    """
    def __init__(self, attempts: int = 3, base_delay: float = 0.5, max_delay: float = 2.0):
        self.attempts = int(attempts)
        self.base_delay = float(base_delay)
        self.max_delay = float(max_delay)

    def run(self, fn: Callable[[], T]) -> T:
        """Execute fn with retries; raise last error if all attempts fail."""
        last_err = None
        for i in range(max(1, self.attempts)):
            try:
                return fn()
            except Exception as e:
                last_err = e
                delay = min(self.max_delay, self.base_delay * (2 ** i))
                delay += random.uniform(0, 0.2)
                time.sleep(delay)
        raise last_err if last_err else RuntimeError("retry_failed")
"""Exponential-backoff retry helper for transient errors."""
