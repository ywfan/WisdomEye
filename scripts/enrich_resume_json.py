import argparse
import os
import sys

CURR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(CURR)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from modules.resume_json.enricher import ResumeJSONEnricher


def main():
    parser = argparse.ArgumentParser(description="富化简历JSON：补全论文与奖项信息")
    parser.add_argument("json_path", help="输入的 resume.json 文件路径")
    args = parser.parse_args()
    enricher = ResumeJSONEnricher()
    out_json = enricher.enrich_file(args.json_path)
    print(f"生成 JSON: {out_json}")


if __name__ == "__main__":
    main()
