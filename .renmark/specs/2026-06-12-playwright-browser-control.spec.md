---
artifact_type: spec
schema_version: 1
created_at: 2026-06-12
source_sha: 8955bf1
related_plan: null
generator: brainstorm
stale_after: null
dependency_refs:
  - PRD.md  # REQ-19
  - .renmark/research/2026-06-12-playwright-browser-control-best-practices.research.md
  - .renmark/research/2026-06-12-playwright-browser-control-mcp-prior-art.research.md
  - .renmark/research/2026-06-12-playwright-browser-control-reference-repos.research.md
---

# Spec — Playwright browser control with session memory

> Feature branch: `feature/playwright-browser-control`. Serves `REQ-19`.

## Context

renmark's only live-browser capability today is `/renmark:verify --qa` / `--deep-qa`,
which drives Chrome through the **Chrome DevTools MCP**. There is no way to
*persist an authenticated session* — every QA pass starts cold, so any flow
behind a login can't be verified without re-authenticating by hand each time.

This feature adds an **OPTIONAL Playwright layer with session memory**: a
one-time `renmark-browser login <profile>` bootstrap captures browser session
state, which is then reused — across verify runs — by both a deterministic
Python scripted path and a live LLM-driven QA path, so authenticated/stateful
flows resume without re-login. The core Python runtime stays stdlib-only;
Playwright is an opt-in dependency that degrades gracefully when absent (PRD
`REQ-19`).

## Goals

- A user authenticates **once** (`renmark-browser login <profile>`); subsequent
  verify runs reuse that session without re-login.
- Session state persists across runs, `/clear`, and new sessions, inside
  `.renmark/` (REQ-6), and is **never** read into orchestrator context (REQ-5).
- Two reuse channels share one saved session: deterministic **Python scripted
  flows** and **live LLM-driven QA** via an `@playwright/mcp` server.
- The layer is **auto-detected and optional**: present + browser installed →
  Playwright; otherwise fall back to the existing Chrome DevTools MCP channel
  (today's cold-session behavior). An explicit override forces a channel.
- The core runtime remains **stdlib-only**; nothing breaks for users who never
  install Playwright.

## Non-goals (feature-scoped)

- **Not replacing** the Chrome DevTools MCP channel — this is additive; Chrome
  DevTools MCP keeps its exclusive perf-trace / Lighthouse roles and is the
  absent-Playwright fallback.
- **Not** auto-injecting a saved session into the Chrome DevTools MCP / CDP
  channel — research confirmed CDP-attach can't natively load `storageState`
  (playwright-mcp #983); best-effort cookie injection is out of scope.
- **Not** managing or storing user **credentials** — only the post-login
  session artifact (cookies / localStorage); the human performs the actual login
  interactively during bootstrap. (Product non-goal "managing user secrets"
  stays in PRD; this references it, doesn't duplicate it.)
- **Not** auto-installing browser binaries silently — the bootstrap detects and
  *guides* `python -m playwright install chromium`; it does not run heavy
  downloads without consent.
- **Not** a credential vault, multi-tenant session store, or remote/CI session
  cache (reference repos like `browserstate` do cloud backends — explicitly out
  of MVP).

## Architecture

Three legs over one shared session artifact; channel chosen by capability
detection with an override.

```
renmark-browser login <profile>          (Python Playwright, headed)
  └ save storageState JSON  → .renmark/state/browser-sessions/<profile>.json   (gitignored)
       (+ opt-up user-data-dir → .renmark/state/browser-sessions/<profile>/  , single-process only)
       └ sidecar meta: { saved_at, browser, mode: storageState|user-data-dir }

reuse leg 1 — Python scripted flows (deterministic verify path)
  └ browser.new_context(storage_state=<profile>.json)  → run flow → bounded JSON verdict

reuse leg 2 — live LLM-driven QA
  └ @playwright/mcp  --isolated --storage-state=<profile>.json   → starts authenticated
       (LLM may re-save mid-session via the browser_storage_state tool)

fallback — Playwright unavailable
  └ Chrome DevTools MCP  (today's behavior; no session memory)

channel selection
  └ auto: (playwright importable) AND (chromium installed) → playwright ; else mcp(chrome-devtools)
     override: --browser=playwright|mcp|auto  /  RENMARK_BROWSER=playwright|mcp|auto
```

## Components

1. **`renmark/browser.py`** (optional-import module) — capability detection
   (`is_playwright_available()`: import guard + chromium-installed check), a
   `BrowserChannel` abstraction (`PlaywrightChannel`, `ChromeDevToolsMCPChannel`),
   storageState save/load helpers, profile-path + sidecar-meta + staleness logic.
   Import of `playwright` is lazy/guarded so the module never breaks a
   stdlib-only install.
2. **`renmark-browser` CLI entrypoint** (`bin/` + `__main__` subcommand) —
   `login <profile>` (headed bootstrap → save storageState), `list`, `status
   <profile>` (saved_at / stale?), `forget <profile>`. Guides
   `python -m playwright install chromium` when binaries are missing.
3. **`@playwright/mcp` MCP server registration** — added to the project MCP
   config alongside the existing Chrome DevTools MCP, launched with
   `--isolated --storage-state=<resolved profile path>`. Additive; Chrome
   DevTools MCP entry untouched.
4. **`pyproject.toml`** — `[project.optional-dependencies] browser =
   ["playwright>=1.40.0"]`; `pip install renmark[browser]` installs bindings
   only (binaries via the separate install step).
5. **`/renmark:verify` integration** — verify resolves the channel (auto +
   override), loads the named profile's session when present, and routes the QA
   flow through the chosen channel. Bounded ≤5-line verdict only — no session
   bytes, cookies, or page content enter orchestrator context.
6. **`.gitignore` / release-zip exclusion** — confirm
   `.renmark/state/browser-sessions/` is gitignored (it is, via
   `.renmark/state/`) and excluded from release distribution zips.

## Data flow & storage

- Session artifact: `.renmark/state/browser-sessions/<profile>.json`
  (Playwright-native `storageState` schema: `cookies` + `origins[].localStorage`).
  Optional full profile dir at `.renmark/state/browser-sessions/<profile>/`.
- Sidecar `<profile>.meta.json`: `{ saved_at, browser, mode }` for staleness.
- All under gitignored `.renmark/state/`; never logged, never passed inline to a
  subagent, never read into orchestrator context, excluded from release zips.

## Error handling & guardrails (research-derived)

- **Optional dep absent** → `is_playwright_available()` false → fall back to
  Chrome DevTools MCP; surface a one-line "session memory unavailable (Playwright
  not installed)" note. Never raise.
- **Binaries missing** (bindings present, no chromium) → bootstrap detects and
  prints the exact `python -m playwright install chromium` command; does not
  auto-download.
- **Stale session** → if `now - saved_at > threshold` (configurable; default
  conservative), warn and prompt re-login rather than running against dead auth.
  Save storageState **immediately before** a flow for short-lived SPA tokens.
- **Parallelism** → `storageState` is the default (parallelism-safe);
  `user-data-dir` is opt-up + single-process (Chromium `SingletonLock`); MCP
  channel always `--isolated`.
- **Headed→headless** → never share a raw `user-data-dir` across the
  headed/headless boundary (Playwright #35466); hand off via
  `storage_state() → json → new_context(storage_state=…)`.
- **Schema mismatch** → only Playwright-generated storageState is loaded; reject
  foreign-schema files with a clear error.

## Success criteria

- `renmark-browser login <profile>` opens a headed browser, lets the human
  authenticate, and writes a valid `storageState` JSON + sidecar meta under
  `.renmark/state/browser-sessions/`.
- A second, later run (new process) reuses that session — a Python scripted flow
  AND the `@playwright/mcp` live channel both start **authenticated**, no
  re-login.
- With Playwright **not** installed, `/renmark:verify --qa` behaves exactly as
  today (Chrome DevTools MCP, cold session) — no error, no regression.
- `--browser=playwright|mcp|auto` / `RENMARK_BROWSER` selects the channel; `auto`
  picks Playwright only when importable + chromium installed.
- No session bytes, cookies, or page content ever appear in orchestrator context
  or a release zip; `.renmark/state/browser-sessions/` is gitignored.
- `pip install renmark[browser]` installs cleanly; a stdlib-only
  `pip install renmark` still imports and runs every non-browser path.

## Scope contract

- **Stack:** Python ≥3.10 (renmark runtime) + optional `playwright>=1.40.0`
  extra; Node `@playwright/mcp` MCP server (opt-in); existing Chrome DevTools MCP
  retained as fallback.
- **Deployment:** Claude Code plugin — no server/host; session artifacts live
  on-disk under gitignored `.renmark/state/`.
- **MVP boundary:** full hybrid — bootstrap + Python scripted reuse +
  `@playwright/mcp` live-QA reuse + auto-detect/override + storageState-default
  (user-data-dir opt-up) + verify integration + graceful fallback.
- **Out of scope (MVP):** cookie injection into the CDP/Chrome DevTools MCP
  channel; remote/CI/cloud session caches; credential storage; silent binary
  auto-install.

## Prior art & references

- `.renmark/research/2026-06-12-playwright-browser-control-best-practices.research.md`
  — storageState vs user-data-dir; optional-dep packaging; secret-safety.
- `.renmark/research/2026-06-12-playwright-browser-control-mcp-prior-art.research.md`
  — `@playwright/mcp` `--storage-state` / `--isolated` / `browser_storage_state`;
  footprint vs Chrome DevTools MCP.
- `.renmark/research/2026-06-12-playwright-browser-control-reference-repos.research.md`
  — `browserstate-org/browserstate` mount/unmount + profile-keying;
  channel-abstraction pattern; auth-reuse pitfalls (TTL, headed→headless,
  profile lock).
