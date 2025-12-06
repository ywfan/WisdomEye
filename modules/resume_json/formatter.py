import json
import re
from pathlib import Path
from typing import Optional
import time

from utils.llm import LLMClient
from infra.schema_contract import SchemaContract
from tools.fs import write_text, read_text


PROMPT_BASE = (
    """# Role
你是一名资深的数据结构化专家，专精于非结构化文本（简历/CV）的清洗与解析。你的任务是将OCR或转换后的混乱纯文本（txt）精准还原为标准化的JSON数据。
# Task
接收一段由PDF/Word转换而来的纯文本简历数据。该数据可能存在排版错乱、分页符残留、乱码符号等噪音。请将其清洗并映射到指定的JSON Schema中，确保层级清晰，内容忠实于原文。

# Constraints & Guidelines (Crucial)
1.  **内容零篡改 (Zero Hallucination)**：
    * **原则**：JSON中的所有Value必须直接摘录自原文。
    * **禁止**：严禁自动补全地址、推算日期、或根据公司名联想行业标签。
    * **处理缺失**：如果原文没有某字段信息（如无学术活动），对应字段保留为空数组 `[]` 或 null，不要编造。

2.  **噪音清洗与文本修复**：
    * 移除转换产生的无意义字符（如 `|`, `______`, `[Page 2]`, `^L`, `*`）。
    * **智能修复**：识别因换行导致的断词（如将 "深度\n学习" 修复为 "深度学习"），还原被截断的长句。

3.  **字段归类原则 (Strict Categorization)**：
    * **学术区分**：
        * **论文**：包含已发表、在投（Under Review）、预印本（ArXiv）等。
        * **学术活动**：不仅包含“参加会议”，还包含“组织会议”、“担任审稿人”、“受邀讲座”等学术服务工作。
    * **荣誉 vs 获奖**：优先区分。无法明确区分时，优先放入 `awards`。

# Output JSON Schema
请严格按照以下结构输出。Key为英文，Value保持原文语言。
"""
)

def _prompt_with_schema() -> str:
    schema_path = Path(__file__).with_name("schema.json")
    try:
        schema_text = schema_path.read_text(encoding="utf-8")
    except Exception:
        schema_text = "{}"
    return PROMPT_BASE + "\n" + schema_text


class ResumeJSONFormatter:
    """Turns plain resume text into schema-conform JSON via LLM + contract."""
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient.from_env(dotenv_path=".env", temperature=0.0)

    def to_json(self, plain_text: str) -> str:
        """Call LLM with schema-aware prompt, validate and conform, return JSON string."""
        t0 = time.time()
        print("[简历转JSON输入]", plain_text[:400])
        msgs = [
            {"role": "system", "content": _prompt_with_schema()},
            {"role": "user", "content": plain_text},
        ]
        out = self.llm.chat(msgs)
        data = self._ensure_json(out)
        contract = SchemaContract()
        ok, errors = contract.validate(data)
        final_data = data if ok else contract.conform(data)
        s = json.dumps(final_data, ensure_ascii=False, indent=2)
        print("[简历转JSON输出]", s[:800])
        try:
            # trace file logging
            from pathlib import Path as _P
            import json as _J
            root = _P.cwd() / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            rec = {
                "kind": "json_format",
                "chars_in": len(plain_text or ""),
                "chars_out": len(s or ""),
                "elapsed_sec": round(time.time() - t0, 3),
                "schema_ok": bool(ok),
                "schema_errors": int(len(errors or [])),
            }
            with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(_J.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return s

    def to_json_file(self, text_file: str, output_folder: Optional[str] = None) -> str:
        """Read text file, format to JSON, and write `resume.json` in output folder."""
        t0 = time.time()
        txt = read_text(text_file)
        s = self.to_json(txt)
        out_json = str(Path(output_folder or Path(text_file).parent) / "resume.json")
        write_text(out_json, s)
        try:
            from pathlib import Path as _P
            import json as _J
            root = _P.cwd() / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            rec = {
                "kind": "write_json",
                "src_txt": text_file,
                "out_json": out_json,
                "chars_in": len(txt or ""),
                "chars_out": len(s or ""),
                "elapsed_sec": round(time.time() - t0, 3),
            }
            with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(_J.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return out_json

    def _ensure_json(self, content: str):
        """Parse LLM output robustly: direct, fenced, greedy braces + cleaning."""
        s = (content or "").strip()
        if not s:
            return {}
        # 1) direct parse
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else (obj or {})
        except Exception:
            pass

        # helper: strip code fences
        def _strip_fences(t: str) -> str:
            t = t.strip()
            t = re.sub(r"^```\w*\n", "", t)
            t = re.sub(r"```\s*$", "", t)
            return t.strip()

        # 2) fenced block
        try:
            m = re.search(r"```json\s*\n([\s\S]*?)```", s, re.I)
            if m:
                candidate = m.group(1).strip()
                obj = json.loads(candidate)
                return obj if isinstance(obj, dict) else (obj or {})
        except Exception:
            pass

        # 3) greedy braces then clean
        def _between_braces(t: str) -> Optional[str]:
            start = t.find("{")
            end = t.rfind("}")
            if start >= 0 and end > start:
                return t[start:end+1]
            return None

        candidate = _between_braces(s) or ""
        if candidate:
            # primary attempt
            try:
                obj = json.loads(candidate)
                return obj if isinstance(obj, dict) else (obj or {})
            except Exception:
                pass
            # cleaning: remove trailing commas, bool/none normalization, single-quote to double-quote
            cleaned = candidate
            try:
                cleaned = _strip_fences(cleaned)
                cleaned = re.sub(r",\s*(?=[}\]])", "", cleaned)
                cleaned = re.sub(r"\bTrue\b", "true", cleaned)
                cleaned = re.sub(r"\bFalse\b", "false", cleaned)
                cleaned = re.sub(r"\bNone\b", "null", cleaned)
                # keys with single quotes -> double quotes
                cleaned = re.sub(r"([\{\[,]\s*)'([^']+)'\s*:", r'\1"\2":', cleaned)
                # string values with single quotes -> double quotes
                cleaned = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned)
                obj = json.loads(cleaned)
                return obj if isinstance(obj, dict) else (obj or {})
            except Exception:
                pass

        # 4) last resort: extract any JSON object-like substring via regex non-greedy
        try:
            m2 = re.search(r"\{[\s\S]*?\}", _strip_fences(s))
            if m2:
                obj = json.loads(m2.group(0))
                return obj if isinstance(obj, dict) else (obj or {})
        except Exception:
            pass

        # log parse failure
        try:
            from pathlib import Path as _P
            root = _P.cwd() / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            rec = {
                "kind": "json_parse_fail",
                "chars_in": len(s),
                "preview": s[:400],
            }
            with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return {}
