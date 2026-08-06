# Release 16 — /renmark:rethink self-upgrade (final release)

Closes REQ-28's remaining gaps per the roadmap's Release 16 section and the
Owner-approved PRD amendment (CHANGELOG.md 2026-08-05 "PRD updated"). Three
migration steps: (a) wire the new independent-Inspector challenge
OPERATIONALLY into `plugin/skills/rethink/SKILL.md` (the PRD text alone is
not wiring — this is what makes the step actually run, not just documented);
(b) wire stage 6/7's own classification/blueprint dispatches through the
reconciled `ledger.work_order_for_task` funnel (Release 3), so rethink's own
dispatches are governed by the same contracts it recommends for the rest of
the codebase; (c) apply lens selection (Release 8's `subagent_gate.resolve_lens_for`)
to stage 5's modularity-assessment dispatch where it touches critical
modules. A test proves the wiring is present (file-content check, matching
`tests/test_dangerous_gate_wiring.py`'s existing precedent for this exact
kind of skill-prose contract — do not import or run the skill).

**Compatibility guarantee:** `pytest -q` count only grows; this changes
`/renmark:rethink`'s own pipeline text/gates only — no other baseline check
touched (`dispatch.py`/`ledger.py`/`fast_path.py` internals unchanged).

### Task 1: wire the independent-Inspector challenge into rethink's pipeline

- **mode:** B
- **target:** plugin/skills/rethink/SKILL.md
- **complexity:** hard
- **executor:** opus
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 2200
- **est_cost_usd:** 0.183
- **verifier:** grep -q "emit_inspection_verdict" plugin/skills/rethink/SKILL.md && grep -q "### 8a. Independent Inspector challenge" plugin/skills/rethink/SKILL.md && echo OK
- **serves:** AC-12 (Req 12)
- **spec:**
  Read `PRD.md`'s REQ-28 (the just-amended text — grep for "independent
  Inspector challenge") and `plugin/skills/rethink/SKILL.md`'s existing
  "### 7a. Solution Gate" section (the closest precedent for a
  gate/review-style subsection's structure and heading level) first.
  Insert a new subsection titled exactly `### 8a. Independent Inspector
  challenge` between the existing `### 8. Incremental transformation
  roadmap` section and `### 9. Execution Gate, then hand off to milestone
  execution` section. This subsection must OPERATIONALLY wire the PRD's
  new prose, not just restate it — include concrete Python/skill-action
  steps:
  - Dispatch ONE isolated `renmark:inspector` role subagent (Agent tool
    call, matching this skill's existing subagent-dispatch conventions
    elsewhere in this file — read one for the pattern) carrying ONLY
    bounded pointers to the stage 3 PRD acceptance contract, stage 4
    external-benchmark findings, stage 5 modularity assessment, and the
    stage 8 roadmap artifact paths — never their full bodies (context
    hygiene, extends REQ-5).
  - The Inspector reviews the roadmap against those three artifacts and
    returns a bounded verdict (`pass`/`fail`/`escalate`, matching
    `ledger.VERDICTS`) plus findings — read-only, no Write/Edit tools,
    same as every other Inspector dispatch in this codebase.
  - Record the verdict via `ledger.emit_inspection_verdict(repo,
    work_result_id=<the roadmap artifact's identity>, work_order_id=<the
    stage-8 roadmap's work order id if one exists, else a stable
    rethink-scoped id>, verdict=<the Inspector's verdict>,
    evidence=<bounded findings list>, inspector_dispatch_identity=
    "renmark:inspector", work_result_dispatch_identity=<the roadmap
    author's dispatch identity>, ts=<now>)`.
  - On `pass`: proceed straight to stage 9's Execution Gate, surfacing the
    Inspector's verdict alongside the roadmap.
  - On `fail`/`escalate`: route the findings back to the roadmap author
    (stage 8) for exactly ONE bounded correction pass, then re-run the
    Inspector challenge once. If it still doesn't clear, this is an
    exception check-in (per this skill's existing exception-check-in
    section — reference it, don't restate its mechanics) — never a silent
    third attempt.
  - The Inspector "may not revise the roadmap itself, only report
    findings" (verbatim from the PRD) — make this explicit: the
    dispatched subagent's tool scope excludes Write/Edit, matching
    `plugin/agents/inspector.md`'s real declared tools.
  Also add one sentence to `### 9. Execution Gate...`'s existing bullet
  list of what gets presented, noting the Inspector challenge's
  verdict/findings are now included (the PRD already states this — mirror
  it operationally: the gate's presented content pulls from the
  `InspectionReport` written above, not a fresh ad-hoc summary).
  Do not touch any other section of this file.

### Task 2: wire stage 6/7 work-order funnel + stage 5 lens selection

- **mode:** B
- **target:** plugin/skills/rethink/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.0336
- **verifier:** grep -q "work_order_for_task" plugin/skills/rethink/SKILL.md && grep -q "resolve_lens_for" plugin/skills/rethink/SKILL.md && echo OK
- **serves:** AC-12 (Req 12)
- **spec:**
  Read `plugin/skills/rethink/SKILL.md`'s `### 6. Evidence-based
  classification`, `### 7` (blueprint — find its exact heading), and
  `### 5. Modularity, scalability, and maintainability assessment`
  sections in full first, plus `renmark/ledger.py`'s
  `work_order_for_task` and `renmark/subagent_gate.py`'s
  `resolve_lens_for` (both already used elsewhere in this codebase's
  dispatch flow — read `plugin/skills/orchestrate/SKILL.md`'s existing
  references to `work_order_for_task`/`check_capability_envelope` for the
  established citation style this file should match).
  In stage 6 and/or stage 7 (whichever section actually describes
  dispatching the classification/blueprint-writing subagent — add the
  note to whichever is the natural fit, or both if both dispatch
  independently), add one or two sentences stating that this stage's own
  subagent dispatch is built via `ledger.work_order_for_task` like any
  other renmark dispatch (extends Release 3's reconciled work-order
  funnel) — rethink's own internal dispatches are governed by the same
  contracts it recommends applying to the rest of the codebase, not a
  parallel/exempt dispatch path.
  In stage 5 (modularity assessment), add one sentence: when the
  assessment's dispatch touches a declared critical module (per
  `ledger._CRITICAL_MODULES` or equivalent), its `WorkOrder` carries the
  lens `subagent_gate.resolve_lens_for` resolves for that risk tier
  (typically `skeptical_user` for high/critical) — Release 8's lens
  mechanism applied to rethink's own architectural-assessment dispatch,
  not just to downstream build work.
  Do not touch stages 8, 8a, or 9 (Task 1's scope) or any other section.

### Task 3: governance-wiring regression test

- **mode:** A
- **target:** tests/test_rethink_skill_governance_wiring.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest -q tests/test_rethink_skill_governance_wiring.py 2>&1 | tail -5
- **serves:** AC-12 (Req 12)
- **spec:**
  Write a pure file-content regression test, following the EXACT pattern
  of `tests/test_dangerous_gate_wiring.py` (read it first — same style:
  read `plugin/skills/rethink/SKILL.md` as text, assert substrings are
  present, do NOT import or run the skill). Assert:
  (1) the heading `### 8a. Independent Inspector challenge` is present
  and appears AFTER `### 8. Incremental transformation roadmap` and
  BEFORE `### 9. Execution Gate` (use `str.index` to check ordering, not
  just presence);
  (2) `ledger.emit_inspection_verdict` is referenced;
  (3) `work_order_for_task` is referenced;
  (4) `resolve_lens_for` is referenced;
  (5) the text `may not revise the roadmap` (or an equivalent phrase
  confirming the Inspector's write restriction) is present;
  (6) confirm the file's existing "three gates"/"3 existing Owner gates"
  language is intact and unchanged (the Inspector challenge is
  deliberately NOT a 4th approval gate) — assert the Inspector-challenge
  heading text does NOT contain the word "Gate" in its own title, since
  PRD.md's amendment explicitly frames it as distinct from the 3 Owner
  gates.

---

**Total tasks:** 3 (3 parallel groups — Task 1 and 2 are sequential, same
file; Task 3 depends on both)
**Total tokens (incl. ~10k Agent overhead/task for sonnet/opus, none for codex):**
~4100 output + 20k Agent overhead (2 sonnet/opus tasks) = ~24.1k
**Total cost:** ~$0.237
**Executors:** opus×1, sonnet×1, codex×1

**Program completion note:** this is the last release in the 16-release
`governed-orchestration-assurance` program. On successful verify, present
the full-program completion summary alongside the normal hand-off.
