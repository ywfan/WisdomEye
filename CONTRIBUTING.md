# Contributing to WisdomEye

## Getting Started
- Install dependencies: `pip install -r requirements.txt`
- Run tests: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`
- Ensure changes follow existing code style and module boundaries.

## Local Development
- 推荐本地使用虚拟环境：`python -m venv .venv && source .venv/bin/activate`
- 复制 `/.env.example` 为 `/.env` 并按需填充；请勿提交真实密钥。
- 示例数据位于 `data/`，发布前需脱敏或移除。

## Pull Requests
- Fork and create a topic branch from `main`.
- Keep PRs focused and reasonably small.
- Include tests for new features or bug fixes.
- Update documentation where user-facing behavior changes.

## Commit Messages
- Use clear, action-oriented subject lines.
- Explain what and why; reference issues if applicable.

## Change Types
- 建议采用 Conventional Commits（例如：`feat:`、`fix:`、`docs:`、`refactor:`、`test:`）。

## Coding Guidelines
- Prefer explicit, readable names over cleverness.
- Follow existing patterns in `infra/`, `modules/`, `utils/`.
- Avoid hardcoding secrets; read from environment variables.

## Release and Versioning
- 版本策略：遵循 Semantic Versioning。
- CI 在每个 PR 上运行测试；维护者进行合并、打 Tag 与发布。
- 变更记录：参见 `CHANGELOG.md`。

## Communication
- Use GitHub Issues for bugs and feature requests.
- Be respectful; see `CODE_OF_CONDUCT.md`.
