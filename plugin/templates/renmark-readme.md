# .renmark/

Persistent project memory + runtime state for the renmark plugin.

## Committed (preserved across sessions)

- `memory/` — INDEX, project facts, conventions, decisions, learnings, routing
- `specs/` — designs from `/renmark:brainstorm`
- `plans/` — task plans from `/renmark:plan`
- `reviews/` — review outputs from `/renmark:codereview`

## Gitignored (regenerable)

- `state/` — runtime: usage ledger, pause file, escalation artifacts
- `debug/` — debug session state from `/renmark:debug`

Renmark commands read `.renmark/memory/INDEX.md` first, then fetch other files on demand. This keeps Opus context lean while preserving project knowledge across sessions.
