# renmark v0.5.1

A Claude Code plugin that turns Claude into a guided build assistant. Type `/renmark:start`, describe what you want to build, and renmark handles stack selection, scope, best practices, and the full build pipeline — no prior knowledge of specs, plans, or executors needed.

For experienced developers it also exposes the full wizard pipeline directly: brainstorm → plan → orchestrate → finish. Validation (check-plan) and verification run automatically inside plan and orchestrate, so the day-to-day path is four commands, not six.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) (desktop app or CLI) — required
- Python 3.10+ — required for `renmark-execute` (Codex task dispatch)
- [Codex CLI](https://github.com/openai/codex) — optional; needed only for `executor: codex` tasks

---

## Install — Mac / Linux

```bash
unzip ai-system-renmark-v0.3.0-*.zip
cd ai-system
bash install.sh
```

That's it. Restart Claude Code and the skills will appear.

To uninstall:
```bash
bash install.sh --uninstall
```

---

## Install — Windows

1. Extract the zip
2. Copy the `plugin\` folder contents into:
   ```
   %USERPROFILE%\.claude\plugins\renmark\
   ```
   The result should look like:
   ```
   %USERPROFILE%\.claude\plugins\renmark\
     .claude-plugin\plugin.json
     skills\start\SKILL.md
     skills\brainstorm\SKILL.md
     skills\plan\SKILL.md
     ... (all 13 skill folders)
     templates\
   ```
3. Restart the Claude Code desktop app

For `renmark-execute` (Codex task dispatch) on Windows: copy `bin\renmark-execute` somewhere on your PATH and ensure Python 3.10+ is installed. This step is optional — skills work without it; only `executor: codex` tasks need it.

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

## All skills

| Command | What it does |
|---|---|
| `/renmark:start` | Vibe coder entry — describe what you want, renmark builds the rest |
| `/renmark:setup` | Add renmark to an existing project (creates CLAUDE.md, AGENTS.md, .renmark/) |
| `/renmark:brainstorm` | Design a feature into a spec — researches prior art + best practices, sets the scope contract |
| `/renmark:plan` | Decompose a spec into executor-tagged tasks with cost preview (auto-validates via check-plan) |
| `/renmark:check-plan` | Validate a plan before spending tokens (runs automatically inside plan) |
| `/renmark:orchestrate` | Execute a plan (Haiku / Codex / Sonnet / Opus, wave-parallel) — auto-verifies on completion |
| `/renmark:verify` | Confirm the feature goal was achieved (runs automatically after orchestrate) |
| `/renmark:finish` | Close branch — create PR, merge, or clean up |
| `/renmark:feature` | Full pipeline with branch isolation |
| `/renmark:debug` | Systematic root-cause loop for bugs |
| `/renmark:codereview` | Multi-pass diff review |
| `/renmark:roadmap` | Project status and token usage report |
| `/renmark:help` | List all commands |

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
