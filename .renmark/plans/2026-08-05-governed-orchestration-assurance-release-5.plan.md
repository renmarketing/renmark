# Plan: governed-orchestration-assurance — Release 5 (PreToolUse capability-envelope spike #7)

**Intent.** This is a BOUNDED, 1-SESSION, PROTOTYPE-ONLY SPIKE per
`.renmark/rethink/governed-orchestration-assurance/roadmap.md`'s Release 5
entry. Its job is to answer a design question for Release 6 (is metadata-driven,
pre-action, hook-time allow/deny enforcement feasible on Claude Code and on
Codex?) — NOT to implement Release 6. This release does **not** touch
`fast_path.py`, `subagent_gate.py`, `dispatch.py`, or any production dispatch
call site, per the roadmap's compatibility guarantee #3
(`fast_path.verify_worker_scope`'s post-action Layer-B semantics stay
untouched — this is a prototype for a NEW, additive pre-action layer, not a
replacement). The prototype hook script and its example registration snippet
live under `.claude/hooks/` and are never wired into this repo's live
`.claude/settings.json` or into any renmark orchestration path — evidence
only, gathered for the Owner's Release 6 decision.

**Pre-decomposition investigation (done at plan time, baked into task specs
below so dispatched executors need no further research):**

1. **Claude Code `PreToolUse` hook contract** (confirmed live against
   `code.claude.com/docs/en/hooks`, fetched 2026-08-05): the hook receives a
   JSON payload on stdin with `session_id`, `cwd`, `hook_event_name`,
   `tool_name`, `tool_input` (e.g. `file_path` for Write/Edit), `tool_use_id`,
   etc. It emits a decision via stdout JSON:
   `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"|"deny"|"ask"|"defer", "permissionDecisionReason": "..."}}`
   with exit code 0 (Claude Code parses the JSON). Exit code 2 is a
   *blocking error* (stderr surfaces to Claude, not a structured decision);
   any other exit code is non-blocking (action proceeds). Hooks register in
   `.claude/settings.json` under `hooks.PreToolUse[].matcher` /
   `hooks.PreToolUse[].hooks[].command`. **Conclusion: real pre-action
   block/deny is supported today, not observe-only.**
2. **Codex's enforcement mechanism**: `renmark/codex_routing.py` (this repo)
   carries no sandbox/approval-policy wiring — Codex routing here is purely
   model/reasoning-tier selection. But `plugin/skills/codereview/SKILL.md`
   (lines ~21, 98, 101, 144, 294) already invokes Codex as
   `codex exec --sandbox read-only -` for the codereview pass, which is a
   real, currently-used, OS-level Codex sandbox flag (not a prompt
   instruction) — confirming Codex *does* have OS-level enforcement, but it
   is coarse-grained (read-only / workspace-write / full-access modes), not
   the fine-grained per-profile glob match (`allowed_targets`) Claude Code's
   `PreToolUse` hook can do. No `.codex/` config in this repo currently
   wires per-role glob enforcement.
3. **`renmark/subagent_profiles.py`'s `ProfileSpec.allowed_targets`**: a
   plain `str` field (glob pattern or human-readable description), currently
   informational only — the module docstring says "Informational for now;
   enforced in future Agency Mode." The `code-implementer` profile's value
   is `"renmark/**/*.py, bin/*, *.py"` (pure comma-separated globs, no
   parenthetical prose, making it the cleanest profile to prototype against).

**No `.claude/settings.json` exists in this repo today** (only
`.claude/settings.local.json`, permissions-only, no `hooks` key) — so there is
no live hook to accidentally collide with.

---

### Task 1: PreToolUse capability-envelope prototype hook script
- **mode:** A
- **target:** .claude/hooks/capability_envelope_prototype.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile .claude/hooks/capability_envelope_prototype.py
- **serves:** AC-2 (Req 2)
- **spec:**
  Write a standalone, prototype-only Python script implementing Claude
  Code's `PreToolUse` hook contract, scoped to ONE agent profile
  (`code-implementer`) from `renmark/subagent_profiles.py`.

  Contract (confirmed against Claude Code docs, do not re-derive):
  - Read one JSON object from stdin with at least `tool_name` (str) and
    `tool_input` (dict, may contain `file_path`).
  - This prototype only judges `Write` and `Edit` tool calls. For any other
    `tool_name`, or if `tool_input` has no `file_path`, print nothing and
    `sys.exit(0)` (defers to normal permission flow — no decision).
  - For `Write`/`Edit` with a `file_path`: import
    `PROFILES["code-implementer"].allowed_targets` from
    `renmark.subagent_profiles` (add `sys.path` handling so the script runs
    standalone: insert the repo root, computed as
    `Path(__file__).resolve().parents[2]`, at the front of `sys.path` before
    the import). Split `allowed_targets` on `,`, strip whitespace, and match
    `file_path` against each glob using `fnmatch.fnmatch` (relative path,
    forward slashes — do not assume any particular cwd beyond what
    `tool_input.get("cwd")` or the JSON payload's `cwd` field says; if `cwd`
    is present, use it to make `file_path` relative before matching, else
    match `file_path` as-is).
  - If any glob matches: print to stdout
    `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "permissionDecisionReason": "path matches code-implementer allowed_targets"}}`
    and `sys.exit(0)`.
  - If no glob matches: print to stdout
    `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "path does not match code-implementer allowed_targets: <the allowed_targets string>"}}`
    and `sys.exit(0)`.
  - Wrap the whole body in `if __name__ == "__main__":` calling a `main()`
    function; use only the Python stdlib (`json`, `sys`, `fnmatch`,
    `pathlib`). No writes to any file — this script only reads stdin and
    writes stdout.
  - Add a short module docstring stating: PROTOTYPE / SPIKE ONLY — not
    wired into `.claude/settings.json`, not used by any renmark dispatch
    path; evidence artifact for Release 5 of the
    `governed-orchestration-assurance` roadmap.
  - Also write a second file (same task, same mode A) as documentation of
    how it *would* be registered, WITHOUT touching the live
    `.claude/settings.json`: create
    `.claude/hooks/capability_envelope_prototype.settings.example.json`
    containing a minimal example `hooks.PreToolUse` block (matcher
    `"Write|Edit"`, command pointing at
    `${CLAUDE_PLUGIN_ROOT}` is NOT applicable here — use a relative
    `${CLAUDE_PROJECT_DIR}/.claude/hooks/capability_envelope_prototype.py`
    path) so a human reviewer can see the intended wiring without it being
    live.

### Task 2: capability-envelope prototype integration test
- **mode:** A
- **target:** tests/test_capability_envelope_prototype.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest tests/test_capability_envelope_prototype.py -q
- **serves:** AC-2 (Req 2)
- **spec:**
  Write a pytest module that proves the Task 1 prototype hook script
  (`.claude/hooks/capability_envelope_prototype.py`) can both pass an
  allowed target and block a disallowed one. Depends on Task 1 already
  existing at that path.

  Use `subprocess.run([sys.executable, "<repo_root>/.claude/hooks/capability_envelope_prototype.py"], input=json.dumps(payload), capture_output=True, text=True)`
  (compute `<repo_root>` via `Path(__file__).resolve().parents[1]`, same
  convention as other tests in `tests/`).

  Two test functions:
  1. `test_allowed_target_passes` — payload
     `{"tool_name": "Write", "tool_input": {"file_path": "renmark/scratch_prototype.py"}, "cwd": "<repo_root>"}`.
     Assert exit code 0, parse stdout as JSON, assert
     `result["hookSpecificOutput"]["permissionDecision"] == "allow"`.
  2. `test_disallowed_target_blocks` — payload
     `{"tool_name": "Write", "tool_input": {"file_path": "secrets/.env"}, "cwd": "<repo_root>"}`.
     Assert exit code 0, parse stdout as JSON, assert
     `result["hookSpecificOutput"]["permissionDecision"] == "deny"`.

  Also add a third test, `test_non_write_tool_defers`, sending
  `{"tool_name": "Bash", "tool_input": {"command": "ls"}}` and asserting
  stdout is empty and exit code is 0 (defer/no-decision path).

### Task 3: Release 5 spike finding
- **mode:** A
- **target:** .renmark/rethink/governed-orchestration-assurance/release-5-finding.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.00
- **verifier:** test -f .renmark/rethink/governed-orchestration-assurance/release-5-finding.md
- **serves:** AC-2 (Req 2)
- **spec:**
  Create a one-page finding doc with this exact top metadata block, then the
  content below verbatim (fill in `source_sha` with the output of
  `git rev-parse HEAD`, and `created_at` with the current UTC ISO8601
  timestamp):

  ```
  ---
  artifact_type: spike-finding
  schema_version: 1
  created_at: <ISO8601>
  source_sha: <git sha>
  related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-5.plan.md
  generator: haiku
  dependency_refs:
    - .renmark/rethink/governed-orchestration-assurance/roadmap.md
    - renmark/subagent_profiles.py
    - plugin/skills/codereview/SKILL.md
  ---
  ```

  Then this content, verbatim:

  ```markdown
  # Release 5 finding — PreToolUse capability-envelope spike (#7)

  ## Question
  Is pre-action, hook-time, metadata-driven allow/deny enforcement feasible
  on both Claude Code and Codex, ahead of Release 6's production wiring?

  ## Claude Code — FEASIBLE (confirmed)
  Claude Code's `PreToolUse` hook receives a JSON payload on stdin
  (`tool_name`, `tool_input`, `cwd`, `session_id`, etc.) before the tool
  call executes, and can genuinely block it: returning
  `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` on stdout
  with exit code 0 denies the call; `"allow"` permits it; `"ask"` escalates
  to the user; `"ask"`/`"defer"` fall back to normal permission handling.
  This is real pre-action enforcement, not observation-only. Evidence:
  `.claude/hooks/capability_envelope_prototype.py` (this release) reads a
  profile's `allowed_targets` from `renmark/subagent_profiles.py` and
  emits allow/deny per target path, proven by
  `tests/test_capability_envelope_prototype.py`'s passing (allowed) and
  blocking (disallowed) cases.

  ## Codex — PARTIALLY FEASIBLE (coarse-grained only)
  Codex has a real OS-level sandbox mechanism — not prompt-only — already
  in production use in this repo: `plugin/skills/codereview/SKILL.md` runs
  `codex exec --sandbox read-only -` for its review pass. `renmark/codex_routing.py`
  carries no sandbox/approval-policy wiring of its own (routing is
  model/reasoning-tier only). However, Codex's sandbox is a small set of
  coarse global modes (read-only / workspace-write / danger-full-access),
  not a per-profile glob matcher like `allowed_targets`. Codex has no
  native equivalent of Claude Code's `PreToolUse` hook that could read a
  renmark `ProfileSpec.allowed_targets` glob and deny per-path. Fine-grained,
  metadata-driven enforcement on Codex would need a wrapper (e.g. a
  pre-exec argv/path check before invoking `codex exec`) — not a built-in
  hook.

  ## Recommendation for Release 6
  Host-aware dual path: on Claude Code, wire `PreToolUse` hooks reading
  `ProfileSpec.allowed_targets` for real pre-action allow/deny (the
  metadata-driven path Release 6 was designed for). On Codex, fall back to
  coarse sandbox-mode selection (`--sandbox read-only` for read-only roles
  like `audit-reader`/`inspector`, `workspace-write` otherwise) plus
  Layer-B's existing post-action `fast_path.verify_worker_scope` check as
  the real enforcement backstop — Codex does not get symmetric pre-action
  glob enforcement in Release 6 without new wrapper work, which is out of
  this spike's scope and should be raised to the Owner as a scope
  question if Release 6 wants parity.

  ## Stop-condition result
  Hook contract supports metadata-driven allow/deny **on Claude Code**;
  it does **not** on Codex without additional wrapper work. Per the
  roadmap's stated stop condition, this is a partial "proceed" — Release 6
  should proceed with the Claude Code path as designed and treat the Codex
  path as post-action-only (existing Layer-B) unless the Owner explicitly
  approves new Codex wrapper scope.
  ```

---

## Cost preview

| Task | Executor | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|
| 1. capability_envelope_prototype.py | sonnet | 10,900 | $0.03 |
| 2. test_capability_envelope_prototype.py | codex | 600 | $0.02 |
| 3. release-5-finding.md | haiku | 10,500 | $0.00 |

**Tasks:** 3 (2 parallel groups — group 1: Task 1 + Task 3; group 2: Task 2, after Task 1)
**Total tokens (incl. ~10k Agent overhead/task on Claude executors):** ~22,000
**Total cost:** ~$0.05
**Executors:** sonnet×1, codex×1, haiku×1
