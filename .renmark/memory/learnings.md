# Learnings

Auto-maintained by `/renmark:orchestrate` and `/renmark:debug`. Records patterns learned from past runs.

## Format

Each entry: signal, observation, model that caught it, date.

## Common patterns (seeded from prior projects)

- `tests/**.py with threading + setUpClass` — NIM small models often produce invalid Python here. Route to `codex` or `opus`.
- `.js with canvas/DOM API` — NIM small models often write code that crashes at runtime (e.g., `document.canvas.width`). Route to `opus`.
- Codex with `--sandbox workspace-write` will sometimes modify files outside the target — verify with a post-run lane check.

## Learned this project





- (2026-06-04, .renmark/plans/2026-06-04-verify-browser-qa.plan.md) model `opus`: **orchestrate-verify-browser-qa** — Single-file SKILL.md prompt refinement, opus executor. Verifier anchor 'overlap' was too weak (pre-existed in unrelated 'files overlap' text) — tightened to 'overlapping interactive elements' pre-dispatch so the verifier actually gates new work.

- (2026-05-29, run) **task 5 failed on codex** — codex_verifier_failed

- (2026-05-29, .renmark/reviews/2026-05-29-729e0ca.verification.md) model `verify`: **verify-lifecycle-hygiene** — 6/6 behaviors verified; failed: none; regressions: 0

- (2026-05-28, run) **task 1 failed on codex** — codex_verifier_failed

(Empty — will fill as runs complete.)
