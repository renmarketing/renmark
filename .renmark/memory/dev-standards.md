<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-05-29 @ 715ef63 -->

# Dev standards — ai-system

What this project enforces about itself, detected from configuration files. Read this before making non-trivial changes so you don't break gates that are silently checking your work.

## Detected standards

| Standard | Command | Detected in | Notes |
|---|---|---|---|
| test | `pytest -q` | `pyproject.toml` | pytest in deps |
| lint | `ruff check` | `pyproject.toml` | — |
| format | `ruff format` | `pyproject.toml` | — |
| typecheck | `mypy .` | `pyproject.toml` | — |
| ci | — | `.github/workflows/` | GitHub Actions: test |
| env | — | `.env.example` | empty |

## Standards health

**1 gap detected** (1 info). Tightening recommendations below.

### ℹ Inconsistent commit message style

Of the last 20 commits, only 5 follow conventional-commits format.

**Recommendation:** Pick a convention (conventional-commits or freeform) and enforce via commitlint or PR review.
