# Plan: Release 9 — Calibrated blind LLM-judge (governed-orchestration-assurance)

**Context.** `renmark/judge.py`'s `Outcome` currently is `Literal["pass", "fail"]`
(`judge.py:36`) and every parse failure, runner error, or missing-golden case is
collapsed into `outcome="fail", validation_status="unvalidated"` — a
fail-as-uncertain-proxy. This release makes `Outcome` a real 3-state
`Literal["pass", "fail", "uncertain"]` so "the judge couldn't tell" is
represented honestly instead of masquerading as an adjudicated fail.

**THIS IS A BREAKING, COMPILE-TIME-VISIBLE CHANGE, deliberately not a silent
additive default** (target-blueprint.md §2.2). Every real caller that
constructs or pattern-matches on the old 2-state vocabulary must be updated in
THIS release, not deferred — an un-updated caller would silently mishandle or
never produce the new `uncertain` state. Fresh investigation (this session,
2026-08-05) found:

- `renmark/judge.py` itself — `_parse_response` and `judge_behavior`'s
  exception handlers are the primary sites that currently hardcode
  `outcome="fail"` for parse failures / unrecognized outcome / unrecognized
  confidence / missing rationale / runner errors — these become `"uncertain"`.
- `renmark/behavior.py`'s `_escalate_to_judge` (lines ~1117-1133) — two
  defensive fallback dicts that hardcode `"outcome": "fail"` for an unreadable
  or missing golden snapshot. These are the exact "collapsing every parse
  failure into fail" pattern the roadmap calls out — they become `"uncertain"`.
- `renmark/cli/_dispatch_flags.py` and `tests/test_behavior.py` were checked
  and do **not** branch on the judge's `outcome` value — they carry
  `result.judge_verdict` as an opaque dict / use `result.status`
  (PASS/FAIL/ERROR, a separate vocabulary) — no change needed there.
- `tests/test_judge.py` and `tests/test_eval_agent_turn.py` assert
  `verdict.outcome == "fail"` for parse-failure/garbage-response cases — these
  assertions encode the old collapse-to-fail behavior and must flip to
  `"uncertain"`, plus gain new coverage for the third arm, redaction, and
  order-randomization.
- No other file in `renmark/`, `tests/`, or `plugin/` imports `judge.Outcome`
  or does `Literal["pass", "fail"]`-style exhaustive matching (verified via
  `grep -rn "judge\.\|from renmark import judge\|from renmark\.judge"` across
  `renmark/`, `tests/`, `plugin/`).

**Non-goal enforcement (binding, do not violate in any task below).**
`judge.py` and `ledger.py` stay two separate leaf modules connected for the
FIRST time by this release, one-directionally and reference-only:
`InspectionReport.judge_evidence` is an **attachment**, never a merge. A judge
verdict NEVER writes to or overrides `InspectionReport.verdict` or
`ledger.VERDICTS` — those stay governed solely by `ledger.py`'s own verdict
vocabulary. `ledger.py` already has `from __future__ import annotations`
(module top), so `judge_evidence`'s type annotation can be a bare forward-ref
(`"JudgeEvidenceRef | None"`) that is never evaluated at runtime — this avoids
introducing ANY import of `judge.py` into `ledger.py`, module-level or
function-local, sidestepping the cycle risk entirely (safer than mirroring
Release 8's function-local `subagent_gate` import, since no import is needed
at all here).

---

### Task 1: judge.py — 3-state Outcome, redaction, order-randomization, JudgeEvidenceRef
- **mode:** B
- **target:** renmark/judge.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 2200
- **est_cost_usd:** 0.1830
- **verifier:** python3 -c "from renmark.judge import Outcome, JudgeEvidenceRef, compose_judge_prompt, judge_behavior, Verdict; import typing; assert typing.get_args(Outcome) == ('pass','fail','uncertain')" 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  Breaking change, in-place in `renmark/judge.py`:

  1. Change `Outcome = Literal["pass", "fail"]` (line 36) to
     `Outcome = Literal["pass", "fail", "uncertain"]`. Update
     `_VALID_OUTCOMES` to `frozenset({"pass", "fail", "uncertain"})`.
  2. Semantic fix in `_parse_response`: every branch that currently returns
     `outcome="fail", validation_status="unvalidated"` because the response
     could NOT be trusted (empty response, unparseable JSON, unrecognized
     `outcome` string, unrecognized `confidence` string, missing/empty
     rationale) must instead return `outcome="uncertain"`. Only a model
     response that is fully parsed, has a recognized `outcome` value, and
     that recognized value is literally `"fail"` should produce a validated
     `outcome="fail"`. Preserve `validation_status="unvalidated"` on all these
     branches (unchanged) — only the `outcome` field flips. Update each
     branch's `rationale` string only if needed for grammar (do not otherwise
     rewrite them).
  3. Same semantic fix in `judge_behavior`'s two `except` handlers
     (`JudgeUnavailable` and the generic `Exception` catch): both currently
     hardcode `outcome="fail"`; change both to `outcome="uncertain"` — a
     runner failure means "we don't know," not "the judge decided fail."
  4. Update the prompt text in `_build_prompt`: the JSON schema line becomes
     `'{"outcome": "pass"|"fail"|"uncertain", "confidence": ...}'` and the
     trailing instruction sentence changes from `'Use "pass" only if ...
     ... When uncertain, prefer "fail" with low confidence.'` to something
     like: `'Use "pass" only if the with-skill output honors the contract
     relative to the baseline. Use "fail" only if you are confident it does
     not. If the evidence is genuinely ambiguous or insufficient to decide,
     use "uncertain" with low confidence rather than guessing.'`
  5. Redaction step: add a private helper `_redact_worker_fields(data: dict)
     -> dict`, called at data-assembly time BEFORE string composition (not a
     post-hoc filter over the rendered prompt) that strips Worker-authored
     self-assessment/confidence/identity/preferred-verdict keys (e.g.
     `self_assessment`, `worker_confidence`, `dispatch_identity`,
     `preferred_verdict`, `claimed_status`). Widen `golden`/`actual` to
     `str | dict[str, object]`: dict payloads are redacted then
     `json.dumps`-ed into the prompt; strings pass through unchanged.
     Document the contract in the module and `compose_judge_prompt`
     docstrings.
  6. Order-randomization for the BASELINE-vs-ACTUAL comparison (the only
     pairwise call path here): add a keyword-only `swap_order: bool = False`
     to `_build_prompt`/`compose_judge_prompt`/`judge_behavior`; when `True`,
     swap which of BASELINE/ACTUAL is labeled first (still clearly labeled,
     only position changes). Do NOT add `swapped` to `Verdict` (keep its 4
     existing fields unchanged). Instead add a small frozen dataclass
     `JudgeCallRecord(swapped: bool, outcome: Outcome, confidence:
     Confidence)` plus a module-level `resolve_swap_order(seed: object |
     None = None) -> bool` helper a future caller can use to decide/record
     the swap before calling `judge_behavior(..., swap_order=...)`.
     `judge_behavior`'s return type stays `-> Verdict` (backward-compatible;
     existing callers unaffected). Do not write `swapped` into
     `Verdict.rationale` — that pollutes the rationale field; the caller (a
     future eval-harness task, out of scope here) records `swap_order`
     alongside the verdict itself, e.g. via `JudgeCallRecord`.
  7. Add `JudgeEvidenceRef`: a small frozen dataclass in `judge.py` (not
     `ledger.py`) with fields `subject_ref: str`, `outcome: Outcome`,
     `confidence: Confidence`, `validation_status: ValidationStatus`,
     `rationale: str`, `swapped: bool = False`. This is the reference type
     `InspectionReport.judge_evidence` points at (Task 3) — it is
     reference-only evidence, never authoritative over `InspectionReport.verdict`.
     Add a small factory `JudgeEvidenceRef.from_verdict(subject_ref: str,
     verdict: Verdict, *, swapped: bool = False) -> "JudgeEvidenceRef"`
     classmethod for convenience.
  8. Update the module docstring and any affected function docstrings to
     describe the 3-state vocabulary, the redaction contract, and the
     non-goal (`judge.py` never writes to `ledger.InspectionReport.verdict`).
  9. Keep `JUDGE_EST_COST_USD`, `SubagentRunner`, `_default_subagent_runner`,
     `_strip_code_fence`, `_find_balanced_brace`, `_extract_json_object`
     unchanged. Keep `Verdict`'s 4 existing fields unchanged (additive-only
     elsewhere in this program, per the compatibility guarantee).
  10. Add `"JudgeEvidenceRef"` and `"resolve_swap_order"` to `__all__` if one
      exists in this module (it does not currently — do not add one; keep the
      module's existing no-`__all__` convention).

### Task 2: behavior.py — flip fail-as-uncertain-proxy fallbacks to real uncertain
- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.0315
- **verifier:** python3 -c "src=open('renmark/behavior.py').read(); assert '\"outcome\": \"uncertain\"' in src" 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  In `renmark/behavior.py`'s `_escalate_to_judge` (~lines 1099-1145), the two
  defensive fallback dicts that currently return
  `{"outcome": "fail", "confidence": "low", "validation_status": "unvalidated",
  "rationale": ...}` for (a) a golden snapshot that fails to read (the
  `except (json.JSONDecodeError, OSError, BehaviorConfigError)` branch) and
  (b) a golden that is `None`, must change `"outcome"` from `"fail"` to
  `"uncertain"` — "the judge could not be consulted" is not the same as "the
  judge decided fail." `validation_status` stays `"unvalidated"` in both
  branches (unchanged). Do not change `run()`'s separate `_eval_golden_missing`
  short-circuit to `status="ERROR"` — that path already avoids calling
  `_escalate_to_judge` at all and is untouched. Do not change any other
  behavior in this file — this is a two-string-literal change plus the
  associated docstring/comment wording if it references "fail" for these
  cases (update to "uncertain" for accuracy). Depends on Task 1 only insofar
  as `judge.Outcome` must already include `"uncertain"`; this task does not
  import anything new from `judge.py`.

### Task 3: ledger.py — additive judge_evidence field on InspectionReport
- **mode:** B
- **target:** renmark/ledger.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.0318
- **verifier:** python3 -c "from renmark import ledger; import dataclasses; f={fl.name for fl in dataclasses.fields(ledger.InspectionReport)}; assert 'judge_evidence' in f; r=ledger.InspectionReport(judge_evidence=None); assert r.judge_evidence is None" 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  In `renmark/ledger.py`'s `InspectionReport` dataclass (~line 277-303), add
  ONE new additive field after `contract_ref`:
  `judge_evidence: "JudgeEvidenceRef | None" = None` — use the bare string
  forward-ref exactly as shown (the module already has
  `from __future__ import annotations` at the top, so this annotation is
  never evaluated at runtime and requires **no import** of `judge.py` into
  `ledger.py`, module-level or function-local — this is the safer of the two
  options investigated, since it introduces zero import-cycle risk between
  the two leaf modules). Extend the class docstring with a short paragraph
  matching the existing `risk_tier`/`lens`/`contract_ref` style: additive,
  Release 9, `judge_evidence` is optional reference-only evidence pointing at
  a `judge.JudgeEvidenceRef`, attached — never merged — and it NEVER
  overrides `verdict` (`VERDICTS` stays the sole verdict vocabulary; add one
  explicit sentence restating this non-goal, mirroring the existing
  `contract_ref` docstring's "the two shapes stay separate on purpose" style).
  In `validate_inspection_report` (~line 405-416), add one line:
  `issues += _check_opt_str(data, "judge_evidence")` is WRONG (it's not a
  string) — instead add a small dedicated check: since `judge_evidence` when
  serialized (e.g. via `dataclasses.asdict`) becomes a nested dict or `None`,
  add a permissive check that only rejects a non-null, non-dict value:
  ```python
  if "judge_evidence" in data and data["judge_evidence"] is not None:
      if not isinstance(data["judge_evidence"], dict):
          issues.append(
              f"'judge_evidence' must be a dict or null, got "
              f"{type(data['judge_evidence']).__name__}"
          )
  ```
  Do not touch `VERDICTS`, `WorkOrder`, `WorkResult`, `Escalation`,
  `InspectionContract`, `classify_risk_tier`, or any other section of this
  file. Do not import `renmark.judge` anywhere in this file.

### Task 4: test_judge.py — 3-state outcome, redaction, order-randomization coverage
- **mode:** B
- **target:** tests/test_judge.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.05
- **verifier:** python3 -m pytest tests/test_judge.py -q 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  Update `tests/test_judge.py` for Task 1's changes:
  1. Flip the existing assertions that currently expect
     `verdict.outcome == "fail"` for cases that are actually parse-failure /
     unrecognized-field cases (unrecognized `outcome` value e.g. `"maybe"`,
     unrecognized `confidence` value, missing rationale) to
     `verdict.outcome == "uncertain"`. `validation_status` assertions on
     these cases stay `"unvalidated"` (unchanged).
  2. Add a new test asserting a validated `outcome == "fail"` round-trips
     correctly when the model legitimately returns
     `{"outcome": "fail", "confidence": "high", "rationale": "..."}` —
     `validation_status == "validated"` in that case (regression guard that
     a real fail verdict is not accidentally coerced to uncertain).
  3. Add a new test asserting `{"outcome": "uncertain", "confidence": "low",
     "rationale": "insufficient evidence"}` parses to a validated
     `outcome == "uncertain"`, `validation_status == "validated"` (the third
     arm is a legitimate model-returned value, not only a parse-failure
     fallback).
  4. Add a test asserting `judge.judge_behavior`'s `JudgeUnavailable` and
     generic-exception paths both now return `outcome == "uncertain"` (not
     `"fail"`).
  5. Add a redaction test: construct a dict payload for `actual` (or `golden`)
     containing a Worker-authored key such as `self_assessment` or
     `worker_confidence` or `preferred_verdict`, call
     `judge.compose_judge_prompt(...)`, and assert the composed prompt string
     does NOT contain that key's value substring — proving the redaction
     happens before string composition.
  6. Add an order-randomization test: call `judge.compose_judge_prompt` (or
     `_build_prompt` via the public wrapper) twice with `swap_order=False`
     and `swap_order=True` and assert the BASELINE/ACTUAL section ordering in
     the composed string differs between the two, and that
     `judge.resolve_swap_order` exists and returns a `bool`.
  7. Add a `JudgeEvidenceRef` round-trip test:
     `ref = judge.JudgeEvidenceRef.from_verdict("subject-1", verdict)` then
     assert its fields match the source `Verdict`'s fields plus `subject_ref`.
  Do not remove or weaken any existing test not touched by this list.

### Task 5: test_eval_agent_turn.py — flip garbage-response assertion
- **mode:** B
- **target:** tests/test_eval_agent_turn.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 300
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_eval_agent_turn.py -q 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  In `test_parse_judge_verdict_returns_unvalidated_fail_on_garbage` (~line
  162-166), the garbage-response case (`judge.parse_judge_verdict("not json
  at all")`) currently asserts `verdict.outcome == "fail"`. Per Task 1's
  semantic fix, an unparseable response is now `outcome == "uncertain"`
  (still `validation_status == "unvalidated"`). Update the assertion to
  `verdict.outcome == "uncertain"` and rename the test function to
  `test_parse_judge_verdict_returns_unvalidated_uncertain_on_garbage` (update
  the call site if this name is referenced elsewhere — grep this file only,
  no other file references this function name). Leave
  `test_parse_judge_verdict_returns_validated_verdict_for_valid_json`
  unchanged (it already asserts the legitimate `"pass"` case).

### Task 6: test_behavior.py — cover the flipped judge-unavailable fallbacks
- **mode:** B
- **target:** tests/test_behavior.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.035
- **verifier:** python3 -m pytest tests/test_behavior.py -q 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  Add one new test exercising `behavior._escalate_to_judge`'s unreadable-
  golden fallback directly (import it as `from renmark.behavior import
  _escalate_to_judge` or drive it through `behavior.run(..., judge=True)`
  with a case whose golden snapshot file exists but contains invalid JSON,
  forcing the `except (json.JSONDecodeError, OSError, BehaviorConfigError)`
  branch) and assert the resulting `result.judge_verdict["outcome"] ==
  "uncertain"` (was `"fail"` before Task 2). Follow this file's existing
  `_case`/`_write_golden` helper patterns already used by the surrounding
  tests (e.g. `test_judge_escalation_runs_only_for_deterministic_fail_when_enabled`
  at ~line 197). Do not modify any existing passing test's assertions — this
  is an additive test only, since no existing test in this file currently
  exercises the unreadable/missing-golden fallback branches inside
  `_escalate_to_judge` (they're masked upstream by `run()`'s
  `_eval_golden_missing` short-circuit to `status="ERROR"` for the missing
  case — this new test targets the *unreadable* variant specifically, which
  is not masked).

### Task 7: test_ledger.py — judge_evidence attach/round-trip + non-goal guard
- **mode:** B
- **target:** tests/test_ledger.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.035
- **verifier:** python3 -m pytest tests/test_ledger.py -q 2>&1 | tail -3
- **serves:** AC-6
- **spec:**
  Add tests to `tests/test_ledger.py` following the file's existing
  `InspectionReport`-construction pattern (see ~line 47-59 and ~line
  205-207):
  1. Construct `ledger.InspectionReport(subject_ref="x", verdict="pass",
     judge_evidence={"outcome": "uncertain", "confidence": "low",
     "validation_status": "unvalidated", "rationale": "ambiguous",
     "subject_ref": "x"})` (a plain dict, mirroring how a serialized
     `judge.JudgeEvidenceRef` would round-trip through `dataclasses.asdict`),
     serialize with `dataclasses.asdict`, and assert `verdict` stays
     `"pass"` and `judge_evidence` round-trips unchanged — proving attachment
     never touches `verdict`.
  2. Call `ledger.validate_inspection_report(data)` with a valid
     `judge_evidence` dict and assert no issues; with `judge_evidence: None`
     and assert no issues; with `judge_evidence: "not-a-dict"` and assert an
     issue naming `judge_evidence` is returned.
  3. Add a guard test (the non-goal enforcement) asserting `renmark/ledger.py`
     has no import of `renmark.judge` or `renmark.judge.InspectionReport`-
     writing code: read `renmark/ledger.py`'s source text and assert
     `"import judge" not in text and "from renmark.judge" not in text and
     "from .judge" not in text and "renmark.judge" not in text` (a simple
     source-grep guard, not a runtime import-graph tool — keep it
     dependency-free). Also assert `ledger.VERDICTS == ("pass", "fail",
     "escalate")` is unchanged (regression guard that Task 3 did not widen
     the verdict vocabulary).

---

## Cost preview

| Executor | Tasks | Notes |
|---|---|---|
| opus | 1 | judge.py core breaking change — hard/architecture-adjacent, escalation justified |
| sonnet | 2 | behavior.py fallback flip, ledger.py additive field |
| codex | 4 | test_judge.py, test_eval_agent_turn.py, test_behavior.py, test_ledger.py |

Tasks: 7 (3 parallel groups — group 1: judge.py; group 2: behavior.py +
ledger.py; group 3: all 4 test files)

| Task | Executor | est_tokens | overhead | $/kT | est_cost_usd |
|---|---|---|---|---|---|
| 1 judge.py | opus | 2200 | 10000 | 0.015 | 0.1830 |
| 2 behavior.py | sonnet | 500 | 10000 | 0.003 | 0.0315 |
| 3 ledger.py | sonnet | 600 | 10000 | 0.003 | 0.0318 |
| 4 test_judge.py | codex | 1200 | 0 | ~0.03-0.05 | 0.05 |
| 5 test_eval_agent_turn.py | codex | 300 | 0 | ~0.03 | 0.03 |
| 6 test_behavior.py | codex | 700 | 0 | ~0.03 | 0.035 |
| 7 test_ledger.py | codex | 700 | 0 | ~0.03 | 0.035 |

Total tokens (incl. Agent overhead): 12200 + 10500 + 10600 + 1200 + 300 + 700 + 700 = **~36,200**
**Total cost: ~$0.396**
