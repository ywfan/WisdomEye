import json
import time
from typing import Any, Dict, List, Optional

from .observability import emit

class SocialProviderAdapter:
    """Transforms heterogeneous social signals into a common shape."""
    def __init__(self, timeout: float = 8.0):
        self.timeout = float(timeout)

    def normalize(self, items: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
        """Map raw items to normalized fields and infer usernames for known platforms."""
        out: List[Dict[str, Any]] = []
        for it in items or []:
            plat = str(it.get("platform") or platform)
            url = str(it.get("url") or "")
            acc = str(it.get("account") or it.get("title") or "")
            # lightweight username extraction for certain platforms
            try:
                if not acc and plat == "GitHub" and url.startswith("http"):
                    seg = url.split("github.com/")[-1].split("/")[0]
                    acc = seg or acc
                if not acc and plat == "ResearchGate" and "researchgate.net/" in url:
                    seg = url.split("researchgate.net/")[-1]
                    if seg.startswith("profile/"):
                        acc = seg.split("/")[1]
                if not acc and plat == "Google Scholar" and "citations?user=" in url:
                    acc = "Scholar Profile"
            except Exception:
                pass
            out.append({
                "platform": plat,
                "account": acc,
                "url": url,
                "followers": str(it.get("followers") or it.get("metrics") or ""),
                "posts_per_month": str(it.get("posts_per_month") or ""),
                "topics": str(it.get("topics") or it.get("content") or ""),
            })
        return out

    def fetch(self, platform: str, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Placeholder fetch; integration can be implemented per platform."""
        t0 = time.time()
        emit({"kind": "social_fetch_start", "platform": platform, "query": query})
        emit({"kind": "social_fetch_end", "platform": platform, "query": query, "results": 0, "elapsed_sec": round(time.time() - t0, 3)})
        return []
"""Normalize social items across platforms and provide no-op fetch stub."""
