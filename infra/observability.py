import json
import time
import sys
from pathlib import Path

def emit(event: dict) -> None:
    """Append a JSON event with timestamp to trace file.
    
    Silently ignores failures but prints warning to stderr for debugging.
    """
    try:
        root = Path.cwd() / "output" / "logs"
        root.mkdir(parents=True, exist_ok=True)
        event = dict(event or {})
        event.setdefault("ts", time.time())
        with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        # Print warning to stderr for debugging, but don't crash
        try:
            print(f"[WARNING] Failed to emit log event: {e}", file=sys.stderr)
        except Exception:
            pass
"""Structured event logging to output/logs/trace.jsonl."""
