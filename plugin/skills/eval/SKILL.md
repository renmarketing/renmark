---
name: eval
description: "Use to run the in-session, agent-driven eval path — record golden transcripts or run the LLM-judge live inside the current agent session — typed as /renmark:eval (--judge or <skill>)."
disable-model-invocation: true
---

# eval

## Overview

`/renmark:eval` is the **in-session, agent-driven** eval path. It records eval
golden transcripts and runs the LLM-as-judge **live inside the current agent
session** — the session model, dynamic skill loading, and Agent-tool access are
all in play — rather than shelling out to an external CLI. That is the
distinctive value: the model turn that produces the golden (and the judge turn
that scores it) runs in *this* session, so the skill under test is actually
loaded and exercised the way a real user would trigger it.

This skill **composes** APIs that already ship (zero re-implementation):

- `behavior.load_cases("tests/behavioral")` → the eval cases;
- `behavior.compose_eval_prompt(case) -> str` → the skill-enabled golden prompt;
- `behavior.capture_from_transcript(case, transcript) -> str` → writes
  `snapshots/<golden_ref>.json` and returns the transcript unchanged;
- `judge.compose_judge_prompt(*, skill, prompt, baseline, golden, actual, contract) -> str`
  → the judge prompt;
- `judge.parse_judge_verdict(response) -> Verdict` → parses the judge's response
  into a `Verdict` (`outcome`, `confidence`, `validation_status`, `rationale`).

The model calls (golden capture, judge scoring) are the agent's own Agent-tool
turns — Python composes the prompts and parses the results; it never calls the
model here.

## When to Use

- To **record** eval golden transcripts for a skill in-session (the accept path).
- To **judge** a with-skill trajectory live with `--judge`, when the
  deterministic tier is green but you want the load-bearing semantic proof.
- Opt-in only — never in CI, never an auto token spend.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'eval')` and
surface the returned hint if non-None (a cross-domain transition into eval work
is worth a `/clear` note). Do not proceed past a blocking hint without acting on
it.

### 1. Parse args

Accept an optional `<skill>`/case filter and an optional `--judge` flag from
`$ARGUMENTS`. No filter → all cases; a filter → the matching case(s) only.
`--judge` enables the judge pass (Step 4); without it the run only records
goldens (Step 3).

### 2. Load cases

```python
cases = behavior.load_cases("tests/behavioral")
```

Apply the Step-1 filter to `cases`. Run **serially** and as a **singleton** —
one case's model turn at a time, no parallel dispatch (in-session eval is not a
fan-out lane).

### 3. Record the golden (per case, in-session)

For each selected case, in order:

1. `prompt = behavior.compose_eval_prompt(case)` — the skill-enabled golden
   prompt (activates `case.skill`).
2. **The agent issues a REAL Agent-tool call** with that `prompt` — an in-session
   model turn with the skill enabled — and captures the **full response text** as
   `transcript`. This is the model-calling half; it runs here, in this session,
   not through an external runner.
3. `behavior.capture_from_transcript(case, transcript)` — records the golden at
   `snapshots/<golden_ref>.json` and returns it unchanged.

### 4. Judge (only when `--judge`)

For each selected case, source the judge inputs exactly as
`behavior._escalate_to_judge` does (same v2 convention), then judge:

1. Gather the inputs:
   - `skill = case.skill`
   - `prompt = case.prompt` (the shared input given to the model)
   - `contract = case.eval.contract` (what the skill promises to change)
   - `actual` = the **with-skill transcript captured in Step 3** (the in-session
     output under test)
   - `golden` = the **recorded reference** for this case — read the existing
     snapshot at `snapshots/<case.eval.golden_ref>.json` (the golden from a prior
     accepted run). On the FIRST run there is no prior golden: Step 3 just
     established one, so `golden == actual` and the judge effectively scores
     `actual` against the `contract` alone — state this in the verdict rather than
     implying a real reference comparison.
   - `baseline = ""` — v2 keeps no recorded baseline; the judge weighs the
     contract against `actual` (this matches `_escalate_to_judge`).
   Then: `judge_prompt = judge.compose_judge_prompt(skill=skill, prompt=prompt, baseline=baseline, golden=golden, actual=actual, contract=contract)`.
2. **The agent issues a SECOND Agent-tool call** with `judge_prompt` — a second
   in-session model turn — and captures the response.
3. `verdict = judge.parse_judge_verdict(response)` — a `Verdict`
   (`outcome`, `confidence`, `validation_status`, `rationale`). Parses
   defensively: any parse/runner failure yields an unvalidated `fail`, never a
   silent pass.
4. Report the `Verdict` outcome (bounded — see Step 5).

### 5. Context hygiene (non-negotiable)

Transcripts and judge bodies are **high-context**. They go to disk only:

- goldens → `snapshots/<golden_ref>.json` (via `capture_from_transcript`);
- a run record → a `.renmark/reviews/YYYY-MM-DD-<sha>.eval.md` artifact.

**Write the run-record artifact explicitly** (do not just imply it) via
`summary.write_artifact` — this is what gives it G6 provenance metadata:

```python
from renmark import summary
summary.write_artifact(
    artifact_path,                     # .renmark/reviews/<date>-<sha>.eval.md
    artifact_type="eval",
    body=full_run_log,                 # per-case: skill, golden_ref, snapshot path,
                                       # and (if judged) the judge rationale — the
                                       # heavy detail lives HERE, never in chat
    summary_lines=verdict_lines,       # the same ≤5-line bounded block shown to chat
    related_plan=<plan path or "">,
    source_sha=summary.git_head_sha(repo),
    generator="eval",
    completion_state="complete",
    confidence="high" if all_judged_pass else "medium",
    validation_status="validated",
)
summary.emit_pointer(artifact_path, "eval")
```

Per case, the artifact body records: `skill`, `golden_ref`, the snapshot path,
and — if judged — `outcome`/`confidence`/`validation_status`/`rationale`.

Chat sees **ONLY a bounded ≤5-line verdict** (per case: skill + outcome +
confidence, plus the artifact path). **Never paste transcripts, judge prompts,
judge bodies, or golden contents into chat.** Violations are bugs, not
optimizations (G3).

### 6. Hand off

eval is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It reports; it never
advances the pipeline.

> *End by calling `renmark.lifecycle.next_steps(repo, "eval")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`.
> Render via `AskUserQuestion`
> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
> explicit choice. Do not paste the rendering rules or the gate menu — cite the
> files.*

## Boundaries

- **This is the IN-SESSION path.** The model turns (golden capture, judge) run
  inside the current agent session — session model + dynamic skill loading +
  Agent-tool access.
- **The subprocess CLI path is UNCHANGED.** `renmark-execute --behavior --accept`
  and `renmark-execute --behavior --judge` (with `RENMARK_EVAL_RUNNER_CMD`) remain
  the CI / headless option; this skill does not alter it.
- **The DETERMINISTIC tier remains the always-safe default.** `--behavior` (no
  `--accept`/`--judge`) makes no model call, no network, no token spend — it is
  the CI-safe scaffolding guard, untouched by this skill.
- **Opt-in, out-of-CI, no auto token spend.** The judge and golden-capture model
  turns run only when the user explicitly invokes this path.
- **Does not touch the deterministic tier or the dispatch schema.** No change to
  `renmark.dispatch.build_subagent_input`, `assert_metadata_only`, or the
  behavioral deterministic tier.

## Governance compliance

- **G3 (bounded output)** — transcripts/judge bodies go to `snapshots/` and the
  `.renmark/reviews/*.eval.md` artifact; chat sees a ≤5-line verdict only.
- **G6 (provenance)** — the eval artifact is written via `summary.write_artifact`,
  so freshness/provenance metadata is automatic.
- **Explicit uncertainty over silent success** — a missing golden or unparseable
  judge response yields an unvalidated `fail`, never a silent pass.

See `CLAUDE.md` governance rules for definitions.
