# renmark v0.35.0

A Claude Code plugin that turns Claude into a **pipeline-first** build assistant. Instead of memorizing commands, pick the pipeline that matches your situation and renmark runs the whole sequence — continuing on its own and pausing only at real decisions (unclear intent, PRD approval, scope change, risky action, cost, a blocker, or merge/release).

- **`/renmark:init`** — adopt renmark into any repo (new, in-progress, or production)
- **`/renmark:start`** — build something new from plain English
- **`/renmark:feature`** — add or change a feature in an existing build
- **`/renmark:debug`** — fix what's broken
- **`/renmark:roadmap`** — find gaps and decide what's next
- **`/renmark:finish`** — verify, review, and ship

Each pipeline runs its internal stages (PRD → plan → build → verify → QA → review → ship) under renmark's context-hygiene discipline. The supporting skills (plan, orchestrate, prd, audit, …) are the machinery underneath — run `/renmark:help` for the full command list with modifiers.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) (desktop app or CLI) — required
- Python 3.10+ — required for `renmark-execute` (Codex task dispatch)
- [Codex CLI](https://github.com/openai/codex) — optional; needed only for `executor: codex` tasks

---

## Install — Mac / Linux / WSL

```bash
unzip ai-system-renmark-v*.zip
cd ai-system-renmark-v*
bash install.sh
```

The installer:
1. Symlinks the plugin into `~/.claude/plugins/renmark`
2. `pip install -e .` for the Python runtime (`renmark.init`, `renmark.doctor`, dispatch)
3. Asks about installing **Codex CLI** (optional, see below)
4. Writes the Claude Code registry entries (`settings.json` + `installed_plugins.json`)

After install, **restart Claude Code or run `/reload-plugins`** so the new slash commands appear. Then in any project: `/renmark:start`.

To uninstall:
```bash
bash install.sh --uninstall
```

---

## Install — Windows (native, no WSL)

Open PowerShell in the extracted folder and run:

```powershell
.\install.ps1
```

The PowerShell installer mirrors `install.sh` exactly:
- Junction (Windows directory alias, no admin needed) of the plugin into `%USERPROFILE%\.claude\plugins\renmark`
- `pip install -e .`
- Codex CLI prompt
- Writes settings.json + installed_plugins.json entries

After install, **restart Claude Code Desktop** so the new slash commands appear.

To uninstall:
```powershell
.\install.ps1 -Uninstall
```

> If you're running Claude Code inside WSL Ubuntu (not native Windows), use the Mac/Linux/WSL instructions above. `install.ps1` only registers with the Windows-side `%USERPROFILE%\.claude\`, which Claude Code under WSL doesn't read.

---

## Codex CLI (optional, recommended)

Renmark uses [Codex CLI](https://github.com/openai/codex) (OpenAI) as the cheap bulk-emission executor for `executor: codex` tasks. **Renmark works without it** — those tasks fall back to Sonnet automatically — but Codex is cheaper for high-volume code generation.

Both `install.sh` and `install.ps1` ask if you want to install it. If you decline, install later with:

```bash
npm install -g @openai/codex
codex login
```

This requires Node.js (https://nodejs.org). Same command on all three OSes.

---

## Quick start

```
/renmark:start
```

Describe what you want to build. renmark asks at most 2 questions, confirms the plan in plain English, then builds it.

**Setting up an existing project:**
```
/renmark:setup
```

---

## The six pipelines

| Pipeline | For | Internal stages it runs |
|---|---|---|
| `/renmark:init` | Adopt renmark into a repo | repo scan → stack/test detect → CLAUDE/AGENTS → project map → standards → PRD check → lifecycle-ready |
| `/renmark:start` | Build something new | intent → brainstorm (if fuzzy) → PRD → roadmap → first feature → plan → build → verify → review |
| `/renmark:feature` | Add/change a feature | PRD alignment → reuse check → plan → build → verify → review → finish |
| `/renmark:debug` | Fix what's broken | reproduce → root cause → fix → regression test → verify → review |
| `/renmark:roadmap` | Find gaps / what's next | status → gap discovery → backlog proposals → next-feature pick |
| `/renmark:finish` | Verify, review, ship | re-verify → QA/review as needed → report → debug if it fails → PR / merge / release |

---

## All commands

The pipelines above are the front door; every command (with its modifiers) also runs on its own. Run `/renmark:help` for the same list grouped by purpose.

| Command | What it does |
|---|---|
| `/renmark:start` | Vibe coder entry — describe what you want, renmark routes the pipeline |
| `/renmark:brainstorm` | Design a feature into a spec — researches prior art + best practices, sets the scope contract |
| `/renmark:prd` | Create/update the project PRD — the durable source of truth that plans align to |
| `/renmark:blueprint` | Generate/refresh the living schematic (+ prototype for UI builds) |
| `/renmark:plan` | Decompose a spec into executor-tagged tasks with cost preview (auto-validates via check-plan) |
| `/renmark:check-plan` | Validate a plan before spending tokens (runs automatically inside plan) |
| `/renmark:orchestrate` | Execute a plan (Haiku / Codex / Sonnet / Opus / Fable, wave-parallel) — auto-verifies on completion |
| `/renmark:verify` | Confirm the feature goal was achieved (runs automatically after orchestrate) |
| `/renmark:feature` | Full pipeline with branch isolation (PRD alignment → plan → build → verify → review → finish); `--lite` / `--full` |
| `/renmark:loop` | Bounded, resumable agentic loop — iterate until goal verified or budget hit |
| `/renmark:finish` | Close branch — create PR, merge, or clean up |
| `/renmark:backlog` | Triage backlog items; "Approve and build" launches bounded Loop Mode |
| `/renmark:debug` | Systematic root-cause loop for bugs |
| `/renmark:codereview` | Diff-proportional review: lite in-context for small diffs, full Codex pass for core code |
| `/renmark:audit` | Read-only self-audit — verifies registry/docs/skill parity; artifacts under `.renmark/audits/` |
| `/renmark:inventory` | Alias for `/renmark:audit` — lists registered skills and command surface |
| `/renmark:approve` | Flip the human-review gate — sole approval surface for merge/release gates |
| `/renmark:hygiene` | Flag stale artifacts, orphan branches, oversized memory (use `--apply` to clean) |
| `/renmark:doctor` | Diagnose install health — run if `/renmark:*` commands don't appear |
| `/renmark:init` | Scaffold or non-destructively update CLAUDE.md / AGENTS.md / `.renmark/` |
| `/renmark:setup` | Thin alias for `/renmark:init` (rule-block refresh only) |
| `/renmark:resume` | Cold-start recovery after `/clear` — one file read, zero LLM calls |
| `/renmark:roadmap` | Project status, PRD gap discovery, and token usage report |
| `/renmark:usage` | Rolling observed usage — 5-hour / weekly, top features, quota events |
| `/renmark:analytics` | Usage analytics over time — model/executor mix, verification outcomes |
| `/renmark:help` | List all commands |

---

## Troubleshooting — `/renmark:*` commands aren't appearing

If you typed `/renmark:` in Claude Code and nothing comes up, the install probably succeeded on disk but didn't register with Claude Code's plugin system. This is the most common install issue.

**Fix in one command:**

```bash
python -m renmark.doctor --fix
```

(or `python3` if your Python binary is named that). The script:
- Checks 9 things — registry entry, `settings.json` enable flag, `extraKnownMarketplaces`, cache symlink, version parity, etc.
- Auto-repairs the ones that are safely auto-fixable
- Writes timestamped backups of every config file it touches

Then run `/reload-plugins` inside Claude Code.

If the script still reports failures after `--fix`, paste the output — it names the exact remediation for each gap.

---

## renmark-execute

`renmark-execute` is the Python CLI that runs `executor: codex` tasks as subprocesses. It is invoked automatically by `/renmark:orchestrate` — you never call it directly.

It requires Python 3.10+ and the Codex CLI to be on your PATH. If Codex is unavailable, those tasks fall back to Sonnet automatically.

Install as an editable package (already done by `install.sh` on Mac/Linux):
```bash
pip install -e .
```

---

## Project memory

renmark stores persistent project context in `.renmark/` inside each project:

```
.renmark/
  memory/     — stack, decisions, features, bugs, learnings (committed)
  plans/      — generated plan files (committed)
  specs/      — design docs from brainstorm (committed)
  state/      — runtime session state (gitignored)
  debug/      — debug session logs (gitignored)
```

---

## See also

- `CHANGELOG.md` — what changed in each version
- `plugin/templates/CLAUDE.md.template` — the rules template injected into projects
