# Plan — acceptance-criteria (optional per-REQ "done when…" criteria in the PRD)

**Branch:** `feature/acceptance-criteria`

Adds OPTIONAL product-level acceptance criteria under each `REQ-n` in the PRD —
"done when…" outcome bullets, authored/edited only through `/renmark:prd`
(human-gated). Two disjoint files; both follow the SAME format so template and
skill stay consistent. Doc/skill-only (no Python logic) — grep verifiers are the
gate. Out of scope: `verify --coverage`, Gherkin, dogfooding renmark's own PRD.

---

### Task 1: PRD template — optional acceptance criteria per requirement
- **mode:** B
- **target:** plugin/templates/PRD.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "done when" plugin/templates/PRD.md.template && grep -qi "acceptance" plugin/templates/PRD.md.template
- **serves:** REQ-4
- **spec:**
  Read plugin/templates/PRD.md.template first (note the `## Requirements` section
  with its `REQ-1/REQ-2/REQ-3` placeholders). ADD support for OPTIONAL per-REQ
  acceptance criteria:
  - In the Requirements section's instruction line, add one sentence: each
    requirement MAY carry optional **acceptance criteria** — short, plain-English,
    product-level "done when…" OUTCOME bullets (NOT task/implementation steps, NOT
    Gherkin). They're optional; omit when a requirement's outcome is self-evident.
  - Update ONE of the example REQ placeholders to SHOW the format, e.g.:
    ```
    1. `REQ-1` (the required behavior/outcome in user/business terms.)
       - *Acceptance:* done when (an observable product outcome); done when (another).
    ```
  - Keep the other REQ placeholders without criteria (to show they're optional).
  - Do not change other sections (Vision/Target users/Goals/Success metrics/etc.).
  - Add a one-line note distinguishing acceptance criteria (per-REQ, "done when…")
    from Success metrics (project-wide signals) so they don't get conflated.
  Keep the template's existing tone/structure and the provenance header comment intact.

### Task 2: prd skill — author/edit acceptance criteria (CREATE + UPDATE)
- **mode:** B
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "acceptance" plugin/skills/prd/SKILL.md && grep -qi "done when" plugin/skills/prd/SKILL.md
- **serves:** REQ-4
- **spec:**
  Read plugin/skills/prd/SKILL.md first (CREATE mode interview/synthesis steps;
  UPDATE mode reconcile+diff steps; the human-gate section). ADD optional
  acceptance-criteria handling, consistent with Task 1's template format:
  - **CREATE mode (interview path):** after the requirements are gathered, OPTIONALLY
    ask — one requirement at a time, SKIPPABLE — for 1–3 "done when…" acceptance
    criteria per `REQ-n`. Make clear it's optional; a user can skip any/all. (Synthesis
    path: infer obvious acceptance criteria from existing docs where clear, else leave blank.)
  - **UPDATE mode:** acceptance criteria are an editable part of a requirement —
    adding/changing them follows the same reconcile → DIFF → explicit-approval flow as
    any other PRD edit (still human-gated; never silently written).
  - Add a short note on ALTITUDE: acceptance criteria are **product-level outcome
    criteria** ("done when…"), NOT plan task verifiers and NOT the deferred
    `verify --coverage` (ADR-005). `/renmark:verify`'s goal-backward smoke MAY lean on
    them, but this feature does NOT build coverage reporting. Cross-reference the
    template format (Task 1) so they match.
  - Keep everything else (human gate, context-hygiene, governance table) intact.
  Mirror any rule-affecting note for AGENTS.md/CLAUDE.md sync if that convention is present.

---

## Cost preview

| Task | Executor | Total tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|
| 1 PRD template criteria | haiku | 10,400 | $0.0010 |
| 2 prd skill author/edit | sonnet | 11,500 | $0.0345 |

**Tasks: 2 (1 parallel group). Executors: haiku×1, sonnet×1.**
**Total tokens: ~22k. Total cost: ~$0.036**
