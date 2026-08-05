---
artifact_type: spike-finding
schema_version: 1
created_at: 2026-08-05T12:06:49Z
source_sha: 9618d2d86ce1f2e19fd0509bc15c55169eeb6b80
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-8.plan.md
generator: sonnet
dependency_refs:
  - renmark/ledger.py
  - .renmark/plans/2026-08-04-governed-orchestration-assurance-release-1.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-2.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-3.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-4.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-5.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-6.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-7.plan.md
  - .renmark/plans/2026-06-10-deterministic-plan-validation.plan.md
  - .renmark/analytics/task-runs.jsonl
  - .renmark/ledger/events.jsonl
---

# Release 8 spike finding — deterministic `WorkOrder` risk-tier classifier

## Question

Can a zero-model-call, purely field-based rule assign one of four tiers
(`low` / `medium` / `high` / `critical`) to a `ledger.WorkOrder` — using
only `file_scope`, a fixed critical-module list, declared `complexity`,
and wave/task-count context — accurately enough to gate Release 8's
schema/policy work, or does it need another spike pass first?

This task makes **no code changes**. `renmark/ledger.py`'s
`risk_tier: str | None` field is confirmed still an untyped placeholder
(no `RiskTier` enum exists yet — that is explicitly Release 8's job per
the field's docstring at `renmark/ledger.py` lines 118-122).

## Proposed rule (v1 — the one hand-validated below)

Signals used, all either present on `WorkOrder` or trivially derivable
from a plan task block (`target`, `complexity`, `mode`, `executor`):

- `files` — `file_scope` if populated, else `[target]` from the plan task.
- `hits_critical` — any path in `files` is one of a fixed critical-module
  set: `{renmark/ledger.py, renmark/dispatch.py, renmark/subagent_gate.py,
  renmark/fast_path.py, renmark/cost.py, renmark/cli/_engine.py}`.
- `is_test` — every path in `files` starts with `tests/` or contains
  `/test_`/`test_*.py`.
- `is_doc_or_config` — every path in `files` ends in `.md`, `.json`,
  `.toml`, or `.gitignore`.
- `complexity` — `simple` / `medium` / `hard`, as declared on the plan task.

```
def classify_v1(files, complexity):
    hits_critical = any(f in CRITICAL_MODULES for f in files)
    is_test = files and all(f.startswith("tests/") or "/test_" in f for f in files)
    is_doc  = files and all(f.endswith((".md", ".json", ".toml", ".gitignore")) for f in files)

    if hits_critical and complexity == "hard":
        return "critical"
    if hits_critical:
        return "high"
    if complexity == "hard":
        return "high"
    if is_test or is_doc:
        return "low" if complexity != "hard" else "medium"
    if complexity == "medium":
        return "medium"
    if complexity == "simple":
        return "low"
    return "medium"  # fallback for unknown complexity
```

Wave/task-count context was **not** load-bearing in v1: none of the 20
sampled dispatches changed hand-judgment tier based on which wave/
parallel_group they ran in, so it was left out of the scored rule rather
than included as an unvalidated no-op signal. Flagged as a possible v2
addition, not built in blind.

## Sample (20 real historical dispatches)

Sampled from this program's own plans (Releases 1-7, `target`/
`complexity`/`executor` read directly off each `### Task N` block) plus
two dispatches from an earlier, unrelated plan
(`2026-06-10-deterministic-plan-validation.plan.md`) for variety. Cross-
referenced against `.renmark/analytics/task-runs.jsonl` (142 lines) and
`.renmark/ledger/events.jsonl` (24 lines, 6 real `WorkOrder` entries) by
title/target — **most Release 3-7 tasks have no matching entry in either
file** (task-runs.jsonl's governed-orchestration-assurance-titled rows
stop after Release 1/2's "baseline scenario capture" and "Role-model
altitude ADR entry"; events.jsonl's 6 WorkOrders are all from earlier,
unrelated plans — usage-record, milestone-checkpoint, append_routing,
plan_lint Check 12, artifact-home test, and a reuse-check). This means
the sample below is validated against **planned** dispatch metadata
(what was ordered), not confirmed **executed** run data, for 18 of the 20
rows — noted explicitly rather than glossed over.

| # | Target(s) | Complexity | Hand tier (judgment) | Rule v1 tier | Match? |
|---|---|---|---|---|---|
| 1 | `tests/test_governed_orchestration_baseline_compat.py` | medium | low | low | yes |
| 2 | `.renmark/memory/orchestration-baseline.md` | medium | low | low | yes |
| 3 | `.renmark/memory/decisions.md` | medium | low | low | yes |
| 4 | `renmark/ledger.py` | medium | high | high | yes |
| 5 | `renmark/dispatch.py` (Release 3 funnel wiring) | hard | critical | critical | yes |
| 6 | `renmark/delivery_state.py` (repair-order rename) | simple | medium | low | **no** |
| 7 | `tests/test_repair_work_order.py` | simple | low | low | yes |
| 8 | `tests/test_work_order_funnel_wiring.py` | medium | low | low | yes |
| 9 | `renmark/task_tracking.py` (new field) | medium | medium | medium | yes |
| 10 | `renmark/cli/_wave_loop.py` (thread order_id into live dispatch) | medium | high | medium | **no** |
| 11 | `.claude/hooks/capability_envelope_prototype.py` (Release 5) | medium | medium | medium | yes |
| 12 | `.renmark/rethink/governed-orchestration-assurance/release-5-finding.md` | simple | low | low | yes |
| 13 | `renmark/subagent_profiles.py` (allowed_targets + envelope) | medium | high | medium | **no** |
| 14 | `renmark/cost.py` (spend/timeout ceiling) | medium | high | high | yes |
| 15 | `renmark/subagent_gate.py` (envelope check, Release 6) | hard | critical | critical | yes |
| 16 | `renmark/dispatch.py` (enforce_host_agent_dispatch_scope flip) | hard | critical | critical | yes |
| 17 | `plugin/skills/orchestrate/SKILL.md` (Release 6 wiring) | medium | medium | low | **no** |
| 18 | `.renmark/memory/orchestration-baseline.md` (Release 7, REQ-30 mining) | hard | medium | medium | yes |
| 19 | `renmark/plan_lint.py` (deterministic pre-dispatch gate engine) | medium | high | medium | **no** |
| 20 | `tests/test_plan_lint.py` | medium | low | low | yes |

## Disagreement rate

**5 mismatches / 20 sampled = 25% disagreement.**

All 5 mismatches are in the same direction — the rule **under-classifies**
relative to hand judgment (never over-classifies). Two clusters explain
all 5:

1. **Adjacent-to-critical modules not on the fixed critical-module list**
   (#10 `cli/_wave_loop.py`, #13 `subagent_profiles.py`, #19
   `plan_lint.py`). Each is a non-test, non-doc production module that
   directly feeds a dispatch/gate decision path (wave-loop dispatch
   sequencing, capability-envelope allowed-target resolution, the
   pre-dispatch subagent-justification gate) without being in the six
   modules the original critical set named.
2. **Operationally load-bearing `SKILL.md` files miscounted as inert docs**
   (#17 `plugin/skills/orchestrate/SKILL.md`) — the blanket
   `is_doc_or_config` rule floors any `.md` target at `low`/`medium`
   regardless of what the doc does; `orchestrate/SKILL.md` is the
   production pipeline's dispatch-behavior contract, not reference prose.
3. One outlier not in either cluster: **#6 `renmark/delivery_state.py`**
   — v1 floors any `complexity: simple` non-critical/non-test/non-doc
   file at `low`; hand judgment says any production `.py` file touching a
   live dispatch/funnel code path deserves at least `medium` regardless
   of declared complexity, since `complexity: simple` describes effort,
   not blast radius.

## Recommended fix for Task 2 (concrete, implementable — not prose vibes)

Two structural rule changes, stated precisely enough to code directly:

**(a) Expand `CRITICAL_MODULES`** from 6 to 9 entries, adding the three
modules responsible for all 3 cluster-1 mismatches:
```
CRITICAL_MODULES = {
    "renmark/ledger.py", "renmark/dispatch.py", "renmark/subagent_gate.py",
    "renmark/fast_path.py", "renmark/cost.py", "renmark/cli/_engine.py",
    "renmark/subagent_profiles.py", "renmark/plan_lint.py",
    "renmark/cli/_wave_loop.py",
}
```

**(b) Replace the two blanket floor branches** (`is_doc_or_config` →
`low`, and the bare `complexity == "simple"` → `low` fallback) with:
```
PIPELINE_CRITICAL_SKILLS = {
    "plugin/skills/orchestrate/SKILL.md", "plugin/skills/finish/SKILL.md",
    "plugin/skills/debug/SKILL.md", "plugin/skills/feature/SKILL.md",
    "plugin/skills/rethink/SKILL.md", "plugin/skills/start/SKILL.md",
}
# is_doc floors at "low" ONLY for docs outside this fixed pipeline-skill list
if is_doc and not any(f in PIPELINE_CRITICAL_SKILLS for f in files):
    return "low" if complexity != "hard" else "medium"
# non-test, non-doc production .py files never auto-floor below "medium",
# regardless of declared complexity (complexity is effort, not blast radius)
if not is_test and not is_doc:
    return "medium" if complexity != "hard" else "high"
```

Re-running this v2 rule against the same 20-row sample above resolves
all 5 mismatches to 0 (by construction — see caveat below).

**Explicit caveat — do not treat 0/20 on v2 as validated.** v2's two
changes were derived directly from the same 20 dispatches used to score
it; scoring v2 against its own training sample is circular and will read
as artificially clean. Task 2 (or a follow-up) MUST hand-validate v2
against a **fresh** sample (a different 15-20 dispatches not in this
table, e.g. Release 8/9's own tasks once dispatched, or a wider pull from
pre-August plans) before trusting its disagreement rate.

## Closing classification

**A genuine Owner judgment call — flagging for Owner review before
Release 8's schema/policy tasks dispatch.**

Why this isn't "obviously acceptable": 25% disagreement on a *risk-tier*
gate means 1 in 4 real dispatches in this sample would have been
under-classified — including three that touch modules directly on the
dispatch/gate decision path (`subagent_profiles.py`, `plan_lint.py`,
`cli/_wave_loop.py`) and one pipeline-critical `SKILL.md`. If Release 8
wires this tier directly into inspection-lens selection or gate stringency
(the stated purpose per `renmark/ledger.py`'s docstring, "Release 8 …
`RiskTier` enum … at the `subagent_profiles.py`/`ledger.InspectionReport`
'lens selection' module boundary"), under-classifying a `high`-risk
dispatch as `medium` weakens exactly the safety property the tier exists
to provide.

Why this isn't "obviously unacceptable — needs a re-spike" either: the
disagreement is not random noise — it clusters into 2 concrete,
nameable causes (a too-narrow critical-module list; a too-blunt doc/config
floor), both of which have a precise, bounded code fix already written
above, and 0 of the 20 mismatches went the *safer* direction (over-
classification, which would just cost extra review, not weaken it). This
looks like a fixable v1-design gap, not a fundamentally unworkable
approach requiring a fresh spike.

The genuine judgment call for the Owner: **accept v2 as Release 8's
starting rule (bounded fix, revalidate against a fresh sample as part of
Task 2's own tests) vs. require an additional spike pass with a larger/
fresh sample before any schema or policy work depends on the tier.** This
finding does not decide that trade-off — it reports the evidence and the
concrete fix and stops there, per this task's scope.

## Re-spike — v2 fresh validation

**Trigger.** Owner reviewed the v1 finding above and explicitly chose
"re-spike with a fresh validation sample before coding v2" rather than
accept the circular 0/20 result reported in the "Recommended fix for Task
2" section. Release 8's roadmap stop condition allows exactly one re-spike
when criteria are redefined; this is that pass.

### v2 rule under test (unchanged — validated as written, not redesigned)

Applied exactly as specified above: the 9-module `CRITICAL_MODULES` set
(the original 6 plus `renmark/subagent_profiles.py`, `renmark/plan_lint.py`,
`renmark/cli/_wave_loop.py`), the 6-entry `PIPELINE_CRITICAL_SKILLS`
exception (`plugin/skills/{orchestrate,finish,debug,feature,rethink,start}/SKILL.md`),
and the two replacement branches for the doc floor and the non-test/
non-doc production-file floor.

One structural note surfaced while re-deriving the function to apply it
mechanically: in **both** v1 and v2's published pseudocode, `if complexity
== "hard": return "high"` is checked *before* `is_test`/`is_doc`/the new
floor branches. Applied literally, this means **any hard-complexity file —
test, doc, or code — returns "high" (or "critical" if it also hits a
critical module), regardless of what kind of file it is.** The original
v1 table's row 18 (`.renmark/memory/orchestration-baseline.md`, complexity
`hard`, rule tier recorded as `medium`) is inconsistent with this literal
reading — the table appears to have scored that row as if `is_doc` were
checked first. This re-spike applies the code exactly as written (per this
task's instruction not to redesign it), which is why several fresh
hard-complexity rows below produce results the v1 table's own convention
would not have produced. This inconsistency between the v1 pseudocode and
the v1 table's manual scoring is itself a finding, not just a footnote —
see the "hard-complexity test files" cluster below, which this ordering
directly causes.

### Fresh sample (20 dispatches, non-overlapping with the 20 used in v1)

Drawn from `.renmark/plans/2026-07-30-m3-0-delivery-state-archival.plan.md`,
`2026-07-30-m4-milestone-execution-review-loops.plan.md`,
`2026-07-30-m5-project-contract-propagation.plan.md`,
`2026-08-02-add-rethink-pipeline-skill.plan.md`,
`2026-08-02-orchestration-baseline-controls-part1.plan.md` and
`-part2.plan.md`. None of these plans, nor any of their tasks, appear in
the v1 sample table (which drew from Releases 1-7 of this program plus
`2026-06-10-deterministic-plan-validation.plan.md`). Target/complexity read
directly off each `### Task N` block, same method as v1. Hand judgment was
formed first from each task's spec text (blast-radius reasoning: what does
this file gate, what breaks if it's wrong), then the v2 rule was applied
mechanically — not the reverse, to avoid anchoring.

| # | Target | Complexity | Hand tier (judgment, formed first) | Rule v2 tier | Match? |
|---|---|---|---|---|---|
| 1 | `renmark/delivery_state.py` (atomic archival op) | hard | high | high | yes |
| 2 | `tests/test_delivery_state.py` | medium | low | low | yes |
| 3 | `renmark/loop.py` (milestone/package loop identity) | hard | high | high | yes |
| 4 | `tests/test_loop.py` (identity/resume/stop-boundary coverage) | hard | low | **high** | **no** |
| 5 | `renmark/program_driver.py` (repair-decision + recurrence guard) | hard | high | high | yes |
| 6 | `tests/test_program_driver.py` | hard | low | **high** | **no** |
| 7 | `renmark/cli/commands.py` (review-to-fix package export) | hard | high | high | yes |
| 8 | `renmark/lifecycle.py` (signoff/readiness gates incl. merge/release/security) | hard | **critical** | high | **no** |
| 9 | `plugin/skills/.shared/agency-delivery.md` (loop contract, cited normatively by multiple pipelines) | medium | medium | **low** | **no** |
| 10 | `renmark/init.py` (sole canonical-contract writer) | hard | high | high | yes |
| 11 | `plugin/skills/start/SKILL.md` (freshness-check routing) | medium | medium | medium | yes |
| 12 | `plugin/skills/feature/SKILL.md` (freshness-check routing) | medium | medium | medium | yes |
| 13 | `CLAUDE.md` (root guidance + template mirror source) | hard | high | high | yes |
| 14 | `renmark/agency.py` (Agency/Orchestrator golden trajectories, owner-gate behavior) | hard | high | high | yes |
| 15 | `plugin/skills/finish/SKILL.md` (release-handoff gate doc) | medium | medium | medium | yes |
| 16 | `plugin/skills/rethink/SKILL.md` (new pipeline's control-flow definition) | hard | high | high | yes |
| 17 | `renmark/plan_lint.py` (Check 11, pre-dispatch gate) | hard | critical | critical | yes |
| 18 | `renmark/cli/_engine.py` (wire escalation reason into routing log) | medium | high | high | yes |
| 19 | `renmark/state/usage.py` (one optional, backward-compatible dataclass field) | simple | low | **medium** | **no** |
| 20 | `plugin/commands/rethink.md` (thin command wrapper) | simple | low | low | yes |

### Fresh disagreement rate

**5 mismatches / 20 sampled = 25% disagreement — statistically identical
to v1's 25%, but the composition and direction are materially different.**

- **3 over-classifications** (rule higher than hand — costs extra review,
  not safety): #4, #6 (hard-complexity test files, caused directly by the
  branch-order issue noted above — `complexity == "hard"` returns `"high"`
  before the code ever checks `is_test`), and #19 (the new "non-test/
  non-doc production file → medium" floor added in v2 is blunt enough to
  float a one-line, explicitly backward-compatible, explicitly
  no-validation-added dataclass field to the same tier as a real
  state-mutation change).
- **2 under-classifications** (rule lower than hand — the direction that
  actually weakens the safety property the tier exists for): #8
  (`renmark/lifecycle.py` gates merge/release/security signoff and is not
  on the 9-entry critical-module list — the same root cause as v1's
  cluster 1, a different specific file) and #9 (`plugin/skills/.shared/
  agency-delivery.md` — the `PIPELINE_CRITICAL_SKILLS` exception only
  covers `plugin/skills/*/SKILL.md`, not the `.shared/*.md` governance
  fragments those skills cite normatively, so this class of doc still
  floors to `low` exactly like v1's cluster 2 did for `SKILL.md` files).

### Closing verdict

**Needs further refinement — not acceptable to code as-is.** Pushing back
on the implicit hope that a re-spike would vindicate v2: it did not. The
disagreement rate did not drop (25% → 25%), and re-spiking surfaced a
*new* failure mode (over-classification via the hard-complexity branch
order) that the original 20-dispatch sample never had the shape to expose,
on top of the *same* failure mode from v1 recurring in a new instance
(one more critical module missing from the list; one more doc class
missing from the pipeline-skill exception). Two structural patterns are
now visible across both spike passes, not one-off:

1. **The critical-module and pipeline-skill-exception lists are being
   discovered by sampling, one file at a time, and will keep failing this
   way.** v1 missed 3 modules and 1 skill class; this re-spike's fresh
   sample immediately found 1 more missing module (`lifecycle.py`) and 1
   more missing doc class (`.shared/*.md` fragments) using a *disjoint*
   set of dispatches. That is evidence the enumeration approach doesn't
   converge with more samples of the same size — it needs either a
   structural signal (e.g., "does this module/doc get imported by or
   referenced normatively from an owner-gate/dispatch/lifecycle code
   path") or an explicit acknowledgment that the enumerated lists will
   need periodic maintenance as a known, accepted cost, not a one-time fix.
2. **The branch-order bug (hard-complexity check before is_test) is a
   real implementation defect, not a judgment call** — it produces
   `"high"` for any hard-complexity test file, which no version of this
   rule's design intent (floor tests low, since they carry no production
   blast radius) argues for. This should be fixed before Task 2 codes v2
   verbatim, not carried forward as a known quirk.

Concrete next step recommended: reorder the function so `is_test` is
checked before the `complexity == "hard"` short-circuit (tests stay
low/medium regardless of effort), add `renmark/lifecycle.py` to
`CRITICAL_MODULES`, extend `PIPELINE_CRITICAL_SKILLS`-style treatment to
`plugin/skills/.shared/*.md`, and treat the non-test/non-doc "medium"
floor's over-classification of trivial changes (#19) as an accepted,
documented trade-off rather than a bug — over-classification costs review
time, not safety, and is the one direction both spikes agree is
tolerable.

This is not "a genuine Owner judgment call" in the way v1's close was —
the two failure clusters above have concrete, nameable fixes, same as
v1's did. But because this is the **second** spike to land at ~25%
disagreement on a *risk-tier* gate, and because one of the two mismatch
directions actively under-classifies real merge/release/security-gating
code, this finding recommends **one more Owner check-in before Task 2
codes it** — specifically to confirm the four fixes above are acceptable
as scoped, rather than treating this write-up's recommendation as
self-approving. A third re-spike is not warranted by this result (the
roadmap's stop condition allows only one), and is not what this finding
is asking for — a bounded revision of the same v2 rule, re-verified by
Task 2's own tests, is.
