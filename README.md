# renmark — multi-LLM orchestration for Claude Code

A Claude Code plugin that owns the full feature-development workflow across multiple LLMs (NIM, Codex, Opus, Sonnet, plus Ollama and OpenRouter in later phases). Five slash commands, persistent project memory in `.renmark/`, parallel task execution, and permission-economy designed for non-auto-mode use.

## Phase 0 status — bootstrap

This repo currently contains the v0.2.0 baseline copied from `/home/renmark/projects/ai-inference/`, retargeted to the `renmark` package. The five `/renmark:*` skills, the plugin manifest, and the multi-LLM dispatch layer are Phase 1 work.

## Install

```bash
cd /home/renmark/projects/ai-system
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # then put your NVIDIA NIM key in .env
bash install.sh                  # symlinks plugin/ + bin/renmark-execute globally
```

`install.sh` does three things:

1. Backs up any existing `~/.claude/skills/orchestrator/` to `~/.claude/skills/.orchestrator.bak/`
2. Symlinks `plugin/` → `~/.claude/plugins/renmark/`
3. Symlinks `bin/renmark-execute` → `~/.local/bin/renmark-execute`

After install, the new `/renmark:*` skills appear in Claude Code's skill list; the old `/orchestrator` is removed (source code still in `/home/renmark/projects/ai-inference/`).

## Zero permission prompts (recommended)

For non-auto-mode use, paste this into the target project's `.claude/settings.local.json` to pre-approve the renmark-execute command pattern. After this, Claude Code never prompts when the orchestrate skill shells out.

```json
{
  "permissions": {
    "Bash": {
      "allow": [
        "renmark-execute *",
        "git status",
        "git log *",
        "git diff *"
      ]
    }
  }
}
```

(Adjust the path patterns to taste. The renmark-execute pattern covers all `--dry-run`, `--resume`, `--usage`, `--roadmap`, `--logs`, `--no-commit` variants.)

## Five skills

| Command | What it does |
|---|---|
| `/renmark:brainstorm <topic>` | One-question-at-a-time spec discovery; bootstraps fresh projects (creates `CLAUDE.md`, `AGENTS.md`, `.renmark/`) |
| `/renmark:plan <spec>` | Decomposes into atomic single-file tasks; auto-routes each to nim/codex/opus/sonnet based on complexity; emits cost preview |
| `/renmark:orchestrate <plan>` | Wave-based parallel dispatch; tasks in same `parallel_group` run concurrently; serial commits per wave |
| `/renmark:debug <symptom>` | Systematic reproduce → hypothesize → investigate → fix loop with persistent debug session state |
| `/renmark:codereview <ref>` | Multi-pass review (codex adversarial → sonnet quality → opus architecture on hot files) |

## See also

- `PLAN.md` — full implementation plan
- `CHANGELOG.md` — what landed in each version
- `.env.example` — all config knobs

## What's NOT here yet (Phase 1+)

- The five skill SKILL.md files
- `plugin/plugin.json` manifest
- `renmark/dispatch.py` (wave-based parallel dispatcher)
- `renmark/memory.py` (`.renmark/memory/` reader/writer)
- `renmark/providers/claude_agent.py` (opus/sonnet Agent-tool helper)
- Empty-folder bootstrap logic
- Cost preview in dry-run
- `install.sh`

Phase 0 (this commit) is just the working baseline ready for Phase 1 to build on.
