---
artifact_type: plan
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: c3f0ce1
related_plan: null
generator: plan
stale_after: null
dependency_refs:
  - .renmark/specs/2026-07-02-agency-mode.spec.md
  - PRD.md
---

# Agency Mode — walking-skeleton MVP plan

Decomposes `.renmark/specs/2026-07-02-agency-mode.spec.md` (REQ-22) into atomic
tasks. Architecture is a **higher-level delivery workflow** (NOT a third
`mode.py` value): lightweight resumable agency state + an on-demand
`agency-delivery.md` contract fragment + mode-conditioned preamble + agency-aware
CORE SPINE (start → prd → roadmap → finish → resume) + behavior tests + docs.
Reuses (never re-implements) `mode.py` patterns, the `LifecycleBloatError`/1024B
guard, `context.py` dynamic loading, `finish_lanes`, `cost.py`, and the
cost-control `_shared` fragments. Out of scope: auto-detection and the fast-follow
pipelines (feature/plan/orchestrate/verify/codereview).

Waves: (1) core files → (2) registration + preamble wiring → (3) spine SKILL.md
blocks → (4) docs → (5) tests.

---

### Task 1: agency state module
- **mode:** A
- **target:** renmark/agency.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile renmark/agency.py && python3 -c "from renmark import agency; agency.agency_state_path('.')"
- **serves:** REQ-22
- **spec:**
  New module modeled closely on `renmark/mode.py` (read/write helpers, atomic
  writes) and the `renmark/lifecycle.py` bloat-guard pattern
  (`LIFECYCLE_JSON_BYTE_BUDGET = 1024` / `LifecycleBloatError`). Provide
  lightweight, resumable agency project state persisted to
  `.renmark/state/agency.json`:
  - `agency_state_path(repo)` → Path to `.renmark/state/agency.json`.
  - A small dataclass/dict schema with fields: `active: bool`, `current_phase`,
    `current_milestone`, `next_checkpoint`, `signoff_status`, `cost_lane`,
    `roadmap_ref`. Keep it minimal.
  - `read_agency(repo)` → returns state or an inactive/None default when the
    file is missing OR corrupt (never raise into a pipeline). `write_agency(...)`
    → atomic write with an `AGENCY_JSON_BYTE_BUDGET = 1024` guard raising
    `AgencyBloatError` (mirror `LifecycleBloatError` exactly).
  - `is_active(repo)` → bool convenience. `activate(repo, ...)` /
    `deactivate(repo)` helpers. `agency.json` is RUNTIME state — treat like
    `.renmark/state/` (gitignored), distinct from lifecycle/pipeline.
  Do NOT add a third value to `mode.py`. stdlib only.

### Task 2: agency-delivery shared contract fragment
- **mode:** A
- **target:** plugin/skills/_shared/agency-delivery.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "milestone" plugin/skills/_shared/agency-delivery.md && grep -qi "signoff" plugin/skills/_shared/agency-delivery.md
- **serves:** REQ-22
- **spec:**
  New `_shared` contract fragment — the shared Agency delivery contract, loaded
  ON DEMAND only when agency state is active (never eager). Cover, concisely:
  the delivery loop (discovery → PRD agreement → tech-stack rec →
  roadmap/milestones → build → demo/feedback → verification → signoff →
  release); owner-level questioning discipline (ask owner decisions, not needless
  technical ones); milestone/checkpoint/signoff gates distinct from technical
  gates; main-agent-talks / scoped-background-agents-work split; and REUSE
  pointers to the cost-control infra by reference — `finish_lanes`
  (`recommend_lane`/`resolve_lane`), `cost.py` (`estimate_cost`/
  `requires_escalation`), `context_budget_hint`, `subagent_profiles`, and the
  `model-routing.md` / `subagent-budget.md` / `deterministic-first.md` fragments
  (milestone-readiness checks run deterministically). Match the house style of
  existing `_shared/*.md` fragments. Keep it tight.

### Task 3: register agency-delivery fragment for on-demand loading
- **mode:** B
- **target:** renmark/context.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import context; assert 'agency-delivery' in context.fragment_names(), 'not registered'; assert context.fragment_pointer('agency-delivery').endswith('_shared/agency-delivery.md')"
- **serves:** REQ-22
- **spec:**
  Add `"agency-delivery"` to `FRAGMENT_NAMES` so `fragment_names()`,
  `fragment_pointer()`, and `load_fragment()` serve it on demand. This is the
  dynamic-loading registration (AC4/REQ-20): the fragment body is NEVER
  pre-loaded — only its pointer is exposed upfront. Do not change load semantics.

### Task 4: mode-conditioned agency preamble
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile renmark/lifecycle.py && python3 -c "from renmark import lifecycle; lifecycle.skill_preamble('.', 'start')"
- **serves:** REQ-22
- **spec:**
  Extend `skill_preamble` so that WHEN agency state is active
  (`renmark.agency.is_active(repo)`), it additionally surfaces a one-line agency
  hint naming the current phase/milestone and a POINTER to
  `agency-delivery.md` (via `context.fragment_pointer('agency-delivery')`) for
  the given skill — metadata/pointer only, NEVER the fragment body. When agency
  is inactive, behavior MUST be byte-identical to today (this is the load-bearing
  "does not change Conductor/Orchestrator" guarantee). Only surface the agency
  hint for spine skills (start/prd/roadmap/finish/resume); keep it additive to
  the existing hint string. Import `agency` lazily/at top per module style.

### Task 5: cite agency-delivery from the spine skills' metadata
- **mode:** B
- **target:** renmark/skillmeta.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import skillmeta as s; import renmark.context as c; [print(n) for n in ('start','prd','roadmap','finish','resume')]" && python3 -m py_compile renmark/skillmeta.py
- **serves:** REQ-22
- **spec:**
  For the frozen skill registry entries of `start`, `prd`, `roadmap`, `finish`,
  and `resume`, add `"agency-delivery"` to each one's `cites` set (the subset of
  `_shared` fragments that SKILL.md references). Do not touch other skills. Keep
  the registry shape/format exactly as-is; this only records the new citation so
  metadata stays accurate for dynamic loading and the behavior test.

### Task 6: /renmark:start — agency lane + opt-in
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" plugin/skills/start/SKILL.md
- **serves:** REQ-22
- **spec:**
  Add a concise "When Agency Mode is active / opt-in" section. `/renmark:start`
  is the EXPLICIT opt-in entry (no auto-detect): offer an Agency lane framing the
  session as a discovery call (owner intent, users, problem, outcome,
  owner-level questions, project classification), and on opt-in initialize agency
  state via `renmark.agency.activate(...)`. Reference the contract by pointer
  (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`) — do NOT inline it.
  Keep existing behavior intact when agency is not chosen.

### Task 7: /renmark:prd — agency agreement point
- **mode:** B
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 600
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" plugin/skills/prd/SKILL.md
- **serves:** REQ-22
- **spec:**
  Add a short "When Agency Mode is active" block: PRD is the owner-agreed
  source-of-truth lock; owner approval gates the PRD; change control kicks in
  when milestone feedback shifts scope. Reference `agency-delivery.md` by
  pointer. Do not change the existing human-gated create/update flow.

### Task 8: /renmark:roadmap — milestones/checkpoints/signoff
- **mode:** B
- **target:** plugin/skills/roadmap/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 600
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" plugin/skills/roadmap/SKILL.md
- **serves:** REQ-22
- **spec:**
  Add a short "When Agency Mode is active" block: emit milestones with
  checkpoints, demo points, and signoff points; sequencing + risk/dependency
  notes; write `roadmap_ref` into agency state. Reference `agency-delivery.md`
  by pointer. Keep existing roadmap behavior otherwise.

### Task 9: /renmark:finish — milestone demo + signoff + finish-lane
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" plugin/skills/finish/SKILL.md
- **serves:** REQ-22
- **spec:**
  Add a short "When Agency Mode is active" block: milestone demo summary + owner
  signoff gate + finish-lane selection via `finish_lanes.recommend_lane`; on new
  owner feedback, update roadmap + recommend the next milestone. Reference
  `agency-delivery.md` by pointer and REUSE the existing finish-lanes machinery
  — do not re-implement lanes. Keep existing finish behavior intact.

### Task 10: /renmark:resume — resume from milestone
- **mode:** B
- **target:** plugin/skills/resume/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 600
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" plugin/skills/resume/SKILL.md
- **serves:** REQ-22
- **spec:**
  Add a short "When Agency Mode is active" block: resume from the last
  milestone/checkpoint by reading `.renmark/state/agency.json`; summarize where
  we left off; continue without re-discovery. Reference `agency-delivery.md` by
  pointer. Keep the existing zero-LLM resume path intact.

### Task 11: help — document Agency Mode
- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 500
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" plugin/skills/help/SKILL.md
- **serves:** REQ-22
- **spec:**
  Add a concise Agency Mode entry to help output: the third delivery modality
  (above Conductor/Orchestrator, does not replace them), explicit opt-in via
  `/renmark:start`, drives the discovery→signoff loop. One short paragraph.

### Task 12: CLAUDE.md — Agency Mode rule block
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 500
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" CLAUDE.md
- **serves:** REQ-22
- **spec:**
  Add a short "Agency Mode" rule block near the Operating-modes section:
  higher-level delivery workflow above Conductor/Orchestrator (does not replace
  them); explicit opt-in via /renmark:start; lightweight resumable agency state;
  reuses cost-control/finish-lanes/deterministic-first; agency bodies load on
  demand. Note it is mirrored in AGENTS.md.

### Task 13: AGENTS.md — mirror Agency Mode rule block
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 500
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Agency Mode" AGENTS.md
- **serves:** REQ-22
- **spec:**
  Mirror the exact Agency Mode rule block added to CLAUDE.md in Task 12 (same
  wording), per the CLAUDE.md↔AGENTS.md sync convention.

### Task 14: agency state tests
- **mode:** A
- **target:** tests/test_agency.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 5
- **est_tokens:** 1000
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest tests/test_agency.py -q
- **serves:** REQ-22
- **spec:**
  Tests for `renmark/agency.py` against a tmp repo: write→read round-trip;
  inactive/missing file returns the inactive default (no raise); corrupt JSON is
  treated as inactive (no raise); `is_active` reflects state; `activate` /
  `deactivate` toggle correctly; oversize state raises `AgencyBloatError`
  (mirror the lifecycle bloat-guard test). Prove resumability: state persisted
  by one call is read back by a fresh call (AC9).

### Task 15: agency behavior tests (AC11 — changes behavior, no eager bodies)
- **mode:** A
- **target:** tests/test_agency_behavior.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 5
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_agency_behavior.py -q
- **serves:** REQ-22
- **spec:**
  Prove Agency Mode CHANGES renmark behavior WITHOUT loading every skill body
  (AC11): (1) with agency inactive, `lifecycle.skill_preamble` output for a spine
  skill is unchanged vs baseline; with agency active, it gains the agency hint +
  the `agency-delivery` fragment POINTER (assert the pointer string appears, and
  that the fragment BODY text does NOT — dynamic loading, REQ-20). (2)
  `context.fragment_names()` includes `agency-delivery` and `load_fragment` can
  fetch it on demand. (3) the 5 spine skills cite `agency-delivery` in skillmeta;
  non-spine skills do not. (4) Conductor/Orchestrator mode selection is
  unaffected by agency state (AC2). Use a tmp repo; stdlib + pytest only.

---

## Cost preview

| Wave | Tasks | Executors |
|---|---|---|
| 1 — core files | T1, T2 | sonnet×2 |
| 2 — registration + wiring | T3, T4, T5 | sonnet×3 |
| 3 — spine SKILL.md blocks | T6–T10 | haiku×5 |
| 4 — docs | T11–T13 | haiku×3 |
| 5 — tests | T14, T15 | codex×1, sonnet×1 |

**Executors:** haiku×8, sonnet×6, codex×1, opus×0, fable×0 (no escalation).
**Total tokens (incl. ~10k Agent overhead per Claude task):** ~150k.
**Total cost: ~$0.22** (deterministic-first: grounding done via git/grep, not model calls; all infra reused, not rebuilt).

All 15 tasks fit the orchestrate 15-task cap — no split. Verify (REQ-7) runs
after orchestrate regardless of tier.
