import os
import json
from typing import Any, Dict, List, Optional
import time
from pathlib import Path

import requests


class SearchClient:
    """Unified web search client for Tavily and Bocha with simple merging."""
    def __init__(self, tavily_key: Optional[str] = None, bocha_key: Optional[str] = None, bocha_base: Optional[str] = None, timeout: float = 10.0):
        self.tavily_key = tavily_key
        self.bocha_key = bocha_key
        self.bocha_base = (bocha_base or "").rstrip("/")
        self.timeout = float(timeout)

    def tavily(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Call Tavily API; return normalized list of {title,url,content,source}."""
        t0 = time.time()
        if not self.tavily_key:
            return []
        try:
            print(f"[Search请求] engine=tavily url=https://api.tavily.com/search query={query} max_results={max_results}")
        except Exception:
            pass
        url = "https://api.tavily.com/search"
        body = {"api_key": self.tavily_key, "query": query, "max_results": int(max_results)}
        try:
            r = requests.post(url, json=body, timeout=self.timeout)
        except Exception as e:
            try:
                print(f"[Search错误] engine=tavily {e}")
            except Exception:
                pass
            return []
        if not r.ok:
            return []
        try:
            data = r.json()
        except Exception:
            return []
        items = data.get("results") or []
        out: List[Dict[str, Any]] = []
        for it in items:
            out.append({
                "title": it.get("title") or "",
                "url": it.get("url") or "",
                "content": it.get("content") or it.get("snippet") or "",
                "source": "tavily",
            })
        try:
            preview = (out[0].get("content", "") if out else "")
            print(f"[Search输出] engine=tavily count={len(out)} preview={preview[:200]}")
            # trace file logging
            try:
                elapsed = time.time() - t0
                total_chars = sum(len(x.get("content", "")) for x in out)
                root = Path.cwd() / "output" / "logs"
                root.mkdir(parents=True, exist_ok=True)
                path = root / "trace.jsonl"
                rec = {
                    "kind": "web_search",
                    "engine": "tavily",
                    "query": query,
                    "results": len(out),
                    "content_chars": total_chars,
                    "elapsed_sec": round(elapsed, 3),
                }
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception:
                pass
        except Exception:
            pass
        return out

    def bocha(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Call Bocha AI Search; return normalized list of {title,url,content,source}."""
        t0 = time.time()
        if not (self.bocha_key and self.bocha_base):
            return []
        try:
            print(f"[Search请求] engine=bocha url={self.bocha_base} query={query} max_results={max_results}")
        except Exception:
            pass
        url = self.bocha_base
        headers = {"Authorization": f"Bearer {self.bocha_key}", "Content-Type": "application/json"}
        attempts: List[Dict[str, Any]] = [
            {"method": "POST", "url": url, "json": {"q": query, "size": int(max_results)}},
            {"method": "POST", "url": url, "json": {"query": query, "max_results": int(max_results)}},
        ]
        data: Dict[str, Any] = {}
        text_preview = ""
        for req in attempts:
            try:
                if req["method"] == "POST":
                    r = requests.post(req["url"], headers=headers, json=req["json"], timeout=self.timeout)
                else:
                    r = requests.get(req["url"], headers=headers, params=req.get("params", {}), timeout=self.timeout)
                if not r.ok:
                    text_preview = r.text[:200]
                    continue
                try:
                    data = r.json()
                    text_preview = str(data)[:200]
                    break
                except Exception:
                    text_preview = r.text[:200]
                    continue
            except Exception:
                continue
        items = data.get("results") or data.get("items") or data.get("data") or data.get("docs") or []
        if not items:
            msgs = data.get("messages") or []
            for m in msgs:
                c = m.get("content") or ""
                try:
                    obj = json.loads(c)
                    ws = (obj.get("webSearch") or {}).get("results") or []
                    if ws:
                        items = ws
                        break
                except Exception:
                    continue
        out: List[Dict[str, Any]] = []
        for it in items:
            out.append({
                "title": it.get("title") or "",
                "url": it.get("url") or "",
                "content": it.get("content") or it.get("snippet") or "",
                "source": "bocha",
            })
        try:
            preview = (out[0].get("content", "") if out else text_preview)
            print(f"[Search输出] engine=bocha count={len(out)} preview={str(preview)[:200]}")
            # trace file logging
            try:
                elapsed = time.time() - t0
                total_chars = sum(len(x.get("content", "")) for x in out)
                root = Path.cwd() / "output" / "logs"
                root.mkdir(parents=True, exist_ok=True)
                path = root / "trace.jsonl"
                rec = {
                    "kind": "web_search",
                    "engine": "bocha",
                    "query": query,
                    "results": len(out),
                    "content_chars": total_chars,
                    "elapsed_sec": round(elapsed, 3),
                }
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception:
                pass
        except Exception:
            pass
        return out

    def search(self, query: str, max_results: int = 5, engines: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Run engines, combine and deduplicate by URL; adapter if feature enabled."""
        engines = engines or ["tavily", "bocha"]
        try:
            import os as _os
            if _os.getenv("FEATURE_NEW_PIPELINE") == "1":
                from infra.search_adapter import SearchAdapter as _SA
                sa = _SA(tavily_key=self.tavily_key, bocha_key=self.bocha_key, bocha_base=self.bocha_base, timeout=self.timeout)
                return sa.search(query, max_results=max_results, engines=engines)
        except Exception:
            pass
        res: List[Dict[str, Any]] = []
        if "tavily" in engines:
            res.extend(self.tavily(query, max_results))
        if "bocha" in engines:
            res.extend(self.bocha(query, max_results))
        seen: set[str] = set()
        dedup: List[Dict[str, Any]] = []
        for it in res:
            u = it.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                dedup.append(it)
        try:
            print(f"[Search合并] engines={','.join(engines)} total={len(res)} dedup={len(dedup)}")
        except Exception:
            pass
        return dedup

    @classmethod
    def from_env(cls, dotenv_path: Optional[str] = None) -> "SearchClient":
        """Construct client by reading TAVILY/BOCHA keys and base from dotenv."""
        if dotenv_path:
            try:
                with open(dotenv_path, "r", encoding="utf-8") as f:
                    for line in f.readlines():
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        if "=" in s:
                            k, v = s.split("=", 1)
                            val = v.strip()
                            if (val.startswith("\"") and val.endswith("\"")) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            os.environ.setdefault(k.strip(), val)
            except Exception:
                pass
        tavily_key = os.getenv("TAVILY_API_KEY") or None
        bocha_key = os.getenv("BOCHA_WEB_SEARCH_API_KEY") or None
        bocha_base = os.getenv("BOCHA_BASE_URL") or None
        return cls(tavily_key=tavily_key, bocha_key=bocha_key, bocha_base=bocha_base)
