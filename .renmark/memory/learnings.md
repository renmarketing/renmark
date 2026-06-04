# Learnings

Auto-maintained by `/renmark:orchestrate` and `/renmark:debug`. Records patterns learned from past runs.

## Format

Each entry: signal, observation, model that caught it, date.

## Common patterns (seeded from prior projects)

- `tests/**.py with threading + setUpClass` — NIM small models often produce invalid Python here. Route to `codex` or `opus`.
- `.js with canvas/DOM API` — NIM small models often write code that crashes at runtime (e.g., `document.canvas.width`). Route to `opus`.
- Codex with `--sandbox workspace-write` will sometimes modify files outside the target — verify with a post-run lane check.

## Learned this project








- (2026-06-04, bug) **/renmark:feature does not write feature identity to lifecycle.json** — Any pipeline-entry skill that establishes a new work unit must persist that unit's IDENTITY (not just its stage) to canonical state at entry, or downstream stage writes silently inherit stale identity.

- (2026-06-04, .renmark/reviews/2026-06-04-fa745b3bb080ce31e5e7de15f2e59e98a1790671.verification.md) model `verify`: **verify-verify-browser-qa-v2** — Dual browser-channel selection (MCP default / native claude --chrome on Windows app; WSL forces MCP) added on same branch; lint+anchors+pytest green.

- (2026-06-04, .renmark/reviews/2026-06-04-0959d69ca675a6c468246c853153734baec7bb45.verification.md) model `verify`: **verify-verify-browser-qa** — 7/7 smoke behaviors verified for the SKILL.md refinement; pytest 335 passed; no regressions. Anchor-based smoke fits prompt-only features.

- (2026-06-04, .renmark/plans/2026-06-04-verify-browser-qa.plan.md) model `opus`: **orchestrate-verify-browser-qa** — Single-file SKILL.md prompt refinement, opus executor. Verifier anchor 'overlap' was too weak (pre-existed in unrelated 'files overlap' text) — tightened to 'overlapping interactive elements' pre-dispatch so the verifier actually gates new work.

- (2026-05-29, run) **task 5 failed on codex** — codex_verifier_failed

- (2026-05-29, .renmark/reviews/2026-05-29-729e0ca.verification.md) model `verify`: **verify-lifecycle-hygiene** — 6/6 behaviors verified; failed: none; regressions: 0

- (2026-05-28, run) **task 1 failed on codex** — codex_verifier_failed

(Empty — will fill as runs complete.)
