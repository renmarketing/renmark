# Release 15 — Behavioral eval suite: retroactive fixtures + remaining fixtures + CI-gating

Investigation before writing this plan (see CHANGELOG.md 2026-08-05 "fix:
behavior.py — risk_tier_lens_selection.golden fixture was unreachable")
found the roadmap's fixture-split table overstated reality: it claims 7
fixture groups were "authored alongside" releases 1, 4, 6, 8, 9, 10, 13.
Only 1 of those 7 (risk-tier/lens selection, Release 8) actually existed on
disk, and it was silently FAILing (missing `_DISPATCH` wiring, now fixed).
The other 6 groups were never authored despite each release's own
plan/verify claiming completion.

**Owner decision (2026-08-05):** treat Release 15 as the real closure point
for the eval suite regardless of size — author all 9 missing/incomplete
fixture groups (6 retroactive + Release 15's own original 3), then wire
CI-gating. This is a larger release than this program's norm; justified by
the Owner's explicit choice over the alternative (silently descoping and
logging a gap).

**Fixture groups authored in this release** (case name → what it proves →
real function exercised):
1. `fast_path_accept_reject` — `fast_path.classify_fast_path` accepts a
   single-file, non-critical, mode-B dispatch as fast-path-eligible and
   rejects a multi-file or mode-A dispatch.
2. `task_tracker_transitions` — `task_tracking.create_or_reuse_task` →
   `mark_in_progress` → (blocked path) `record_blocker` transitions, and
   that `MissingEvidenceError`/`SelfApprovalError` actually raise on the
   violating paths.
3. `capability_envelope_denial` — `subagent_gate.check_capability_envelope`
   returns a `passed=False` `EnvelopeVerdict` for a role/scope combination
   that violates its `allowed_targets`/`allowed_commands`, and `passed=True`
   for one that doesn't.
4. `judge_input_isolation_and_outcome` — `judge.Outcome` is 3-state
   (`"pass"|"fail"|"uncertain"`, never a 2-state fallback), and
   `judge._redact_worker_fields`/the judge prompt-building path never
   leaks a forbidden field into what's sent.
5. `failure_rule_injection` — `subagent_gate.check_failure_rule_constraints`
   matches an active rule's `applicability` against a real target and
   `apply_failure_rule_constraints` attaches it to a constraints dict;
   an inactive/non-matching rule attaches nothing.
6. `retry_rework_survives_resume` — `cli._engine._cross_check_skip_list`
   (the Release 13 Finding A fix) correctly returns an index as
   `ambiguous` (not silently `safe_to_skip`) when the same index appears
   under a DIFFERENT task title than the current plan's — this is the
   actual regression guard for the most severe bug found this program.
7. `worker_replan_refusal` — a `ledger.Escalation` with
   `is_replannable=False` carries no `replan_evidence`, and the schema
   validator (`ledger`'s validation for `Escalation`, grep
   `_check_bool(data, "is_replannable")`) rejects a malformed replan claim.
8. `inspector_cant_repair` — the `inspector` role's `ProfileSpec` in
   `subagent_profiles.py` declares a context/tool scope that excludes
   Write/Edit (read-only enforcement lives in the Claude agent definition
   `plugin/agents/inspector.md` — read it to confirm the real restriction
   text) and `ledger.InspectionReport` has no code-change/fix field, only
   `verdict`/`findings` — an Inspector can only emit a verdict, never a
   patch.
9. `judge_cant_override_deterministic_fail` — in `behavior.py`'s
   `_cmd_behavior`/`run()` flow, a deterministic-tier FAIL only ever
   ESCALATES to the judge for review (an `OFFER`, cost-noted, never
   auto-spent) — the judge tier cannot flip a deterministic FAIL result
   into a PASS; it can only add judge evidence alongside the FAIL.

**Compatibility guarantee:** `pytest -q` count only grows; `renmark-execute
--behavior` stays deterministic-tier-only by default (zero token spend, no
network) — CI-gating enforces the EXISTING contract more strictly, it does
not relax or bypass it.

### Task 1: fast-path accept/reject fixture

- **mode:** A
- **target:** tests/behavioral/fast_path_accept_reject.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/fast_path_accept_reject.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8 (Req 8)
- **spec:**
  Read `renmark/fast_path.py`'s `classify_fast_path(tasks)` and its
  `ClassificationVerdict` return shape first. Write a new `*.behavior.json`
  fixture (match the shape of `tests/behavioral/agency.behavior.json` —
  `skill`, `prompt`, `deterministic.call`, `deterministic.assertions`,
  `eval.contract`, `eval.golden_ref`). `deterministic.call` MUST be
  `"fast_path.classify_fast_path"` — this exact string, since Task 10
  wires an adapter under this key. Design `assertions` (a list of
  `contains:`/`not_contains:`/`matches:` strings, matching this repo's
  existing fixtures' assertion-string grammar) that prove: a single-file,
  mode-B, non-critical-module task is classified fast-path-eligible, and a
  multi-file OR mode-A task is classified NOT eligible. `eval.contract`:
  one sentence on what a live agent trajectory should additionally prove
  beyond the deterministic check. `golden_ref`: `"fast_path_accept_reject.golden"`.
  Do not write any adapter code — that's Task 10's job on a different file.

### Task 2: task-tracker transitions fixture

- **mode:** A
- **target:** tests/behavioral/task_tracker_transitions.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/task_tracker_transitions.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8 (Req 8)
- **spec:**
  Read `renmark/task_tracking.py`'s `create_or_reuse_task`,
  `mark_in_progress`, `record_blocker`, and the `MissingEvidenceError`/
  `SelfApprovalError`/`MissingVerificationError` exception classes first.
  Write a new `*.behavior.json` fixture (same shape as Task 1's). `call`
  MUST be `"task_tracking.transitions"`. Design assertions proving: a
  fresh task transitions `pending` → `in_progress` correctly, and a
  completion attempt without required evidence is refused (one of the
  named exceptions fires) rather than silently succeeding. `golden_ref`:
  `"task_tracker_transitions.golden"`.

### Task 3: capability-envelope denial fixture

- **mode:** A
- **target:** tests/behavioral/capability_envelope_denial.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/capability_envelope_denial.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8 (Req 8)
- **spec:**
  Read `renmark/subagent_gate.py`'s `check_capability_envelope(role,
  requested_scope, *, host="claude")` and `EnvelopeVerdict` first. Write a
  new `*.behavior.json` fixture. `call` MUST be
  `"subagent_gate.check_capability_envelope"`. Design assertions proving:
  a role/scope combination that violates the role's declared
  `allowed_commands` or path scope gets at least one `passed: False`
  verdict, and a compliant role/scope combination gets all `passed: True`
  verdicts. `golden_ref`: `"capability_envelope_denial.golden"`.

### Task 4: judge input-isolation + 3-state outcome fixture

- **mode:** A
- **target:** tests/behavioral/judge_input_isolation_and_outcome.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.033
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/judge_input_isolation_and_outcome.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8, AC-9 (Req 8, Req 9)
- **spec:**
  Read `renmark/judge.py`'s `Outcome = Literal["pass", "fail",
  "uncertain"]`, `_redact_worker_fields`, and `_parse_response` first.
  Write a new `*.behavior.json` fixture. `call` MUST be
  `"judge.input_isolation_and_outcome"`. Design assertions proving: the
  outcome type is genuinely 3-state (the rendered output must be able to
  show `"uncertain"` as a distinct value from `"fail"`, not a collapsed
  2-state fallback), and a forbidden/sensitive field is redacted before
  it would reach a judge prompt. `golden_ref`:
  `"judge_input_isolation_and_outcome.golden"`.

### Task 5: failure-rule injection fixture

- **mode:** A
- **target:** tests/behavioral/failure_rule_injection.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/failure_rule_injection.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8 (Req 8)
- **spec:**
  Read `renmark/subagent_gate.py`'s `check_failure_rule_constraints(repo,
  applicability, *, host="claude")` and `apply_failure_rule_constraints`
  first. Write a new `*.behavior.json` fixture. `call` MUST be
  `"subagent_gate.failure_rule_injection"`. Design assertions proving: an
  ACTIVE failure rule whose `applicability` matches the given context gets
  attached to the constraints dict, and a non-matching/inactive rule does
  not. `golden_ref`: `"failure_rule_injection.golden"`.

### Task 6: retry/rework survives resume fixture

- **mode:** A
- **target:** tests/behavioral/retry_rework_survives_resume.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.033
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/retry_rework_survives_resume.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8, AC-11 (Req 8, Req 11)
- **spec:**
  Read `renmark/cli/_engine.py`'s `_cross_check_skip_list(done, tasks,
  done_titles=None)` first — this is the Release 13 Finding A fix, the
  most severe bug found this program (an unbounded git-log index-only
  match could silently skip real work on `--resume`). Write a new
  `*.behavior.json` fixture. `call` MUST be
  `"cli_engine.cross_check_skip_list"`. Design assertions proving: an
  index that's `done` under one task title is correctly routed to
  `ambiguous` (NOT silently `safe_to_skip`) when the current plan's task
  at that index has a DIFFERENT title — the exact regression this fix
  guards against. `golden_ref`: `"retry_rework_survives_resume.golden"`.

### Task 7: worker replan-refusal fixture

- **mode:** A
- **target:** tests/behavioral/worker_replan_refusal.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/worker_replan_refusal.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8 (Req 8)
- **spec:**
  Read `renmark/ledger.py`'s `Escalation` dataclass (`is_replannable`,
  `replan_evidence` fields) and its schema-validation function (grep
  `_check_bool(data, "is_replannable")`) first. Write a new
  `*.behavior.json` fixture. `call` MUST be
  `"ledger.worker_replan_refusal"`. Design assertions proving: an
  `Escalation` with `is_replannable=False` correctly carries no
  `replan_evidence`, and a malformed escalation claiming replannability
  without evidence is rejected by validation. `golden_ref`:
  `"worker_replan_refusal.golden"`.

### Task 8: inspector-can't-repair fixture

- **mode:** A
- **target:** tests/behavioral/inspector_cant_repair.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/inspector_cant_repair.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8 (Req 8)
- **spec:**
  Read `renmark/subagent_profiles.py`'s `PROFILES["inspector"]`
  `ProfileSpec`, `plugin/agents/inspector.md` (the real Claude agent
  definition — confirm its declared tool list excludes Write/Edit), and
  `renmark/ledger.py`'s `InspectionReport` dataclass (confirm it has
  `verdict`/`findings` but no code-change/patch/diff field) first. Write
  a new `*.behavior.json` fixture. `call` MUST be
  `"subagent_profiles.inspector_cant_repair"`. Design assertions proving:
  the inspector role's declared scope/output never includes a
  write-capable action — it can only emit a verdict. `golden_ref`:
  `"inspector_cant_repair.golden"`.

### Task 9: judge can't override deterministic fail fixture

- **mode:** A
- **target:** tests/behavioral/judge_cant_override_deterministic_fail.behavior.json
- **complexity:** medium
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -c "import json; d=json.load(open('tests/behavioral/judge_cant_override_deterministic_fail.behavior.json')); assert d['deterministic']['call'] and d['deterministic']['assertions'] and d['eval']['golden_ref'] && echo OK"
- **serves:** AC-8, AC-9 (Req 8, Req 9)
- **spec:**
  Read `renmark/behavior.py`'s `_run_deterministic`/`run()` and
  `renmark/cli/_dispatch_flags.py`'s `_cmd_behavior` (the `--judge` path)
  first. Write a new `*.behavior.json` fixture. `call` MUST be
  `"behavior.judge_cant_override_deterministic_fail"`. Design assertions
  proving: the judge tier can only ESCALATE a deterministic FAIL (offer
  cost-noted review) — it structurally cannot turn a deterministic-tier
  FAIL result into a PASS status. `golden_ref`:
  `"judge_cant_override_deterministic_fail.golden"`.

### Task 10: wire adapters 1-3 (fast-path, task-tracker, capability-envelope)

- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 2500
- **est_cost_usd:** 0.1875
- **verifier:** python3 -m pytest -q tests/test_behavior.py 2>&1 | tail -5
- **serves:** AC-8 (Req 8)
- **spec:**
  Read Tasks 1-3's fixture files (now on disk) for their exact `call`
  names and assertion strings. Following the EXACT pattern of the
  existing `_render_risk_tier_lens_selection` adapter (calls the real
  function, never hand-copies its logic, returns a bounded text render
  whose content satisfies the fixture's assertions), write three new
  adapter functions in `renmark/behavior.py`:
  `_render_fast_path_accept_reject`, `_render_task_tracker_transitions`,
  `_render_capability_envelope_denial` — each `(repo: Path, case: Case)
  -> str`. Register all three in `_DISPATCH` under the exact `call`
  strings from the fixtures (`"fast_path.classify_fast_path"`,
  `"task_tracking.transitions"`,
  `"subagent_gate.check_capability_envelope"`). If a fixture's assertions
  don't actually match what the real function produces once you exercise
  it, FIX THE FIXTURE FILE (not the adapter to lie) — the adapter must
  always reflect genuine current behavior, never a fabricated render.
  Run `renmark-execute --behavior` after wiring and confirm these 3 new
  cases go PASS (existing 7 cases must stay PASS too — do not touch any
  existing adapter or `_DISPATCH` entry).

### Task 11: wire adapters 4-6 (judge, failure-rule, retry-rework)

- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 2500
- **est_cost_usd:** 0.1875
- **verifier:** python3 -m pytest -q tests/test_behavior.py 2>&1 | tail -5
- **serves:** AC-8, AC-9, AC-11 (Req 8, Req 9, Req 11)
- **spec:**
  Same pattern and constraints as Task 10 (runs sequentially AFTER it —
  same target file). Read Tasks 4-6's fixture files for exact `call`
  names/assertions. Write three new adapters:
  `_render_judge_input_isolation_and_outcome`,
  `_render_failure_rule_injection`,
  `_render_retry_rework_survives_resume` — register under
  `"judge.input_isolation_and_outcome"`,
  `"subagent_gate.failure_rule_injection"`,
  `"cli_engine.cross_check_skip_list"`. The retry-rework adapter is the
  most important one this release — it must call the REAL
  `_cross_check_skip_list` from `renmark.cli._engine` (import it directly;
  it's a private-underscore function but this is exactly the kind of
  regression-guard use case that justifies reaching into it) with a
  same-index-different-title scenario and render whether the result
  landed in `ambiguous` or `safe_to_skip`. Fix any fixture whose
  assertions don't match genuine behavior, same rule as Task 10. Confirm
  `renmark-execute --behavior` shows these 3 plus the prior 3 plus the
  original 7 all PASS (13/13 at this point).

### Task 12: wire adapters 7-9 (replan-refusal, inspector-repair, judge-override) + full 20-case count check

- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 4
- **est_tokens:** 2500
- **est_cost_usd:** 0.1875
- **verifier:** renmark-execute --behavior 2>&1 | tail -5
- **serves:** AC-8 (Req 8)
- **spec:**
  Same pattern as Tasks 10-11 (sequential, same file). Read Tasks 7-9's
  fixtures. Write three new adapters: `_render_worker_replan_refusal`,
  `_render_inspector_cant_repair`,
  `_render_judge_cant_override_deterministic_fail` — register under
  `"ledger.worker_replan_refusal"`,
  `"subagent_profiles.inspector_cant_repair"`,
  `"behavior.judge_cant_override_deterministic_fail"`. Fix any fixture
  whose assertions don't match genuine behavior. Run `renmark-execute
  --behavior` and confirm ALL cases (the original 7 plus these 9 new
  ones = 16) show PASS. Report the FINAL actual case count honestly in
  your summary — if it's not literally 20, that's expected and correct
  (this release closes the roadmap's fixture-split gap with 9 real,
  grounded cases rather than padding to a specific number); do not
  author filler cases to hit "20".

### Task 13: CI-gate the deterministic tier

- **mode:** B
- **target:** .github/workflows/test.yml
- **complexity:** simple
- **executor:** haiku
- **role:** release-manager
- **parallel_group:** 5
- **est_tokens:** 200
- **est_cost_usd:** 0.0102
- **verifier:** renmark-execute --behavior 2>&1 | tail -3
- **serves:** AC-8 (Req 8)
- **spec:**
  Add one new step to the `test` job, after the existing `pytest` step and
  before `shadow regression net`: name it `behavioral eval suite
  (deterministic tier)`, `run: renmark-execute --behavior`. This runs on
  every matrix combination (same as the other steps) — no new matrix
  dimension. Confirm the workflow YAML stays valid (same indentation
  style as the surrounding steps). Do not touch any other step or the
  `on:`/`strategy:` blocks.

### Task 14: CI-gating regression test

- **mode:** A
- **target:** tests/test_behavior_ci_gating.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest -q tests/test_behavior_ci_gating.py 2>&1 | tail -5
- **serves:** AC-8 (Req 8)
- **spec:**
  Write a pytest test that invokes `renmark-execute --behavior` as a
  subprocess (`subprocess.run`, matching how other CLI-invoking tests in
  this repo shell out — grep `tests/` for an existing `subprocess.run`
  pattern against `renmark-execute` and reuse its style) against THIS
  repo and asserts exit code `0` — a deterministic, CI-safe regression
  guard proving the whole deterministic tier stays green, independent of
  the GitHub Actions workflow file itself (which pytest can't execute).
  Also assert the printed summary line matches `r"behavior: \d+/\d+
  passed, 0 failed"` (regex) so a partial-pass silently going undetected
  is caught here too, not just by CI's exit code.

---

**Total tasks:** 14 (5 parallel groups)
**Total tokens (incl. ~10k Agent overhead/task for sonnet/opus, none for codex/haiku):**
~15,300 output + 100k Agent overhead (10 sonnet/opus tasks) = ~115.3k
**Total cost:** ~$0.99
**Executors:** sonnet×9, opus×3, haiku×1, codex×1

**Scope note:** this release is deliberately larger than this program's
norm — Owner-approved (2026-08-05) to close the roadmap's fixture-split
gap for real rather than descope or pad to a specific count. AC-8 (Req 8)
closes if all 14 tasks land clean and CI-gating goes live; report the
actual final case count honestly regardless of whether it's 20.
