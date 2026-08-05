# Plan: Release 10 — Failure-derived constraint registry (governed-orchestration-assurance)

**Context.** roadmap.md's Release 10 section (revised 2026-08-05 for
peer-review Gap 4) closes AC-7 (PRD Req 7): a curated, versioned,
cross-run **failure-derived constraint registry** — rules created only from
OBSERVED failures/near-misses/repeated review findings, each with a
lifecycle (`proposed`→`active`→`deprecated`), dedup/contradiction detection,
and a periodic review mechanism. prd-acceptance-map.md's AC-7 row and its
REQ-24 row are explicit that this is **distinct** from
`renmark/recurrence.py`'s existing REQ-24 mechanism
(`pre_attempt`/`observe_issue`/`acknowledge_issue`/`resolve_issue`) — a
narrower, already-working, **per-run/fingerprint-scoped** recurrence
detector that stops a 3rd equivalent attempt inside one session. The two do
not merge: REQ-24 answers "have I seen this exact failure signature
recently, in this run/session lineage" and gates a retry; Req 7 answers
"has the project accumulated enough evidence to make this a standing,
curated constraint that should shape every future dispatch matching its
applicability" and gates a subagent's `WorkOrder.constraints`.

**THIS RELEASE DOES NOT TOUCH REQ-24's EXISTING BEHAVIOR.** Every one of
`pre_attempt`, `observe_issue`, `acknowledge_issue`, `resolve_issue`, their
dataclasses (`IssueObservation`, `RecurrenceDecision`), and their persisted
schema (`.renmark/state/recurrences.json`, `STATE_VERSION = 1`) stay
byte-for-byte unchanged. This release is purely additive: a new
`FailureRule` structure living alongside REQ-24 inside `recurrence.py` (per
roadmap's non-goals section and modularity-assessment §6 — extend, don't
add a sibling module), with `recurrence.py`'s existing `durable_guard`
entries (a `remediation_class` value already assigned to entries observed
3+ times) becoming ONE read-only evidence input a `FailureRule`'s
`source_evidence` can cite — never the registry itself, never mutated or
replaced by this work.

**New in this release beyond the registry itself:** `subagent_gate.py`
(Release 6's pre-dispatch funnel, alongside `justify_task` /
`validate_r008_dispatch` / `check_capability_envelope`) gains a fourth,
independent, zero-LLM check that consumes ONLY `status: active`
`FailureRule` entries, matches them against a dispatch's `applicability`,
and populates `WorkOrder.constraints` (Release 3's placeholder field,
currently unpopulated by any code path). Per the roadmap's compatibility
guarantee #7, constraint text still only reaches a subagent through the
existing `dispatch.build_subagent_input` funnel (confirmed unchanged by
grep — `dispatch.py` has no `constraints` references today); this release
does not add a second prompt-composition pathway, only a verdict + a
populated `constraints` dict a future release's dispatch path can read.

**ADR precondition.** Per the roadmap's migration step (a), the ADR
(Task 1) is a precondition for the code tasks and is written first,
independent of any file the code tasks touch.

---

### Task 1: ADR-051 — Req 7 (failure-derived constraint registry) vs REQ-24 (recurrence.py)
- **mode:** B
- **target:** .renmark/memory/decisions.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** grep -c "^## ADR-051" .renmark/memory/decisions.md | grep -q "^1$" && echo OK
- **serves:** AC-7
- **spec:**
  Prepend a new ADR entry at the TOP of `.renmark/memory/decisions.md` (above
  the current `## ADR-050` entry — this file lists newest-first), numbered
  `## ADR-051 — Failure-derived constraint registry (Req 7) is distinct from
  recurrence.py's REQ-24 recurrence-prevention`, following the exact
  `**Date:**` / `**Status:**` / `**Context.**` / `**Decision.**` structure
  ADR-050 uses (read ADR-050 in full for the format — do not invent a new
  ADR shape). Content requirements:

  1. **Context** must name both mechanisms precisely and cite
     `prd-acceptance-map.md`'s AC-7 row and REQ-24 row verbatim reasoning:
     REQ-24 (`renmark/recurrence.py`'s `pre_attempt`/`observe_issue`/
     `acknowledge_issue`/`resolve_issue`) is a same-run/cross-run
     **fingerprint-based** recurrence detector — it tracks one logical issue
     key (`check:rule_id:target`), counts occurrences, and blocks a 3rd
     equivalent attempt until acknowledged or resolved. It has no concept of
     a curated rule, no lifecycle beyond `open`/`acknowledged`/`resolved`,
     and is scoped to the fingerprint sequence of ONE recurring issue, not a
     library of standing constraints. Req 7 (this release) is a **curated,
     versioned, cross-run constraint registry**: rules are proposed only
     from observed failures/near-misses/repeated review findings (which MAY
     include a `durable_guard`-classified `recurrence.py` entry as one
     evidence input, never the registry itself), carry a
     `proposed`/`active`/`deprecated` lifecycle, dedup/contradiction
     detection across rules, and a `review_after` staleness mechanism —
     and, once `active`, are consulted by `subagent_gate.py` at dispatch
     time to populate `WorkOrder.constraints` for matching dispatches. State
     plainly: these solve different problems (retry-throttling within a
     recurring-issue sequence vs. standing cross-run constraints library)
     and neither supersedes the other.
  2. **Decision** must state, in one explicit sentence each: (a) REQ-24's
     four functions and its persisted schema in
     `.renmark/state/recurrences.json` are UNCHANGED by this release; (b)
     the new `FailureRule` structure lives inside `recurrence.py` (not a new
     module) per the roadmap's non-goals section; (c) a `durable_guard`
     entry (an existing `remediation_class` value on a `recurrence.py`
     entry) becomes one allowed `source_evidence` input for a proposed
     `FailureRule` — reading it never writes to or replaces the entry; (d)
     `subagent_gate.py` consumes only `status == "active"` rules, never
     `proposed` or `deprecated`, and cites the matched `rule_id` in its
     verdict rather than composing prompt text itself (the existing
     `dispatch.build_subagent_input` funnel is the sole prompt-composition
     path, unchanged).
  3. Follow ADR-050's closing convention (a stop-condition / consequence
     sentence). Do not remove, renumber, or edit any existing ADR entry —
     this is a pure prepend.

### Task 2: recurrence.py — FailureRule registry, lifecycle, dedup, review
- **mode:** B
- **target:** renmark/recurrence.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 2500
- **est_cost_usd:** 0.0375
- **verifier:** python3 -c "
from renmark import recurrence as r
import dataclasses
assert {f.name for f in dataclasses.fields(r.FailureRule)} >= {'rule_id','status','trigger','applicability','required_behavior','prohibited_failure','source_evidence','enforcement','regression_test_ref','created_at','last_triggered_at','review_after'}
assert r.observe_issue and r.pre_attempt and r.acknowledge_issue and r.resolve_issue
print('OK')
" 2>&1 | tail -5
- **serves:** AC-7
- **spec:**
  Add a genuinely new, additive section to `renmark/recurrence.py` (do NOT
  modify any existing REQ-24 function, dataclass, constant, or the
  `recurrences.json` schema — this is append-only to the file). Match the
  module's existing conventions: `from __future__ import annotations`,
  frozen `@dataclass(slots=True)` value objects, pure functions that accept
  `repo: str | os.PathLike[str]`, an advisory-locked atomic
  read-modify-write persistence helper mirroring `_read_state`/`_write_state`
  (reuse the same `tempfile` + `os.replace` + `_advisory_lock` pattern —
  factor a second lock/state pair, do not share the `recurrences.json` lock
  or file).

  1. **Storage location.** Registry lives at
     `.renmark/memory/failure_rules.jsonl` — NOT under `.renmark/state/`.
     Rationale (state in a code comment above the path helper): this
     registry is curated and versioned like `.renmark/memory/decisions.md`
     (survives `/renmark:hygiene`, is meant to be read/reviewed, not
     per-run scratch state), unlike `recurrences.json` which is gitignored
     runtime state. One JSON object per line, newest-append-friendly but
     rewritten in full on every mutation (small file, simplicity over
     incremental-append complexity). Add
     `_failure_rule_registry_path(repo) -> Path` returning
     `Path(repo) / ".renmark" / "memory" / "failure_rules.jsonl"`.

  2. **Types:**
     ```python
     FailureRuleStatus = Literal["proposed", "active", "deprecated"]

     @dataclass(frozen=True, slots=True)
     class FailureRuleEnforcement:
         prompt: str | None = None
         validator: str | None = None
         capability_policy: str | None = None

     @dataclass(frozen=True, slots=True)
     class FailureRule:
         rule_id: str
         status: FailureRuleStatus
         trigger: str
         applicability: str
         required_behavior: str
         prohibited_failure: str
         source_evidence: tuple[str, ...]
         enforcement: FailureRuleEnforcement
         regression_test_ref: str
         created_at: str
         last_triggered_at: str | None = None
         review_after: str | None = None

     @dataclass(frozen=True, slots=True)
     class RuleConflict:
         rule_id_a: str
         rule_id_b: str
         kind: Literal["duplicate_trigger", "contradiction"]
         detail: str
     ```

  3. **Registry read/write:**
     - `load_failure_rules(repo) -> tuple[FailureRule, ...]` — tolerant of a
       missing file (returns `()`), a malformed line (skip, do not raise),
       reconstructs `FailureRuleEnforcement` from its nested dict.
     - `_save_failure_rules(repo, rules: Sequence[FailureRule]) -> None` —
       private; atomic write via the same tempfile+replace pattern as
       `_write_state`, one `json.dumps` object per line, sorted by
       `rule_id` for stable diffs.

  4. **Lifecycle functions** (each loads, mutates one rule, saves, returns
     the updated `FailureRule`; each raises `ValueError` with a clear
     message on an unknown `rule_id` — do not silently no-op, unlike
     REQ-24's query functions, since a curated registry mutation on a
     missing id is a caller bug, not a normal miss):
     - `propose_failure_rule(repo, *, rule_id: str, trigger: str,
       applicability: str, required_behavior: str, prohibited_failure: str,
       source_evidence: Sequence[str], enforcement: FailureRuleEnforcement
       | None = None, regression_test_ref: str = "", review_after: str |
       None = None, created_at: datetime | str | None = None) ->
       FailureRule` — status starts `"proposed"`. Raise `ValueError` if
       `rule_id` already exists in the registry (no silent overwrite).
     - `activate_failure_rule(repo, rule_id: str) -> FailureRule` — only
       legal from `"proposed"`; raise `ValueError` if called on an already
       `"active"` or `"deprecated"` rule (lifecycle is forward-only:
       proposed→active→deprecated, no skipping backward).
     - `deprecate_failure_rule(repo, rule_id: str, *, reason: str = "") ->
       FailureRule` — legal from `"proposed"` or `"active"`; sets status to
       `"deprecated"`; append `reason` (if given) into `source_evidence` as
       a bounded trailing entry so the deprecation rationale is not lost.

  5. **Dedup/contradiction detection (flag, never auto-resolve):**
     `detect_failure_rule_conflicts(rules: Sequence[FailureRule]) ->
     tuple[RuleConflict, ...]` — pure function, pairwise over `rules`
     (caller passes the loaded registry; do not have this function load
     state itself, keep it testable on arbitrary lists). For each pair
     where BOTH are `status in ("proposed", "active")` (a deprecated rule
     never conflicts) and `trigger` and `applicability` are equal
     (case-insensitive, whitespace-collapsed compare): if
     `required_behavior` and `prohibited_failure` also match →
     `kind="duplicate_trigger"`; if either differs →
     `kind="contradiction"`. Order-stable: always
     `rule_id_a < rule_id_b` lexicographically in the returned
     `RuleConflict`. This function only detects and reports — it never
     mutates the registry or changes any rule's status.

  6. **Review-date surfacing (does not auto-deprecate):**
     `failure_rules_due_for_review(repo, *, as_of: datetime | str | None =
     None) -> tuple[FailureRule, ...]` — loads the registry, returns
     `status == "active"` rules whose `review_after` is set and
     `review_after <= as_of` (default `as_of` = now, UTC, same
     `_normalise_timestamp` helper this module already has). Read-only:
     never changes `status`, never touches `review_after`. A docstring note
     states this is the read the roadmap's Release 12 `/renmark:hygiene`
     pruning-sweep extension point calls — this release only adds the read,
     it does not wire the hygiene call site (out of scope, deferred).

  7. **Durable-guard seed helper (read-only bridge, not a merge):**
     `durable_guard_seed_candidates(repo, *, min_occurrences: int = 3) ->
     tuple[dict[str, Any], ...]` — reads `.renmark/state/recurrences.json`
     via this module's EXISTING `_read_state`/`_state_paths` helpers
     (read-only call, no write), filters entries where
     `remediation_class == "durable_guard"`, `occurrence_count >=
     min_occurrences`, and `not resolved`, and returns bounded dicts (
     `{"key": ..., "occurrence_count": ..., "target": ...,
     "last_observed_at": ...}`) suitable to pass as one string in a future
     `propose_failure_rule(..., source_evidence=[...])` call. This function
     never constructs or persists a `FailureRule` itself — it only surfaces
     candidate evidence text; a human or a future release decides whether
     to actually call `propose_failure_rule`. Docstring must say explicitly:
     "This reads `durable_guard` entries as evidence; it does not consume,
     mutate, or replace `recurrence.py`'s REQ-24 state."

  8. Extend `__all__` with the new public names: `"FailureRule"`,
     `"FailureRuleEnforcement"`, `"FailureRuleStatus"`, `"RuleConflict"`,
     `"load_failure_rules"`, `"propose_failure_rule"`,
     `"activate_failure_rule"`, `"deprecate_failure_rule"`,
     `"detect_failure_rule_conflicts"`, `"failure_rules_due_for_review"`,
     `"durable_guard_seed_candidates"`. Do not remove any existing name from
     `__all__`.

  Depends on Task 1 conceptually (the ADR is the design record for this
  structure) but not by import — this task does not read
  `decisions.md`.

### Task 3: subagent_gate.py — consume active FailureRules at pre-dispatch
- **mode:** B
- **target:** renmark/subagent_gate.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.0336
- **verifier:** python3 -c "
from renmark import subagent_gate as g
assert hasattr(g, 'check_failure_rule_constraints')
assert hasattr(g, 'apply_failure_rule_constraints')
assert hasattr(g, 'FailureRuleVerdict')
print('OK')
" 2>&1 | tail -5
- **serves:** AC-7
- **spec:**
  Add a FOURTH independent, zero-LLM, pure, never-raises check to
  `renmark/subagent_gate.py`, alongside (not replacing or calling)
  `justify_task`, `validate_r008_dispatch`, `check_capability_envelope` —
  matching this module's existing "composable, none calls the others"
  convention (see the module's own comment above
  `check_capability_envelope`, ~line 397-411; update that comment block to
  mention this fourth check exists in the same funnel, one added sentence,
  do not rewrite the rest of it).

  1. Add `from renmark import recurrence` to this module's imports
     (module-level; `recurrence.py` does not import `subagent_gate`, so
     this introduces no cycle — confirmed by grep before writing).

  2. ```python
     @dataclass(frozen=True)
     class FailureRuleVerdict:
         passed: bool
         matched_rule_ids: tuple[str, ...]
         challenge: str | None
         reason: str
     ```
     Same non-raising verdict-shape convention `SubagentVerdict` /
     `EnvelopeVerdict` already use in this file.

  3. `check_failure_rule_constraints(repo: str | os.PathLike[str],
     applicability: str, *, host: str = "claude") -> FailureRuleVerdict` —
     calls `recurrence.load_failure_rules(repo)` (wrap in a broad
     `try/except Exception` returning a conservative
     `FailureRuleVerdict(passed=True, matched_rule_ids=(), challenge=None,
     reason="failure-rule registry unavailable; treated as no constraints")`
     — matching this module's "never raises, degrade to the safe/
     conservative answer" convention stated in the module docstring).
     Filters to `status == "active"` only (a `proposed` or `deprecated`
     rule is NEVER matched — this is the load-bearing behavior this task's
     verifier and Task 5's tests must prove). Matches a rule when its
     `applicability` string and the caller's `applicability` argument share
     at least one case-insensitive whitespace-split token (simple,
     deterministic keyword overlap — no fuzzy matching, no LLM call).
     Returns `passed=False` with a `challenge` string naming each matched
     rule's `rule_id` and `prohibited_failure` when one or more rules
     match; `passed=True, matched_rule_ids=()` when none match. `reason`
     always names the matched `rule_id`(s) when any exist (this is what lets
     a caller "cite the specific rule_id in its verdict", per the roadmap's
     Owner acceptance scenario) — never a bare summary with no id.

  4. `apply_failure_rule_constraints(existing_constraints: dict | None,
     verdict: FailureRuleVerdict, rules: Sequence[Any]) -> dict` — pure,
     does not mutate `existing_constraints` in place; returns a NEW dict
     (`dict(existing_constraints or {})` plus a
     `"failure_rules": [...]` key listing, for each matched rule id, a
     small `{"rule_id", "required_behavior", "prohibited_failure"}` dict
     pulled from `rules`). This is the function a caller uses to populate
     `WorkOrder.constraints` (Release 3's placeholder field, confirmed by
     grep to have zero existing writers in `dispatch.py` or elsewhere
     before this task). Do NOT have this function or `check_failure_rule_
     constraints` call `dispatch.build_subagent_input` or write prompt
     text anywhere — per the roadmap's compatibility guarantee #7, the
     existing `dispatch.build_subagent_input` funnel remains the sole
     prompt-composition pathway; this task only produces a verdict and a
     constraints dict a caller may attach to a `WorkOrder`.

  5. Do not touch `justify_task`, `validate_r008_dispatch`,
     `check_capability_envelope`, `ENVELOPE_CONTROL_STATUS`,
     `resolve_lens_for`, or any existing dataclass in this file.

  Depends on Task 2 (imports `recurrence.load_failure_rules` and the
  `FailureRule` shape) — must run after Task 2.

### Task 4: test_recurrence.py — FailureRule lifecycle, dedup, review, REQ-24 guard
- **mode:** B
- **target:** tests/test_recurrence.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 1200
- **est_cost_usd:** 0.05
- **verifier:** python3 -m pytest tests/test_recurrence.py -q 2>&1 | tail -5
- **serves:** AC-7
- **spec:**
  Extend `tests/test_recurrence.py` (reuse this file's existing `tmp_path`
  fixture pattern and `_observation`/`_observe_twice` helpers where they
  apply — do not reinvent fixtures for the parts that overlap). Add tests
  covering:
  1. **Lifecycle**: `propose_failure_rule` creates a `status=="proposed"`
     rule; `activate_failure_rule` transitions it to `"active"`;
     `deprecate_failure_rule` transitions an active rule to `"deprecated"`.
     Assert `activate_failure_rule` raises `ValueError` when called on an
     already-`"active"` rule (no backward/repeat transition), and
     `propose_failure_rule` raises `ValueError` on a duplicate `rule_id`.
  2. **Persistence**: rules round-trip through `load_failure_rules` after
     a fresh-process-style reload (re-read via `load_failure_rules(tmp_path)`
     after each mutation), and the registry file lives at
     `tmp_path / ".renmark" / "memory" / "failure_rules.jsonl"` (not under
     `.renmark/state/`).
  3. **Dedup/contradiction**: construct two rules with identical `trigger`
     + `applicability` and conflicting `required_behavior` /
     `prohibited_failure`; assert `detect_failure_rule_conflicts` returns
     one `RuleConflict` with `kind == "contradiction"`. Construct two rules
     identical in all four of `trigger`/`applicability`/
     `required_behavior`/`prohibited_failure`; assert `kind ==
     "duplicate_trigger"`. Assert a `"deprecated"`-status rule never
     produces a conflict against an otherwise-colliding active rule.
  4. **Review surfacing**: an active rule with `review_after` in the past
     appears in `failure_rules_due_for_review`; one with `review_after` in
     the future, or `review_after=None`, or `status != "active"`, does not.
     Assert calling `failure_rules_due_for_review` does NOT change the
     rule's `status` (still `"active"` after the call — no auto-deprecate).
  5. **`durable_guard_seed_candidates`**: seed `.renmark/state/
     recurrences.json` (via `recurrence.observe_issue` called 3x with the
     same signal, matching this file's existing `_observe_twice`-style
     pattern extended to a 3rd call) so an entry has
     `occurrence_count >= 3` and `remediation_class == "durable_guard"`
     (reuse this module's `_DURABLE_GUARD_RULE_MARKERS` convention by
     choosing a `rule_id` containing one of those markers, e.g.
     `"policy-violation"`); assert `durable_guard_seed_candidates` returns
     that entry's key; assert calling it does NOT write to or change
     `recurrences.json` (read file bytes before/after, assert unchanged)
     and does NOT create a `FailureRule` (registry file absent or
     unchanged before/after the call).
  6. **REQ-24 unchanged guard** (byte-for-byte behavior guard, reusing this
     file's existing fixtures): re-run this file's EXISTING
     `test_equivalent_observations_block_across_runs_but_changed_signal_
     resets`-style scenario (or call the same helpers directly) and assert
     `pre_attempt`, `observe_issue`, `acknowledge_issue`, `resolve_issue`
     produce identical `RecurrenceDecision` field values to what they
     produced before this release (occurrence counts, `retry_blocked`,
     `remediation_class`, `summary_lines` shape) — i.e. add this as a new
     test rather than editing any existing assertion in this file, proving
     the new `FailureRule` code path was purely additive.
  Do not modify or weaken any existing test in this file.

### Task 5: test_subagent_gate.py — FailureRule consumption verdict + non-goal guard
- **mode:** B
- **target:** tests/test_subagent_gate.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 900
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest tests/test_subagent_gate.py -q 2>&1 | tail -5
- **serves:** AC-7
- **spec:**
  Extend `tests/test_subagent_gate.py` (match this file's existing
  fixture/assertion style for `justify_task`/`check_capability_envelope`
  if present; if this test file does not yet exist, create it following
  this project's standard pytest conventions used by `tests/test_
  recurrence.py`). Add tests covering:
  1. Seed a `tmp_path` repo with one ACTIVE `FailureRule` (via
     `recurrence.propose_failure_rule` then `recurrence.activate_failure_
     rule`) whose `applicability` shares a token with a test dispatch's
     `applicability` string; call
     `subagent_gate.check_failure_rule_constraints(tmp_path, <applicability>)`
     and assert `passed is False`, the matched rule's `rule_id` appears in
     both `matched_rule_ids` and the `reason`/`challenge` text.
  2. Seed a `"proposed"` (never activated) `FailureRule` with the same
     matching `applicability`; assert `check_failure_rule_constraints`
     returns `passed=True, matched_rule_ids=()` — a `proposed` rule is
     NEVER matched. Repeat for a `"deprecated"` rule.
  3. No registry file present at all (fresh `tmp_path`, no
     `failure_rules.jsonl`): assert `check_failure_rule_constraints`
     returns `passed=True` and does not raise.
  4. `apply_failure_rule_constraints`: given a matched verdict and the
     source rules, assert the returned dict contains a `"failure_rules"`
     key listing the matched rule's `rule_id`/`required_behavior`/
     `prohibited_failure`, and that passing an existing non-empty
     `existing_constraints` dict preserves its other keys unchanged
     (merge, not replace) and does not mutate the input dict object
     (`existing_constraints is not` the returned dict).
  5. **Non-goal guard**: read `renmark/subagent_gate.py`'s source text and
     assert it contains no reference to `build_subagent_input` (the
     compatibility guarantee that this module never composes prompt text
     itself) — a simple source-grep guard, dependency-free, mirroring this
     program's existing non-goal guard-test pattern (see Release 9's
     `test_ledger.py` guard test for the same style).
  6. Assert `justify_task`, `validate_r008_dispatch`, and
     `check_capability_envelope`'s existing public signatures/behavior
     (call each once with a minimal valid input matching this file's
     existing usage, if any pre-existing tests exist for them) are
     unaffected — i.e. add, do not edit, any pre-existing test in this
     file.

---

## Cost preview

| Executor | Tasks | Notes |
|---|---|---|
| sonnet | 3 | ADR-051 (docs), recurrence.py FailureRule registry (reasoning-heavy dedup/contradiction logic), subagent_gate.py consumption |
| codex | 2 | test_recurrence.py, test_subagent_gate.py |

Tasks: 5 (4 parallel groups — group 1: ADR; group 2: recurrence.py; group 3:
subagent_gate.py (depends on group 2); group 4: both test files, disjoint,
parallel, depend on groups 2/3 respectively)

| Task | Executor | est_tokens | overhead | $/kT | est_cost_usd |
|---|---|---|---|---|---|
| 1 ADR-051 | sonnet | 700 | 10000 | 0.003 | 0.0321 |
| 2 recurrence.py | sonnet | 2500 | 10000 | 0.003 | 0.0375 |
| 3 subagent_gate.py | sonnet | 1200 | 10000 | 0.003 | 0.0336 |
| 4 test_recurrence.py | codex | 1200 | 0 | ~0.03-0.05 | 0.05 |
| 5 test_subagent_gate.py | codex | 900 | 0 | ~0.03-0.04 | 0.04 |

Total tokens (incl. Agent overhead): 10700 + 12500 + 11200 + 1200 + 900 =
**~36,500**
**Total cost: ~$0.1932**

REQ-24's existing `pre_attempt`/`observe_issue`/`acknowledge_issue`/
`resolve_issue` functions and `recurrences.json` schema are untouched by
every task above — Task 2 is append-only to `recurrence.py`, Task 4 adds a
new guard test rather than editing any existing assertion, and Tasks 1/3/5
do not import or modify REQ-24's code paths at all.
