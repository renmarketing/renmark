---
artifact_type: spec
schema_version: 1
created_at: 2026-06-08
source_sha: TBD
generator: brainstorm
related_plan: TBD
dependency_refs:
  - PRD.md
  - .renmark/memory/decisions.md  # cost-efficiency ADR (C+A first, B deferred)
  - plugin/skills/feature/SKILL.md
  - plugin/skills/codereview/SKILL.md
  - renmark/parser.py
status: draft
---

# Spec — proportional-pipeline (C+A): pipeline cost ∝ feature size/risk

## Context

renmark pays a **fixed pipeline toll per feature regardless of size**. Measured
this session: a 2-task feature cost ~340k tokens, ~40% of it a single codex
codereview (~120–160k, real from logs) run once per feature no matter how small.
The user ships a steady stream of tiny features and (rightly) flagged that the
overhead dwarfs the work.

Decision (ADR this session): build **C+A** now — make cost proportional to
size/risk — and defer **B** (roadmap-batch) + the modularity lens. Basis:
proportionality + automatic per-feature savings + lowest risk + preserves the
per-feature isolation/review that caught real bugs this session. PRD alignment:
**aligned** (REQ-2 cost-appropriate; REQ-7 untouched — verify still runs and
codereview ≠ the verify gate; commit-to-main already sanctioned by single-branch-rule).

## Goals

1. Small/doc features are cheap by **default**, with no behavior change required.
2. Cost tracks **risk/size**, not feature-count: heavy stages (full codex review,
   branch/PR/release) run only when the change warrants them.
3. **Never blind, never silent:** a review always runs (cheap by default,
   escalate on demand); the chosen tier + rationale is always surfaced; the user
   can override either way in one keystroke.
4. Mandatory regardless of tier: **plan validation + goal-backward verify** (REQ-7).

## Non-goals (feature-scoped)

- Roadmap-batch execution (B) — deferred (next feature).
- Modularity health lens — deferred.
- Compressing the *variable* subagent floor (not spawning subagents for trivial
  edits) — noted as a future micro-lever, out of scope here.
- New runtime deps (stdlib + markdown only).

## Architecture

**1. `renmark/sizing.py` — deterministic, zero-LLM classifier (single source of truth).**
- `classify_plan(tasks) -> Tier` and `classify_diff(repo, range) -> Tier`, where
  `Tier ∈ {lite, standard, full}`.
- Signals (reuse what exists — parser `Task.complexity/mode/target/est_tokens`,
  task count, git diff stat):
  - any `complexity: hard` → never `lite` (≥ standard).
  - target file types: all docs/config (`.md`, `.txt`, `.json`, `.toml`,
    `.gitignore`, templates) → doc-leaning; any code (`.py`, etc.) → code-leaning.
  - task count + est diff size (lines changed) → thresholds.
- Tiers (thresholds as documented module constants, tunable):
  - **lite:** ≤3 tasks, no `hard`, doc/config-dominant **or** very small code diff.
  - **standard:** moderate code change.
  - **full:** `hard` present, many tasks, core-module edits, or large diff.
- Pure, testable, never raises (degrades to `standard` — the safe middle — on any
  uncertainty).

**2. Size-tier lite lane (feature router).** On `tier == lite`:
- skip brainstorm (already optional); **plan (+validate — ALWAYS)**; orchestrate;
  **verify (ALWAYS — REQ-7)**; **proportional codereview** (below); then land on
  **`main`** without PR/codex/release ceremony (per single-branch-rule).
- *Mechanism note:* classification needs the validated plan, so the lane decision
  (branch-vs-main, lite-vs-full finish) is made **after plan-validated**. For lite,
  the work lands on `main` (no feature branch / no PR / no release); standard/full
  keep the existing branch → PR/merge → (optional) release flow. Plan/execution
  decides the cleanest implementation (classify-before-branch, or branch then
  fast-forward main on lite finish) — behavior is what matters: lite lands on main
  cheaply.
- **standard/full:** the full pipeline, unchanged.

**3. Proportional codereview (`codereview/SKILL.md` + sizing).** codereview runs
`classify_diff` on the range:
- **lite/doc diff → built-in cheap `/review` by default** (~10–25k, in-context;
  catches obvious + cross-file/consistency bugs), then offer a **one-keystroke
  escalate to full codex**. Never silently skipped.
- **standard/full → full codex review** (current behavior).
- Flags: `--full` forces codex; `--skip` skips entirely (explicit). The diff tier
  + which review will run is stated before running.

**4. Transparency + override.** The classified tier, the stages that will run, and
the est-token band show up in the feature/orchestrate **cost preview**. Overrides:
`/renmark:feature <name> --full|--lite`; `/renmark:codereview --full|--skip`.

## Data flow

```
/renmark:feature <name>
  → plan (+validate, ALWAYS)
  → sizing.classify_plan(tasks) → tier {lite|standard|full}   (deterministic, shown in cost preview)
  → lite:     orchestrate → verify(ALWAYS) → cheap /review (+escalate) → land on main (no PR/codex/release)
     standard/full: branch → orchestrate → verify → full codex codereview → finish (PR/merge/release)
  → --full/--lite overrides the tier; tier + rationale always surfaced
```

## Error handling / edge cases

- Classifier uncertainty / unreadable signals → default to **standard** (safe
  middle), never `lite` by accident.
- A `hard` task or core-module (`renmark/*.py`, lifecycle/parser/dispatch) edit
  forces ≥ standard even if small (risk, not just size).
- `--full`/`--lite` always win over the heuristic (explicit > inferred).
- Lite lane still runs **verify** and **plan validation** — those never skip.
- Escalate-to-codex remains available after the cheap review on any tier.

## Success criteria

- A tiny/doc feature runs the lite lane by default: cheap review, lands on main,
  **no ~130k codex pass** — token use drops from ~HIGH to ~LOW–MED, *demonstrated*.
- A `hard`/core-code/large-diff feature still gets the full pipeline + full codex.
- `--full` on a tiny feature forces the full pipeline; `--lite` forces lite;
  `--full`/`--skip` on codereview behave as documented. No silent skips.
- `sizing.classify_*` is pure + stdlib + unit-tested at the tier boundaries
  (doc-vs-code, hard-task bump, task-count/diff thresholds, uncertainty→standard).
- `pytest -q`, `ruff`, `mypy`, `lint_all` all green.

## Prior art & references

- This session's cost evidence (no separate research artifact — gathered inline):
  codereview logs (~120–160k codex/feature), subagent token observations.
- Reuse: `renmark/parser.py` (`Task` fields, complexity), the existing
  `single-branch-rule` (commit-to-main for small changes), the built-in
  `code-review`/`/review` skill (cheap lane), `codereview/SKILL.md` `--focus` arg
  pattern (add `--full`/`--skip`).
- Decision basis (4 axes: proportionality / automatic / risk+isolation / build
  cost) + deferral of B — `.renmark/memory/decisions.md`.
