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


def main():
    parser = argparse.ArgumentParser(description="将简历文件转换为文本与Markdown")
    parser.add_argument("inputs", nargs="+", help="输入的简历文件路径（pdf/docx/txt等）")
    parser.add_argument("--output", help="输出根目录，可选，默认项目下的 output")
    args = parser.parse_args()

    extractor = ResumeTextExtractor()
    formatter = ResumeJSONFormatter()

    for p in args.inputs:
        txt_path = extractor.extract_to_text(p, output_folder=args.output)
        json_path = formatter.to_json_file(txt_path)
        print(f"[完成] 文本={txt_path} JSON={json_path}")


if __name__ == "__main__":
    main()
