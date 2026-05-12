# Memory index

Renmark's persistent project memory. Each file follows a documented format and is updated by specific commands. Load this index first; fetch the rest on demand.

## Files

| File | What it documents | Auto-updated by |
|---|---|---|
| `project.md` | What this project is — purpose, scope, audience | `/renmark:brainstorm` |
| `stack.md` | Languages, frameworks, deps, runtime requirements | `/renmark:brainstorm`, `/renmark:orchestrate` (on new deps) |
| `architecture.md` | Components, data flow, module boundaries | `/renmark:brainstorm`, `/renmark:plan` |
| `features.md` | Shipped, in-progress, and planned features | `/renmark:orchestrate` (on task pass) |
| `bugs.md` | Open + fixed bugs, with root causes | `/renmark:debug`, `/renmark:codereview`, `/renmark:orchestrate` |
| `decisions.md` | ADR-style architectural decisions | `/renmark:brainstorm`, `/renmark:plan`, hand-edited |
| `conventions.md` | Code, test, commit conventions | hand-edited (skills read but don't write) |
| `routing.md` | Which executor for which task signature | `/renmark:orchestrate` (auto) |
| `learnings.md` | Cross-run patterns (failure modes, cost surprises) | `/renmark:debug`, `/renmark:orchestrate` (auto) |

## Counts

(Auto-maintained — currently zero entries everywhere.)

- features: 0 shipped, 0 in-progress, 0 planned
- bugs: 0 open, 0 fixed
- decisions: 0 ADRs
- routing entries: 0 learned overrides

## Conventions

- All files are newest-first (CHANGELOG.md style). New entries go at the top of their section.
- Each entry has an explicit date (`YYYY-MM-DD`).
- Skills append; they do not rewrite history. Hand-edit if needed.
- Files are committed to git — `.renmark/state/`, `.renmark/debug/`, and `.renmark/logs/` are gitignored; `memory/` is preserved.

## Other `.renmark/` dirs (not memory)

- `.renmark/specs/` — `/renmark:brainstorm` output (committed)
- `.renmark/plans/` — `/renmark:plan` output (committed)
- `.renmark/reviews/` — `/renmark:codereview` output (committed)
- `.renmark/state/` — runtime: usage ledger, pause file, escalations (gitignored)
- `.renmark/debug/` — debug session state (gitignored)
- `.renmark/logs/` — per-invocation logs for troubleshooting (gitignored, list via `renmark-execute --logs`)
