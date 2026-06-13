---
artifact_type: plan
schema_version: 1
created_at: 2026-06-12
source_sha: 8955bf1
related_spec: .renmark/specs/2026-06-12-playwright-browser-control.spec.md
generator: plan
dependency_refs:
  - .renmark/specs/2026-06-12-playwright-browser-control.spec.md
  - PRD.md  # REQ-19
---

# Plan — Playwright browser control with session memory

Decomposition of `.renmark/specs/2026-06-12-playwright-browser-control.spec.md`
(branch `feature/playwright-browser-control`, serves `REQ-19`). Adds an OPTIONAL
Playwright layer: a `renmark-browser login <profile>` bootstrap saves
`storageState` under gitignored `.renmark/state/browser-sessions/`, reused by a
deterministic Python path and an `@playwright/mcp` live channel, with auto-detect
+ `--browser/RENMARK_BROWSER` override and graceful fallback to the existing
Chrome DevTools MCP. Core runtime stays stdlib-only (guarded import).

**Locked constraints (from CHANGELOG "Do not change" + spec):** Playwright is
optional; absent → Chrome DevTools MCP fallback, no regression. Session artifacts
hold live auth — gitignored, never logged, never inline to subagents, never in
orchestrator context, excluded from release zips. storageState is the
parallelism-safe default; user-data-dir is single-process opt-up only.

---

### Task 1: pyproject optional browser extra
- **mode:** B
- **target:** pyproject.toml
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'playwright' pyproject.toml
- **serves:** REQ-19
- **spec:**
  In `[project.optional-dependencies]`, add a new extra below the existing `dev`
  block:
  ```
  browser = [
      "playwright>=1.40.0",
  ]
  ```
  Do NOT touch `dependencies` (core stays stdlib + python-dotenv only) or the
  `dev` extra. Keep the existing comment about no `[project.scripts]`. This makes
  `pip install renmark[browser]` install the Python bindings only — browser
  binaries are a separate `python -m playwright install chromium` step (do not
  add a script for that here).

### Task 2: .mcp.json — register @playwright/mcp (opt-in)
- **mode:** A
- **target:** .mcp.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** python3 -c "import json,sys; d=json.load(open('.mcp.json')); sys.exit(0 if 'playwright' in json.dumps(d) else 1)" >/dev/null 2>&1
- **serves:** REQ-19
- **spec:**
  Create a project `.mcp.json` registering the opt-in Playwright MCP server
  alongside (NOT replacing) the existing Chrome DevTools MCP. Use the standard
  Claude Code MCP schema:
  ```json
  {
    "mcpServers": {
      "playwright": {
        "command": "npx",
        "args": [
          "@playwright/mcp@latest",
          "--isolated",
          "--storage-state=.renmark/state/browser-sessions/active.json"
        ]
      }
    }
  }
  ```
  Rationale (from research): `--isolated` avoids profile-lock on parallel runs;
  `--storage-state` points at a STABLE "active session" path that the verify
  integration (Task 6) writes the selected profile into before a live QA run —
  the MCP config is static, so profile selection happens by populating
  `active.json`, not by re-launching the server. Do NOT add the chrome-devtools
  server here (it is configured globally and must stay the fallback).

### Task 3: renmark/browser.py — core channel + session module
- **mode:** A
- **target:** renmark/browser.py
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.04
- **verifier:** python3 -m py_compile renmark/browser.py && python3 -c "import renmark.browser" >/dev/null 2>&1
- **serves:** REQ-19
- **spec:**
  Core module for the optional browser layer. **The `playwright` import MUST be
  lazy/guarded** — `import renmark.browser` MUST succeed on a stdlib-only install
  with playwright NOT installed (the verifier enforces this). Provide:
  - `SESSIONS_DIR = ".renmark/state/browser-sessions"` path helpers:
    `profile_path(name) -> <dir>/<name>.json`, `meta_path(name)`,
    `active_path() -> <dir>/active.json`.
  - `is_playwright_available() -> bool`: True only when `playwright` imports AND a
    chromium browser is installed (guarded check; never raises — catch ImportError
    and the playwright "executable doesn't exist" condition, return False).
  - `resolve_channel(override: str|None) -> str`: precedence
    explicit arg `--browser` > `RENMARK_BROWSER` env > auto. `auto` →
    `"playwright"` if `is_playwright_available()` else `"chrome-devtools"`.
    Valid values: `playwright | mcp | auto` (treat `mcp` as the playwright MCP
    channel; `chrome-devtools` is the implicit fallback id). Unknown value →
    clear ValueError.
  - `save_storage_state(name, context)` / `load_context(browser, name)` helpers
    wrapping Playwright's `context.storage_state(path=...)` and
    `new_context(storage_state=...)` — import playwright INSIDE these functions.
  - Sidecar meta: write `{ "saved_at": <iso8601>, "browser": "chromium",
    "mode": "storageState"|"user-data-dir" }` next to the session; `is_stale(name,
    max_age_hours=24) -> bool` reads `saved_at`.
  - `validate_storage_state(path) -> bool`: accept only Playwright-native schema
    (`cookies` list + `origins` list); reject foreign schema with a clear error.
  - `activate(name)`: copy `profile_path(name)` → `active_path()` so the static
    MCP server (Task 2) starts authenticated. Refuse if the session is stale
    (caller decides re-login).
  - NEVER log cookie/token values; never print storageState contents. Use stdlib
    only outside the guarded playwright calls (json, os, pathlib, datetime,
    shutil). Match the repo's existing style in renmark/*.py.

### Task 4: renmark/browser_cli.py — CLI commands
- **mode:** A
- **target:** renmark/browser_cli.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile renmark/browser_cli.py && python3 -c "import renmark.browser_cli" >/dev/null 2>&1
- **serves:** REQ-19
- **spec:**
  Argparse CLI (module entrypoint: `python -m renmark.browser_cli`). Imports
  `renmark.browser` (NOT playwright at module top — keep import-safe without the
  extra). Subcommands:
  - `login <profile>`: if `not browser.is_playwright_available()`, print the exact
    remediation — `pip install renmark[browser]` then `python -m playwright
    install chromium` — and exit non-zero WITHOUT downloading anything. Otherwise
    launch a HEADED chromium, let the human authenticate, then save storageState +
    sidecar meta via `renmark.browser`. Save immediately after the human confirms
    login (short-lived SPA tokens).
  - `list`: list saved profiles with saved_at + stale flag.
  - `status <profile>`: print saved_at, mode, stale? (never print secrets).
  - `forget <profile>`: delete the session JSON + meta + any user-data-dir.
  Provide `main(argv=None)`; `if __name__ == "__main__": raise SystemExit(main())`.
  Stdlib + renmark.browser only outside the guarded login path.

### Task 5: bin/renmark-browser — bash wrapper
- **mode:** A
- **target:** bin/renmark-browser
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** bash -n bin/renmark-browser
- **serves:** REQ-19
- **spec:**
  Mirror `bin/renmark-execute` exactly (symlink resolution, INSTALL_DIR, `.venv`
  python preference, package-not-found guard), but dispatch to the browser CLI:
  the final exec line runs `"$PY" -m renmark.browser_cli "$@"` instead of the
  execute entrypoint. Keep `#!/usr/bin/env bash` + `set -euo pipefail`. Make it
  executable (chmod +x semantics — the orchestrator commits the mode).

### Task 6: verify SKILL.md — channel resolution + session reuse
- **mode:** B
- **target:** plugin/skills/verify/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1100
- **est_cost_usd:** 0.03
- **verifier:** grep -qE 'RENMARK_BROWSER|--browser' plugin/skills/verify/SKILL.md
- **serves:** REQ-19
- **spec:**
  Add a section documenting the optional Playwright session-memory channel for the
  `--qa` / `--deep-qa` browser modes. Describe: channel resolution via
  `renmark.browser.resolve_channel` (precedence `--browser` arg > `RENMARK_BROWSER`
  env > auto; auto → Playwright when available else Chrome DevTools MCP); how a
  named profile's saved session is loaded — for the live channel verify calls
  `renmark.browser.activate(<profile>)` to populate `active.json` before driving
  the `@playwright/mcp` server, so the browser starts authenticated; graceful
  fallback to Chrome DevTools MCP (today's cold-session behavior) when Playwright
  is absent, with a one-line "session memory unavailable" note and NO regression.
  Reaffirm the bounded-output contract: NO session bytes, cookies, or page content
  ever enter orchestrator context (REQ-5) — verdict stays ≤5 lines. Do not remove
  existing verify content; this is additive. Mirror any cross-doc rule note per the
  repo's sync convention if you touch a governance clause (you should not need to).

### Task 7: tests/test_browser.py — unit tests
- **mode:** A
- **target:** tests/test_browser.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 4
- **est_tokens:** 1600
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest -q tests/test_browser.py >/dev/null 2>&1
- **serves:** REQ-19
- **spec:**
  Pytest unit tests for `renmark/browser.py` that run WITHOUT playwright installed
  (mock/monkeypatch the guarded calls — never require a real browser). Cover:
  - `is_playwright_available()` returns False when import fails (monkeypatch) and
    True when both import + browser-installed checks pass.
  - `resolve_channel` precedence: explicit arg overrides env overrides auto; auto
    → "playwright" vs "chrome-devtools" by availability; unknown value raises.
  - storageState save/load roundtrip using a temp dir + a fake context object
    whose `storage_state(path=...)` writes a valid-schema JSON; assert file lands
    under the sessions dir and meta sidecar has `saved_at`.
  - `validate_storage_state`: accepts native schema, rejects foreign schema.
  - `is_stale`: fresh vs aged `saved_at`.
  - `activate` copies profile → active.json and refuses a stale profile.
  Use `tmp_path` and monkeypatch `SESSIONS_DIR`; assert NO secret values are
  written to logs/stdout. Keep fast + hermetic.

### Task 8: CLAUDE.md — entry point + optional-dep note
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'renmark-browser' CLAUDE.md
- **serves:** REQ-19
- **spec:**
  In the "Project at a glance" → "Entry points" line, add `bin/renmark-browser`
  to the list. In the same section's stack/note area, add ONE sentence: "Optional
  browser layer: `pip install renmark[browser]` (Playwright) enables
  session-memory QA; absent, verify falls back to the Chrome DevTools MCP." Do NOT
  alter any rule block or governance clause. Keep the file under 200 lines. This
  edit MUST be byte-identical in intent to the AGENTS.md edit (Task 9) per the
  CLAUDE.md↔AGENTS.md mirror convention — use the same wording.

### Task 9: AGENTS.md — mirror entry point + optional-dep note
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'renmark-browser' AGENTS.md
- **serves:** REQ-19
- **spec:**
  Mirror Task 8 in AGENTS.md: add `bin/renmark-browser` to the entry-points
  reference and the same one-sentence optional-browser-layer note, using identical
  wording to the CLAUDE.md edit (mirror convention — edits land in the same
  commit/wave). Do NOT alter rule blocks or governance clauses.

---

## Cost preview

| # | Task | executor | group | est_tokens | est_cost |
|---|---|---|---|---|---|
| 1 | pyproject optional extra | haiku | 1 | 300 | $0.00 |
| 2 | .mcp.json @playwright/mcp | haiku | 1 | 250 | $0.00 |
| 3 | renmark/browser.py | sonnet | 2 | 1800 | $0.04 |
| 4 | renmark/browser_cli.py | codex | 3 | 1200 | $0.03 |
| 5 | bin/renmark-browser | haiku | 3 | 250 | $0.00 |
| 6 | verify SKILL.md | sonnet | 4 | 1100 | $0.03 |
| 7 | tests/test_browser.py | codex | 4 | 1600 | $0.04 |
| 8 | CLAUDE.md | haiku | 4 | 250 | $0.00 |
| 9 | AGENTS.md | haiku | 4 | 250 | $0.00 |

**Executors:** haiku×5, sonnet×2, codex×2, opus×0, fable×0
**Total tokens (incl. ~10k Agent overhead per haiku/sonnet task):** ~80k
**Total cost: ~$0.14**

4 waves: [1,2] config → [3] core module → [4,5] CLI+wrapper → [6,7,8,9] verify/tests/docs.
