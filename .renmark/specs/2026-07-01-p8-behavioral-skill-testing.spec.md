<!--
artifact_type: spec
schema_version: 1
created_at: 2026-07-01T00:00:00Z
source_sha: b286cc0
related_plan: null
generator: brainstorm
stale_after: null
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
  - .renmark/specs/2026-06-29-p7-skill-templates.spec.md
-->

# Spec — P8: Behavioral skill testing + LLM-as-judge eval tier

**Topic:** p8-behavioral-skill-testing
**Target release:** v0.23.0 (combined with the P7 skill-consistency lint, which is
already built on branch `worktree-p7-skill-templates` and only needs merging).
**Source study:** `.renmark/research/2026-06-25-external-skills-study.research.md`
(P8 = item 8; inspired by superpowers' TDD-authored skills + gstack's Tier-3
LLM-judge eval).

## Context

Renmark's audit (`renmark-execute --audit`) and lint layer test that a skill is
*structurally* correct — registry consistency, description drift, next-steps
citation, shared-block signatures. Nothing tests that a skill actually **changes
agent behavior**. A skill can lint clean and still fail to do its job.

P8 closes that gap by hardening skills the way renmark already hardens products:
a **deterministic behavioral tier** (baseline-fail → add skill → pass, replayed
in CI against recorded golden transcripts) plus an **opt-in LLM-as-judge tier**
that adjudicates semantic behavior when the deterministic check fails or is
ambiguous.

## Goals

1. Prove a skill changes behavior: capture a subagent transcript **without** the
   skill (baseline — must fail/differ) and **with** the skill (golden — must
   pass), and assert the difference is real.
2. Run deterministically in CI: **no network, no token spend** on the default
   path — replay recorded goldens and diff, reusing the `renmark/shadow.py`
   baseline-accept pattern.
3. Provide a semantic safety net: an LLM-as-judge tier, **fully implemented but
   escalation-only** — offered on a deterministic failure, run only on explicit
   opt-in (~$0.15/run), never silent (mirrors renmark's T2 web-research gating).
4. Seed the corpus with **2 reference skills** as the proven pattern others copy.

## Non-goals (feature-scoped)

- Behavioral coverage of all ~30 skills — MVP seeds 2 reference cases; broader
  coverage is follow-up work.
- The P7 `.tmpl`→SKILL.md generator — deliberately dropped (shared blocks are
  already single-sourced under `plugin/skills/_shared/*.md`); P7 ships as the
  consistency lint on its existing branch.
- Changing or replacing the structure audit (`renmark/audit.py`,
  `renmark/lint.py`, `renmark/skillgen.py`) — P8 is additive.
- Auto-spending on the judge tier — it is opt-in only.

## Architecture

- **`renmark/behavior.py`** — the harness. Loads declarative cases, orchestrates
  capture / replay / diff, and owns the escalation offer. Builds on
  `renmark/shadow.py` (`run_subsystem` / `accept_subsystem` — golden replay+diff
  with accept-snapshots).
- **`renmark/judge.py`** — the LLM-as-judge tier. Given a `(baseline, golden,
  actual)` triple and the skill's contract, returns a structured verdict
  (`pass|fail`, confidence, rationale). Escalation-only; carries the reasoning
  contract; reports cost.
- **Dispatch** — live capture and judge calls go through `renmark/dispatch.py`'s
  mockable `subagent_runner` injection point (`dispatch_task_isolated` /
  `parse_subagent_response`), keeping tests injectable.
- **CLI** — `renmark-execute --behavior` runs the deterministic replay tier;
  `--behavior --judge` (or an interactive opt-in on failure) enables the judge
  escalation; `--behavior --accept` (re)records goldens deliberately.

## Test corpus format

`tests/behavioral/<skill>.behavior.json` (one file per skill), each case:

```
{
  "skill": "roadmap",
  "prompt": "<representative user prompt that exercises the skill's contract>",
  "assertions": [ "<deterministic checks over the transcript>" ],
  "baseline_ref": "<snapshot path — subagent WITHOUT the skill>",
  "golden_ref":   "<snapshot path — subagent WITH the skill>"
}
```

Snapshots (recorded transcripts) live alongside as accept-snapshots, managed by
the shadow accept pattern. A case **errors** (never silently passes) if its
golden is missing — you must `--accept` first.

## Data flow

1. **Capture** (`--accept`, deliberate, live): dispatch a real subagent with and
   without the skill → record `golden_ref` and `baseline_ref`.
2. **Replay** (default, CI, deterministic): re-run the recorded interaction,
   diff against `golden_ref`; assert (a) the with-skill transcript matches the
   golden and (b) it differs meaningfully from the baseline (skill had an
   effect). Pure diff — no network, no tokens.
3. **Escalate** (on deterministic failure): report the failure and **offer** the
   judge tier; on explicit opt-in, `renmark/judge.py` runs live (~$0.15) and
   returns a semantic verdict + rationale.

## Reference skills (MVP corpus)

- **`roadmap`** — asserts the read-only / zero-LLM contract: status mode makes no
  LLM calls and writes only its own snapshot (a strong, checkable behavioral
  invariant).
- **next-steps menu contract** — asserts a skill ends its turn with an
  `AskUserQuestion` next-steps menu (recommended-first), a cross-cutting
  behavioral rule the structure lint can't verify.

(Exact second skill may be swapped during planning if a cleaner deterministic
signal is available; the pattern is what matters.)

## Error handling

- Missing golden/baseline snapshot → **error**, not pass ("run --accept first").
- Judge tier: gated behind explicit opt-in + a surfaced cost note; a judge
  failure/timeout reports as `unvalidated`, never a silent green.
- Live capture failure → reported with the executor error; deterministic tier is
  unaffected (it only reads recorded snapshots).

## Testing (the harness's own tests)

- Unit tests for the replay/diff logic with a mocked `subagent_runner` (fully
  deterministic, free).
- The 2 reference behavioral cases themselves, runnable via `--behavior` in CI.
- Judge tier: unit-tested with a mocked runner (assert gating/opt-in and verdict
  parsing); the live path is exercised only on demand, never in CI.

## Success criteria

- `renmark-execute --behavior` runs green and deterministically in CI — no
  network, no token spend.
- ≥2 reference behavioral cases prove baseline-fail → with-skill-pass.
- LLM-judge escalation implemented, opt-in-gated, never auto-spends; cost
  surfaced before it runs.
- `pytest -q`, `ruff check`, `mypy .` all pass.
- CLAUDE.md / AGENTS.md updated to describe the behavioral tier (mirror in the
  same commit).

## Prior art & references

- `.renmark/research/2026-06-25-external-skills-study.research.md` — the study
  that proposed P8 (superpowers TDD skills + gstack Tier-3 LLM-judge).
- Internal reuse targets: `renmark/shadow.py` (baseline replay+diff),
  `renmark/dispatch.py` (mockable subagent runner),
  `tests/integration/test_dispatch_isolation_e2e.py` (closest existing pattern).
- Companion: `.renmark/specs/2026-06-29-p7-skill-templates.spec.md` (P7, merges
  alongside for v0.23.0).
