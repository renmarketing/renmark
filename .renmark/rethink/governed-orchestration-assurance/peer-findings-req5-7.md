---
artifact_type: rethink-survey-supplement
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source: cross-session peer report (unsolicited agent-message, not a dispatched stage subagent of this run)
related_plan: .renmark/rethink/governed-orchestration-assurance/intake.md
generator: peer-session
---

# Peer-supplied evidence — Requirements 5, 6, 7 (risk-tiered InspectionContract, calibrated judge, failure-rule registry)

Received from another Claude session mid-run, not dispatched by this pipeline.
Content appears evidence-grounded (file:line citations, test names) and is
folded in here as supplementary survey input for Stage 1/Stage 6 — it does
NOT replace this run's own dispatched Stage 1 survey and must be
cross-checked against that artifact once it lands, not accepted uncritically.

## Requirement 5 — risk-tiered InspectionContract + falsification lenses

- R-0.4 Inspector (RELEASED v0.39.7) has two mechanisms:
  (a) deterministic default — `renmark/cli/_engine.py:762-766` reruns
  `run_verifier` independently of the Worker's own run
  (`renmark/cli/_codex_runner.py:644`); verdict sourced from the fresh
  rerun (`_emit_inspection_verdict`, lines 767-777), non-circularity
  confirmed by
  `tests/test_ledger_wiring.py::test_inspection_verdict_derived_from_independent_rerun_not_worker_ok`.
  (b) optional LLM Inspector — `plugin/agents/inspector.md`: receives only
  WorkOrder+WorkResult+prior Escalation events from the ledger, explicitly
  never the Worker's transcript/reasoning (lines 16-24); returns
  pass|fail|escalate; read-only tools only. `InspectionReport` schema at
  `renmark/ledger.py:135-146`; dispatch-independence enforcement via
  `check_dispatch_independence` (unmodified since `83d7c8f`).
  Closeout: `.renmark/reviews/2026-08-01-r-0.4-wp6b-rereview.md` — PASS,
  F-R0.4-1 resolved. Residual F-R0.4-2 (non-blocking): verifier rerun
  assumes read-only/idempotent commands by convention only, no mechanical
  enforcement — earmarked in that doc for "Milestone 5 (Inspector registry
  + risk-based selection)."
- **Risk-tiering does not exist.** `grep "risk_tier\|InspectionContract"`
  across `renmark/` and `plugin/` — zero hits. No low/medium/high/critical
  mechanism; inspection depth is uniform regardless of change risk.
- **Lens-selection does not exist.** `grep "lens\|lenses"` — only unrelated
  hits (a UI metaphor in `plugin/skills/verify/SKILL.md`;
  `renmark/modularity.py`'s docstring self-describing as a "health lens" —
  one fixed check, not a selectable family). "Adversarial" exists only as a
  routing-tier classification for expensive-model selection
  (`renmark/cost.py:74 _ESCALATION_KINDS`, `renmark/codex_routing.py:49
  HARD_KINDS`, `renmark/plan_lint.py:390`) — one undifferentiated
  adversarial-review kind, not selectable falsification lenses
  (maintainer/compatibility/competitor/skeptical-user etc). Confirmed the
  closed `renmark-architecture` rethink did not touch this area.

## Requirement 6 — calibrated LLM-as-judge

`renmark/judge.py`:
- No rubric freeze/versioning — the "contract" is a free-text string param
  (`judge.py:99`), not a versioned schema.
- Doesn't ingest Worker self-assessment/confidence/identity at all — not
  designed for that use case, so input isolation is incidental, not a
  designed control.
- Two-state only (pass/fail, `judge.py:36`) — not the proposal's required
  three-state pass|fail|uncertain; unparseable/failed responses map to
  fail + `validation_status: unvalidated` as an uncertain-proxy, not a
  first-class outcome.
- Zero bias controls: no different-provider-than-Worker preference, no
  pairwise order randomization, no calibration-against-human-decisions
  loop — single frontier-model call via injectable `subagent_runner`.
- Wholly separate from `ledger.py`'s `InspectionReport`/`inspector.md` — no
  code path connects them.
- `renmark/behavior.py`'s `--judge` path (lines 1109-1135) IS this same
  `judge.py:judge_behavior` — the only judge mechanism in the repo, used
  solely for behavioral-eval regression (skill A/B vs baseline/golden), not
  for grading Worker deliverables against an InspectionContract.

## Requirement 7 — failure-derived constraint registry

- **Does not exist.** `grep "failure_rule\|FR-[0-9]\|constraint_registry"`
  across `renmark/`, `plugin/`, `.renmark/memory` — zero hits.
- Negative prompting is pure accumulating prose: this repo's own `CLAUDE.md`
  (352 lines) contains ~35 distinct must-not/never/do-not occurrences, all
  always-loaded — no applicability-based injection, despite `CLAUDE.md`'s
  own "Context taxonomy" section documenting a static/dynamic/memory/
  task-local split in principle.
- No source-evidence linkage, no regression-test-required-before-activation,
  no dedup/staleness review mechanism.

## Net read for Stage 6 classification

Requirements 5, 6, 7 are **the least-covered** of the proposal's 13 —
R-0.4 gives a real, tested foundation for deterministic + blind-scoped LLM
inspection (partial credit toward Req 5's inspection mechanics), but risk
tiering, lens selection, judge calibration/three-state/bias-controls, and
the failure-rule registry are all **missing**, not partial. This is
meaningfully more greenfield than Requirements 1/3 (work orders, task
tracker) where R-0.2/R-0.3/REQ-31 give substantial existing structure.
