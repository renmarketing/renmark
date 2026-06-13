# Tech stack

What this project depends on and how it runs. Updated by `/renmark:brainstorm` initially, then by `/renmark:orchestrate` when tasks add new dependencies.

## Languages

- Python ≥3.10 (pyproject.toml)
- Markdown (Claude Code plugin: commands + skills)

## Frameworks / libraries

| Library | Version | Purpose |
|---|---|---|
| python-dotenv | ≥1.0 | Runtime — `.env` file loading for optional local config; `requests` was removed in 0.9.0 (stdlib `urllib` used instead) |
| playwright | ≥1.40.0 | **OPTIONAL** browser-control extra (`pip install renmark[browser]`) — session-memory QA layer; core runtime stays stdlib-only and degrades to the Chrome DevTools MCP channel when absent. Browser binaries via separate `python -m playwright install chromium`. First optional runtime dep (per amended PRD non-goal). |

## MCP servers (opt-in)

| Server | Purpose | Notes |
|---|---|---|
| chrome-devtools | live-browser QA (`/renmark:verify --qa`), perf trace, Lighthouse | pre-existing; the absent-Playwright fallback channel (no session memory) |
| @playwright/mcp | live LLM-driven QA that starts authenticated from a saved session | **opt-in (Node)**; launched `--isolated --storage-state=<profile>`; additive, does not replace chrome-devtools |

## Development dependencies

| Tool | Purpose |
|---|---|
| pytest | unit testing (`pytest -q`) |
| ruff | lint (`ruff check`) |
| mypy | type checking (`mypy .`) |

## Runtime environment

- OS / platform: WSL2 Ubuntu on Windows 11; plugin installed on both WSL + Windows
- Required services: none (Codex CLI optional as a bulk-emit executor)
- Environment variables: none required

## Frontend

**none** — renmark is a CLI/plugin (code-only). Recorded explicitly because
`/renmark:blueprint`'s UI gate reads this field: Frontend = none → schematic
only, no prototype, for renmark itself.

## External APIs

| Service | What for | Auth |
|---|---|---|
| (none) | — | — |

## Notes

- Stack confirmed during the `blueprint` (prototype/schematic step) brainstorm,
  2026-06-05. The feature adds **no new runtime dependencies** — pure Python +
  markdown, consistent with the existing plugin.
- 2026-06-08 (`next-step-engine` brainstorm): no stack change. Adds **no new
  runtime deps** — `lifecycle.next_steps()` is stdlib; optional Tier-2 web
  research uses Claude Code's own web tools, not a Python dependency.
- 2026-06-08 (`init-pipeline` brainstorm): no stack change. **No new deps** —
  reuses `bootstrap.py`, `memory.template_dir()`, and lint's BEGIN/END marker
  logic; new `merge_rule_blocks()` is stdlib; `init.py` stays zero-LLM.
- 2026-06-08 (`proportional-pipeline` brainstorm): no stack change. **No new deps**
  — new `renmark/sizing.py` is a deterministic stdlib classifier reusing
  `parser.Task` signals + `git diff` stat; cheap-review lane uses the existing
  built-in `/review`, not a new dependency.
- 2026-06-08 (`modularity-health-lens` brainstorm): no stack change. **No new deps**
  — new `renmark/modularity.py` uses stdlib `ast` only (no radon/pylint); feeds
  init's existing standards-health pipeline; advisory, zero-LLM, never raises.
- 2026-06-09 (`loop-mode` brainstorm): no stack change. **No new deps** — new
  `renmark/loop.py` driver + `usage_by_run_id` helper are stdlib; reuses
  `state.py` (usage.jsonl), verify/orchestrate/resume skills, plan cost model.
  Loop runtime state in `.renmark/loops/<id>/loop.json` (not lifecycle.json).
- 2026-06-12 (`playwright-browser-control` brainstorm): **first optional runtime
  dep + first opt-in MCP server.** Adds `playwright>=1.40.0` as an OPTIONAL extra
  and `@playwright/mcp` as an opt-in Node MCP server (alongside chrome-devtools).
  Core runtime stays stdlib-only; both degrade gracefully when absent (PRD
  REQ-19, amended non-goal). New `renmark/browser.py` (lazy/guarded import) +
  `renmark-browser` CLI. Session state in `.renmark/state/browser-sessions/`
  (gitignored, secret-bearing).
