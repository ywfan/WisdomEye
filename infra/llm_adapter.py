import os
import json
import time
from typing import Any, Dict, List, Optional, Union
import requests

from .cache import TTLCache
from .rate_limit import RateLimiter
from .retry import RetryPolicy
from .observability import emit
from .errors import classify_http, ExternalError

class LLMAdapter:
    def __init__(self, api_key: Optional[str], base_url: str, model: str, temperature: float = 0.0, max_tokens: Optional[int] = None, timeout: float = 200.0, retries: int = 2, cache_ttl: float = 60.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = float(temperature)
        self.max_tokens = max_tokens
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.cache = TTLCache()
        self.limiter = RateLimiter(limit=int(os.getenv("LLM_RATE_LIMIT", "60")), window_seconds=float(os.getenv("LLM_RATE_WINDOW", "60")))
        self.retry = RetryPolicy(attempts=self.retries, base_delay=0.6, max_delay=2.0)
        self.cache_ttl = float(cache_ttl)
        self.calls = 0

    def chat(self, messages: Union[str, List[Dict[str, str]]], stream: bool = False) -> Union[str, List[str]]:
        if stream:
            return ""
        if isinstance(messages, str):
            msgs = [{"role": "user", "content": messages}]
        else:
            msgs = messages
        max_budget = None
        try:
            max_budget = int(os.getenv("BUDGET_MAX_LLM_CALLS", "0") or "0")
        except Exception:
            max_budget = 0
        if max_budget and self.calls >= max_budget:
            raise ExternalError("budget_exceeded")
        if not self.limiter.acquire("llm_chat"):
            raise ExternalError("rate_limited")
        body: Dict[str, Any] = {"model": self.model, "messages": msgs, "temperature": self.temperature, "stream": False}
        if self.max_tokens:
            body["max_tokens"] = int(self.max_tokens)
        url = self.base_url + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        prompt_text = "\n".join([str(m.get("content") or "") for m in msgs])
        cache_key = json.dumps({"u": url, "n": self.model, "t": self.temperature, "p": prompt_text})
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        t0 = time.time()
        def call() -> str:
            r = requests.post(url, headers=headers, json=body, timeout=self.timeout)
            status = classify_http(r.status_code)
            if status != "ok":
                raise ExternalError(status, r.text[:200])
            data = r.json()
            choices = data.get("choices") or []
            if choices:
                m = choices[0].get("message") or {}
                out = m.get("content") or choices[0].get("text") or ""
            else:
                out = r.text or ""
            return out
        out = self.retry.run(call)
        self.calls += 1
        elapsed = time.time() - t0
        emit({"kind": "llm_adapter_chat", "model": self.model, "base": self.base_url, "temperature": self.temperature, "chars_in": len(prompt_text), "chars_out": len(out), "elapsed_sec": round(elapsed, 3), "status": "ok"})
        self.cache.set(cache_key, out, ttl=self.cache_ttl)
        return out
