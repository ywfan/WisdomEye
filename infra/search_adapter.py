import os
import json
import time
from typing import Any, Dict, List, Optional
import requests

from .cache import TTLCache
from .rate_limit import RateLimiter
from .retry import RetryPolicy
from .observability import emit
from .errors import classify_http, ExternalError

class SearchAdapter:
    def __init__(self, tavily_key: Optional[str], bocha_key: Optional[str], bocha_base: Optional[str], timeout: float = 10.0, cache_ttl: float = 120.0):
        self.tavily_key = tavily_key
        self.bocha_key = bocha_key
        self.bocha_base = (bocha_base or "").rstrip("/")
        self.timeout = float(timeout)
        self.cache = TTLCache()
        self.limiter = RateLimiter(limit=int(os.getenv("SEARCH_RATE_LIMIT", "120")), window_seconds=float(os.getenv("SEARCH_RATE_WINDOW", "60")))
        self.retry = RetryPolicy(attempts=3, base_delay=0.4, max_delay=1.5)
        self.cache_ttl = float(cache_ttl)
        self.calls = 0

    def search(self, query: str, max_results: int = 5, engines: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        engines = engines or ["tavily", "bocha"]
        if not self.limiter.acquire("web_search"):
            raise ExternalError("rate_limited")
        max_budget = None
        try:
            max_budget = int(os.getenv("BUDGET_MAX_SEARCH_CALLS", "0") or "0")
        except Exception:
            max_budget = 0
        if max_budget and self.calls >= max_budget:
            raise ExternalError("budget_exceeded")
        key = json.dumps({"q": query, "n": int(max_results), "e": engines})
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        t0 = time.time()
        res: List[Dict[str, Any]] = []
        if "tavily" in engines and self.tavily_key:
            def call_t() -> List[Dict[str, Any]]:
                url = "https://api.tavily.com/search"
                body = {"api_key": self.tavily_key, "query": query, "max_results": int(max_results)}
                r = requests.post(url, json=body, timeout=self.timeout)
                status = classify_http(r.status_code)
                if status != "ok":
                    raise ExternalError(status)
                data = r.json()
                items = data.get("results") or []
                out: List[Dict[str, Any]] = []
                for it in items:
                    out.append({"title": it.get("title") or "", "url": it.get("url") or "", "content": it.get("content") or it.get("snippet") or "", "source": "tavily"})
                return out
            res.extend(self.retry.run(call_t))
        if "bocha" in engines and self.bocha_key and self.bocha_base:
            def call_b() -> List[Dict[str, Any]]:
                url = self.bocha_base
                headers = {"Authorization": f"Bearer {self.bocha_key}", "Content-Type": "application/json"}
                r = requests.post(url, headers=headers, json={"q": query, "size": int(max_results)}, timeout=self.timeout)
                status = classify_http(r.status_code)
                if status != "ok":
                    raise ExternalError(status)
                data = r.json()
                items = data.get("results") or data.get("items") or data.get("data") or data.get("docs") or []
                out: List[Dict[str, Any]] = []
                for it in items:
                    out.append({"title": it.get("title") or "", "url": it.get("url") or "", "content": it.get("content") or it.get("snippet") or "", "source": "bocha"})
                return out
            res.extend(self.retry.run(call_b))
        seen: set[str] = set()
        dedup: List[Dict[str, Any]] = []
        for it in res:
            u = it.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                dedup.append(it)
        elapsed = time.time() - t0
        self.calls += 1
        emit({"kind": "web_search_adapter", "query": query, "results": len(dedup), "elapsed_sec": round(elapsed, 3)})
        self.cache.set(key, dedup, ttl=self.cache_ttl)
        return dedup
