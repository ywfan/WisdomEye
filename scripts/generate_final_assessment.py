import argparse
import os
import sys

CURR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(CURR)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from modules.resume_json.enricher import ResumeJSONEnricher


def main():
    parser = argparse.ArgumentParser(description="基于简历JSON生成综合评价，输出 resume_final.json")
    parser.add_argument("json_path", help="输入的简历JSON文件路径（可为 resume.json 或 resume_rich.json）")
    args = parser.parse_args()
    enricher = ResumeJSONEnricher()
    out = enricher.generate_final(args.json_path)
    print(f"生成综合评价: {out}")


if __name__ == "__main__":
    main()
