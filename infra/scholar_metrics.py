import re
import time
from typing import Dict, Optional

from .observability import emit

class ScholarMetricsFetcher:
    """Extracts h-index, h10-index and citation counts from given content."""
    def __init__(self, timeout: float = 10.0):
        self.timeout = float(timeout)

    def _parse(self, html: str) -> Dict[str, str]:
        """Best-effort regex extraction; returns empty strings if not found."""
        s = html or ""
        out: Dict[str, str] = {
            "h_index": "",
            "h10_index": "",
            "citations_total": "",
            "citations_recent": "",
        }
        m = re.search(r"h[-\s]?index[^0-9]*([0-9]+)", s, re.I)
        if m:
            out["h_index"] = m.group(1)
        m = re.search(r"h10[-\s]?index[^0-9]*([0-9]+)", s, re.I)
        if m:
            out["h10_index"] = m.group(1)
        m = re.search(r"Citations[^0-9]*([0-9]+)", s, re.I)
        if m:
            out["citations_total"] = m.group(1)
        m = re.search(r"Recent[^0-9]*([0-9]+)", s, re.I)
        if m:
            out["citations_recent"] = m.group(1)
        return out

    def run(self, name: str, profile_url: Optional[str] = None, content: Optional[str] = None) -> Dict[str, str]:
        """Emit start/end events and return parsed metrics."""
        t0 = time.time()
        emit({"kind": "scholar_metrics_start", "name": name, "profile_url": profile_url or ""})
        out = self._parse(content or "") if content is not None else {"h_index": "", "h10_index": "", "citations_total": "", "citations_recent": ""}
        emit({"kind": "scholar_metrics_end", "name": name, "metrics": out, "elapsed_sec": round(time.time() - t0, 3)})
        return out
"""Heuristic parser for scholar metrics from HTML text."""
