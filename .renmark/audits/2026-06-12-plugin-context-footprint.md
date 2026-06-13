---
artifact_type: audit
schema_version: 1
created_at: 2026-06-12
generator: claude
related: plugin context-window footprint
---

# renmark plugin — context footprint audit (2026-06-12)

## Always-loaded per Claude Code session (~8.5k tok)

| Source | Tokens | Note |
|---|---|---|
| `CLAUDE.md` | ~3,450 | was ~7,200 pre-slim (claude-doc-slimming halved it) |
| 26 skill descriptions | ~2,660 | SKILL frontmatter, every skill, every session |
| 26 command descriptions | ~2,440 | largely DUPLICATES the skill descriptions |

`AGENTS.md` (~3,180) is NOT loaded by Claude Code (Codex/other-agent surface).
Heaviest skill descriptions: codereview 194, backlog 177, blueprint 176, prd 175, loop 162, init 152 tok.

## On-demand (only when a skill is invoked; not per-session)

SKILL bodies total ~78k across 26 skills. Heaviest: verify 10.4k, prd 5.6k, orchestrate 5.6k, finish 4.6k, codereview 4.2k, brainstorm 4.1k.

## Optimization levers (ranked)

1. **De-dup command vs skill descriptions (~2k always-on)** — biggest single win; command shims mirror skill descriptions. Trim shims to one-line pointers. Risk: command desc is slash-command help text.
2. **Trim 6 verbose skill descriptions** (>150 tok → ~80) → ~500-700 tok. Risk: descriptions drive auto-invocation routing.
3. **Slim heavy SKILL bodies** (verify 10.4k esp.) — on-demand only.
4. **Further CLAUDE.md cuts** (two-tier governance doc) — diminishing returns; defer.
5. **Meta:** add a context-footprint lens to `/renmark:audit` so this is repeatable.
