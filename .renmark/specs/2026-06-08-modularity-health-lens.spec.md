---
artifact_type: spec
schema_version: 1
created_at: 2026-06-08
source_sha: TBD
generator: brainstorm
related_plan: TBD
dependency_refs:
  - .renmark/research/2026-06-08-modularity-health-lens.research.md
  - PRD.md
  - renmark/init.py        # existing standards-health pipeline (reuse)
  - renmark/sizing.py      # constants + never-raise style to mirror
status: draft
---

# Spec — modularity-health-lens (advisory code-health gaps)

## Context

renmark enforces modularity at **plan time** (one-file-per-task, no mode C) but
never **measures** it on the shipped codebase — `init`'s standards-health flags
missing linter/types/tests/CI, never oversized files / god-objects / coupling.
This adds an ADVISORY, deterministic, zero-LLM, **stdlib-`ast`-only** lens that
surfaces those gaps through the existing standards-health mechanism.

Research (see artifact): mirror established defaults (pylint, mccabe, radon,
SonarQube); suppress known false-positives; the parsing layer is **net-new**
(`init` uses regex, `sizing` only reads `git --stat`) but everything downstream —
the `Gap` dataclass, `evaluate_health`, `dev-standards.md` render, the `HEALTH:`
stdout line — is REUSED. PRD alignment: **aligned** (same advisory-gap pattern
`init` ships; REQ-7 quality; no new dep; never auto-refactors).

## Goals

1. `python -m renmark.init` surfaces modularity/scalability health gaps alongside
   the existing standards-health gaps — **advisory, never blocking, never
   auto-refactors**.
2. Deterministic + zero-LLM + **no new runtime deps** (pure `ast` + stdlib).
3. Low false-positive: tests/generated/`__init__` and data/config suppressed;
   count code lines, not raw.
4. Tunable thresholds as documented constants; never raises (degrade to "no gaps
   reported" on any parse failure — same safety posture as `sizing.py`).

## Non-goals (feature-scoped)

- Blocking the pipeline / auto-refactoring / rewriting code.
- A separate `/renmark:hygiene` surface (rides `init` standards-health only).
- Cross-tool deps (radon/wily/pylint) — implement a stdlib `ast` subset.
- Cross-file maintainability-index / true cognitive-complexity parity — ship a
  faithful `ast`-feasible approximation.

## Architecture

**New `renmark/modularity.py`** — pure-`ast`, zero-dep, never-raise analyzer
(mirror `sizing.py`: module constants, defensive, returns data not prose):
- Walks Python source files (reuse `init`'s source-file walker / exclusion set if
  present; else stdlib `pathlib` with the same excludes).
- Per file / per function computes the **5 metrics**, each with two bands
  (warn / major) from tunable constants:

  | Metric | warn | major | source |
  |---|---|---|---|
  | module LOC (code lines) | 500 | 1000 | pylint `max-module-lines` |
  | function length (LOC) | 50 | 100 | common |
  | cyclomatic branch count / fn | 10 | 20 | mccabe |
  | import fan-out / module | 15 | 25 | tunable |
  | cognitive complexity / fn (nesting-weighted) | 15 | 30 | SonarQube |

- **False-positive suppression:** skip `tests/`, generated markers, `__init__.py`
  for the fan-out metric, dataclass/Enum field-count effects; count code lines
  (exclude blanks/comments/docstrings).
- Returns a list of findings in the shape `init`'s standards-health expects (a
  `Gap` — reuse `init`'s `Gap` dataclass; do NOT invent a parallel shape).
- `analyze(repo) -> list[Gap]` (or equivalent) — never raises; on any per-file
  parse error, skip that file and continue.

**`renmark/init.py` wiring** — call `modularity.analyze(repo)` inside the existing
`evaluate_health` flow; merge its `Gap`s into the standards-health gap list so
they render in `dev-standards.md` and count toward the `HEALTH:` stdout line.
Additive only — do not alter existing standards-health detectors.

**`init/SKILL.md`** — one line noting init's health report now includes advisory
modularity/scalability gaps (oversized files, long/complex functions, coupling).

## Data flow

```
python -m renmark.init
  → evaluate_health(repo):
      existing detectors (linter/types/tests/CI...) → Gaps
      + modularity.analyze(repo) → Gaps   (5 ast metrics, FP-suppressed, never-raise)
  → write_standards_md (renders all Gaps) + "HEALTH: <n gaps>" stdout line
  (advisory only — init still exits 0; nothing blocks)
```

## Error handling / edge cases

- Unparseable / syntax-error file → skipped (never raises); analysis continues.
- Non-Python repo / no source files → zero modularity gaps (clean), no error.
- A file legitimately above threshold (e.g. a big generated/data module) →
  suppressed by the exclusion rules; document how to exclude.
- `__init__.py` re-export fan-out → excluded from the fan-out metric.
- Thresholds tunable via constants; advisory bands never escalate to a hard fail.

## Success criteria

- `python -m renmark.init` on this repo reports modularity gaps (if any) in the
  `HEALTH:` line + `dev-standards.md`, and still exits 0 (advisory).
- All 5 metrics computed via `ast` with no third-party import; suppression rules
  keep tests/generated/`__init__` out of the noise.
- `modularity.analyze` is pure + never raises (parse-error file skipped) —
  unit-tested at each metric's warn/major boundary + the suppression cases.
- `pytest -q`, `ruff`, `mypy`, `lint_all` green; no new dependency in pyproject.

## Prior art & references

- Research artifact: `.renmark/research/2026-06-08-modularity-health-lens.research.md`
  (external metric/threshold table + sources; FP list; stdlib-`ast` feasibility;
  internal reuse map).
- Reuse: `renmark/init.py` (`Gap`, `evaluate_health`, `write_standards_md`,
  `HEALTH:` line, source-file walker); `renmark/sizing.py` (tunable-constants +
  never-raise style). Build new: the `ast` metric walker.
