import os
import sys
import argparse
from pathlib import Path
import concurrent.futures

# ensure project root on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules.resume_text.extractor import ResumeTextExtractor
from modules.resume_json.formatter import ResumeJSONFormatter
from modules.resume_json.enricher import ResumeJSONEnricher
from modules.output.render import render_html, render_pdf

# Offline adapters
class DummyLLM:
    """Offline LLM stub: returns minimal JSON or empty strings for prompts."""
    def chat(self, msgs, stream=False):
        text = "\n".join([str(m.get("content","")) for m in (msgs if isinstance(msgs, list) else [msgs])])
        if isinstance(msgs, list) and msgs and msgs[0].get("role") == "system" and "Output JSON Schema" in str(msgs[0].get("content","")):
            return "{}"
        if "严格输出JSON对象" in text:
            return "{}"
        if "评分" in text and "0-10" in text:
            return "{}"
        return ""

class DummySearch:
    """Offline search stub: returns no results."""
    def search(self, query, max_results=5, engines=None):
        return []

def process_file(path: Path, offline: bool) -> str:
    """Process a single file through the pipeline; HTML path is returned."""
    ext = ResumeTextExtractor()
    txt_path = ext.extract_to_text(str(path))
    fmt = ResumeJSONFormatter(llm=(DummyLLM() if offline else None))
    json_path = fmt.to_json_file(txt_path)
    enr = ResumeJSONEnricher(search=(DummySearch() if offline else None), llm=(DummyLLM() if offline else None))
    rich_path = enr.enrich_file(json_path)
    final_path = enr.generate_final(rich_path)
    html_path = render_html(final_path)
    try:
        render_pdf(final_path)
    except Exception:
        pass
    return html_path

def main():
    """CLI entry: run batch processing with concurrency and offline option."""
    ap = argparse.ArgumentParser(description="Batch resume pipeline")
    ap.add_argument("--input", required=True, help="Input directory containing .pdf/.docx/.txt")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--feature", default=os.getenv("FEATURE_NEW_PIPELINE", "0"))
    ap.add_argument("--budget-llm", type=int, default=int(os.getenv("BUDGET_MAX_LLM_CALLS", "0") or "0"))
    ap.add_argument("--budget-search", type=int, default=int(os.getenv("BUDGET_MAX_SEARCH_CALLS", "0") or "0"))
    ap.add_argument("--offline", action="store_true", help="Run without external calls")
    args = ap.parse_args()

    os.environ["FEATURE_NEW_PIPELINE"] = str(args.feature)
    if args.budget_llm:
        os.environ["BUDGET_MAX_LLM_CALLS"] = str(args.budget_llm)
    if args.budget_search:
        os.environ["BUDGET_MAX_SEARCH_CALLS"] = str(args.budget_search)

    root = Path(args.input)
    files = [p for p in root.iterdir() if p.suffix.lower() in {".pdf", ".docx", ".txt"}]
    if not files:
        print("No input files found")
        return 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        futs = [ex.submit(process_file, p, args.offline) for p in files]
        for f in concurrent.futures.as_completed(futs):
            try:
                print("Generated:", f.result())
            except Exception as e:
                print("Error:", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
