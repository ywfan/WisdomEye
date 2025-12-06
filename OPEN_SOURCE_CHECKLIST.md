# Open-Source Checklist

This repository is prepared for public release. The following items may contain sensitive data or environment-specific configuration and are not suitable to publish as-is.

## Do Not Publish (keep local)
- `.env` and any `.env.*` files — real credentials and endpoints
- `data/` — may contain personal resumes or proprietary documents
- `output/` — generated artifacts, logs and reports with personal data
- `.vercel/` — deployment project metadata (IDs, environments)

## Review Before Publish
- `vercel.json` — optional for local hosting; confirm it does not leak internal routes
- `arch.md`, `arch2.md`, `plan.md` — internal notes; publish only if intended

## Already Configured
- `.gitignore` excludes `output/`, `.env*`, `.vercel/`, `data/`
- `.env.example` provides placeholders only

## Recommended Release Steps
- Run tests: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`
- Sanitize sample inputs under `data/` or remove the folder before first push
- Verify no secrets in commit history (e.g., `git log -p | grep -i "api_key"`)
