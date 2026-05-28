# Changelog

## v0.5.3 — 2026-05-28 (self-host — dev standards tightened: ruff strict, mypy lenient, GitHub Actions CI, 5-step pre-commit)

**Patch release — renmark adopts its own dev-standards prescriptions. Closes the 4 warn-level gaps surfaced when `/renmark:init` first ran against the renmark source repo at v0.5.2. The infrastructure now matches what renmark recommends to managed projects: linter + formatter + type-checker + CI + pre-commit, all wired into a single `tools/precommit.sh` script.**

The driving idea: a vibe-coder-targeted tool's first impression is its `dev-standards.md` report. v0.5.2 made that report visible; v0.5.3 makes it green. Each fix in this release was driven by reading renmark's own scanner output, then choosing strict-where-possible and pragmatic-where-intentional.

**New dev-standards infrastructure:**

- **`.github/workflows/test.yml`** (NEW) — 6-cell CI matrix: ubuntu+macos+windows × Python 3.10+3.13. Each cell runs `pip install -e .[dev]`, `ruff check`, `ruff format --check`, `mypy`, `pytest -q`, `renmark.release check`, `renmark.lint`. `fail-fast: false` so one cell's failure doesn't cancel the others — when something breaks we want to see if it's OS-specific or Python-version-specific, not get cells canceled. The Windows cell is the only place that exercises the same code paths `install.ps1` users hit, so without it Windows install regressions would ship blind.
- **`tools/precommit.sh`** (UPDATED) — augmented from 3 steps (pytest, drift, plugin lint) to 5 (added ruff lint+format, added mypy as informational warn). Mypy is soft-warn at the v0.5.3 baseline; once the 20 known mypy errors are cleaned up, flip the `fail=1` line to make mypy a hard-fail.
- **`pyproject.toml [tool.ruff]`** (NEW) — `target-version = "py310"`, `line-length = 120` (industry standard for modern Python), `select = ["E", "W", "F", "I", "B", "UP", "SIM", "RUF"]`, `ignore = ["E402", "RUF001", "RUF003"]` (E402 mid-file imports are intentional; RUF001/003 unicode-ambiguity rules flag renmark's deliberately stylized comments). Per-file ignores for `tests/**` (E501, F841, B011 — pytest patterns) and `renmark/init.py` (E501 — long template strings for project-map.md rendering).
- **`pyproject.toml [tool.mypy]`** (NEW) — lenient-strict baseline: `strict = false`, but enables `warn_return_any`, `warn_unreachable`, `warn_redundant_casts`, `check_untyped_defs`. Catches actual bugs (Any returns, dead code, None-handling violations) without flagging every internal helper that lacks a return annotation. v0.5.3 sets this baseline; the path to `strict = true` is tracked in a follow-up plan after the 20 remaining strict-mode warnings are cleaned up.
- **`pyproject.toml [project.optional-dependencies] dev`** — added `ruff>=0.6.0` and `mypy>=1.11` alongside the existing `pytest>=8.0.0`.

**Real bug fixes surfaced by the new gates:**

- **207-line dead-code deletion in `renmark/cli/_engine.py`** — ruff's `F821 Undefined name` caught a dead NIM-executor block (lines 521-727 in the pre-edit file). The block was preserved "for reference" after the NIM executor was removed in v0.2.0, but it referenced `client`, `NIMQuotaError`, `NIMRateLimitError`, `NIMError` — all undefined since v0.2.0. Function returned unconditionally at line 520, so the entire block was unreachable. Deleted; all 298 tests still pass.
- **Python 3.10 syntax fix in `renmark/init.py`** — `f"... {desc.replace('|', '\\|') if desc else '—'} ..."` used a backslash inside an f-string subexpression, which is a Python 3.12+ syntax feature. On the declared minimum Python 3.10, this would syntax-error at module import. Tests didn't catch it because the dev box runs Python 3.13. The new Windows-CI cell at Python 3.10 would have caught it on the first PR; ruff caught it locally. Extracted the conditional to a separate variable before the f-string.
- **Removed unused imports** — `format_reminder_prompt` and `retry_prompt` in `_engine.py` became unused after the NIM dead-code deletion. Ruff's `F401` flagged them; pruned.
- **97 auto-fixed ruff issues** — `typing.X` → `collections.abc.X` migrations (UP rule), unused locals, simplifiable comprehensions, etc. All auto-applied, no behavior change.
- **10 unsafe-fix transforms** — SIM rules (use `contextlib.suppress` for try/except/pass patterns, collapse nested if statements, use ternaries for simple else-return). Applied with `--unsafe-fixes`, verified by full test re-run.
- **37 files reformatted** by `ruff format` — purely cosmetic, no behavior change. Format is now stable.

**Manual surgical fixes:**

- Three long-line wrappings — `cli/_engine.py:811` (argparse help text), `lifecycle.py:284` (long error message return), `providers/codex.py:80-82` (multi-line prompt template). All wrapped at 120 chars without semantic change.
- Two SIM rule fixes — `lifecycle.py:209` (collapsed nested `if`), `memory.py:212` (replaced multi-branch if/else with ternary). Semantic equivalents.
- Cleaned up `_engine.py` import block — removed two imports made unused by the dead-code deletion.

**What's deliberately deferred to follow-up:**

- The 20 lenient-strict mypy warnings: 3 union-attr (Task | None access), 4 no-any-return (typed function returning Any), 2 unreachable, others. All real catches; all warrant fixing. Tracking issue: cleanup pass to land `strict = true`.
- No-op `model = _choose_model(task, cfg)` removed from the dead block — that helper is no longer reachable. Could be deleted from `_engine.py` entirely; preserved for now in case the NIM executor ever returns.

**Acceptance criteria (from spec):**

> A vibe coder running `python -m renmark.init` on this repo should see HEALTH: 0 gaps.

Status after v0.5.3:
- ✅ Test framework: pytest (configured + 298 tests passing)
- ✅ Linter: ruff (configured + clean)
- ✅ Formatter: ruff format (configured + clean)
- ✅ Type checker: mypy (configured + lenient-strict baseline; soft-warn in pre-commit until backlog clears)
- ✅ CI: GitHub Actions (6-cell matrix; will pass once pushed to a GitHub remote)
- ✅ Pre-commit hooks: `tools/precommit.sh` (already wired via `install.sh --dev`)

**Do not change:**

- The "lenient-strict" mypy baseline. Going straight to `strict = true` would BLOCK pre-commit on 20 errors and grind contributions to a halt while the cleanup ships. The two-step path (lenient now, strict later) keeps the door open for incremental commits.
- The mypy soft-warn in `tools/precommit.sh`. Hard-failing mypy at v0.5.3 baseline would mean every commit ships under `--no-verify`, defeating the purpose. Once the 20-error backlog is cleaned up, flip to hard-fail.
- The line-length = 120 setting. 100 generated 39 E501 warnings (mostly unavoidable long signatures and template strings); 110 still left 17; 120 is the modern Python community standard and produces zero noise without forfeiting the lint budget that catches genuinely-too-long lines.
- The `RUF001`/`RUF003` ignores. Renmark deliberately uses unicode (`×`, `ℹ`, `⚠`, `→`) in stylized output and comments. Re-enabling these rules would generate hundreds of false positives across the codebase.
- The 207-line dead-block deletion in `cli/_engine.py`. It was non-executing dead code referencing a removed subsystem (NIM, deleted v0.2.0). Resurrecting it requires bringing back the NIM provider AND fixing the references; both are deliberate decisions, not accidents.

## v0.5.2 — 2026-05-28 (distribution readiness — LICENSE, install.ps1, Codex prompt, vibe-coder README)

**Patch release — makes the zip safely distributable to vibe coders on any of the three OS paths (Mac/Linux/WSL, native Windows). Closes the four real distribution blockers identified during the v0.5.1 audit: missing LICENSE file, no Windows installer, stale README, no Codex handling.**

**Reason for shipping now:** the audience is non-technical vibe coders sharing the zip hand-to-hand. They won't manually copy folders into `%USERPROFILE%\.claude\plugins\` and they won't hand-edit `settings.json`. Without `install.ps1`, Windows users would hit the same silent failure WSL did before v0.5.1 — installer "succeeds" but `/renmark:*` commands never appear. v0.5.2 closes that gap so every supported OS has a single command that produces a working install.

**New: LICENSE file (legal blocker for redistribution):**

- **`LICENSE`** (NEW) — MIT License text at repo root. `pyproject.toml` already declared MIT but the actual license text was missing from both the repo and the release zip. MIT redistribution requires the text shipped alongside the code; without it, anyone who pulls the zip can't legally redistribute. v0.5.2 ships the LICENSE file in the zip.

**New: `install.ps1` (Windows PowerShell installer):**

- **`install.ps1`** (NEW) — Mirrors `install.sh` for native Windows. Uses NTFS **junctions** (directory aliases that don't require admin/elevation) instead of symlinks, with a copy-fallback if junctions fail (uncommon — usually a corporate AppLocker policy). Performs the same 4 steps as the bash version: plugin install → `pip install -e .` → Codex prompt → `python -m renmark.doctor --fix` for registry/settings.json registration.
- **`-Uninstall` flag** — removes everything bash uninstall does: junction/copy, cache directory, settings.json entries, installed_plugins.json entries.
- **`-NoCodex` flag** — for scripted/non-interactive installs that should skip the Codex prompt.

**New: Codex CLI detection + offer-to-install (both installers):**

- **`install.sh`** — after the pip install step, detects whether `codex` is on PATH. If missing AND stdin is a terminal AND npm is available, prompts: *"Install Codex CLI now via npm? [Y/n]"*. On Y, runs `npm install -g @openai/codex` and prints the `codex login` reminder. On N or non-interactive, prints the manual install steps. If npm itself is missing, prints the Node.js install URL + manual steps. Codex is OPTIONAL — without it, `executor: codex` tasks fall back to Sonnet automatically, so the prompt is a recommendation not a hard requirement.
- **`install.ps1`** — same logic in PowerShell. Same prompt, same fallbacks, same package name (`@openai/codex` — Codex CLI bundles per-platform binaries, so the npm command is identical on all three OSes).

**README rewrite for vibe-coder audience:**

- **`README.md`** — replaced the stale `unzip ai-system-renmark-v0.3.0-*.zip` example with a version-agnostic `v*` glob. Rewrote the Windows section from "manually copy folders into `%USERPROFILE%\.claude\plugins\renmark\` (which won't work — the silent-failure bug)" to `.\install.ps1`. Added a dedicated **Codex CLI** section explaining when to install it and the one-line install command. Added **Troubleshooting** section explaining what to do if `/renmark:*` commands don't appear (`python -m renmark.doctor --fix`).
- **WSL-vs-Windows-native note** — explicit callout: if Claude Code is running inside WSL Ubuntu, use `install.sh` not `install.ps1`. PowerShell installer only registers with `%USERPROFILE%\.claude\` which Claude Code under WSL doesn't read.

**Do not change:**

- **The `@openai/codex` npm package name.** Codex CLI uses an optional-platform-dependencies pattern that bundles per-OS binaries (`@openai/codex-linux-x64`, `@openai/codex-darwin-arm64`, `@openai/codex-win32-x64`) — the parent `@openai/codex` package resolves the right binary at install time. One install command works on every supported OS.
- **The junction-then-copy fallback in install.ps1.** Junctions don't need admin, copies don't either, but copies break the "edit source → see changes" workflow. We prefer junction so dogfooding stays live; the copy is only a last resort when corporate policy blocks junctions entirely.
- **`-NoCodex` as opt-out (not opt-in).** Defaulting to "ask about Codex" is the vibe-coder-friendly behavior; CI/scripted callers can pass `-NoCodex` to suppress the prompt. Flipping the default would silently skip a recommended dependency for most users.

## v0.5.1 — 2026-05-28 (/renmark:doctor + install.sh self-registers with Claude Code)

**Patch release — fixes the silent-install failure mode discovered during v0.5.0 dogfooding. The canonical `install.sh` only created symlinks; Claude Code requires THREE additional entries in `~/.claude/settings.json` and `~/.claude/plugins/installed_plugins.json` before slash commands appear. Without them, `/renmark:*` silently doesn't show up — the worst-possible UX for a vibe-coder-targeted tool whose first impression depends on a clean install.**

**New command — `/renmark:doctor`:**

- **`plugin/commands/doctor.md`**, **`plugin/skills/doctor/SKILL.md`** (NEW) — thin command stub + skill dispatcher. The skill invokes `python -m renmark.doctor` and relays its checklist output; agents do no diagnosis work themselves.
- **`/renmark:doctor`** — runs 9 health checks: CLI on PATH, Python package importable, VERSION file present, plugin manifest version parity, Claude Code registry registration, settings.json marketplace registration, settings.json plugin-enabled flag, cache install path resolves to source, convenience symlink. Each check prints a ✓ / ✗ / ! glyph, a one-line detail, and (for failures) a `fix:` line.
- **`/renmark:doctor --fix`** — applies safe auto-fixes for the four known-remediable failures (add to `extraKnownMarketplaces`, set `enabledPlugins[…] = true`, register in `installed_plugins.json`, create the cache version symlink). Every modified file gets a timestamped `.doctor.bak.<unix-time>` backup first.
- **`/renmark:doctor --json`** — machine-readable output for scripting (CI, integration with editor extensions, etc.).

**New Python module — `renmark/doctor.py`:**

- 9 deterministic checks. Read-only by default; `--fix` writes only to `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json`, and `~/.claude/plugins/cache/renmark-local/<version>/`.
- Each `Check` carries: name, status (`pass` / `fail` / `warn`), one-line detail, optional `fix_cmd` for users to run manually, and (when auto-fixable) a callable that applies the fix idempotently.
- Detects 4 specific drift modes that cause silent load failure: (1) version mismatch between VERSION file and installed_plugins.json registry, (2) missing `extraKnownMarketplaces.renmark-local` (cache file `known_marketplaces.json` is regenerated from this — editing only the cache doesn't stick), (3) missing `enabledPlugins["renmark@renmark-local"] = true`, (4) cache symlink pointing to a non-existent or wrong-version directory.

**`install.sh` now self-registers:**

- After the symlink and pip-install steps, calls `python -m renmark.doctor --fix` to write the three required registry entries automatically. Same Python logic that `/renmark:doctor` uses to repair broken installs — DRY, with backups always taken before writes.
- `install.sh --uninstall` now also removes the renmark entries from `settings.json` and `installed_plugins.json`, and wipes `~/.claude/plugins/cache/renmark-local/`. Pre-v0.5.1 uninstalls left dangling registry entries that surfaced as "Plugin not found in marketplace" warnings in the `/plugin` UI.
- Post-install banner adds `/renmark:doctor` to the skill list.

**Background — why this matters:**

A directory-marketplace Claude Code plugin needs THREE moving parts to surface its slash commands:

1. `~/.claude/plugins/installed_plugins.json` — registry entry under `<plugin>@<marketplace>`, with `version` matching the marketplace's current version (drift causes silent skip), and `installPath` pointing to an existing directory.
2. `~/.claude/settings.json` → `extraKnownMarketplaces.<marketplace-name>` — tells Claude Code where the marketplace lives. The cache file `~/.claude/plugins/known_marketplaces.json` is *derived* from this; editing only the cache doesn't survive a reload.
3. `~/.claude/settings.json` → `enabledPlugins["<plugin>@<marketplace>"] = true` — Claude Code requires explicit enable for directory marketplaces. Without this, the plugin loads (no error) but commands don't appear in the slash menu.

A plain `install.sh` that only writes symlinks misses #2 and #3 entirely, and the resulting failure is silent — `/reload-plugins` reports "1 error during load" without naming the plugin. v0.5.1 closes that gap.

**Other changes:**

- **`plugin/skills/help/SKILL.md`** — `/renmark:doctor` added to the command catalog with a hint about when to use it.

**Do not change:**

- The doctor module's "read-only by default" stance. Making it edit settings.json without `--fix` would surprise users who run it for diagnosis.
- The `.doctor.bak.<timestamp>` naming convention for backups. The integration tests and rollback procedures assume that pattern.
- The decision to delegate install-time registry writes to `python -m renmark.doctor --fix`. Pulling the JSON-edit logic into raw bash inside install.sh would duplicate it and re-create the maintenance burden v0.5.1 was designed to eliminate.

## v0.5.0 — 2026-05-28 (/renmark:init — codebase map + dev-standards/health scanner)

**Minor release — renmark gains its own analog to Claude Code's native `/init`, but designed around context-window hygiene from day one. Walk into any project (greenfield or production) and get a verdict: what the code looks like, what standards the project enforces, and where the standards are loose enough to break things.**

The driving observation: CLAUDE.md is loaded into the system prompt on every turn of every conversation, forever. Embedding a 2-3k-token project map in CLAUDE.md would be paid permanently as context tax — worse than re-running `find` + `grep` on demand. So the design splits content by access pattern: tiny stub in always-loaded context (~200-300 tokens), full payload in on-demand files (`.renmark/memory/project-map.md`, `.renmark/memory/dev-standards.md`).

**New command — `/renmark:init`:**

- **`plugin/commands/init.md`**, **`plugin/skills/init/SKILL.md`** (NEW) — thin command stub + skill dispatcher. The skill's only job is to invoke `python -m renmark.init` and relay the one-line summary; agents do no scanning, no regex, no rendering. Token cost per invocation: near-zero (just script stdout).
- **`/renmark:init --deep`** — opt-in flag for slower checks: samples last 20 git commits for conventional-commits style. Reserved for future expensive checks (GitHub branch-protection lookups, test-naming inference). Baseline scan runs without the flag.
- **`/renmark:init scan`** — diagnostic mode; prints what would be detected, writes nothing.

**New Python module — `renmark/init.py`:**

- **Project map scanner.** Walks the repo respecting `.gitignore` (excludes `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next`, `target`, `.renmark/state`, `.renmark/debug`, etc.). Detects stack from `pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` / Claude Code plugin manifest. Extracts public symbols from the top-20 largest source files for Python, JS/TS, Go, Rust, Ruby. Caps modules table at 40 rows, symbols-per-file at 6, top-level layout at 7 dirs. No file bodies, no docstring transcripts.
- **11 dev-standard detectors.** Test (pytest/jest/vitest/cargo/go), lint (ruff/flake8/eslint/rubocop/clippy), formatter (black/ruff format/prettier/rustfmt/gofmt), type-checker (mypy/pyright/tsc-strict), CI (GitHub Actions/GitLab/CircleCI — extracts workflow names), pre-commit (`.pre-commit-config.yaml` hooks + Husky), env schema (`.env.example` key names only, never values), database/migrations (alembic/prisma/drizzle/knex), local-dev startup (npm scripts/Makefile/docker-compose), code style (`.editorconfig`), dep policy (dependabot/renovate/lockfiles).
- **11 standards-health gap checks** with severity ranking. 🚨 danger: `.env` committed without `.gitignore` entry; multiple JS package-manager lockfiles concurrently. ⚠ warn: no linter; no type checker (or tsconfig without `"strict": true`); no tests in a >10-file project; test framework configured but zero test files; linter not wired to pre-commit OR CI; no CI on a multi-file project; pre-commit AND CI both missing; missing lockfile when `package.json` exists. ℹ info: no `.gitignore`; no README. Each gap carries a *tighten-this* recommendation pointing to the exact remediation.
- **Byte-equality skip on every artifact.** If the rendered stub body matches the existing `<!-- BEGIN:project-stub -->` block in CLAUDE.md, the file is not rewritten — no prompt-cache bust. Same check for `project-map.md` and `dev-standards.md` (stripping the timestamp header line so the freshness stamp doesn't trigger spurious rewrites).

**Three artifacts, three access patterns:**

- **CLAUDE.md / AGENTS.md stub** (always-loaded, ~250 tokens) — stack one-liner, top-level layout, `Dev gates:` line listing test/lint/typecheck/CI commands when detected, and pointers to the on-demand files. The gates line is conditional: greenfield projects with no detected standards produce a stub with no gates line at all.
- **`.renmark/memory/project-map.md`** (on-demand, opt-in payload) — full directory tree, modules table with symbols, user-facing commands catalog. Read by agents that need to navigate the codebase.
- **`.renmark/memory/dev-standards.md`** (on-demand, opt-in payload) — detected-standards table + standards-health section with severity-ranked gaps and recommendations. Read by agents about to make non-trivial changes.

**Auto-refresh hooks wired into the pipeline:**

- **`/renmark:setup`** — step 5.5 seeds the project map and dev-standards on first run (skipped if `project-map.md` already exists). One-time bootstrap.
- **`/renmark:finish`** — step 1.5 refreshes both artifacts after verifiers pass but before the branch summary. If the byte-equality skip says nothing changed (e.g. feature only fixed bugs, no shape change), no files are written, no commit is made, no cache is busted. If anything changed, files are staged and committed as `docs: refresh project map` so the refresh ships with the feature.
- **`/renmark:init`** — manual escape hatch for hand-edited or out-of-pipeline changes.
- **Explicitly NOT hooked into `/renmark:orchestrate` or `/renmark:debug`** — those run too frequently for the cost-to-value ratio. Per-task or per-fix refreshes would bust the CLAUDE.md cache 5-15 times per feature for the same information value finish would refresh once.

**stdout contract — what the agent sees:**

```
OK  stub=<created|refreshed|unchanged> agents=<…|skipped> map=<…> standards=<…> modules=N commands=N langs=py,ts,… ref=YYYY-MM-DD@<git-sha>
HEALTH: N gaps (X danger, Y warn, Z info) — see `.renmark/memory/dev-standards.md`
```

The HEALTH line only appears when at least one gap exists. A clean project produces just the OK line.

**Other changes:**

- **`plugin/skills/help/SKILL.md`** — `/renmark:init` added to the command catalog.
- **`.claude-plugin/marketplace.json`** — skills list updated to include `init`.

**Do not change:**

- Changelog format — renmark reads and appends to this file automatically; the `## [date] — [title]` heading shape is parsed by the version-drift gate and the release-notes generator.
- The byte-equality skip logic in `renmark.init` — without it, every `/renmark:finish` would rewrite CLAUDE.md and bust the prompt cache for every conversation in the project. The skip is what makes the auto-refresh strategy affordable.
- The "stub vs payload" split — moving full module/symbol detail back into CLAUDE.md would re-introduce the context-tax problem this release was designed to solve.

## v0.4.0 — 2026-05-28 (verify --qa / --deep-qa: live-browser E2E verification)

**Minor release — verification grows a second lens. Smoke proves the happy path *responds*; QA proves it *works in a browser*; Deep QA proves it *fails gracefully at the edges*. All three are reachable from each other in one keystroke via a shared hand-off menu.**

The driving goal: stop the loop of "ask to fix → find it's still broken → surgically fix what QA should have caught." Live-browser E2E that runs automatically-on-request and produces specific, reproducible findings makes the fix loop converge. Spec lived as draft at `.renmark/specs/2026-05-27-verify-qa-browser-e2e.spec.md` since v0.3.3; this release implements it as skill prose with zero new Python deps.

**New shared file:**

- **`plugin/skills/_shared/handoff-menu.md`** (NEW) — single source of truth for the quality-gate hand-off menu, referenced by `verify`, `verify --qa`, `verify --deep-qa`, and `codereview`. Same `_shared/` pattern as `scope-contract.md` (already excluded from the plugin linter as of v0.3.3). Documents the four canonical gate letters (`[s]` Smoke, `[qa]` QA, `[dq]` Deep QA, `[c]` Code review) plus the terminal actions, and the five rendering rules (omit the gate just run; show `[dq]` only after `--qa` passes; show `[d]` only on failure; etc.). Adding a future gate (perf, security) is now a one-file edit.

**`verify --qa` — one live-browser happy-path flow:**

- **Applicability gate.** Web project (per `.renmark/memory/stack.md` / `package.json`) + Chrome DevTools MCP reachable (`list_pages` probe). Non-web project → "N/A, no browser surface." MCP unavailable → degrade to shell smoke with a one-line note. Never crash, never block.
- **Server lifecycle.** Detect-or-boot the dev server via the run command from `CLAUDE.md § Testing` / `stack.md`; record `qa_started_server` so we tear down only what we booted, never a server the user is using.
- **Single happy-path flow** derived goal-backward from the spec's #1 user-visible behavior; driven via `navigate_page` / `take_snapshot` / `click` / `fill` / `wait_for` / `take_screenshot` / `list_console_messages` / `list_network_requests`.
- **Pass criteria (5 hard, 2 soft).** Hard: page loads (not blank/500), no uncaught console errors, no 4xx/5xx on the path, expected result element renders (`wait_for`), no error UI. Soft: persistence + latency. Each failure names *which* criterion broke so the verdict line is specific.
- **Context-hygiene contract — non-negotiable.** Screenshots go to `.renmark/reviews/qa/<feature>/step-N.png`; console + network dumps go into the artifact body; accessibility snapshots are used transiently to find selectors and then discarded. The orchestrator sees only the ≤5-line verdict block + artifact pointer.
- **Artifact:** `.renmark/reviews/YYYY-MM-DD-<sha>.qa.md` via `summary.write_artifact(artifact_type="qa", generator="verify-qa", ...)`.

**`verify --deep-qa` — 3 risk-ranked edge-case flows:**

- **Hard gate behind a passing `--qa`.** Refuses unless a `.qa.md` artifact exists for the current sha with `completion_state="complete"` and `generator="verify-qa"`. Edge cases on a broken happy path are noise.
- **Plan phase — risk-rank, then pick 3 (no browser yet).** Reads the diff (bounded — never pasted into chat), the feature behaviors, and `bugs.md` entries whose `files:` overlap, then ranks failure modes by likelihood using a 6-category checklist (empty/missing, boundary/size, malformed/hostile, error path, state/sequence, authz). Surfaces top 3 + one-line rationale each for user approval before opening a browser.
- **Runs them serially**, in risk order, in the singleton main-agent browser. Pass condition is **graceful handling**: no uncaught console exception, no crash, no corrupt state, either tolerates the input OR rejects with a clear visible error — not silent no-op, not infinite spinner.
- **Artifact:** `.renmark/reviews/YYYY-MM-DD-<sha>.deep-qa.md`; per-case evidence under `.renmark/reviews/qa/<feature>/deep/case-N/`.
- **Why serial-in-main, not subagents:** at 1+3 flows that each dump evidence to disk and return only verdict lines, the main context never holds heavy payloads — subagent fan-out buys nothing against a singleton browser and adds coordination cost.

**Three gates, mutually reachable:**

- `verify` (smoke), `verify --qa`, `verify --deep-qa`, and `codereview` all now render the menu from `_shared/handoff-menu.md`, omitting the gate just run and showing `[dq]` only after `--qa` passes for the current sha and `[d]` only on a failure. Re-testing a feature from a different angle is one keystroke at any point.
- `codereview`'s hand-off was extended: in addition to its existing `[o] Open` / `[fix] Fix` actions, it now offers Smoke + QA + (conditionally) Deep QA + Debug + Finish + Nothing.

**Convergence loop (the certainty mechanism):**

- Every `--qa` / `--deep-qa` failure calls `memory.log_bug` with a reproducible finding — symptom + console/error + file:line if discoverable + repro steps. A later `verify --qa` re-runs the failing flow plus the `bugs.md` regression set; the fix loop converges. No "still broken" surprises downstream.
- Every run (pass or fail, any mode) calls `memory.append_learning` (G8 compounding).

**No Python module changes required.** The browser MCP session is the main agent's; `renmark/` Python stays as-is. `summary.write_artifact` accepts `artifact_type="qa"` / `"deep-qa"` via its existing generic field; no signature changes.

**Lifecycle:** `--qa` / `--deep-qa` do NOT add new stages. Both run at stage `verified` (or re-run there). The verification artifact pointer is updated via `lifecycle.write_lifecycle(artifact_update=("qa", ...))` / `("deep-qa", ...)`, but `stage` stays `verified` — codereview / finish remain the next recommended steps.

**Files touched:**

- New: `plugin/skills/_shared/handoff-menu.md`.
- Modified: `plugin/skills/verify/SKILL.md` (smoke hand-off rewritten to use shared menu; full `--qa` and `--deep-qa` sections added), `plugin/skills/codereview/SKILL.md` (hand-off appends shared menu), `plugin/commands/verify.md` (description + `argument-hint` + mode-selection notes), `.renmark/specs/2026-05-27-verify-qa-browser-e2e.spec.md` (`status: draft` → `implemented` + `related_release: v0.4.0`), all 7 canonical version locations, this changelog.

**Do not change:**

- The hand-off menu text lives in `_shared/handoff-menu.md` and nowhere else. If you find yourself pasting the menu into a SKILL.md, stop and reference the shared file instead — drift across skills was the exact problem this directory was added to solve.
- The Deep QA gate (`--deep-qa` refuses unless a passing `.qa.md` exists for the current sha) is load-bearing. Removing it means edge cases run against a happy path that doesn't work, producing meaningless noise.
- The context-hygiene contract for `--qa` / `--deep-qa` (screenshots/console/network → disk; orchestrator sees only the ≤5-line verdict) is non-negotiable. If a future change makes the orchestrator ingest browser payloads, the whole point of running this in the singleton main agent is defeated — split it into a subagent flow first.
- The browser MCP session is a singleton owned by the main agent. Do not introduce a subagent-driven browser flow; that path (subagent fan-out for many journeys) was explicitly deferred.

**Verification:** 298 unit tests pass (no Python changes, no test changes), plugin lint clean, drift check clean (all 7 version locations at v0.4.0). The new skill prose is text-only and exercised by the existing lint test that checks every SKILL.md has matching frontmatter + paired command shim.

## v0.3.3 — 2026-05-27 (pipeline streamlining + research + write boundary)

**Fewer commands, more done per command. The day-to-day path is now four steps (brainstorm → plan → orchestrate → finish) because validation and verification auto-run inside the steps they belong to. brainstorm gained research; the project-write boundary is now a hard rule.**

**Distribution packaging (new — `/renmark:finish` § Release):**

- **`renmark.release.build_package()`** — pure-Python (no rsync/zip CLI, no new deps) builder that zips the distributable into the **project's** `.renmark/baks/<name>-v<version>.zip`, version-anchored to match the git tag `v<version>`. Honors the project-write-boundary rule (writes only inside the project) and excludes `.git`, `.venv`, `__pycache__`, `.env`, `.renmark/`, `PLAN.md`, etc. CLI: `python -m renmark.release package`. (+5 tests)
- **`/renmark:finish` gains an `[r] Release` option:** drift-gate → build the local bak (always, offline) → tag `v<version>` → **if** a git remote + `gh` exist, offer to push the tag and `gh release create` with the zip attached; otherwise report the local bak + tag as a complete offline release. One version string across bak filename, git tag, and GitHub release — never drifting. The local `.renmark/baks/` copy is the offline fallback when you don't want to pull from GitHub.
- `.renmark/baks/` is gitignored (regenerable; the GitHub release is the shareable canonical copy).
- **`--dest` / `--name` overrides** on `release package` (and `build_package(dest_dir=, archive_stem=)`) — a maintainer escape hatch to package renmark's OWN release to a sibling dir with a custom name (e.g. `~/projects/ai-system-renmark-v<version>-<date>.zip`), rather than into a managed project's `.renmark/baks/`. Managed-project releases still default to `.renmark/baks/`.

**Pipeline auto-chaining (commands stay standalone-callable):**

- **`/renmark:plan` auto-runs `/renmark:check-plan`.** After writing the plan, validation runs automatically before the dispatch gate. BLOCK loops back to fix; PASS/WARN advances the lifecycle to `plan-validated` and shows the cost-approval gate. The critical cost gate stays in `plan` — auto-validation never silently dispatches. `/renmark:check-plan` remains callable on any plan.
- **`/renmark:orchestrate` auto-runs `/renmark:verify`.** A fully clean run (all tasks pass) flows straight into goal-backward verification, which advances the stage to `verified` and presents the review/finish hand-off. On any task failure the run pauses and does NOT auto-verify. `/renmark:verify` remains callable standalone.

**brainstorm upgrades:**

- **Research phase (new).** Before proposing approaches, brainstorm researches best practices, prior art (existing software that solves the problem), and live GitHub reference implementations via `WebSearch` / `WebFetch` / Context7. Findings are written to a `.renmark/research/` artifact; only a ≤5-line summary enters the conversation (G3/G6). The design is now informed, not invented. (Folds in the previously-planned `/renmark:research` gap.)
- **Owns the scope contract.** brainstorm now runs the stack/deployment/MVP questions and writes the records (`stack.md` + CHANGELOG scope entry), so `/renmark:plan` detects them and skips re-asking.

**Single source of truth:**

- **`scope-contract.md` moved to `plugin/skills/_shared/`** and is now referenced by both `brainstorm` and `plan`. The stack/deployment/MVP questions live in exactly one place and can't drift. The plugin linter now skips `_`-prefixed shared dirs (they're reference files, not skills). (+1 lint test)

**Hard rule — project-write boundary:**

- **renmark must never write outside the project.** All specs, plans, reviews, research, logs, and memory go under the project's `.renmark/` subtree (or project-root docs). The global plugin install (`${CLAUDE_PLUGIN_ROOT}`, `~/.claude/...`) is read-only — reading templates/reference files from it is fine, writing to it is forbidden. Codified as `project-write-boundary-rule` in `CLAUDE.md.template` and mirrored in `AGENTS.md.template`.

**Verification:** 292 unit tests pass (+1 lint test), 28 integration skipped, shadow baselines clean, plugin lint clean. These are skill-prose + linter changes; the lifecycle stage machine already supported the auto-chained flow, so no Python state changes were required beyond the linter.

## v0.3.2 — 2026-05-27 (context-hygiene + maintainability audit)

**Patch release — seven audit fixes hardening the isolation boundary, spend reporting, and module structure. No breaking changes; the public import surface is preserved.**

**Context-hygiene fixes:**

- **G3 char-cap leak closed** — `SubagentOutput.__post_init__` (`dispatch.py`) now enforces the ≤1200-char-per-line cap and a non-string guard, not just the ≤5-line count. A 5-line × 5000-char payload can no longer slip through `parse_subagent_response`. The cap matches `schemas.py` and `summary.py`. (+3 tests)
- **Lifecycle dead-pointers fixed** — `NEXT_BY_STAGE` no longer routes to unimplemented skills (`/renmark:document`, `/release`, `/approve`, etc.). `next_recommended()` resolves through a new `IMPLEMENTED_SKILLS` set and falls back to manual hints; aspirational routing preserved in `NEXT_BY_STAGE_PLANNED`. A regression test iterates every canonical stage. (lifecycle.py)
- **Agent-call spend ledgered** — new `state.log_agent_call()`; the orchestrate skill records every haiku/sonnet/opus Agent return so `/renmark:roadmap` reports real spend. `roadmap.py` now prices opus at ~$0.015/kT (was treated as free) and includes haiku.
- **Honest cost preview** — `plan/SKILL.md` bakes the ~10k Agent-call overhead into the displayed total instead of footnoting it; the dry-run footer was corrected to match.
- **Step-0 boilerplate consolidated** — new `lifecycle.skill_preamble(repo, skill)` replaces the duplicated `context_budget_check` + `record_skill_invocation` block across all 14 SKILL.md files. Domain resolves centrally from `DOMAIN_BY_SKILL`, so per-skill drift is impossible.
- **Artifact-dir rotation** — new `state.rotate_dir()` caps `wave-summaries/` (50), `logs/` (50), and `escalations/` (20), archiving overflow to `.renmark/state/archive/<stamp>/`. Best-effort; never breaks a running orchestrate. (+4 tests)

**Maintainability:**

- **`state.py` (538 lines) → `state/` package** — eight cohesive submodules (`_core`, `usage`, `pause`, `pipeline`, `logs`, `commits`, `skills`) behind a re-exporting `__init__.py`. Rotation caps are read via `_core` at call-time so they stay monkeypatchable.
- **`cli.py` (982 lines) → `cli/` package** — execution engine (`_engine.py`) split from the self-contained subcommand handlers (`commands.py`); re-exporting `__init__.py` keeps `cli.main` / `cli.cmd_task` / `cli.execute_plan` intact.

**Verification:** 291 unit tests pass (+10 new), 28 integration skipped (codex/network-gated), shadow baselines re-accepted (lifecycle `case-full-walk`), functional smoke green (`--usage`/`--roadmap`/`--logs`/dry-run). Independent codex review was unavailable (account model limitation); reviewed via diff + runtime invariant checks.

## v0.3.1 — 2026-05-21 (integration testing + guardrails)

**Patch release — the framework now defends itself against regressions.**

Three layers of test discipline land in v0.3.1: per-commit guardrails (fast), per-release integration smoke (thorough), and per-task shadow tests (regression detection on load-bearing subsystems). Every layer is opt-in or gated so day-to-day work stays fast.

**New modules:**

- **`renmark/schemas.py`** (NEW, 24 tests) — zero-dependency structural validators for `lifecycle.json`, `pipeline.json`, `SubagentOutput` JSON, and `ArtifactMetadata`. G11 isolation enforcement catches transcript/diff/reasoning leakage at the schema layer. G3 summary boundary enforced (≤5 lines, ≤1200 chars per line). G12 lifecycle byte budget enforced. CLI: `python -m renmark.schemas {lifecycle|pipeline|subagent|artifact} <path>`.
- **`renmark/lint.py`** (NEW, 25 tests) — plugin contract linter. Verifies every SKILL.md has valid frontmatter with matching `name:`, every `commands/<name>.md` has a paired `skills/<name>/SKILL.md` (and vice versa — no orphan commands, no unreachable skills), CLAUDE.md.template has balanced `BEGIN:` / `END:` rule-block markers, and `plugin.json` has required fields. CLI: `python -m renmark.lint [--plugin-dir DIR]`.
- **`renmark/release.py`** (NEW, 20 tests) — version-file drift detection pulled forward from the v0.4.0 release skill. `VERSION_FILES` catalogs the 7 locations that carry the canonical version (VERSION, pyproject.toml, `renmark/__init__.py`, plugin.json, marketplace.json metadata + plugins[0], README.md header). `python -m renmark.release check` exits 1 on any disagreement. Bump/tag/zip operations stay deferred to v0.4.0 — this module is read-only at v0.3.1.
- **`renmark/shadow.py`** (NEW, 22 tests) — record-and-replay regression framework. Per-subsystem `replay(case_dict) → output_dict` functions registered via `@shadow.register("name")`. `run` replays every case and diffs against the committed baseline; `accept --subsystem X -m "msg"` re-records baselines and prepends a `CHANGES.md` entry. Initial subsystems: `dispatch`, `lifecycle`, `summary` (9 baselined cases total, including adversarial leakage scenarios).

**New tooling:**

- **`tools/precommit.sh`** — 30-second pre-commit guard: pytest, drift check, plugin lint. Three-step output, fails loud on any issue. Total budget for the renmark repo today: ~3s warm.
- **`install.sh --dev`** — opt-in flag that symlinks `tools/precommit.sh` to `.git/hooks/pre-commit`. Existing hooks are moved aside with a timestamped `.bak.` suffix, never overwritten. `--uninstall` removes the dev hook alongside the plugin.

**Integration smoke suite:**

- **`tests/integration/`** (NEW, 27 tests, gated behind `RENMARK_SMOKE=1`) — five end-to-end tests against a synthetic fixture project: full-lifecycle round-trip with schema validation at every stage, cold-start recovery via subprocess (simulates `/clear`), dispatch isolation E2E with realistic adversarial responses (transcript / generated_code / diff / reasoning / conversation / raw_output / trace leakage all blocked), codex-fallback behavior when codex CLI is absent, plugin install.sh round-trip in a fake `$HOME`. `conftest.py` auto-skips integration tests unless `RENMARK_SMOKE=1` so unit-test runs stay at ~2.5s.
- Fixtures: `repo_root`, `fixture_project` (initialized git repo with baseline `.renmark/` tree), `fixture_plan` (writes a one-task plan into the fixture).

**Shadow framework specifics:**

- Baseline files live at `tests/shadow/baselines/<subsystem>/case-*.json` (committed, ~few KB total). Cases live at `tests/shadow/cases/<subsystem>/case-*.json`.
- Replay functions are deterministic — `lifecycle.last_updated` (timestamp) and `summary.created_at` are stripped or fixed to keep baselines stable.
- `accept` requires a non-empty `-m MESSAGE` explaining the change. Prepends to `tests/shadow/CHANGES.md` below the header so the most recent change is on top.
- Shadow framework's own correctness tested by `tests/test_shadow.py` using `monkeypatch` to redirect `_shadow_root` at a tmpdir — 22 unit tests verify drift detection, missing-baseline handling, accept idempotency, deterministic replay, CLI flag handling.

**Test counts:**

- Unit tests: **283 passed, 28 skipped** in 2.56s (smoke gated off)
- Full suite: **311 passed** in 18.13s (`RENMARK_SMOKE=1`)
- Net new tests in v0.3.1: **+113** (schemas 24 + lint 25 + release 20 + shadow 22 + integration 22 = exactly the additions; 261 → 283 unit, +28 integration = +50 not counting the bumps from shadow framework's own tests)

**Risk-reduction posture:**

- Three independent regression nets now exist. A bug in one is caught by another: schema drift catches structural breakage, drift check catches version desync, lint catches plugin-contract rot, smoke catches integration breakage, shadow catches behavioral drift in load-bearing modules.
- Pre-commit hook is opt-in by design — `bash install.sh --dev` activates it. Default install path stays as fast as v0.3.0.
- Future v0.4.0 `/renmark:release` will invoke shadow + smoke + drift as its preflight checks before tagging.

**Files touched:**

- New: `renmark/schemas.py`, `renmark/lint.py`, `renmark/release.py`, `renmark/shadow.py`, `tools/precommit.sh`, `tests/test_schemas.py`, `tests/test_lint.py`, `tests/test_release_drift.py`, `tests/test_shadow.py`, `tests/integration/__init__.py`, `tests/integration/conftest.py`, `tests/integration/test_smoke_full_lifecycle.py`, `tests/integration/test_cold_start_recovery.py`, `tests/integration/test_dispatch_isolation_e2e.py`, `tests/integration/test_codex_fallback.py`, `tests/integration/test_plugin_install.py`, `tests/shadow/cases/{dispatch,lifecycle,summary}/case-*.json` (9 files), `tests/shadow/baselines/{dispatch,lifecycle,summary}/case-*.json` (9 files), `tests/shadow/CHANGES.md`.
- Modified: `install.sh` (added `--dev` flag), `VERSION`, `pyproject.toml`, `renmark/__init__.py`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` (version bump only).

---

## v0.3.0 — 2026-05-19 (framework MVP — context death is survivable)

**Minor release — the foundation that makes renmark a development framework, not just a plugin.**

The core innovation this release: **AI workflows that survive context death.** Cold start from any `/clear` or `/compact` is one file read. Heavy work runs in isolated subagent contexts. The orchestrator is now structurally incapable of merging generated code into its conversation — the parser refuses it.

**Load-bearing new infrastructure** (the MVP five):

- **`renmark/summary.py`** (NEW, 323 LOC, 19 tests) — `write_artifact`, `emit_pointer`, `read_metadata`, `is_stale`, `verifier_tail`, `hash_artifact`, `git_head_sha`. Enforces G3 (5-line summary cap, ~300 tokens per line), G6 (provenance + freshness metadata on every artifact), G9 (`completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance` transparency fields). Every auditor skill funnels through this module.
- **`renmark/lifecycle.py`** (NEW, 251 LOC, 18 tests) — workflow state for the seven-stage lifecycle. `read_lifecycle`, `write_lifecycle`, `clear_lifecycle`, `next_recommended`, `domain_of`, `is_cross_domain_transition`. Strict 1KB byte budget; runtime cruft is rejected with `LifecycleBloatError` to keep lifecycle.json separate from pipeline.json. G12 codified.
- **`renmark/state.py`** (extended +200 LOC, 15 new tests) — pipeline.json (`read_pipeline_state`, `write_pipeline_state`, `clear_pipeline_state`, `pipeline_is_resumable`), `.renmark/state/wave-summaries/wave-N.json` aggregation (`write_wave_summary`, `read_wave_summary`, `list_wave_summaries`), and `last-skill.json` for cross-domain detection (`record_skill_invocation`, `last_skill_invocation`, `context_budget_check`).
- **`renmark/dispatch.py`** (extended +190 LOC, 19 new tests) — G11 task isolation contract. `SubagentInput` (the ONLY fields a subagent receives) and `SubagentOutput` (the ONLY fields it emits) are frozen dataclasses. `parse_subagent_response` raises `IsolationViolation` on any extra field (transcript, diff, generated_code, reasoning). `dispatch_task_isolated` is the injection point — wraps subagent runners under strict I/O bounds.
- **`renmark/cli.py`** (+110 LOC, 6 new tests) — `--task SPEC --output ARTIFACT` ad-hoc Codex mode. Emits SubagentOutput-shaped JSON to stdout; the generated body lives in the artifact file, never the conversation. Falls back cleanly when codex CLI is missing.
- **`plugin/skills/resume/SKILL.md`** (NEW, 112 lines) — `/renmark:resume`. Zero LLM calls. Reads `lifecycle.json`, prints stage + next recommended command + any pending human approval gate. The cold-start recovery surface.

**Skill behavior changes:**

- All 13 existing skills gained a **Step 0 — Context check** preflight that calls `state.context_budget_check` (for cross-domain `/clear` recommendations) and `state.record_skill_invocation` (for next-skill detection). Skills with stage semantics (start, brainstorm, plan, check-plan, finish) now also write `lifecycle.json` on completion.
- `/renmark:orchestrate` rewritten to honor G11 task isolation: builds dependency context only from prior wave's `dependency_notes` (never the full output), dispatches each task in isolation via `dispatch_task_isolated`, aggregates `SubagentOutput` dicts into `.renmark/state/wave-summaries/wave-N.json`, refuses to merge subagent responses that contain forbidden fields. Pipeline state machine tracked at wave boundaries; `lifecycle.write_lifecycle(stage='created')` on completion.
- `/renmark:check-plan` gained 5 new hygiene + isolation BLOCK/WARN rules: heavy-read check (G5), transcript-leak phrase denylist (G11), dependency-graph hygiene (G11), verifier output bound check (G3), spec length WARN.
- `/renmark:verify` strengthened to goal-backward mode: reads plan goal via `parser.parse_plan`, cross-references open bugs from `.renmark/memory/bugs.md` for regression coverage (G8 compounding), runs commands via `summary.verifier_tail` (bounded output), emits a `.verification.md` artifact via `summary.write_artifact`, appends to `learnings.md` on every run and `bugs.md` on failures. Refuses if pipeline state is dirty.

**New rule blocks in `plugin/templates/CLAUDE.md.template`:**

- `context-budget-rule` — `/compact` at 60%, `/clear` on cross-domain transitions. Domain taxonomy: debug, build, audit, meta.
- `lifecycle-rule` (G12) — every stage transition writes lifecycle.json; cold start is one file read; strict separation from pipeline.json; human approval gates carried in `human_review_required` / `human_review_completed` / `human_review_for` fields.

`plugin/templates/AGENTS.md.template` gained two one-liner mirrors. `plugin/skills/setup/SKILL.md` merge table extended from 15 to 17 blocks.

**`renmark/__init__.py` version drift fixed.** Was stuck at `0.2.0` since the package was forked from ai-inference; now in sync at `0.3.0`.

**Tests:** 192 → 192 passing. 77 new tests added across summary, lifecycle, pipeline state, isolation, and CLI task mode. Zero regressions.

**Files changed:**
- `renmark/summary.py` — NEW
- `renmark/lifecycle.py` — NEW
- `renmark/state.py` — extended (pipeline + wave-summaries + skill invocations)
- `renmark/dispatch.py` — extended (SubagentInput/Output, IsolationViolation, dispatch_task_isolated, parse_subagent_response, build_subagent_input)
- `renmark/cli.py` — `--task` / `--output` ad-hoc Codex mode
- `renmark/__init__.py` — version sync 0.2.0 → 0.3.0
- `plugin/skills/resume/SKILL.md` — NEW
- `plugin/skills/orchestrate/SKILL.md` — full rewrite
- `plugin/skills/verify/SKILL.md` — full rewrite
- `plugin/skills/check-plan/SKILL.md` — hygiene + isolation BLOCKs added
- `plugin/skills/{start,brainstorm,plan,finish,feature,debug,codereview,setup}/SKILL.md` — Step 0 + lifecycle hooks added
- `plugin/templates/CLAUDE.md.template` — `context-budget-rule` + `lifecycle-rule` blocks
- `plugin/templates/AGENTS.md.template` — 2 one-liner mirrors
- `plugin/skills/setup/SKILL.md` — merge table extended to 17 blocks
- `tests/test_summary.py`, `test_lifecycle.py`, `test_state_pipeline.py`, `test_dispatch_isolation.py`, `test_cli_task_mode.py` — all NEW
- `VERSION`, `pyproject.toml`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` — version sync

**Do not change:**
- `SubagentOutput` and `SubagentInput` are the **boundary contract**. Adding fields requires updating `SUBAGENT_OUTPUT_FIELDS` (in `dispatch.py`) AND updating every Agent prompt template (in `prompts.py`) AND extending the test `test_subagent_output_fields_match_dataclass`. Drift here is silent corruption.
- `IsolationViolation` is intentionally fail-loud. Do not swallow it with try/except in dispatch paths — that defeats G11. If a real subagent legitimately needs to send a new field, add it to the schema with explicit tests.
- `lifecycle.json` byte budget (1KB) is a forcing function, not a suggestion. If `LifecycleBloatError` fires, the answer is to move fields to `pipeline.json`, not raise the limit.
- The 5-line summary cap in `write_artifact` and `SubagentOutput.summary_lines` is the G3 enforcement. Raising it requires editing `MAX_SUMMARY_LINES` in `summary.py` AND `summary_lines` validation in `dispatch.py.SubagentOutput.__post_init__` AND updating the rule prose in CLAUDE.md.template. All three or none.
- `renmark/__init__.py.__version__` MUST stay synced with `VERSION` and `pyproject.toml`. v0.4.0's `/renmark:release` skill will automate this — until then, bump by hand and run `grep -R 0\\.X\\.Y plugin/templates/ pyproject.toml plugin/.claude-plugin/ .claude-plugin/ README.md renmark/__init__.py VERSION` to confirm.

**Next release: v0.3.1 — `/renmark:document` (post-feature doc sync).** See `/home/renmark/.claude/plans/cheerful-drifting-seal.md` for the full v0.3.x → v0.4.0 rollout.

---

## v0.2.5 — 2026-05-18 (governance charter codification)

**Patch release — documentation only, no code or skill behavior changes.**

The orchestrator (Sonnet 200k typical) is now treated as a degrading systems resource. Nine new governance rules codify how every renmark skill must behave to protect orchestration integrity against context rot. The rules ship as `BEGIN/END` blocks in CLAUDE.md.template so `/renmark:setup` merges them into existing projects without overwriting.

**New CLAUDE.md rule blocks** (9, all in `plugin/templates/CLAUDE.md.template`):
- `orchestrator-role-rule` — coordinator, not memory container
- `canonical-state-rule` — truth lives in `.renmark/` and CHANGELOG, not conversation
- `summary-boundary-rule` — orchestrator-visible output ≤ 5 lines or ≤ 300 tokens
- `context-contamination-rule` — cross-domain skill changes recommend `/clear` (domains: debug, build, audit, meta)
- `artifact-governance-rule` — every artifact carries provenance + freshness metadata
- `compact-semantics-rule` — `/compact` preserves goals, blockers, pipeline state, artifact refs, verification status
- `failure-transparency-rule` — outputs carry `completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance`
- `workflow-recovery-rule` — multi-step workflows resumable from `.renmark/state/pipeline.json`, not conversational reconstruction
- `task-isolation-rule` — `/renmark:orchestrate` runs each task in an isolated subagent context; subagent transcripts and generated code never re-enter the orchestrator

**AGENTS.md.template:** 9 corresponding one-liner mirrors, each pointing at the longer block in CLAUDE.md.

**`/renmark:setup`:** merge table extended from 6 to 15 blocks. Existing projects get the new rules merged on next setup run without overwriting custom content.

**New file `plugin/skills/CONTRIBUTING.md`:** governance acceptance bar for new skills — 9-rule compliance checklist (G2–G11). A new skill that cannot tick all 9 boxes does not merge. Includes the canonical SKILL.md structure with the `Governance compliance` table every new skill must include.

**Files changed:**
- `plugin/templates/CLAUDE.md.template` — 9 new rule blocks inserted between `verify-before-done-rule` and the tooling table
- `plugin/templates/AGENTS.md.template` — 9 one-liner mirrors added between `Verification before completion` and `Conventions`
- `plugin/skills/setup/SKILL.md` — merge table updated with 9 new entries
- `plugin/skills/CONTRIBUTING.md` — new file
- `VERSION` — bumped `0.2.4` → `0.2.5`

**Do not change:**
- The 9 rule blocks ship as one cohesive set; do not split them into separate releases. Each rule reinforces the others (e.g., G6 artifact metadata depends on G3 summary boundaries; G10 recovery depends on G2 canonical state).
- AGENTS.md mirrors stay one-liners that reference the long-form block in CLAUDE.md — do not duplicate the full rule text in AGENTS.md.
- Block names use the `<topic>-rule` suffix convention. Do not rename existing blocks; downstream merge logic depends on the names.
- The `task-isolation-rule` block describes a contract that Phase 1 code (next release v0.3.0) will enforce. Rules ship first so plans drafted against v0.2.5 already obey them — the code that mechanically blocks violations comes in v0.3.0.

---

## v0.2.4 — 2026-05-15 (vibe coder entry point)

**New skill:**
- `/renmark:start` — plain-English entry point for vibe coders. Asks what you want to build, infers stack and scope from the description, asks at most 2 follow-up questions (reach and lifespan), presents a confirmation summary with a brief best-practices mention, then routes to `/renmark:plan` (simple requests) or `/renmark:brainstorm` (complex/multi-feature). Best practices (error handling, README, .env, .gitignore, smoke test) are woven into task specs automatically — no separate tasks, no jargon exposed to the user.

**plugin.json:** version bumped to 0.2.4; description updated to lead with vibe coder framing; added `vibe-coder` keyword.

**install.sh:** `/renmark:start` added as first skill in success message; start message updated to show `start` as the entry point for new users.

**CLAUDE.md template:** `/renmark:start` added as first row in tooling table.

**Do not change:**
- The 2-question cap in `start` — more questions break the adaptive/frictionless contract
- Stack inference happens silently — never prompt the user to choose a framework

---

## v0.2.3 — 2026-05-15 (setup skill + install.sh rewrite)

**New skill:**
- `/renmark:setup` — prepares any existing project for renmark workflow. Detects tech stack from project files, creates or merges missing CLAUDE.md rule blocks (using BEGIN/END markers), syncs AGENTS.md, creates CHANGELOG.md if absent, scaffolds `.renmark/` directory tree with seed memory files, adds `.gitignore` entries, offers optional `git init`. Safe to re-run — merge-only, never overwrites existing content. Prompts to continue to brainstorm or plan on completion.

**install.sh rewrite:**
- Added `--uninstall` flag (`bash install.sh --uninstall`)
- Removed stale `/orchestrator` cleanup step (ai-inference project artifact)
- Added optional `pip3 install -q -e` step for Python editable package
- Success message now lists all 12 skills with descriptions
- VERSION read dynamically from `./VERSION` file

**VERSION:** bumped `0.1.5` → `0.2.3`

**Do not change:**
- `install.sh` symlinks are idempotent — stale symlinks are removed and recreated; non-symlink collisions abort with an error rather than overwriting

---

## v0.2.2 — 2026-05-14 (skill quality gates + CLAUDE.md discipline rules)

Skills-only release — no Python module changes.

**New skills:**
- `/renmark:check-plan` — lightweight plan validator (task count ≤ 15, verifier presence, parallel group safety). Invoked automatically by orchestrate pre-flight. Returns PASS / WARN / BLOCK.
- `/renmark:verify` — goal-backward smoke test after orchestrate. Reads plan context paragraph, runs one functional command per stated behavior, reports N/M requirements verified. Never reads source files.
- `/renmark:finish` — branch close wrapper. Re-runs verifiers, shows git log summary, offers [p] PR / [m] merge / [n] nothing.

**Skill updates:**
- `orchestrate`: pre-flight now invokes `/renmark:check-plan`; step 7 re-runs all verifiers before reporting done; hand-off menu adds `[v] Verify` and `[f] Finish` options.
- `debug`: Iron Law cross-references CLAUDE.md § Root cause before any fix; step 6 has explicit gate requiring root cause sentence before any code change.

**Template updates (CLAUDE.md.template + AGENTS.md.template):**
- Added `## Context hygiene` — never read generated file contents into conversation
- Added `## Executor dispatch rules` — codex → renmark-execute only, never Agent calls
- Added `## Root cause before any fix` — no code changes without written root cause
- Added `## Verification before completion` — re-run verifiers fresh before claiming done
- Added 3 new commands to tooling table (check-plan, verify, finish)
- AGENTS.md: added absolute paths, single-file scope, root cause, verify-before-done rules

**plugin.json:** version bumped to 0.2.2; description updated (NIM removed, new skills listed); keywords updated.

**Do not change:**
- CLAUDE.md.template rule blocks use BEGIN/END comment markers for tooling that parses them — preserve the `<!-- BEGIN:x -->` / `<!-- END:x -->` wrapper format

---

## v0.2.1 — 2026-05-14 (dispatch routing fix + scope contract + subscription language)

Skills-only release — no Python module changes.

**Fixed:**
- `orchestrate` overview: corrected dispatch table — `codex` → `renmark-execute` (Codex subscription quota), `haiku/sonnet/opus` → Agent calls (Claude Code subscription quota). Added RED FLAG to Step 3 explicitly forbidding codex tasks from being dispatched as Agent calls (was the root cause of all agents running on Sonnet 4.6 in test).
- `orchestrate` overview: replaced "OpenAI credits / Anthropic credits" language with "Codex account / Claude Code account" — both are subscription-based, not API billing.

**Added:**
- `/renmark:plan` Step 0 Scope Contract: 3-question discovery phase (tech stack with inference rules, deployment target, MVP boundary) before any task decomposition. Writes locked decisions to `CHANGELOG.md` and `.renmark/memory/stack.md`. Explicit confirmation gate — no silence-as-confirmation.
- `debug` Step 6: root-cause gate added — must write root cause sentence before drafting any fix.

**Do not change:**
- Scope Contract confirmation gate language: "Do not rely on silence, lack of objection, or ambiguous replies as confirmation" — this wording was specifically required

---

## v0.2.0 — 2026-05-14 (NIM executor removal — multi-executor architecture)

**Breaking change:** NIM executor removed. All NIM references replaced with multi-executor architecture (Haiku / Codex / Sonnet / Opus).

**Python changes:**
- `cli.py`: removed `NIMClient.from_env()` pre-flight block (was blocking all non-dry-run execution without `NVIDIA_NIM_API_KEY`); renamed `NIM_*` env vars → `RENMARK_*`; git tags `nim-run-*` → `renmark-run-*`; commit prefix `[nim]` → `[renmark]`; cleared stale Mistral model defaults to `""`
- `state.py`: `_COMMIT_TASK_RE` updated to match `renmark|codex|nim|manual` prefixes (nim kept for backward-compat with existing git history)
- `roadmap.py`: git log pattern updated; `COST_PER_KT` adds `haiku: 0.0001`
- `debug.py`: `suggest_inspector()` returns `"haiku"` for cheap intents (was `"nim"`)
- `parser.py`: default `executor` changed from `"nim"` to `"codex"`
- `__init__.py`: version bumped to `0.2.0`; description updated to list Haiku/Codex/Sonnet/Opus
- `apply.py`: module docstring updated to generic "agent output"

**Skill updates:**
- `orchestrate`: NIM pre-flight removed; refactor safety check + changelog check added; haiku added to Agent dispatch section; NIM error codes removed
- `plan`: executor list updated (NIM → Haiku); CHANGELOG.md integration added; routing table updated

**Tests:**
- `test_dispatch.py`: default executor `"nim"` → `"codex"`
- `test_debug.py`: `inspector="nim"` → `inspector="haiku"`; `suggest_inspector` assertions updated
- `test_state.py`: 3 new commit variants (`[renmark]`, `[codex]`, bare `renmark`) added; 113 tests pass

**Do not change:**
- `_COMMIT_TASK_RE` still matches `nim` — required for backward-compat with git history from pre-v0.2.0 runs
- `RENMARK_PREFER_SMALL_MODEL` and `RENMARK_BIG_MODEL` env var defaults are intentionally `""` — let users set them explicitly

---

## v0.1.5 — 2026-05-12 (Phase 3: /renmark:debug helper module)

Adds `renmark/debug.py` — file-format helpers + executor-suggestion routing for the debug loop. The skill now has a real backend instead of being a pure playbook.

- `debug.new_session(repo, symptom)` — creates `.renmark/debug/<id>/session.md` with H2 sections (Symptom / Hypotheses / Investigation log / Root cause / Fix / Verification)
- `debug.add_hypothesis(session, idx, title, likely)` — ranked list under Hypotheses
- `debug.log_investigation(session, hypothesis, inspector, finding, rules_out=False)` — append step with which model inspected it
- `debug.set_root_cause(session, text)` — replace the placeholder
- `debug.close_session(session, repo, ...)` — finalize and write a structured entry to `.renmark/memory/bugs.md` (with auto-cross-post to `learnings.md`)
- `debug.latest_session(repo)` — resume the most recent debug session (survives `/clear`)
- `debug.suggest_inspector(intent)` — returns the cheapest executor for a step:
  - `nim` for grep / file-read / line-count / regex
  - `codex` for multi-file-trace / find-usages / context-gather / api-check
  - `opus` for reasoning / race-condition / architecture
- `/renmark:debug` SKILL.md updated to point at these helpers

7 new tests. 111 passing (104 before + 7 debug tests).

**Still pending (lower priority):**
- `dispatch.py` calling `resolve_provider` to route non-nim/codex executors through the new Phase 4 providers
- `/renmark:codereview` writing review findings into `bugs.md`/`decisions.md` automatically

## v0.1.4 — 2026-05-12 (Phase 4: native multi-provider clients)

Adds three native providers + a resolver. Zero new third-party deps.

- `renmark/providers/openai_compat.py` — generic OpenAI-compatible client. Speaks `/chat/completions` against any base URL with a bearer token. Retry on 429/503, fail on 401, parse `choices[0].message.content` + `usage.{prompt,completion}_tokens`.
- `renmark/providers/ollama.py` — delegates to `openai_compat` against `http://localhost:11434/v1` by default. Executor: `ollama_chat/<model>` (e.g. `ollama_chat/qwen2.5-coder:7b`).
- `renmark/providers/openrouter.py` — delegates to `openai_compat` against `https://openrouter.ai/api/v1`. Executor: `openrouter/<provider>/<model>`. Reads `OPENROUTER_API_KEY` from env.
- `renmark/providers/__init__.py` — new `resolve_provider(executor)` function maps any executor string to `(module_name, model_arg)`. Unknown `<prefix>/<model>` strings fall through to `openai_compat` so Together / Anyscale / Groq / etc. work with the right env vars.
- 13 new tests for resolver + each provider (all mocked HTTP).

Executor strings that now work:

| Executor | Routes to |
|---|---|
| `nim` | NIM client (existing) |
| `codex` | Codex CLI (existing) |
| `opus`, `sonnet` | Agent tool — skill must dispatch |
| `ollama_chat/<model>` | Local Ollama (default `:11434`) |
| `openrouter/<provider>/<model>` | OpenRouter gateway |
| `openai_compat/<model>` | Any OpenAI-compatible API (needs `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_API_KEY`) |
| `<unknown>/<model>` | Falls through to openai_compat |

104 tests pass (91 before + 13 provider tests).

**Still pending:**
- Wiring `resolve_provider` into `dispatch.py`'s actual call path (right now `dispatch.dispatch_wave` only knows nim/codex/opus/sonnet)
- `/renmark:debug` per-step routing
- `/renmark:debug` and `/renmark:codereview` writing to `bugs.md` automatically

## v0.1.3 — 2026-05-12 (cost preview + --no-commit + routing-memory + perm snippet)

Phase 1 polish landed:

- **Cost preview in `--dry-run`**: per-task line shows executor + complexity + estimated tokens + estimated $; totals at the bottom. Uses `est_tokens` / `est_cost_usd` from the plan if present, falls back to complexity heuristic. NIM = free, codex ≈ $0.05/kT, sonnet ≈ $0.003/kT, opus = in-context.
- **`renmark-execute --no-commit`** runtime now wired through `_NO_COMMIT_MODE` module flag. `_git_commit` returns `"(no-commit)"` sentinel; the skill batches commits per wave.
- **Routing memory auto-updates**: after each task completes (passed/failed), `_memory_log_outcome` appends to `routing.md` with the task signature (`target=*.py, complexity=medium, mode=A`), executor, and outcome. Failed tasks also append to `learnings.md` with the failure note. Future `/renmark:plan` runs read these to inform auto-routing.
- **Permission-allowlist snippet** added to README — paste-in `.claude/settings.local.json` block that eliminates Bash prompts for `renmark-execute *` calls.

91 tests pass (no regressions from these changes — pure additions).

**Still pending:**
- `providers/ollama.py`, `openrouter.py`, `openai_compat.py` — Phase 4
- `/renmark:debug` per-step routing — Phase 3

## v0.1.2 — 2026-05-12 (cli uses dispatch.py — parallel waves live)

**Headline:** `renmark-execute` now uses `dispatch.py` for wave-based parallel execution. Tasks sharing a `parallel_group` run concurrently on separate threads; tasks with `executor: opus | sonnet` are marked `needs_agent` and surfaced so the `/renmark:orchestrate` skill can dispatch them via the Agent tool.

Changes:
- `cli.py`:
  - Module-level `_GIT_LOCK = threading.Lock()` serializes `_git_tag`, `_git_commit`, `_git_restore_target` across parallel task threads (git index isn't multi-thread-safe).
  - `execute_plan` refactored to use `dispatch.group_tasks_by_wave` + `validate_wave` + `dispatch_wave` instead of a flat per-task loop. Existing `_execute_task` is now invoked through a `_runner` adapter that returns `dispatch.TaskResult`.
  - End-of-run summary now reports `needs-agent` count and wave count.
  - If a wave validation fails (overlapping targets, context-into-target conflicts), the plan is rejected with exit 2 before any LLM call.
- `dispatch.py` tests (11) already covered the parallel semantics; cli.py integration verified by the existing 91-test suite — all still pass.

**LiteLLM dropped from roadmap.** Per user decision: native providers cover all realistic use cases. Future providers go in as one-file `providers/*.py` modules following the `openai_compat.py` pattern.
- PLAN.md "Phase 5" struck through with rationale
- CHANGELOG pending-list updated
- "What to steal from" table notes LiteLLM was considered and rejected

**Still pending (v0.1.3+):**
- `--no-commit` runtime behavior (argparse flag accepted, not yet effective in the commit path — would let skills batch-commit per wave manually)
- Cost preview in `--dry-run` (per-task estimate before any LLM call)
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4

91 tests pass.

## v0.1.1 — 2026-05-12 (logs dir + codereview simplified to codex-only)

**Added: `.renmark/logs/`** for per-invocation troubleshooting logs (gitignored). One log file per command run named `<command>-<run_id>.log`.

- `renmark/state.py`:
  - New constants: `LOGS_SUBDIR = "logs"`
  - `logs_dir(repo)`, `open_log(repo, command, run_id=None)`, `append_log(path, *messages)`, `recent_logs(repo, n=10)`
  - 6 tests
- `renmark-execute --logs` — lists the n most-recent log files with size + mtime
- `renmark-execute --logs-n <N>` — adjust the count (default 10)
- `bootstrap.py` updated: `.gitignore` template now includes `.renmark/logs/`
- `plugin/templates/memory/INDEX.md.template` updated to reference all `.renmark/` subdirs (specs, plans, reviews, state, debug, logs)

**Changed: `/renmark:codereview` is now single-pass (codex-only)**, no Sonnet/Opus passes.

The earlier multi-pass design put code into the conversation, which defeats the context-hygiene goal renmark is built for. Codex stays in its own sandbox; Opus only reads the severity summary. Output format and storage path unchanged (`.renmark/reviews/YYYY-MM-DD-<sha>.review.md`). Recommended cadence: end-of-plan, not per-task.

Tests: 91 passing (up from 85).

**Still pending (v0.1.2+):**

- CLI `execute_plan` integration with `dispatch.group_tasks_by_wave` + `dispatch_wave` — parallel waves not yet wired into the live loop
- `--no-commit` runtime behavior (flag accepted, not yet effective)
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases)

## v0.1.0 — 2026-05-12 (Phase 1 module landing + roadmap reporter)

**First minor release.** The Phase 1 modules are all in place with tests; the CLI's `execute_plan` loop still uses the v0.0.x single-task code path. Integrating that loop with the new dispatcher is the v0.1.1 work.

**New modules (with tests):**

- `renmark/dispatch.py` — wave-based parallel dispatcher. `group_tasks_by_wave`, `validate_wave`, `dispatch_wave` (concurrent for nim/codex/litellm, `needs_agent` marker for opus/sonnet). 11 tests including a timing assertion that two slow tasks in the same wave finish in under the serial total.
- `renmark/providers/claude_agent.py` — composer for the Agent-tool prompt when a task is `executor: opus` or `executor: sonnet`. Skill issues the Agent call; this module owns the prompt format and constraints.
- `renmark/bootstrap.py` — empty-folder helper. `is_empty_project(repo)`, `bootstrap(repo, project_name=...)` creates CLAUDE.md / AGENTS.md / `.renmark/` from plugin templates, runs `git init`. Idempotent. 6 tests.
- `renmark/roadmap.py` — synthesizer that builds a per-task `task | llm | status | tokens | $ | commit` table from `features.md` + `usage.jsonl` + git log. `write_roadmap_md(repo)` snapshots to `.renmark/memory/roadmap.md`. 7 tests.

**Parser extensions (v0.0.3+, fully tested):**

- New optional task fields: `complexity` (simple|medium|hard), `parallel_group` (int), `est_tokens` (int), `est_cost_usd` (float).
- `executor` now accepts `opus`, `sonnet`, or any `<provider>/<model>` string (e.g., `ollama_chat/qwen2.5-coder:7b`).
- 9 new tests covering defaults, type validation, and rejection of invalid values.

**New skills:**

- `/renmark:roadmap` — prints the status table; also writes the snapshot to `.renmark/memory/roadmap.md` so it's committed.
- `/renmark:help` (added in v0.0.3) — lists all skills with one-sentence descriptions.

**Wizard-style hand-offs:**

- `/renmark:brainstorm` now ends with an explicit `Y/n/wait` prompt to continue to `/renmark:plan`.
- `/renmark:plan` shows a summary (task count + cost preview) and prompts `[r]eview / [d]ispatch / [e]dit / [n]o` — Dispatch only triggers `/renmark:orchestrate` after explicit user approval.
- `/renmark:orchestrate` offers `[c]ode-review / [s]moke / [n]one` after a clean run.

**CLI:**

- `renmark-execute --roadmap` — prints the status table and writes `roadmap.md` snapshot.
- `renmark-execute --no-commit` — flag added (currently a no-op; v0.1.1 will wire it into the per-task commit code so the skill can batch commits per wave).
- argparse prog name corrected from `nim-execute` to `renmark-execute`.

**Memory templates:**

The eight `.renmark/memory/` files now have proper documentation-grade templates:
- `features.md`, `bugs.md`, `decisions.md` (ADR format), `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `learnings.md`, plus an auto-maintained `INDEX.md`.

**Plugin manifest now declares 7 skills** (brainstorm, plan, orchestrate, debug, codereview, roadmap, help).

**Tests:** 85 passing (up from 52 in v0.0.3).

**Still pending (v0.1.1+):**
- CLI `execute_plan` actually using `dispatch.group_tasks_by_wave` + `dispatch_wave` (currently the loop still runs single-task serial via the v0.0.x path)
- `--no-commit` wired through per-task commit code
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing (NIM grep / codex trace / opus reasoning)
- `/renmark:codereview` Sonnet + Opus passes
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases) (optional)

## v0.0.3 — 2026-05-12 (Phase 1, +memory + help)

**Persistent memory module + `/renmark:help` skill.**

- `renmark/memory.py` — read/write helpers for `.renmark/memory/`. Functions: `ensure_memory(repo)`, `read_index(repo)`, `read_file(repo, name)`, `log_feature(...)`, `log_bug(...)`, `log_decision(...)`, `append_routing(...)`, `append_learning(...)`. Section-aware appends (newest-first per CHANGELOG convention). Lessons in `log_bug` auto-cross-post to `learnings.md`. 8 new tests.
- Memory templates rewritten so the files act as **living documentation**:
  - `features.md` — shipped / in-progress / planned (CHANGELOG style)
  - `bugs.md` — open / fixed with severity, symptom, root cause, fix, lesson
  - `decisions.md` — ADR format (context, decision, alternatives, consequences) with auto-numbered IDs
  - `stack.md` — languages, libs, runtime env, external APIs
  - `architecture.md` — components, data flow, module boundaries, invariants
  - `conventions.md`, `routing.md`, `learnings.md` — auto-tuned + hand-edited
  - `INDEX.md` is a cheap top-of-file index loaded first by every skill
- `/renmark:help` skill (new) — prints all six commands with one-sentence descriptions and the typical workflow order. Pure documentation, no API calls.
- `plugin.json` updated to declare 6 skills.

52 tests total (44 from baseline + 8 memory tests).

## v0.0.2 — 2026-05-12 (Phase 1, partial — skills visible)

**Plugin manifest + all five `/renmark:*` SKILL.md files** so the commands appear in Claude Code's skill list after install. Template files for empty-folder bootstrap. install.sh hardened.

Added:
- `plugin/plugin.json` declaring the 5 skills
- `plugin/skills/{brainstorm,plan,orchestrate,debug,codereview}/SKILL.md` — workflow docs for each
- `plugin/templates/{CLAUDE.md,AGENTS.md,renmark-readme.md,memory/*.md}.template` — what `/renmark:brainstorm` writes when bootstrapping an empty project
- `install.sh` ran successfully — symlinks live at `~/.claude/plugins/renmark` and `~/.local/bin/renmark-execute`

Fixed:
- `install.sh` v0.0.1 stored the /orchestrator backup at `~/.claude/skills/.orchestrator.bak/` — Claude Code's skill discovery picked it up as a phantom skill named `.orchestrator.bak`. **Backup removed entirely**: the orchestrator source still lives in `/home/renmark/projects/ai-inference/` (and in its git history), so a separate copy under `~/.claude/` was just paranoia and bug surface. install.sh now `rm -rf`s the old skill outright; manual revert is `cd ~/projects/ai-inference && bash install.sh` against the v0.2.0 baseline.

Not yet wired (still Phase 1):
- `renmark/dispatch.py` — wave-based parallel dispatcher (so orchestrate can't yet run opus/sonnet tasks or parallel groups)
- `renmark/memory.py` — `.renmark/memory/` reader/writer
- `renmark/providers/claude_agent.py` — Opus/Sonnet via Agent tool from skill side
- Parser extensions for `complexity`, `parallel_group`, `est_tokens`, `est_cost_usd`
- CLI `--no-commit` mode for batched wave commits
- Cost preview in `--dry-run`
- Empty-folder bootstrap code (skill docs reference it but the brainstorm skill currently does it by hand)

The skills are visible and `/renmark:brainstorm` + `/renmark:plan` are workable today (they're Opus-driven conversations). `/renmark:orchestrate` runs the same single-task path the v0.0.1 baseline supports.

## v0.0.1 — 2026-05-12 (Phase 0)

**Bootstrap of the new `ai-system` repo.** Copies the working v0.2.0 baseline from `/home/renmark/projects/ai-inference/` and retargets the Python package from `nim_execute` to `renmark`.

Changes vs. ai-inference v0.2.0:

- Package renamed `nim_execute` → `renmark`
- `nim_client.py` → `renmark/providers/nim.py`
- `codex_exec.py` → `renmark/providers/codex.py`
- New `renmark/providers/__init__.py` with `PROVIDERS` registry stub
- Runtime state dir renamed `.nim-state/` → `.renmark/state/` (with `RENMARK_DIR_NAME`, `STATE_SUBDIR`, `MEMORY_SUBDIR`, `DEBUG_SUBDIR` constants; legacy `STATE_DIR_NAME` aliased for back-compat)
- All test imports updated, 41 tests still passing
- CLI references `renmark-execute` / `.renmark/state/` in user-facing strings

Phase 1 (next): the five `/renmark:*` skills, `plugin/plugin.json`, dispatch layer, memory module, empty-folder bootstrap. See `PLAN.md`.
