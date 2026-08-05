# Plan: governed-orchestration-assurance — Release 2 (Role-model altitude ADR, spike #28)

Context: Release 2 of the 16-release `governed-orchestration-assurance` program
(`.renmark/state/program.json`, stage `release-2-role-altitude-adr`). Bounded
1-session spike, no code change: produce one ADR paragraph confirming (or
correcting) that Release 6's capability-envelope enforcement belongs at the
per-dispatch-role altitude (`subagent_profiles.py`), not the project-phase
altitude (`agency.py`). Source: `.renmark/rethink/governed-orchestration-assurance/roadmap.md`
"Release 2" section + `modularity-assessment.md` §1 (lines ~48, ~105-117,
~203-207) which frame this as an open two-altitude split, not a settled fact.

### Task 1: Role-model altitude ADR entry
- **mode:** B
- **target:** .renmark/memory/decisions.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** grep -q "ADR-050" .renmark/memory/decisions.md
- **serves:** REQ-1, REQ-2, REQ-12
- **spec:**
  Append one new ADR entry to the TOP of `.renmark/memory/decisions.md`
  (entries are newest-first; the current top entry is `ADR-049`), following
  the exact existing format (see `ADR-049`/`ADR-045` for the section shape:
  `## ADR-### — <title>`, `**Date:**`, `**Status:**`, `**Context.**`,
  `**Decision.**`, separated by `---`). Number it `ADR-050`. Title:
  "Role-model altitude for capability-envelope enforcement (Release 2 spike
  #28)". Date: 2026-08-05. Status: Accepted (or "Accepted — corrects roadmap
  lean" if your investigation contradicts the roadmap's stated default).

  Before writing the paragraph:
  1. Read `.renmark/rethink/governed-orchestration-assurance/roadmap.md`'s
     "Release 2" section in full for exact scope and the stated default lean.
  2. Read `.renmark/rethink/governed-orchestration-assurance/modularity-assessment.md`
     §1 in full, especially the passages describing `agency.py`'s
     `AgencyState`/milestone/signoff tracking (the *project-phase* altitude)
     vs `subagent_profiles.py`'s `ProfileSpec`/`allowed_targets`
     (*per-dispatch-role* altitude), and the note that these are "not yet
     unified."
  3. Treat this as a genuinely open judgment call, not a foregone conclusion.
     Actually check whether `agency.py`'s phase gates (milestone/signoff,
     project-phase state transitions) are structurally distinct from what a
     capability envelope does (per-dispatch scope/command/path/network
     enforcement at the moment a subagent is dispatched) — read enough of
     `agency.py` and `subagent_profiles.py` (via Read/Grep) to confirm this
     structurally, not just restate the roadmap's hint. If the evidence
     contradicts the roadmap's stated lean, say so and correct it in the ADR
     instead of rubber-stamping it.

  Write the **Context** section summarizing the open question (does Release
  6's capability envelope enforce at per-dispatch-role altitude, project-phase
  altitude, or both) and what modularity-assessment.md observed. Write the
  **Decision** section as one clear paragraph stating which altitude the
  capability envelope enforces at (per-dispatch-role, `subagent_profiles.py`,
  per the roadmap's default lean — unless your check found otherwise), and
  explicitly note that `agency.py`'s phase/signoff gates remain a separate,
  milestone-level concern already covered by existing lifecycle/agency gates,
  not something Release 6 needs to also touch. Note the stop condition: ADR
  accepted, no code change unless the confirmation contradicts the lean.

  No production code changes — this task touches only `decisions.md`. Do not
  edit `agency.py`, `subagent_profiles.py`, or any other file.

---

## Cost preview

| Executor | Tasks | Tokens (incl. overhead) | Cost |
|---|---|---|---|
| sonnet | 1 | 10,700 | $0.0321 |

**Total tokens (incl. ~10k Agent overhead/task): ~10,700**
**Total cost: ~$0.0321**
