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

## P8-v2 revision (2026-07-01)

The v1 build was reviewed twice and found under-built at its core. Three findings
drove this redesign:

1. **Major 1 (fatal):** the deterministic tier could not produce a *current*
   model-driven transcript without a live call, so "replay" collapsed to asserting
   a stored golden against itself — it proved nothing.
2. **Un-bootstrappable:** `--accept`/`capture()` hard-failed and no snapshots were
   committed, so the reference cases always ERRORed on a fresh checkout.
3. **Weakened assertions:** a mini-format conversion dropped the real contract
   force ("explicit choice required", "menu terminal", "roadmap read-only").

**Root reframe (Google "New SDLC" tests-vs-evals split):** a skill's behavior is
*model-driven*, not a pure function — you cannot test it deterministically without
a live call. So P8-v2 splits into two honestly-labelled tiers:

- **Deterministic tier = a TEST.** It runs renmark's *real deterministic
  behavior-shaping code* (recomputed every run) and asserts the genuine current
  output. It is a **scaffolding / regression guard**, CI-safe — it does NOT prove
  the model follows the scaffolding.
- **Eval tier = the behavioral PROOF.** The live LLM-judge over a real model
  trajectory. Opt-in, out of CI. This is where the load-bearing proof lives.

Docs and command names MUST keep this split explicit — green CI (deterministic
tier) is **not** "the skill works"; only the eval tier proves that.

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

## Architecture (P8-v2)

- **`renmark/behavior.py`** — the harness. Loads declarative cases and, for the
  deterministic tier, **calls renmark's real behavior-shaping functions on live
  inputs** and asserts their genuine current output. No transcript replay; the
  output is recomputed by current code every run, so it is a true test rather than
  a golden echoed at itself (fixes Major 1). The eval-tier path (capture + judge)
  is separate and only reachable under explicit flags.
- **`renmark/judge.py`** — the LLM-as-judge / eval tier (unchanged from v1, which
  reviewed clean). Given a `(baseline, golden, actual)` triple and the skill's
  contract, returns a structured verdict (`pass|fail`, confidence, rationale);
  malformed payloads become `unvalidated`, never a silent pass. Escalation-only;
  carries the reasoning contract; reports cost.
- **Live runner wiring** — `capture()` and the judge escalation take a `str→str`
  subagent runner (the shape both modules already expect), wired to the real
  provider only under `--accept` / `--judge`. The default `--behavior` path never
  constructs a live runner, so **CI spends zero tokens** by construction.
- **CLI** — `renmark-execute --behavior` runs the **deterministic tier only**
  (real-code assertions, CI-safe); `--behavior --accept` records the **eval-tier**
  golden transcripts (deliberate live step); on a deterministic FAIL the CLI
  prints an OFFER line and escalates to the judge **only** when `--judge` is
  passed.

## Test corpus format (P8-v2)

`tests/behavioral/<skill>.behavior.json` (one file per skill), each case carries
**both** a deterministic block (asserted in CI against real-code output) and an
eval block (adjudicated by the judge on demand):

```
{
  "skill": "roadmap",
  "prompt": "<representative user prompt that exercises the skill's contract>",
  "deterministic": {
    "call": "<renmark function invoked, e.g. lifecycle.next_steps>",
    "assertions": [ "<checks over the genuine current output of that call>" ]
  },
  "eval": {
    "contract": "<plain-language behavioral contract the judge adjudicates>",
    "golden_ref": "<transcript snapshot under snapshots/ — recorded via --accept>"
  }
}
```

The deterministic block needs **no snapshot** — its input is computed at test
time, so it runs green on a fresh checkout (fixes the un-bootstrappable ERROR).
The eval block's `golden_ref` is recorded deliberately via `--accept` and is only
read by the judge tier.

## Data flow (P8-v2)

1. **Deterministic tier** (default `--behavior`, CI): for each case, invoke the
   named renmark function on live inputs and assert the current output satisfies
   the deterministic block. No network, no tokens, no snapshot dependency.
2. **Record eval goldens** (`--accept`, deliberate, live): dispatch a real
   subagent with the skill → record the eval `golden_ref` transcript under
   `snapshots/`.
3. **Escalate** (on a deterministic FAIL, or on demand): print the OFFER line;
   only when `--judge` is passed, `renmark/judge.py` runs live (~$0.15) over the
   real trajectory and returns a semantic verdict + rationale.

## Reference skills (MVP corpus) — P8-v2 tier split

Each case restores full contract force by splitting assertions across the two
tiers (this repairs the weakened-assertion finding):

- **next-steps menu contract**
  - *Deterministic:* call `lifecycle.next_steps(repo, "roadmap")` → assert the
    `NextSteps` struct is non-empty, `tier0` present, **recommended-first
    ordering**, `(Recommended)` label present, and the render includes the
    terminal Finish/Nothing fallback (menu is terminal, no dangling prose).
  - *Eval:* the agent **actually ended its real turn** with the menu (turn
    terminality in a live transcript — not provable from structure alone).
- **`roadmap` read-only**
  - *Deterministic:* the generated roadmap output `not_contains` `Agent(`,
    `codex exec`, or `renmark-execute --task`, and `plan_lint`'s read-only
    verdict holds (`_check_transcript_leak`).
  - *Eval:* the agent **stayed read-only across the whole live session** — no
    writes or commits attempted anywhere in the trajectory.

(Exact function bindings may be refined during planning if a cleaner
deterministic signal exists; the two-tier split is what matters.)

## Error handling (P8-v2)

- Deterministic tier: a named renmark function that errors or a failed assertion
  is a **FAIL**, reported with the mismatch; no snapshot is involved, so there is
  no "missing golden → ERROR" path for this tier.
- Eval tier: a missing eval `golden_ref` when `--judge` is requested → **error**,
  not pass ("run --accept first").
- Judge tier: gated behind explicit `--judge` + a surfaced cost note; a judge
  failure/timeout reports as `unvalidated`, never a silent green.
- Live capture/judge failure → reported with the executor error; the
  deterministic tier is unaffected (it never touches a live runner).

## Testing (the harness's own tests)

- Unit tests for the deterministic tier: real renmark functions asserted on fixed
  inputs (fully deterministic, free) — plus a negative test proving a broken
  scaffolding output FAILs.
- The 2 reference cases' deterministic blocks, runnable via `--behavior` in CI.
- Eval/judge tier: unit-tested with a mocked runner (assert `--accept`/`--judge`
  gating and verdict parsing, incl. malformed→`unvalidated`); the live path runs
  only on demand, never in CI.

## Success criteria (P8-v2)

- `renmark-execute --behavior` runs green and deterministically on a **fresh
  checkout** — no network, no token spend, no snapshot dependency (the
  un-bootstrappable ERROR is gone).
- The deterministic tier asserts **genuine current output of real renmark
  functions** — no golden-echoed-at-itself (Major 1 closed).
- ≥2 reference cases carry restored full-force assertions, correctly split into a
  deterministic block and an eval block.
- Eval/judge tier wired to a live `str→str` runner; reachable only under
  `--accept` / `--judge`; never auto-spends; cost surfaced before it runs.
- **Honest labelling:** docs + command help state that green `--behavior` is a
  scaffolding/regression guard, and the eval tier is the load-bearing behavioral
  proof — green CI is not "the skill works".
- `pytest -q`, `ruff check`, `mypy renmark/` all pass.
- CLAUDE.md / AGENTS.md updated to describe both tiers with the honest split
  (mirror in the same commit).

## Prior art & references

- `.renmark/research/2026-06-25-external-skills-study.research.md` — the study
  that proposed P8 (superpowers TDD skills + gstack Tier-3 LLM-judge).
- Internal reuse targets: `renmark/shadow.py` (baseline replay+diff),
  `renmark/dispatch.py` (mockable subagent runner),
  `tests/integration/test_dispatch_isolation_e2e.py` (closest existing pattern).
- Companion: `.renmark/specs/2026-06-29-p7-skill-templates.spec.md` (P7, merges
  alongside for v0.23.0).
