# Routing memory

Auto-maintained by `/renmark:orchestrate`. Records which executor worked best for which task signature.

## Format

Each entry: `(signal) → executor, confidence, last-confirmed-on, sample-size`

## Defaults (until experience accumulates)

- (target=`.gitignore`, complexity=simple) → nim
- (target=`*.css`, complexity=simple) → nim
- (target=`*.json`, complexity=simple) → nim
- (target=`tests/**`) → codex
- (signal=canvas|DOM|state-machine|coord-math|threading) → opus
- (complexity=medium, refactor) → sonnet

## Learned overrides









- (2026-06-08) `target=_shared/*.md contract + renmark/*.py helper+lint, complexity=medium/hard, mode=A/B` → **sonnet** (passed (8/8, no regressions in own verifiers), run=next-step-engine)

- (2026-06-08) `target=plugin/skills/**/SKILL.md, complexity=simple, mode=B (citation refit)` → **haiku** (passed (13/13 refits, 1-shot), run=next-step-engine)

- (2026-06-05) `target=tests/**, complexity=medium, mode=A` → **sonnet** (passed (escalated from codex read-only failure))

- (2026-06-05) `target=tests/**, complexity=medium, mode=B` → **codex** (passed, run=20260605-145814-f2fe)

- (2026-06-04) `target=tests/**, complexity=medium, mode=A` → **codex** (passed, run=20260604-183746-05fd)

- (2026-05-29) `target=tests/**, complexity=medium, mode=B` → **codex** (failed, run=20260529-155804-f7e2)

- (2026-05-29) `target=tests/**, complexity=hard, mode=B` → **codex** (passed, run=20260529-155804-f7e2)

- (2026-05-28) `target=*.toml, complexity=medium, mode=B` → **codex** (failed, run=20260528-210652-36fc)

(Empty — will fill as runs complete.)
