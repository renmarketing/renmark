---
artifact_type: plan
schema_version: 1
created_at: 2026-06-25T00:00:00Z
source_sha: f736542
related_plan: null
generator: opus
stale_after: 2026-09-25T00:00:00Z
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
completion_state: complete
confidence: high
validation_status: validated
---

# Plan — graduated preamble-tier (P3)

## Goal
Make `lifecycle.skill_preamble(repo, skill)` **graduated** instead of all-or-nothing.
Today it runs the same context-budget + cross-domain check and (for synthesis skills)
fable-hint logic for every skill. P3 assigns each skill a **preamble tier** so zero-LLM /
meta skills carry a minimal preamble while heavy pipeline skills get the full block.
Finer per-turn token dial; complements v0.20.0 (P1 trigger-only descriptions + P2
`disable-model-invocation`). Pure backend refactor — no new commands, no SKILL.md changes.
Serves REQ-5 (context hygiene); see the 2026-06-25 PRD In-scope revision note.

## Design (the one decision to review)

`context_budget_check` only ever returns `"clear"` (cross-domain) or `None` — the
`"compact"` branch in today's `skill_preamble` is already dead code. So a zero-LLM/meta
skill today only ever receives the cross-domain `/clear` hint (it is never a synthesis
skill, so never the fable hint).

**Three tiers** (`PREAMBLE_TIER_BY_SKILL`, default `"full"` for any unlisted skill — safe):

| Tier | What `skill_preamble` surfaces | Skills |
|---|---|---|
| `minimal` | **nothing** (returns `None`); records invocation only | `resume`, `help`, `doctor`, `usage`, `analytics`, `approve`, `hygiene`, `check-plan` |
| `standard` | cross-domain `/clear` hint only (no fable) | `audit`, `scan`, `inventory` |
| `full` | cross-domain `/clear` + fable hint (today's behavior, unchanged) | everything else (default) |

**Hard-constraint handling — cross-domain `/clear` detection is NOT compromised:**
- `record_skill_invocation` is called for **every** skill, every tier, FIRST — so the
  "last skill / domain" stays accurate and the *next* skill's detection mechanism is intact.
- The tier only gates *hint surfacing*, not the detection mechanism.
- `audit` / `scan` / `inventory` are the audit-**domain** skills you transition *into* from a
  build/debug session, so they keep the `/clear` hint (`standard`) — the one place the nudge
  is genuinely actionable. The remaining 8 (the disable-model-invocation set minus audit/scan,
  plus inventory→standard) are pure navigation/status/same-domain reads where a `/clear`
  nudge is counterproductive (e.g. mid-`resume`) → `minimal`.
- `/renmark:resume` cold-start stays zero-LLM AND now skips the `context_budget_check` read
  entirely (`minimal` returns before it), so recovery is strictly cheaper, never costlier.

> **Reviewer note:** the only judgement call is `audit`/`scan`/`inventory` = `standard`
> rather than `minimal`. The feature description listed all 11 disable-model-invocation
> skills as "minimal", but the hard constraint ("never compromise cross-domain `/clear`
> detection") wins for the 3 that live in a *different* domain. If you'd rather they be
> fully `minimal`, pick **Edit** at the dispatch gate.

`full`-tier behavior is preserved **byte-identical** (existing `test_lifecycle.py` preamble
tests cover brainstorm/verify/debug — all full-tier — and must stay green).

---

### Task 1: tier-aware skill_preamble
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_lifecycle.py -q && python3 -m py_compile renmark/lifecycle.py
- **serves:** REQ-5
- **spec:**
  In `renmark/lifecycle.py`, add a module-level `PREAMBLE_TIER_BY_SKILL: dict[str, str]`
  immediately after `DOMAIN_BY_SKILL` (mirror that style — alphabetical-ish, commented).
  Map: `resume, help, doctor, usage, analytics, approve, hygiene, check-plan` → `"minimal"`;
  `audit, scan, inventory` → `"standard"`. Do NOT list any other skill (default is full).

  Add `def preamble_tier(skill: str) -> str:` next to `domain_of` — returns
  `PREAMBLE_TIER_BY_SKILL.get(skill, "full")`. Must never raise; mirror `domain_of`.

  Refactor `skill_preamble(repo, skill)`:
  1. Resolve `domain = domain_of(skill)` and `tier = preamble_tier(skill)`.
  2. Call `_state.record_skill_invocation(repo, skill, domain)` **FIRST, unconditionally,
     for every tier** — this preserves cross-domain detection for the next skill (the load-
     bearing invariant; do not move it below an early return).
  3. If `tier == "minimal"`: `return None` immediately (do NOT call `context_budget_check`,
     do NOT build fragments).
  4. Otherwise build `fragments` exactly as today: `context_budget_check` → `"clear"` adds
     the cross-domain `/clear` fragment (keep the current wording verbatim). The fable
     fragment (SYNTHESIS_SKILLS + `capabilities.top_tier == "fable"`) is added **only when
     `tier == "full"`** (synthesis skills are all full-tier, so this is behavior-preserving,
     but gate it on `full` explicitly so `standard` can never emit fable).
  5. Return `" | ".join(fragments)` or `None` — unchanged.

  Keep the lazy imports (`from . import state as _state`, capabilities) exactly as-is.
  Do NOT touch SKILL.md files, DOMAIN_BY_SKILL, or context_budget_check. Full-tier output
  must be byte-identical to today's. Update the `skill_preamble` docstring to note the tier.

### Task 2: graduated-preamble tier tests
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest tests/test_lifecycle.py -q
- **serves:** REQ-5
- **spec:**
  Add focused tests for the new tier behavior to `tests/test_lifecycle.py` (append; do not
  modify the existing preamble tests, which must stay green). Cover:
  - `preamble_tier()` returns `"minimal"` for `resume`/`help`/`usage`/`analytics`/`approve`/
    `doctor`/`hygiene`/`check-plan`, `"standard"` for `audit`/`scan`/`inventory`, and `"full"`
    for an unlisted skill (e.g. `orchestrate`, `feature`) and for an unknown skill name.
  - A `minimal` skill returns `None` from `skill_preamble` **even after a cross-domain
    transition** — e.g. record a build skill first (`skill_preamble(tmp, "debug")`), then
    assert `skill_preamble(tmp, "resume") is None`.
  - `record_skill_invocation` still ran for a `minimal` skill: after the call above,
    `renmark.state.last_skill_invocation(tmp)["skill"] == "resume"` (proves cross-domain
    detection for the NEXT skill is preserved).
  - A `standard` skill (`audit`) **does** surface the cross-domain `/clear` hint after a
    build-domain skill, but never the fable hint even in a declared-fable repo (reuse the
    `_write_declared_fable_routing` helper): assert `"cross-domain transition"` in hint and
    `"declared top tier: fable"` not in hint.
  - Full-tier unchanged: a declared-fable `brainstorm` after a cross-domain transition still
    joins both hints (this may already be covered — do not duplicate if so).
  Follow the existing test style (tmp_path, monkeypatch.delenv RENMARK_TOP_TIER, the
  `_write_declared_fable_routing` helper). Keep tests deterministic and isolated.

---

## Cost preview

| Task | Executor | Tokens (incl. overhead) | Cost |
|---|---|---|---|
| 1 — tier-aware skill_preamble | sonnet | ~11,200 | ~$0.034 |
| 2 — tier tests | codex | ~900 | ~$0.020 |
| **Total** | — | **~12,100** | **~$0.05** |

Executors: sonnet×1, codex×1. Two waves (serial: task 2's tests exercise task 1's API).
