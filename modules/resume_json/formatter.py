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
