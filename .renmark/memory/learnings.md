# Learnings

Auto-maintained by `/renmark:orchestrate` and `/renmark:debug`. Records patterns learned from past runs.

## Format

Each entry: signal, observation, model that caught it, date.

## Common patterns (seeded from prior projects)

- `tests/**.py with threading + setUpClass` — NIM small models often produce invalid Python here. Route to `codex` or `opus`.
- `.js with canvas/DOM API` — NIM small models often write code that crashes at runtime (e.g., `document.canvas.width`). Route to `opus`.
- Codex with `--sandbox workspace-write` will sometimes modify files outside the target — verify with a post-run lane check.

## Learned this project














- (2026-06-05, bug) **pre-existing: 3 integration tests fail under RENMARK_SMOKE=1** — Integration tests gate on RENMARK_SMOKE=1 and were not being exercised; surfaced during PRD verify. Track and fix independently.

- (2026-06-05, .renmark/reviews/2026-06-05-ebf06f951e88958c0e4d005d15da87cbb5e7843a.verification.md) model `verify`: **verify-prd-source-of-truth** — 6/6 behaviors verified; 0 new regressions; fixed _shared parity test; 3 pre-existing integration failures remain (cold_start_with_pending_approval, cold_start_recovers_at_every_stage, human_approval_gate_blocks_progression) under RENMARK_SMOKE=1, unrelated to PRD work.

- (2026-06-05, orchestrate) **test_commands_directory_complete + _shared/ dir** — Parity test treated every plugin/skills/ subdir as a skill needing a command; _shared/ broke it under RENMARK_SMOKE=1. Pre-existing; fixed by excluding underscore-prefixed dirs. Run integration tests with RENMARK_SMOKE=1 — they skip by default and hide real failures.

- (2026-06-05, orchestrate) model `haiku`: **parallel mirror-pair edits (CLAUDE.md.template + AGENTS.md.template)** — A task scoped to one file edited BOTH mirror files; resolved benignly (idempotent insert, no dup) but for mirror pairs prefer one task owning both files or sequential dispatch.

- (2026-06-04, .renmark/reviews/2026-06-04-eb5ce2d.verification.md) model `verify`: **verify-qa-flow-memory** — 7/7 behaviors verified; failed: none; full suite 343 passed/0 failed (+6 new tests).

- (2026-06-04, orchestrate run 20260604-qa-flow-memory) **mixed-executor plan, lone codex task in wave 2** — Dispatch a single codex task via a one-task plan + `renmark-execute --no-commit`. The ad-hoc `--task` mode forces YAML-frontmatter artifact format, which corrupts .py source targets; the normal plan path (run_codex_task) edits the source file directly.

- (2026-06-04, bug) **/renmark:feature does not write feature identity to lifecycle.json** — Any pipeline-entry skill that establishes a new work unit must persist that unit's IDENTITY (not just its stage) to canonical state at entry, or downstream stage writes silently inherit stale identity.

- (2026-06-04, .renmark/reviews/2026-06-04-fa745b3bb080ce31e5e7de15f2e59e98a1790671.verification.md) model `verify`: **verify-verify-browser-qa-v2** — Dual browser-channel selection (MCP default / native claude --chrome on Windows app; WSL forces MCP) added on same branch; lint+anchors+pytest green.

- (2026-06-04, .renmark/reviews/2026-06-04-0959d69ca675a6c468246c853153734baec7bb45.verification.md) model `verify`: **verify-verify-browser-qa** — 7/7 smoke behaviors verified for the SKILL.md refinement; pytest 335 passed; no regressions. Anchor-based smoke fits prompt-only features.

- (2026-06-04, .renmark/plans/2026-06-04-verify-browser-qa.plan.md) model `opus`: **orchestrate-verify-browser-qa** — Single-file SKILL.md prompt refinement, opus executor. Verifier anchor 'overlap' was too weak (pre-existed in unrelated 'files overlap' text) — tightened to 'overlapping interactive elements' pre-dispatch so the verifier actually gates new work.

- (2026-05-29, run) **task 5 failed on codex** — codex_verifier_failed

- (2026-05-29, .renmark/reviews/2026-05-29-729e0ca.verification.md) model `verify`: **verify-lifecycle-hygiene** — 6/6 behaviors verified; failed: none; regressions: 0

- (2026-05-28, run) **task 1 failed on codex** — codex_verifier_failed

(Empty — will fill as runs complete.)
