# Plan: governed-orchestration-assurance — Release 6 (Capability-envelope enforcement wiring)

**Intent.** This release closes AC-2's (Req 2) `failed` status for the
path/command/spend-timeout control dimensions of the capability envelope, and
wires the concrete F1 fix — `renmark/dispatch.py`'s `enforce_wave_dispatch_scopes`
(built and unit-tested since R-0.2/WP-9, but confirmed by this plan's
pre-decomposition investigation to have **zero production callers** anywhere
outside `tests/`) gets a real production call site for the first time. Three
explicit scope carve-outs, stated up front:

1. **This release does NOT merge anything into the live `.claude/settings.json`.**
   Task 4 below hardens the Release 5 `PreToolUse` prototype hook
   (`.claude/hooks/capability_envelope_prototype.py`) but explicitly does not
   register it in `.claude/settings.json` — going live is a SEPARATE,
   Owner-approved action outside this plan's dispatch, presented as a
   post-plan diff-review step (see "Post-plan gate" at the bottom), never an
   auto-dispatched task.
2. **`renmark:inspector` stays read-only**, untouched by this release — no
   task here modifies `plugin/agents/inspector.md` or grants it new write
   targets; the envelope reads `allowed_targets`/`allowed_commands`, it does
   not add any.
3. **`fast_path.verify_worker_scope`'s Layer-B git-diff semantics remain the
   authoritative post-action check on BOTH hosts**, even after this release's
   pre-action wiring lands on Claude Code. Pre-action enforcement is additive
   defense-in-depth, never a replacement — Codex keeps Layer-B as its sole
   enforcement mechanism per the Owner's 2026-08-05 scope decision recorded in
   `.renmark/rethink/governed-orchestration-assurance/release-5-finding.md`
   (Claude-only pre-action wiring; Codex stays post-action-only with an
   honest `advisory`/`unsupported` status; no new Codex wrapper work).

**Pre-decomposition investigation (done at plan time — code actually read,
not guessed):**

- `renmark/fast_path.py` — `classify_fast_path` (5-signal eligibility),
  `WorkerScope`/`verify_worker_scope` (Layer-B git-diff check). Confirmed:
  `enforce_wave_dispatch_scopes` does **not** live here — it lives in
  `renmark/dispatch.py` (see below); `fast_path.py` itself is untouched by
  this release except by reference.
- `renmark/dispatch.py` — `dispatch_wave()` (line 138) builds a
  `WaveResult.scoped_dispatches` map ONLY for the single-Claude-task case via
  `_maybe_scoped_claude_dispatch` (line 251, reuses
  `fast_path.classify_fast_path`/`worker_scope_from_verdict`).
  `enforce_wave_dispatch_scopes(wave_result, repo, base_sha)` (line 351)
  raises `WaveScopeViolationError` on any scoped-dispatch violation; it is
  fully built and covered by `tests/test_wp9_scope_enforcement_wiring.py`.
  **Confirmed gap, more specific than the roadmap's framing**: the LIVE
  Claude Code orchestration path
  (`plugin/skills/orchestrate/SKILL.md` Step 3b, "Host-agent dispatch shape")
  does not call `dispatch_wave()` at all for host-agent tasks — it calls
  `dispatch.group_tasks_by_wave()` then `dispatch.build_host_dispatch_plan()`
  directly (line 242 of the skill), a completely separate code path that
  never populates `scoped_dispatches` and therefore never has anything for
  `enforce_wave_dispatch_scopes` to check. A repo-wide grep for
  `enforce_wave_dispatch_scopes`/`verify_wave_dispatch_scopes`/
  `verify_agent_dispatch_scope` confirms zero non-test callers today. Task 8
  below is scoped accordingly: it extends `build_host_dispatch_plan`'s
  single-Claude-task case with the same scope-construction logic
  `_maybe_scoped_claude_dispatch` already uses, and exposes a
  `enforce_host_agent_dispatch_scope()` wrapper the orchestrate skill can
  call post-dispatch — not a change to `dispatch_wave()`'s own internals
  (which correctly cannot call enforcement synchronously; the real Agent
  tool call happens outside this Python process, per the module's own
  docstring).
- `renmark/subagent_gate.py` — `justify_task`/`challenge_plan` (the existing
  Q1-Q4 pre-dispatch justification gate) is the funnel `check_capability_envelope`
  (new, Task 3) hooks into, per the roadmap's explicit instruction. Same
  never-raises, degrade-to-conservative style as the rest of the module.
- `renmark/subagent_profiles.py` — `ProfileSpec.allowed_targets` (line 44-46:
  "Informational for now; enforced in future Agency Mode" — this release
  makes the analogous `allowed_commands` field real from day one, and
  `allowed_targets` real via Task 8's wiring). `PROFILES` dict (9 specialist
  roles + `general-purpose` fallback) is the natural home for the new
  `allowed_commands: tuple[str, ...]` field (Task 1).
- `renmark/cost.py` — `PRICE_PER_KTOK`, `_AGENT_EXECUTORS`, no existing
  spend/timeout ceiling check. `renmark.ledger.WorkOrder.budget: dict | None`
  (Release 3 placeholder field, schema-only today) is the natural input to
  the new ceiling check (Task 2) — this is a check-before-dispatch against a
  configured max, not a new billing system.
- `.claude/hooks/capability_envelope_prototype.py` (Release 5's prototype,
  109 lines) — currently handles only `Write`/`Edit` tool calls against one
  hardcoded profile (`code-implementer`)'s `allowed_targets`. Task 4 extends
  it to read `allowed_commands` too (for `Bash` tool calls) and to accept any
  profile from `PROFILES`, not just `code-implementer` — still never
  registered in `.claude/settings.json`.

**Per-control status this release claims** (status vocabulary: `enforced` /
`verified_after` / `advisory` / `unsupported` — no `enforced` claim without a
passing denial-integration test backing it, per the roadmap's own
requirement):

| Control | Claude Code | Codex |
|---|---|---|
| Path/target scope | `enforced` (pre-dispatch via Task 8 + post-action Layer-B, unchanged) | `verified_after` (post-action Layer-B only) |
| Command allowlist | `enforced` | `enforced` (host-independent, pure Python) |
| Spend/timeout ceiling | `enforced` | `enforced` (host-independent, pure Python) |
| Network-domain restriction | `advisory` | `advisory` |
| Git-action restriction | `advisory` | `advisory` |
| External-action restriction | `unsupported` | `unsupported` |

Network-domain / git-action / external-action restrictions get NO mechanical
enforcement claim this release (no OS-level or hook-level mechanism is
confirmed to exist for them) — recorded honestly, rolled to a named
Owner-visible follow-up outside this program's numbered releases.

**Task ordering note (test-before-flip-switch, required by this release's
risk profile):** Tasks 5, 6, 7 (all test files) are in parallel_group 3,
strictly BEFORE Task 8 (parallel_group 4, the `dispatch.py` wiring that
actually makes `enforce_wave_dispatch_scopes`'s production caller exist) and
Task 9 (parallel_group 5, the `orchestrate/SKILL.md` wiring). Task 6 in
particular is the required baseline enforcement-path pair — an allowed
dispatch passes through unchanged, a genuinely out-of-envelope dispatch is
denied with a clear error — written against the API Task 8 will implement,
so Task 8 is verified against real coverage that existed before the flip,
not just `py_compile`.

---

### Task 1: command-allowlist field on ProfileSpec
- **mode:** B
- **target:** renmark/subagent_profiles.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.0324
- **verifier:** python3 -m py_compile renmark/subagent_profiles.py
- **serves:** AC-2 (Req 2)
- **spec:**
  Add a new frozen field `allowed_commands: tuple[str, ...] = ()` to the
  `ProfileSpec` dataclass (near `allowed_targets`), mirroring its docstring
  style: "Command-name allowlist this role may invoke via Bash/exec. Empty
  tuple = no command restriction declared (informational-only, matches
  today's `allowed_targets` behavior for roles that don't set it — do NOT
  silently deny everything for an empty tuple)." Populate sensible per-role
  defaults on the existing `PROFILES` dict entries — keep every existing
  entry's other fields unchanged, only add the new field:
  - `docs-editor`: `()` (no shell commands expected)
  - `code-implementer`: `("python3", "pytest", "git", "ruff", "mypy")`
  - `test-writer`: `("python3", "pytest")`
  - `reviewer`: `("git", "python3")`
  - `audit-reader`: `()`  (read-only role; Read/Grep/Glob only, no Bash)
  - `release-manager`: `("git", "python3")`
  - `researcher`: `()`
  - `inspector`: `("git", "python3")`  (read-only Bash for `git diff`/inspection, never write commands)
  - `finish-lane-specialist`: `("git", "python3", "pytest")`
  - `general-purpose`: `()`  (fallback — no restriction declared, matches `allowed_targets`'s "any" fallback semantics)
  Add a short module-level comment near `PROFILES` noting `allowed_commands`
  becomes REAL enforcement in Release 6 (Task 3 in this same plan), same as
  `allowed_targets`'s docstring already promises for "future Agency Mode."
  Do not change `resolve_profile`, `profile_tier`, or any existing test's
  expected fields — this is a strictly additive dataclass field.

### Task 2: spend/timeout ceiling check
- **mode:** B
- **target:** renmark/cost.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -m py_compile renmark/cost.py
- **serves:** AC-2 (Req 2)
- **spec:**
  Add a new pure function `check_spend_timeout_ceiling(budget: dict | None,
  *, tier: str = "sonnet") -> "SpendTimeoutVerdict"` plus a new frozen
  dataclass `SpendTimeoutVerdict(passed: bool, reason: str, max_tokens:
  int | None = None, max_timeout_s: int | None = None)`. This is a
  check-before-dispatch against a configured max, reusing this module's
  existing budget/tier machinery — NOT a new billing system. `budget` is the
  same shape as `ledger.WorkOrder.budget: dict | None` (Release 3's
  placeholder field) — expect optional keys `max_tokens` (int) and
  `max_timeout_s` (int). Behavior: `budget is None` → `passed=True,
  reason="no budget declared — nothing to enforce"` (matches the
  never-silently-deny convention already used for `allowed_commands`/
  `allowed_targets` empty defaults in this same release). When `budget` sets
  `max_tokens`, compare against a per-tier default ceiling constant you add
  near `PRICE_PER_KTOK` (e.g. `DEFAULT_MAX_TOKENS_PER_DISPATCH: dict[str,
  int] = {"haiku": 50_000, "sonnet": 100_000, "opus": 150_000, "fable":
  150_000, "codex": 200_000}` — pick reasonable, clearly-labeled defaults;
  `budget["max_tokens"]` when present OVERRIDES the tier default, it does not
  add to it). Same pattern for `max_timeout_s` against a
  `DEFAULT_MAX_TIMEOUT_S: dict[str, int]` constant (a reasonable default such
  as 600s across tiers is fine — document your choice inline). Never raises
  — malformed `budget` (wrong types, negative numbers) degrades to
  `passed=False, reason="malformed budget — treated as failing, not silently
  passing"` (this is the one place in this module that fails closed rather
  than degrading to a lenient default, because a budget ceiling's entire
  purpose is refusing an unverifiable spend). Do not modify
  `estimate_cost`, `requires_escalation`, or any other existing function's
  signature or behavior.

### Task 3: check_capability_envelope + EnvelopeControlStatus
- **mode:** B
- **target:** renmark/subagent_gate.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.171
- **verifier:** python3 -m py_compile renmark/subagent_gate.py
- **serves:** AC-2 (Req 2)
- **spec:**
  Add to `renmark/subagent_gate.py` (do not touch `justify_task`,
  `challenge_plan`, `preview_line`, or the R-008 checklist machinery below
  them — purely additive):

  1. `EnvelopeControlStatus` — a frozen dataclass or small `dict`-backed
     table (your call on the cleanest fit given this module's existing
     dataclass style) recording, per control dimension × host, one of the
     status strings `"enforced"` / `"verified_after"` / `"advisory"` /
     `"unsupported"`. Encode exactly this table as a module-level constant
     `ENVELOPE_CONTROL_STATUS: dict[str, dict[str, str]]` keyed by control
     name then host name (`"claude"` / `"codex"`):
     ```
     path:            claude=enforced,        codex=verified_after
     command:         claude=enforced,        codex=enforced
     spend_timeout:   claude=enforced,        codex=enforced
     network_domain:  claude=advisory,        codex=advisory
     git_action:      claude=advisory,        codex=advisory
     external_action:  claude=unsupported,    codex=unsupported
     ```
     This is the SAME table stated in this plan's "Per-control status" table
     above — do not invent different values. Add a helper
     `control_status(control: str, host: str) -> str` returning `"unsupported"`
     for any unknown control/host pair (never raises, never a KeyError).

  2. `EnvelopeVerdict` — a frozen dataclass with the SAME non-raising verdict
     shape convention `SubagentVerdict` already uses: `passed: bool`,
     `control: str`, `host: str`, `status: str` (the control_status value),
     `reason: str`, `violations: tuple[str, ...] = ()`.

  3. `check_capability_envelope(role: str, requested_scope: dict, *, host:
     str = "claude") -> tuple[EnvelopeVerdict, ...]` — the new function. It
     evaluates EVERY control dimension for the given `role`/`host` and
     returns one `EnvelopeVerdict` per dimension (never a single verdict —
     callers need to see all six). `requested_scope` is a dict the caller
     builds, with optional keys: `paths: list[str]`, `commands: list[str]`,
     `budget: dict | None`. Behavior per control:
     - `path`: `status = control_status("path", host)`. When `status ==
       "enforced"` (claude only), evaluate `requested_scope.get("paths",
       [])` against `subagent_profiles.PROFILES[role].allowed_targets` (reuse
       `fnmatch.fnmatch`, same as `capability_envelope_prototype.py` — do not
       reimplement glob matching differently); a path outside the allowed
       globs is a violation. When `status == "verified_after"` (codex),
       `passed=True` always — not evaluated pre-dispatch on Codex; `reason`
       must say so explicitly (e.g. "codex: path scope verified post-action
       via fast_path.verify_worker_scope only, not pre-dispatch") so a caller
       can never mistake `passed=True` here for "enforced."
     - `command`: `status = "enforced"` on both hosts. Evaluate
       `requested_scope.get("commands", [])` against
       `subagent_profiles.PROFILES[role].allowed_commands` from Task 1. An
       empty `allowed_commands` tuple on the profile means "no restriction
       declared" → always passes (matches Task 1's non-denial-by-default
       convention). A non-empty `allowed_commands` tuple that doesn't
       contain a requested command is a violation.
     - `spend_timeout`: `status = "enforced"` on both hosts. Call
       `cost.check_spend_timeout_ceiling(requested_scope.get("budget"),
       tier=subagent_profiles.profile_tier(role))` from Task 2 and translate
       its `SpendTimeoutVerdict` into this dimension's `EnvelopeVerdict`
       (`passed`/`reason` pass through).
     - `network_domain`, `git_action`: `status = "advisory"` on both hosts.
       Always `passed=True`; `reason` = "advisory only — no code-level
       enforcement mechanism confirmed this release; recorded as a
       constraints-object statement only."
     - `external_action`: `status = "unsupported"` on both hosts. Always
       `passed=True`; `reason` = "unsupported — no enforcement mechanism
       wired for this control."
     Never raises: same try/except-degrade-to-conservative style
     `justify_task` uses — on any unexpected error, return one
     `EnvelopeVerdict(passed=False, control="unknown", host=host,
     status="unsupported", reason="gate could not classify — review before
     dispatch")` (conservative-failure, never silently pass on internal error).

  4. Wire `check_capability_envelope` into the SAME pre-dispatch funnel
     `justify_task` is called from conceptually (do not literally call it
     FROM `justify_task` — two separate, composable checks a caller runs
     together, same relationship `validate_r008_dispatch` has to
     `justify_task` today). One short docstring paragraph explaining this
     composability, matching the module's existing header comment style.

  Do not modify `.claude/settings.json` or any hook file — that is Task 4.

### Task 4: harden the Release 5 PreToolUse prototype hook (still not wired live)
- **mode:** B
- **target:** .claude/hooks/capability_envelope_prototype.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** python3 -m py_compile .claude/hooks/capability_envelope_prototype.py
- **serves:** AC-2 (Req 2)
- **spec:**
  Harden the Release 5 prototype WITHOUT wiring it into `.claude/settings.json`
  — it stays a standalone script under `.claude/hooks/`, invoked by nothing
  in this repo yet. Two changes, both additive to the existing `main()`:

  1. Generalize past the hardcoded `PROFILES["code-implementer"]` lookup:
     read the acting role from the hook payload if present (`payload.get
     ("renmark_role")` — a hypothetical future field; if absent, fall back to
     `"code-implementer"` exactly as today, so existing behavior for the
     documented case is unchanged) and look up `PROFILES[role]` defensively
     (`PROFILES.get(role, PROFILES["code-implementer"])` — never KeyError on
     an unrecognized role).
  2. Handle `Bash` tool calls (not just `Write`/`Edit`): when `tool_name ==
     "Bash"`, extract the command name from `tool_input.get("command", "")`
     (first whitespace-separated token, stripped of any path prefix — e.g.
     `"git status"` → `"git"`, `"/usr/bin/python3 foo.py"` → `"python3"`) and
     check it against the resolved profile's `allowed_commands` (from Task
     1 — import it the same way `PROFILES` is already imported at the top of
     this file). An empty `allowed_commands` tuple on the profile → allow
     (no restriction declared, matches Task 1's convention). A non-empty
     tuple that doesn't contain the extracted command name → deny, same
     `hookSpecificOutput`/`permissionDecision` JSON shape the existing
     Write/Edit path already emits, with a `permissionDecisionReason`
     explaining which command was rejected and what the allowlist is.
     Malformed/missing `command` → pass through silently (`sys.exit(0)`,
     no decision), matching this file's existing conservative-defer style
     for malformed input.
  3. Add one clear top-of-file comment reaffirming: "Still PROTOTYPE /
     SPIKE evidence for Release 6 of governed-orchestration-assurance —
     hardened per Release 6, but NOT registered in `.claude/settings.json`.
     Going live requires a SEPARATE, explicit Owner-approved step outside
     this program's task dispatch — see Release 6's plan file, 'Post-plan
     gate' section."
  Do not touch `.claude/settings.json` or `.claude/settings.local.json` from
  this task.

### Task 5: envelope tests
- **mode:** A
- **target:** tests/test_subagent_gate_capability_envelope.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.027
- **verifier:** python3 -m pytest tests/test_subagent_gate_capability_envelope.py -q | tail -5
- **serves:** AC-2 (Req 2)
- **spec:**
  New test file for `renmark.subagent_gate.check_capability_envelope` and
  `renmark.subagent_gate.control_status` (both added in Task 3 — this file
  can only be written correctly once Task 3's parallel_group has landed;
  since Task 3 is parallel_group 2 and this task is parallel_group 3, treat
  Task 3's `subagent_gate.py` as already-merged context). Cover, at minimum:
  - `control_status("path", "claude") == "enforced"`;
    `control_status("path", "codex") == "verified_after"`;
    `control_status("command", "codex") == "enforced"`;
    `control_status("network_domain", "claude") == "advisory"`;
    `control_status("external_action", "codex") == "unsupported"`;
    `control_status("nonsense", "claude") == "unsupported"` (unknown control
    degrades safely, never raises).
  - `check_capability_envelope` for `role="code-implementer"`,
    `host="claude"`, `requested_scope={"paths": ["renmark/subagent_gate.py"]}`
    (in-envelope per that role's `allowed_targets`) → the `path` dimension's
    verdict `passed is True`.
  - Same role/host with `requested_scope={"paths": ["secrets/keys.pem"]}`
    (out of envelope) → the `path` dimension's verdict `passed is False` and
    `violations` is non-empty.
  - Same as above but `host="codex"` → the `path` dimension's verdict
    `passed is True` (verified_after is never a pre-dispatch block) AND its
    `reason` explicitly mentions post-action-only verification — assert on
    the reason text, not just `passed`.
  - `command` dimension: `role="test-writer"` (allowed_commands includes
    `"pytest"`) with `requested_scope={"commands": ["pytest"]}` passes;
    `requested_scope={"commands": ["rm"]}` fails with a non-empty
    `violations` tuple. `role="general-purpose"` (empty `allowed_commands`)
    with any command always passes (no restriction declared).
  - `spend_timeout` dimension: a `requested_scope["budget"]` well within
    tier defaults passes; a `requested_scope["budget"]` exceeding
    `DEFAULT_MAX_TOKENS_PER_DISPATCH` for the role's tier fails.
  - `network_domain` / `git_action` / `external_action` dimensions: always
    `passed=True` regardless of `requested_scope` content, on both hosts,
    with the `status` field correctly `"advisory"`/`"advisory"`/
    `"unsupported"`.
  - A test asserting the module's `ENVELOPE_CONTROL_STATUS` table matches
    exactly the 6-control × 2-host table in this plan's "Per-control status"
    section (guards against silent drift between the code and the claimed
    status — no `enforced` claim the table doesn't back).
  No production code in this task — test file only.

### Task 6: baseline enforcement-path tests (required before Task 8 flips the switch)
- **mode:** A
- **target:** tests/test_r6_host_agent_scope_enforcement.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.027
- **verifier:** python3 -m pytest tests/test_r6_host_agent_scope_enforcement.py -q | tail -5
- **serves:** AC-2 (Req 2)
- **spec:**
  This is the REQUIRED baseline that must exist and be reviewable BEFORE
  Task 8 flips `enforce_wave_dispatch_scopes` from "never called in
  production" to "actually called" — write it test-first, against the API
  Task 8 will add (below), the same TDD pattern
  `tests/test_wp9_scope_enforcement_wiring.py` already used for
  `enforce_wave_dispatch_scopes` itself. Task 8 will add
  `dispatch.build_host_dispatch_plan_with_scope(wave, *, host, ...) ->
  HostDispatchPlan` (extends the existing `build_host_dispatch_plan` to also
  populate a `scoped_dispatches: dict[int, fast_path.WorkerScope]` attribute
  on the returned `HostDispatchPlan`, using the SAME eligibility logic
  `dispatch._maybe_scoped_claude_dispatch` already uses — single Claude task,
  passes `fast_path.classify_fast_path`) and
  `dispatch.enforce_host_agent_dispatch_scope(host_plan, repo, base_sha) ->
  None` (raises `dispatch.WaveScopeViolationError` on violation, no-op when
  `host_plan.scoped_dispatches` is empty — mirrors
  `enforce_wave_dispatch_scopes`'s exact contract, reusing
  `fast_path.verify_worker_scope` under the hood, not reimplementing it).
  Write exactly these two cases at minimum (real git repos via
  `tmp_path`, same fixture pattern as
  `tests/test_wp9_scope_enforcement_wiring.py`'s `_init_repo_with_files`):
  1. **Allowed dispatch passes through unchanged**: build a single-task wave
     targeting one narrow file, call `build_host_dispatch_plan_with_scope`,
     confirm `host_plan.scoped_dispatches` has one entry, make an in-scope
     git commit, call `enforce_host_agent_dispatch_scope` — must NOT raise.
  2. **Out-of-envelope dispatch is denied with a clear error**: same setup,
     but the committed diff touches a file outside the declared scope (or
     deletes a file) — `enforce_host_agent_dispatch_scope` must raise
     `dispatch.WaveScopeViolationError` whose message names the violating
     task index and the specific violation kind (reuse
     `WaveScopeViolationError`'s existing `__str__`/`.violations` shape,
     asserted the same way `test_wp9_scope_enforcement_wiring.py` already
     asserts on it).
  Also add one test confirming a multi-task Claude wave (no single eligible
  task) produces an EMPTY `scoped_dispatches` and a no-op enforce call — the
  unscoped case must stay silent, matching R-0.1/WP-9's existing
  no-enforcement-without-opt-in convention.
  This file will FAIL to import/collect until Task 8 adds the two new
  `dispatch` functions it references — that is expected and correct for a
  test-before-flip-switch ordering; Task 8's own verifier re-runs this file
  and must see it pass.

### Task 7: prototype hook tests for the hardened Bash/multi-role path
- **mode:** B
- **target:** tests/test_capability_envelope_prototype.py
- **complexity:** simple
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 500
- **est_cost_usd:** 0.015
- **verifier:** python3 -m pytest tests/test_capability_envelope_prototype.py -q | tail -5
- **serves:** AC-2 (Req 2)
- **spec:**
  Extend the existing test file (58 lines today, covering the Write/Edit
  path against `code-implementer`) with cases for Task 4's hardening,
  invoking the hook script the same way the existing tests already do
  (subprocess with JSON on stdin, or direct function import — match
  whatever pattern the existing tests use, do not introduce a second
  invocation style). Add:
  - A `Bash` tool call with `tool_input.command = "pytest tests/"` for a
    role whose `allowed_commands` includes `"pytest"` → `permissionDecision:
    "allow"`.
  - A `Bash` tool call with `tool_input.command = "rm -rf /"` for the same
    role → `permissionDecision: "deny"`, with a reason mentioning the
    allowlist.
  - A `Bash` tool call for a role with an empty `allowed_commands` (e.g.
    `general-purpose`) → always `allow` regardless of command (no
    restriction declared).
  - Malformed/missing `command` field on a `Bash` payload → hook exits 0
    with no decision (pass-through), matching existing malformed-input
    tests' pattern.
  Do not modify the hook script itself in this task — Task 4 owns that file.

### Task 8: wire the flip — enforce_host_agent_dispatch_scope in dispatch.py
- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 4
- **est_tokens:** 2000
- **est_cost_usd:** 0.18
- **verifier:** python3 -m pytest tests/test_r6_host_agent_scope_enforcement.py tests/test_wp9_scope_enforcement_wiring.py tests/test_dispatch.py -q | tail -5
- **serves:** AC-2 (Req 2)
- **spec:**
  This is the concrete F1 fix, scoped precisely by this plan's
  pre-decomposition investigation (see the plan's intent paragraph above —
  read it before starting): the production Claude Code orchestration path
  (`plugin/skills/orchestrate/SKILL.md` Step 3b) calls
  `dispatch.build_host_dispatch_plan()` directly, NOT `dispatch.dispatch_wave()`
  — so `dispatch_wave()`'s existing `scoped_dispatches`/
  `enforce_wave_dispatch_scopes` machinery, while fully built and tested
  (`tests/test_wp9_scope_enforcement_wiring.py`), has never had a live
  caller. Add exactly two new functions to `renmark/dispatch.py`, reusing
  existing logic, not reimplementing it:

  1. `build_host_dispatch_plan_with_scope(wave, *, host, dependency_summaries
     =None, upstream_artifact_pointers=None, reasoning_instruction="") ->
     HostDispatchPlan` — thin wrapper around the EXISTING
     `build_host_dispatch_plan` (call it, don't duplicate its body). After
     getting the plan back, when `host == "claude"`, compute scope the SAME
     way `_maybe_scoped_claude_dispatch` already does (reuse that private
     helper directly — it already takes `claude_tasks: list[Task]` and
     `repo: Path` and returns `tuple[int, AgentDispatch] | None`) against the
     wave's Claude-executor tasks, and set a new `scoped_dispatches:
     dict[int, fast_path.WorkerScope]` attribute on the returned plan
     (extract `.scope` off the `AgentDispatch` `_maybe_scoped_claude_dispatch`
     returns — you will need to add `scoped_dispatches:
     dict[int, "fast_path.WorkerScope"] = field(default_factory=dict)` to the
     `HostDispatchPlan` dataclass itself, additive field, default empty dict
     so every EXISTING caller of `build_host_dispatch_plan` is byte-identical
     unaffected). When `host == "codex"`, `scoped_dispatches` stays empty —
     per the Owner's 2026-08-05 scope decision, Codex gets no pre-action
     scoping this release (path stays `verified_after`, Layer-B only).

  2. `enforce_host_agent_dispatch_scope(host_plan: HostDispatchPlan, repo:
     Path, base_sha: str) -> None` — mirrors `enforce_wave_dispatch_scopes`'s
     exact contract (same docstring conventions: call this AFTER the host's
     real Agent tool call completed and the diff is present at HEAD; a wave
     with empty `scoped_dispatches` is a silent no-op, matching R-0.1
     baseline for anything that never opted in). Internally, for each
     `(task_index, scope)` in `host_plan.scoped_dispatches.items()`, call
     `fast_path.verify_worker_scope(scope, repo, base_sha)` (reused directly,
     not reimplemented) and collect any failing verdicts into the SAME
     `WaveScopeViolation`/`WaveScopeViolationError` types
     `enforce_wave_dispatch_scopes` already uses (reuse those classes
     unchanged — do not create parallel violation types) — raise
     `WaveScopeViolationError` if any violation exists.

  Run `tests/test_r6_host_agent_scope_enforcement.py` (Task 6, already
  written against exactly this API) and confirm it now passes — that file
  must go from failing-to-collect (missing functions) to fully green. Also
  re-run `tests/test_wp9_scope_enforcement_wiring.py` and `tests/test_dispatch.py`
  to confirm zero regression to `dispatch_wave()`'s own existing behavior —
  this task must not touch `dispatch_wave()`, `enforce_wave_dispatch_scopes`,
  `verify_wave_dispatch_scopes`, or `_maybe_scoped_claude_dispatch`'s bodies,
  only ADD the two new functions plus the one additive dataclass field. Do
  NOT modify `plugin/skills/orchestrate/SKILL.md` in this task — that is
  Task 9 and it is the only task that actually makes this new API reachable
  from the live orchestration flow.

### Task 9: wire enforcement into the live orchestrate flow
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 5
- **est_tokens:** 1000
- **est_cost_usd:** 0.033
- **verifier:** grep -q "enforce_host_agent_dispatch_scope" plugin/skills/orchestrate/SKILL.md && grep -q "check_capability_envelope" plugin/skills/orchestrate/SKILL.md
- **serves:** AC-2 (Req 2)
- **spec:**
  This is the task that makes Release 6's enforcement code actually reachable
  from the real orchestration path — everything before this task in the plan
  is built-and-tested-but-inert until this lands, matching this plan's own
  intent paragraph about the "flip the switch" ordering. Two prose edits to
  the skill, both near the existing "Host-agent dispatch shape" subsection
  (around line 239) and the "3c. Run verifier per task" subsection (around
  line 299) — do not restructure the skill's step numbering, insert
  sub-bullets/sub-steps into the existing flow:

  1. **Before** the existing `host_plan = dispatch.build_host_dispatch_plan(...)`
     call: replace that call with
     `host_plan = dispatch.build_host_dispatch_plan_with_scope(wave, host=<host>,
     ...)` (same arguments, new function name — Task 8 added it as a drop-in
     superset). Immediately before issuing the Agent/spawn_agent call for
     each host-agent task, add one explicit sentence instructing the skill
     to call `subagent_gate.check_capability_envelope(role=<task.role>,
     requested_scope={"paths": [task.target], "commands": [], "budget":
     task.budget if hasattr(task, "budget") else None}, host=<host>)` and,
     if ANY returned `EnvelopeVerdict.passed` is `False` for the `command` or
     `spend_timeout` dimensions (the two `enforced`-on-both-hosts controls —
     `path` is handled separately by step 2 below since it's post-action),
     treat that task as a pre-dispatch DENIAL: do not issue the Agent call,
     mark the task FAIL with the verdict's `reason`, and do not retry.
  2. **After** the existing "3c. Run verifier per task" step, for any task
     whose Claude Code host-agent dispatch was scoped (i.e.
     `host_plan.scoped_dispatches` is non-empty for that task's index — this
     only ever happens on Claude Code per Task 8's host-gating, never
     Codex), add one explicit instruction: call
     `dispatch.enforce_host_agent_dispatch_scope(host_plan, repo, base_sha)`
     (using the same `base_sha` the wave started from) immediately after
     that task's changes are committed. If it raises
     `WaveScopeViolationError`, treat the task as a scope-violation FAIL
     (downgrade from any earlier PASS) and surface the violation's message
     verbatim in the task's summary — this must NOT be silently swallowed.
     State explicitly in this new text: "This is additive defense-in-depth
     on top of Layer-B (`fast_path.verify_worker_scope`, unchanged); Layer-B
     remains the authoritative post-action check on both Claude Code and
     Codex."
  Do not add a new Owner-facing gate/question here — this is routine
  per-task enforcement inside the existing dispatch flow, not a milestone
  gate (Pause-Policy is unaffected). Do not touch any other section of the
  skill file.

---

## Post-plan gate (NOT a dispatched task — separate Owner approval required)

Task 4 hardens `.claude/hooks/capability_envelope_prototype.py` but this
plan deliberately does **not** include a task that registers it in
`.claude/settings.json`. Making the `PreToolUse` hook live is its own,
separately-gated action: after this plan's tasks land and verify green,
present the exact `.claude/settings.json` diff (the `hooks.PreToolUse[]`
registration block) to the Owner for one explicit approval before it is
applied — never as part of `/renmark:orchestrate`'s normal task dispatch for
this plan.

---

## Cost preview

| Task | Executor | Est. tokens (+overhead) | Est. cost |
|---|---|---|---|
| 1 — subagent_profiles.py | sonnet | 800 + 10,000 | $0.0324 |
| 2 — cost.py | sonnet | 700 + 10,000 | $0.0321 |
| 3 — subagent_gate.py | opus | 1,800 + 10,000 | $0.1770 |
| 4 — prototype hook hardening | sonnet | 900 + 10,000 | $0.0327 |
| 5 — envelope tests | codex | 900 (no overhead) | $0.0270 |
| 6 — baseline enforcement tests | codex | 900 (no overhead) | $0.0270 |
| 7 — prototype hook tests | codex | 500 (no overhead) | $0.0150 |
| 8 — dispatch.py wiring (flip) | opus | 2,000 + 10,000 | $0.1800 |
| 9 — orchestrate/SKILL.md wiring | sonnet | 1,000 + 10,000 | $0.0330 |

**Tasks:** 9 (5 parallel groups) — well under the 15-task cap.
**Total estimated tokens (incl. ~10k Agent overhead per non-codex task):** ~59,300
**Total estimated cost: ~$0.556**
**Executors:** sonnet×4, opus×2, codex×3
**Subagents used:** yes (all 9 tasks). No Fable/adversarial-review escalation in this plan.
