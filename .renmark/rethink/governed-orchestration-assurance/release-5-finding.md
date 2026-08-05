---
artifact_type: spike-finding
schema_version: 1
created_at: 2026-08-05T04:41:54Z
source_sha: 6e868ffc68cfa163ad87c20e3bc7eaf01cb711da
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-5.plan.md
generator: haiku
dependency_refs:
  - .renmark/rethink/governed-orchestration-assurance/roadmap.md
  - renmark/subagent_profiles.py
  - plugin/skills/codereview/SKILL.md
---

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
