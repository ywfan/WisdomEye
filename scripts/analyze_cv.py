import argparse
import os
import sys
from pathlib import Path

CURR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(CURR)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from modules.resume_text import ResumeTextExtractor
from modules.resume_json import ResumeJSONFormatter
from modules.resume_json.enricher import ResumeJSONEnricher
from modules.output.render import render_html, render_pdf


def process_single(input_path: str, output_root: str | None = None) -> dict:
    """Run end-to-end analysis for one resume and return artifact paths."""
    extractor = ResumeTextExtractor()
    formatter = ResumeJSONFormatter()
    enricher = ResumeJSONEnricher()

    txt_path = extractor.extract_to_text(input_path, output_folder=output_root)
    json_path = formatter.to_json_file(txt_path)
    rich_path = enricher.enrich_file(json_path)
    final_path = enricher.generate_final(rich_path)
    html_path = render_html(final_path)
    pdf_path = render_pdf(final_path)
    return {
        "text": txt_path,
        "json": json_path,
        "rich_json": rich_path,
        "final_json": final_path,
        "html": html_path,
        "pdf": pdf_path,
    }


def main():
    """CLI entry: process one or more input files sequentially."""
    parser = argparse.ArgumentParser(description="端到端分析简历：PDF/Docx/Txt → Text → JSON → 富化 → 终评 → HTML/PDF")
    parser.add_argument("inputs", nargs="+", help="输入的简历文件路径（pdf/docx/txt 等）")
    parser.add_argument("--output", help="输出根目录（默认在项目 output/<文件名> 下）", dest="output_root")
    args = parser.parse_args()

    results = []
    for p in args.inputs:
        try:
            out = process_single(p, output_root=args.output_root)
            results.append((p, out))
            print(f"[完成] 输入={p}\n  文本={out['text']}\n  JSON={out['json']}\n  富化JSON={out['rich_json']}\n  终评JSON={out['final_json']}\n  HTML={out['html']}\n  PDF={out['pdf']}")
        except Exception as e:
            print(f"[错误] 处理 {p} 失败：{e}")

    if not results:
        print("[结束] 未成功处理任何输入")
    else:
        print(f"[结束] 共处理 {len(results)} 个输入")


if __name__ == "__main__":
    main()
