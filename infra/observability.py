import json
import time
from pathlib import Path

def emit(event: dict) -> None:
    """Append a JSON event with timestamp to trace file; ignore failures."""
    try:
        root = Path.cwd() / "output" / "logs"
        root.mkdir(parents=True, exist_ok=True)
        event = dict(event or {})
        event.setdefault("ts", time.time())
        with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass
"""Structured event logging to output/logs/trace.jsonl."""
