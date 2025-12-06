# Security Policy

## Supported Versions
- 支持分支：`main` 为安全修复的唯一目标分支；后续将根据发布版本提供支持矩阵。

## Reporting a Vulnerability
- 请勿在公开 Issue 中披露安全问题。
- 优先通过 GitHub Security Advisories（私密）报告；若不可用，请发送邮件至维护者私密渠道（请在仓库简介或主页中添加联系邮箱）。
- 报告内容应包含：影响范围、复现步骤、利用难度、潜在影响与修复建议。
- 响应与处理：在收到报告后 72 小时内确认并沟通；修复完成前采用负责任披露策略。

## Handling Secrets
- 切勿提交真实 API 密钥或凭据到仓库或 Issue。
- 使用本地 `.env` 与示例 `/.env.example`；CI/部署环境通过密钥管理系统（例如 GitHub Actions Secrets）。
- 运行日志与观测文件（`output/logs/trace.jsonl`）不应包含敏感头或密钥。
