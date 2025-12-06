import os
from pathlib import Path
import time
from typing import Optional

from tools.fs import create_resume_folder, write_text


def _pdf_to_text(path: str) -> str:
    """Extract text from PDF using PyMuPDF, falling back to PyPDF2/pdfminer."""
    # Preferred: PyMuPDF (pymupdf)
    try:
        import fitz  # type: ignore
        txt_parts = []
        with fitz.open(path) as doc:
            for i in range(doc.page_count):
                try:
                    page = doc.load_page(i)
                    txt_parts.append(page.get_text("text") or "")
                except Exception:
                    pass
        return "\n".join(txt_parts).strip()
    except Exception:
        pass
    # Fallback: PyPDF2
    try:
        import PyPDF2  # type: ignore
        txt_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    txt_parts.append(page.extract_text() or "")
                except Exception:
                    pass
        return "\n".join(txt_parts).strip()
    except Exception:
        pass
    # Fallback: pdfminer.six
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        return (extract_text(path) or "").strip()
    except Exception:
        pass
    return ""


def _docx_to_text(path: str) -> str:
    """Extract plain text paragraphs from a .docx file."""
    try:
        import docx  # type: ignore
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs).strip()
    except Exception:
        return ""


def _bytes_to_text(path: str) -> str:
    """Read bytes and decode as UTF-8 (ignore errors)."""
    try:
        b = Path(path).read_bytes()
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


class ResumeTextExtractor:
    def extract_to_text(self, input_path: str, output_folder: Optional[str] = None) -> str:
        """Convert resume file to sanitized plain text and write to output folder."""
        t0 = time.time()
        input_path = str(input_path)
        ext = Path(input_path).suffix.lower().strip()
        folder = output_folder or create_resume_folder(input_path)
        out_txt = str(Path(folder) / "resume.txt")
        print(f"[简历抽取] input={input_path} ext={ext} out={out_txt}")
        text = ""
        if ext == ".pdf":
            text = _pdf_to_text(input_path)
        elif ext in {".docx"}:
            text = _docx_to_text(input_path)
        elif ext in {".txt", ""}:
            try:
                text = Path(input_path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = _bytes_to_text(input_path)
        else:
            text = _bytes_to_text(input_path)
        text = _sanitize_text(text.strip())
        if not text:
            print("[简历抽取] 警告：未能解析文本，输出空内容")
        write_text(out_txt, text)
        print(f"[简历抽取输出] {text[:400]}")
        try:
            # trace file logging
            from pathlib import Path as _P
            import json as _J
            root = _P.cwd() / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            rec = {
                "kind": "extract_text",
                "input": input_path,
                "ext": ext,
                "out_txt": out_txt,
                "chars": len(text or ""),
                "elapsed_sec": round(time.time() - t0, 3),
            }
            with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(_J.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return out_txt


def _sanitize_text(text: str) -> str:
    """Clean common artifacts and normalize whitespace/bullets/newlines."""
    try:
        import re
        # remove (cid:NNN) artifacts
        text = re.sub(r"\(cid:\d+\)", "", text)
        # collapse excessive spaces
        text = re.sub(r"[\t\x0b\x0c]+", " ", text)
        # normalize bullets
        text = text.replace("•", "-").replace("⋄", "-")
        # collapse multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text
    except Exception:
        return text
