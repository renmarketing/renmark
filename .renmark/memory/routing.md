# Routing memory

Auto-maintained by `/renmark:orchestrate`. Records which executor worked best for which task signature.

## Format

Each entry (as written by `renmark.memory.append_routing`):

```
- (YYYY-MM-DD) `<signature>` → **<executor>** (<outcome>, run=<run-id>)
```

Example: `- (2026-06-09) \`target=tests/**, complexity=medium, mode=A\` → **codex** (passed, run=20260609-190829-757f)`

When entries conflict for the same signature, the newest dated entry wins.

## Defaults (until experience accumulates)

- (target=`.gitignore`, complexity=simple) → haiku
- (target=`*.css`, complexity=simple) → haiku
- (target=`*.json`, complexity=simple) → haiku
- (target=`tests/**`) → codex
- (signal=canvas|DOM|state-machine|coord-math|threading) → opus
- (signal=ideation|strategy-synthesis|adversarial-audit|refutation-pass, stakes=highest) → fable (escalation only — REQ-2)
- (complexity=medium, refactor) → sonnet

## Learned overrides

- (2026-06-11) `target=tests/**, complexity=medium, mode=B` → **codex** (passed, run=20260611-142135-bcc2)

- (2026-06-09) `target=tests/**, complexity=medium, mode=A` → **codex** (passed, run=20260609-190829-757f)

- (2026-06-09) `target=renmark/loop.py (state machine, complexity=hard, mode=A)` → **opus** (passed (1-shot, thorough API; no codereview findings yet), run=loop-mode)

- (2026-06-08) `target=renmark/modularity.py (ast metric analyzer, complexity=hard, mode=A)` → **opus** (passed (1-shot, thorough; 21 tests green; no codereview findings yet), run=modularity-health-lens)

- (2026-06-08) `target=renmark/sizing.py (deterministic heuristic classifier, complexity=hard, mode=A)` → **opus** (passed (1-shot, thorough API; no codereview findings yet), run=proportional-pipeline)

- (2026-06-08) `target=plugin/templates|skills/*.md (doc/contract edits, mode=B)` → **haiku+sonnet** (passed (2/2, format aligned across files via shared spec), run=acceptance-criteria)

- (2026-06-08) `target=renmark/init.py, complexity=hard, mode=B (scaffold+marker-merge, correctness-critical)` → **opus** (passed (1-shot, no codereview findings yet), run=init-pipeline)

- (2026-06-08) `target=_shared/*.md contract + renmark/*.py helper+lint, complexity=medium/hard, mode=A/B` → **sonnet** (passed (8/8, no regressions in own verifiers), run=next-step-engine)

- (2026-06-08) `target=plugin/skills/**/SKILL.md, complexity=simple, mode=B (citation refit)` → **haiku** (passed (13/13 refits, 1-shot), run=next-step-engine)

- (2026-06-05) `target=tests/**, complexity=medium, mode=A` → **sonnet** (passed (escalated from codex read-only failure))

- (2026-06-05) `target=tests/**, complexity=medium, mode=B` → **codex** (passed, run=20260605-145814-f2fe)

- (2026-06-04) `target=tests/**, complexity=medium, mode=A` → **codex** (passed, run=20260604-183746-05fd)

- (2026-05-29) `target=tests/**, complexity=medium, mode=B` → **codex** (failed, run=20260529-155804-f7e2)

- (2026-05-29) `target=tests/**, complexity=hard, mode=B` → **codex** (passed, run=20260529-155804-f7e2)

- (2026-05-28) `target=*.toml, complexity=medium, mode=B` → **codex** (failed, run=20260528-210652-36fc)

(Empty — will fill as runs complete.)
