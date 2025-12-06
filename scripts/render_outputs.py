import argparse
import os
import sys

CURR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(CURR)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from modules.output.render import render_html, render_pdf


def main():
    parser = argparse.ArgumentParser(description="从 resume_final.json 生成 HTML 与 PDF 输出")
    parser.add_argument("final_json", help="resume_final.json 文件路径")
    args = parser.parse_args()
    html_path = render_html(args.final_json)
    pdf_path = render_pdf(args.final_json)
    print(f"生成 HTML: {html_path}")
    print(f"生成 PDF: {pdf_path}")


if __name__ == "__main__":
    main()
