---
artifact_type: research
schema_version: 1
created_at: 2026-06-11T20:58:53+00:00
source_sha: 0113ee4a699a63723ff87bdb7bfef045e15ec2c2
related_plan: .renmark/plans/2026-06-10-fable-integration-part2.plan.md
generator: fable
stale_after: null
dependency_refs: []
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Fable routing strategy — adopted direction (declared-capability tier routing)

Decided 2026-06-11 with the user after a 9-agent evidence workflow (5 readers over
brainstorm/plan/prd/blueprint SKILLs + runtime hooks + PRD REQ-2; 3 competing designs;
judge panel). Winner: **Declared-Capability Tier Routing** (46 vs 41/41).

## Core decisions
- Fable becomes the DEFAULT brain for ideation/strategy synthesis (brainstorm discovery/
  approaches/design/spec; plan decomposition/scoring/routing; prd interview/reconcile)
  WHEN a project declares `top_tier: fable`.
- Availability is DECLARED, never detected: `## Model tiers` block in
  `.renmark/memory/routing.md` (`top_tier: fable|opus`), set via Y/N in init/setup/doctor;
  `RENMARK_TOP_TIER` env override. Absent flag → opus → byte-identical current behavior.
  Detection is impossible (no API key for probes; opaque Agent failure modes).
- Skills cannot switch the session model — interactive synthesis runs on the session
  brain; the skill_preamble surfaces a deterministic "/model fable" hint when declared.
- Busy-work demotions (phase 0, no PRD change needed): PRD-alignment subagent → haiku
  (sonnet if PRD large); brainstorm Step 3 research → parallel sonnet subagents
  (artifact + ≤5-line summary); blueprint Step 3b → top tier writes ~10-line design spec,
  codex emits PROTOTYPE.html bulk.
- New deterministic guards: plan_lint BLOCKs `executor: fable` in undeclared projects AND
  on mechanical/bulk tasks; orchestrate gets fable→opus one-retry fallback, logged via
  memory.append_routing (never silent).
- NEW `renmark/capabilities.py` (pure functions, test-pinned) + tests; cost preview
  renders fable rows per declaration.
- Later phase: shared rate-table helper across roadmap.py/_engine.py/loop.py (drift fix).

## Gates
- PRD REQ-2 amendment REQUIRED first (current wording = escalation-only, default NOT
  permitted): via /renmark:prd UPDATE + /renmark:approve.
- Cost honesty: +$1.20–1.60/feature for declared-Fable synthesis, partly offset by
  research/read demotions.

## Judge-identified pitfalls to honor
- No per-checkpoint fable Agent calls inside interactive loops (10k overhead each).
- routing.md Defaults grammar: keep machine-format compatible (append_routing).
- Per-project flag encodes per-user entitlement — env override is the collaborator escape.
- Keep "Fable 5 when available, Opus otherwise" as the single user-facing formula.

Full evidence: workflow wf_3aa04adf-a0a (session transcript dir), routing matrix in body.

## Summary

- adopted: declared-capability fable routing (top_tier flag + capabilities.py)
- phase 0 (no PRD change): haiku PRD-alignment, sonnet research, codex blueprint bulk
- phase 1 (PRD-gated): REQ-2 amendment, plan_lint gates, fable→opus fallback, init/doctor declaration
- next: /renmark:prd UPDATE then brainstorm/plan the feature
