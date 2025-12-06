# 慧眼 · WisdomEye

<p>
  <img src="assets/logo/wisdomeye-logo.svg" alt="WisdomEye Logo" width="180" />
</p>

将 `PDF/DOCX/TXT` 简历解析为结构化 `JSON`，自动进行网络检索富化与综合评价，并生成可分享的 `HTML/PDF` 报告。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Status](https://img.shields.io/badge/status-active-brightgreen)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 核心特性
- 文本抽取：支持 `PDF/.docx/.txt` 多格式，自动清洗与规范化
- 结构化解析：LLM+Schema 合同，确保字段形状稳定且零臆测
- 外网富化：论文、奖项、社交踪迹与学术指标的检索与拼接
- 评审生成：学术综述、维度评价、数值评分与综合报告
- 报告渲染：一键生成美观的 `HTML/PDF`，便于分享与归档
- 可控调用：内置缓存、限流、重试、预算上限与离线模式

## 架构总览
- 数据管线：`文本 → JSON → 富化 → 终评 → 报告`
- 模块职责：
  - `modules/resume_text/extractor.py` 文本抽取
  - `modules/resume_json/formatter.py` 结构化与 Schema 校验/整形
  - `modules/resume_json/enricher.py` 外部信号富化与评审聚合
  - `modules/output/render.py` 报告渲染（HTML/PDF）
  - `infra/*` 适配层（LLM/WebSearch/缓存/限流/重试/观测）

## 快速开始
- 克隆并安装：
  - `pip install -r requirements.txt`
- 配置环境：
  - 复制 `/.env.example` 到 `/.env`，填写真实密钥与服务地址
  - 关键变量：`LLM_DEFAULT_PROVIDER`、`LLM_DEFAULT_MODEL`、`DASHSCOPE_API_KEY`、`AIHUB_API_KEY`、`MOONSHOT_API_KEY`、`TAVILY_API_KEY`、`BOCHA_WEB_SEARCH_API_KEY`
- 运行单文件分析：
  - `python -m scripts.analyze_cv data/高行健简历-a4.pdf`
- 批量处理与离线模式：
  - `python -m scripts.batch_resume_pipeline --input data --offline`

## CLI 用法
- 文本与JSON：
  - `python -m scripts.convert_resume data/linting.pdf --output output/linting`
- 富化JSON：
  - `python -m scripts.enrich_resume_json output/linting/resume.json`
- 终极综合评价：
  - `python -m scripts.generate_final_assessment output/linting/resume_rich.json`
- 报告输出：
  - `python -m scripts.render_outputs output/linting/resume_final.json`

## 程序接口
示例：在 Python 中使用各阶段组件。

```python
from modules.resume_text import ResumeTextExtractor
from modules.resume_json import ResumeJSONFormatter
from modules.resume_json.enricher import ResumeJSONEnricher
from modules.output.render import render_html, render_pdf

txt = ResumeTextExtractor().extract_to_text("data/linting.pdf")
json_path = ResumeJSONFormatter().to_json_file(txt)
rich_path = ResumeJSONEnricher().enrich_file(json_path)
final_path = ResumeJSONEnricher().generate_final(rich_path)
html_path = render_html(final_path)
pdf_path = render_pdf(final_path)
```

## 配置说明
- LLM 提供商（OpenAI 兼容）：
  - `LLM_DEFAULT_PROVIDER`，`LLM_DEFAULT_MODEL`
  - 支持示例：`dashscope`、`aihub`、`moonshot`、`deepseek`
- Web 搜索：
  - `TAVILY_API_KEY`，`BOCHA_BASE_URL`，`BOCHA_WEB_SEARCH_API_KEY`
- 预算与速率：
  - `BUDGET_MAX_LLM_CALLS`，`BUDGET_MAX_SEARCH_CALLS`
  - `LLM_RATE_LIMIT`/`LLM_RATE_WINDOW`，`SEARCH_RATE_LIMIT`/`SEARCH_RATE_WINDOW`
- 功能开关：
  - `FEATURE_NEW_PIPELINE=1` 使用适配层（更强的缓存/限流/重试）
  - `FEATURE_SOCIAL_FILTER=1` 社交踪迹LLM辅助过滤

## 输出目录
- 单文件示例输出位于 `output/<文件名>/`：
  - `resume.txt` 原文清洗文本
  - `resume.json` 结构化 JSON
  - `resume_rich.json` 富化后 JSON
  - `resume_final.json` 终评聚合 JSON
  - `resume_final.html` 综合评估报告（可直接打开）
  - `resume_final.pdf` 报告 PDF
- 运行日志与观测：`output/logs/trace.jsonl`

## 测试
- 运行全部测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`

## 版本与发布
- 版本遵循 Semantic Versioning；变更参见 `CHANGELOG.md`
- 当前通过源代码分发与 `requirements.txt` 安装；后续可考虑 PyPI/Docker
- CI 状态徽章将在仓库发布后添加至此（基于 `/.github/workflows/ci.yml`）

## 支持矩阵
- Python：3.10、3.11、3.12（参见 CI 配置）


## 常见问题
- PDF 渲染失败：安装 `weasyprint` 所需的系统 Cairo/Pango/字体，或安装 `wkhtmltopdf`
- 外部 API 限流：降低并发、提高缓存 TTL、设置合理预算与速率窗口
- 第三方 PyTest 插件冲突：使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`

## 贡献
- 提交 PR 前请先运行测试并遵循现有代码风格
- 建议在 `tests/` 增加覆盖用例，避免引入未验证的回归
- 参见 `CONTRIBUTING.md` 与 `CODE_OF_CONDUCT.md`

## 路线图
- 更细粒度的证据链与可视化
- 更丰富的站点抽取器与摘要规则
- 多语言支持与国际化报告模板

## 许可与安全
- 本项目采用 MIT 许可，参见 `LICENSE`
- 请勿将真实密钥提交到版本库，使用 `/.env` 管理配置
- 安全披露流程参见 `SECURITY.md`
- 开源前检查参见 `OPEN_SOURCE_CHECKLIST.md`

## 致谢
- 感谢 OpenAI 兼容生态与 `WeasyPrint`/`wkhtmltopdf` 渲染工具
- 搜索服务感谢 `Tavily` 与 `Bocha AI Search`

## 品牌与Logo
- 主 Logo：`assets/logo/wisdomeye-logo.svg`（magnifier-doc 主题）
- 备用候选：
  - `assets/logo/wisdomeye-logo-eye-circuit.svg`
  - `assets/logo/wisdomeye-logo-owl-min.svg`
  - `assets/logo/wisdomeye-logo-monogram-we.svg`
  - `assets/logo/wisdomeye-logo-shield-eye.svg`
- 主题版本：
  - 深色背景：`assets/logo/wisdomeye-logo-magnifier-doc-dark.svg`
  - 单色版：`assets/logo/wisdomeye-logo-magnifier-doc-mono.svg`
- 小尺寸标志（头像/favicon）：`assets/logo/wisdomeye-mark.svg`
- 使用规范参见 `assets/branding.md`
