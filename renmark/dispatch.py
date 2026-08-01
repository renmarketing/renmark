"""Wave-based parallel dispatcher.

Groups tasks by parallel_group, validates that tasks sharing a group write
to disjoint targets, and dispatches each task to its executor backend.

Host-agent tasks cannot run from this Python process. The dispatcher returns a
``needs_agent`` compatibility marker; :func:`build_host_dispatch_plan` then
maps the same bounded packet to Claude's Agent/Workflow tools or Codex's
spawn_agent/wait_agent/followup_task tools. This module shapes contracts only
and never claims to execute either host tool.

Permission-economy: by accepting a list of tasks per wave call, the user
sees one Bash prompt per wave instead of one per task.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import fast_path
from .parser import Task
from .providers import claude_agent

# ── R-0.0 baseline tracing (opt-in, additive, disabled by default) ────────────
#
# Behind RENMARK_BASELINE_TRACE=1 only. Unset (the default) means dispatch_wave's
# runtime behavior is byte-identical to before this block existed — see
# .bootstrap-renmark/milestones/R-0.0/instrumentation-design.md. Not part of
# Renmark's product surface; exists solely to measure current orchestration
# behavior for the R-0.0 baseline evidence package.

_BASELINE_TRACE_ENV = "RENMARK_BASELINE_TRACE"
_BASELINE_TRACE_LEDGER = "baseline-trace.jsonl"


def _append_baseline_trace(repo: Path, record: dict[str, object]) -> None:
    """Append one opt-in trace row. Never raises; a trace failure must not
    affect the caller's real return value."""
    try:
        path = Path(repo) / ".renmark" / "analytics" / _BASELINE_TRACE_LEDGER
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": datetime.now(timezone.utc).isoformat(), **record}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        pass


@dataclass
class TaskResult:
    task_index: int
    executor: str
    status: str  # "passed" | "failed" | "needs_agent" | "skipped"
    sha: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_s: float = 0.0
    note: str = ""


@dataclass
class WaveResult:
    group_id: int
    tasks: list[TaskResult] = field(default_factory=list)
    # R-0.2/WP-8a: populated only for the single-task, single-file-target
    # Claude-model case (see `_maybe_scoped_claude_dispatch` below). Keys are
    # `task_index`. Multi-task Claude waves intentionally leave this empty —
    # see the module-level note near `verify_agent_dispatch_scope` for why
    # (design doc §3's multi-wave/multi-task diff-attribution problem applies
    # equally within one wave when >1 Claude task shares a base_sha).
    scoped_dispatches: dict[int, "claude_agent.AgentDispatch"] = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        return all(t.status == "passed" for t in self.tasks)

    @property
    def needs_agent(self) -> list[TaskResult]:
        return [t for t in self.tasks if t.status == "needs_agent"]


def group_tasks_by_wave(tasks: list[Task]) -> list[list[Task]]:
    """Split tasks into waves by parallel_group.

    Tasks without an explicit parallel_group default to their task index
    (= each in its own group = serial). Waves are returned in numerically-
    sorted group order.
    """
    groups: dict[int, list[Task]] = {}
    for t in tasks:
        gid = t.parallel_group if t.parallel_group is not None else t.index
        groups.setdefault(gid, []).append(t)
    return [groups[k] for k in sorted(groups.keys())]


def validate_wave(wave: list[Task]) -> None:
    """A wave must touch disjoint target files, and no task can list
    another's target in its context_files.

    Raises ValueError on conflict.
    """
    targets = {t.target for t in wave}
    if len(targets) != len(wave):
        dup = [t.target for t in wave]
        seen: set[str] = set()
        repeated: list[str] = []
        for x in dup:
            if x in seen:
                repeated.append(x)
            else:
                seen.add(x)
        raise ValueError(
            f"parallel wave has overlapping targets: {sorted(set(repeated))}. "
            f"Tasks in the same parallel_group must touch disjoint files."
        )
    for t in wave:
        for ctx in t.context_files:
            if ctx in targets and ctx != t.target:
                raise ValueError(
                    f"task {t.index} reads `{ctx}` (in context_files) which is "
                    f"another wave-member's target. Move it to a later wave."
                )


def dispatch_wave(
    wave: list[Task],
    *,
    repo: Path,
    run_task: Callable[[Task, Path], TaskResult],
    max_workers: int | None = None,
) -> WaveResult:
    """Run all non-Claude tasks in a wave concurrently.

    `run_task` is injected (test-friendly). Claude-model tasks (opus/sonnet)
    don't run here — they get `status="needs_agent"` so the skill can issue
    Agent tool calls itself.
    """
    if not wave:
        return WaveResult(group_id=0, tasks=[])

    validate_wave(wave)
    gid = wave[0].parallel_group if wave[0].parallel_group is not None else wave[0].index

    if os.environ.get(_BASELINE_TRACE_ENV) == "1":
        _append_baseline_trace(
            repo,
            {
                "kind": "wave_dispatch",
                "group_id": gid,
                "wave_size": len(wave),
                "parallel_groups": sorted(
                    {t.parallel_group for t in wave if t.parallel_group is not None}
                ),
                "task_targets": [t.target for t in wave],
            },
        )

    result = WaveResult(group_id=gid)

    # Split: Claude-model tasks marked needs_agent; everything else runs in parallel.
    claude_tasks = [t for t in wave if claude_agent.is_claude_executor(t.executor)]
    runnable = [t for t in wave if not claude_agent.is_claude_executor(t.executor)]

    # R-0.2/WP-8a: for a wave whose Claude-model sub-group is exactly one
    # task with a narrow, single/few-file target (same eligibility signals
    # `fast_path.classify_fast_path` already uses), construct that task's
    # `WorkerScope` and build a scoped `AgentDispatch` so the caller (the
    # host-agent skill issuing the real Agent tool call) can later run
    # `verify_agent_dispatch_scope` against the real git diff. Multi-task
    # Claude waves are left unscoped here on purpose — see `WaveResult
    # .scoped_dispatches`'s docstring and `verify_wave_dispatch_scopes` below.
    scoped_dispatch = _maybe_scoped_claude_dispatch(claude_tasks, repo)
    if scoped_dispatch is not None:
        task_index, agent_dispatch = scoped_dispatch
        result.scoped_dispatches[task_index] = agent_dispatch

    for t in claude_tasks:
        note = "dispatch this via the Agent tool from the orchestrate skill"
        if t.index in result.scoped_dispatches:
            note += (
                " (scope declared — after it returns, call "
                "enforce_wave_dispatch_scopes(result, repo, base_sha) to raise "
                "loud on any violation, or verify_wave_dispatch_scopes for the "
                "inspectable-tuple form)"
            )
        result.tasks.append(
            TaskResult(
                task_index=t.index,
                executor=t.executor,
                status="needs_agent",
                note=note,
            )
        )

    if not runnable:
        return result

    workers = max_workers or min(len(runnable), 8)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_run_one, run_task, t, repo): t for t in runnable}
        for fut in concurrent.futures.as_completed(futures):
            result.tasks.append(fut.result())

    # Sort results by task index for deterministic reporting.
    result.tasks.sort(key=lambda r: r.task_index)
    return result


def _run_one(run_task: Callable[[Task, Path], TaskResult], task: Task, repo: Path) -> TaskResult:
    start = time.monotonic()
    try:
        r = run_task(task, repo)
        r.elapsed_s = time.monotonic() - start
        return r
    except Exception as e:
        return TaskResult(
            task_index=task.index,
            executor=task.executor,
            status="failed",
            elapsed_s=time.monotonic() - start,
            note=f"{type(e).__name__}: {e}",
        )


# ── R-0.2/WP-5: generalized post-hoc scope verification ─────────────────────
#
# Per .renmark/plans/r-0.2/scope-enforcement-generalization-design.md §4/§9:
# reuse fast_path.WorkerScope/verify_worker_scope UNCHANGED; only the call
# site generalizes to any AgentDispatch (fast-path or normal) that declared
# a scope. Multi-wave/cumulative verification (design doc §3/§7, Options
# A/B/C) is explicitly NOT decided here — this function verifies exactly one
# dispatch's diff against exactly one declared scope, the same granularity
# fast-path already uses. Wiring cumulative or per-wave verification across
# multiple dispatches in a single wave/program run is a documented follow-up,
# not implemented in this work package.


def _maybe_scoped_claude_dispatch(
    claude_tasks: list[Task],
    repo: Path,
) -> tuple[int, "claude_agent.AgentDispatch"] | None:
    """R-0.2/WP-8a wiring: build a scoped ``AgentDispatch`` for the simplest
    case only — exactly one Claude-model task in this wave, whose target
    passes the SAME 5-signal eligibility check ``fast_path.classify_fast_path``
    already uses for the fast path (reused, not reinvented — same threshold,
    e.g. ``MAX_FAST_PATH_FILES``).

    Returns ``None`` (no scope constructed, unchanged R-0.1 behavior) when:
    - there isn't exactly one Claude-model task in the wave (multi-task
      Claude waves are a documented follow-up — see the diff-attribution
      problem in scope-enforcement-generalization-design.md §3, which applies
      within a single multi-task wave just as much as across waves), or
    - the lone task doesn't pass ``classify_fast_path``'s signals (e.g. a
      wide/glob target, a renmark/**-or-plugin/** target, a chained verifier).

    This function performs no I/O beyond composing prompt strings via
    ``claude_agent.build_agent_dispatch`` and never calls the Agent tool
    itself (Python cannot).
    """
    if len(claude_tasks) != 1:
        return None
    task = claude_tasks[0]
    verdict = fast_path.classify_fast_path([task])
    if not verdict.eligible:
        return None
    scope = fast_path.worker_scope_from_verdict(verdict, [task])
    agent_dispatch = claude_agent.build_agent_dispatch(task, repo, scope=scope)
    return task.index, agent_dispatch


@dataclass(frozen=True)
class WaveScopeViolation:
    """One scoped dispatch's FAILING post-hoc verification, structured so a
    caller can act on it (block wave completion, log, escalate) instead of
    the violation being silently dropped."""

    task_index: int
    verdict: fast_path.ScopeVerdict


def verify_wave_dispatch_scopes(
    scoped_dispatches: dict[int, "claude_agent.AgentDispatch"],
    repo: Path,
    base_sha: str,
) -> tuple[WaveScopeViolation, ...]:
    """Post-hoc Layer-B check for every scoped dispatch a wave produced.

    Call this AFTER the host has issued the real Agent tool call(s) for
    ``scoped_dispatches`` and the resulting changes are committed (or at
    least present in the working tree) at HEAD. Delegates per-dispatch to
    ``verify_agent_dispatch_scope`` (reused, not reimplemented).

    Returns an empty tuple when every scoped dispatch passed (or there were
    none to check) — NOT when verification was skipped. A non-empty tuple is
    a hard signal: the caller MUST NOT treat the corresponding task(s) as
    complete/mergeable. This function never swallows a violation; it always
    surfaces it in the returned tuple.
    """
    violations: list[WaveScopeViolation] = []
    for task_index, agent_dispatch in scoped_dispatches.items():
        scope_verdict = verify_agent_dispatch_scope(agent_dispatch, repo, base_sha)
        if scope_verdict is not None and not scope_verdict.passed:
            violations.append(WaveScopeViolation(task_index=task_index, verdict=scope_verdict))
    return tuple(violations)


# R-0.2/WP-9 — the WP-8 independent re-review (`.renmark/reviews/
# 2026-08-01-r-0.2-closeout.md`, "WP-8 Wiring Re-Review") found that
# `verify_wave_dispatch_scopes` above is real enforcement logic that nothing
# ever CALLS: a tuple return a caller can inspect (or just as easily ignore)
# is not enforcement. `enforce_wave_dispatch_scopes` is the fail-loud
# counterpart — it raises `WaveScopeViolationError` instead of handing back
# a value that could silently go unread. There is no synchronous point
# inside `dispatch_wave` itself where a scoped Claude dispatch's real
# post-dispatch diff is available (the actual Agent tool call happens
# outside this process, after `dispatch_wave` already returned
# `status="needs_agent"` — see `_maybe_scoped_claude_dispatch`'s docstring
# and `fast_path.py`'s module docstring steps 1-4 for the same established
# two-phase build-then-verify pattern). This function is therefore the
# sanctioned call site for whoever holds the real post-dispatch `base_sha`
# once the host's Agent call has actually completed — call it instead of
# `verify_wave_dispatch_scopes` whenever a violation must not be able to go
# unnoticed.
class WaveScopeViolationError(RuntimeError):
    """Raised by `enforce_wave_dispatch_scopes` when one or more scoped
    dispatches in a wave failed post-hoc verification. Carries the full
    tuple of `WaveScopeViolation` (never swallowed) so the caller can log or
    act on the specific task(s)/violation(s) involved."""

    def __init__(self, violations: tuple[WaveScopeViolation, ...]) -> None:
        self.violations = violations
        summary = "; ".join(
            f"task {v.task_index}: {len(v.verdict.violations)} disallowed change(s)" for v in violations
        )
        super().__init__(f"wave scope violation(s) detected — {summary}")


def enforce_wave_dispatch_scopes(
    wave_result: WaveResult,
    repo: Path,
    base_sha: str,
) -> None:
    """Fail-loud counterpart to `verify_wave_dispatch_scopes`.

    Call this AFTER the host has issued the real Agent tool call(s) for
    `wave_result.scoped_dispatches` and the resulting changes are present at
    HEAD. Raises `WaveScopeViolationError` when any scoped dispatch in this
    wave failed its post-hoc scope check — a violation can no longer be
    represented only as a field nothing reads. A wave with no scoped
    dispatches (`wave_result.scoped_dispatches` empty — unscoped tasks, or a
    wave whose Claude sub-group didn't qualify for `_maybe_scoped_claude_dispatch`)
    is a silent no-op: verification stays strictly opt-in per WP-8a, exactly
    matching R-0.1 behavior for anything that never declared a scope.
    """
    violations = verify_wave_dispatch_scopes(wave_result.scoped_dispatches, repo, base_sha)
    if violations:
        raise WaveScopeViolationError(violations)


def verify_agent_dispatch_scope(
    dispatch: claude_agent.AgentDispatch,
    repo: Path,
    base_sha: str,
) -> fast_path.ScopeVerdict | None:
    """Post-hoc Layer-B check for one ``AgentDispatch``.

    Returns ``None`` when ``dispatch.scope`` is unset — no verification is
    performed and the caller must treat this exactly as R-0.1 unscoped
    dispatch behaved (no enforcement). When a scope IS declared, delegates
    to ``fast_path.verify_worker_scope`` (reused, not reimplemented) against
    the real git diff between ``base_sha`` and ``HEAD``. A caller MUST NOT
    treat ``None`` as a pass; ``None`` means "not opted in," not "verified
    clean."
    """
    if dispatch.scope is None:
        return None
    return fast_path.verify_worker_scope(dispatch.scope, repo, base_sha)


def estimate_wave_cost(wave: list[Task]) -> tuple[int, float]:
    """Sum est_tokens and est_cost_usd across a wave (treating None as 0)."""
    tok = sum(t.est_tokens or 0 for t in wave)
    cost = sum(t.est_cost_usd or 0.0 for t in wave)
    return tok, cost


# ─────────────────────────────────────────────────────────────────────────────
# G11 — Task-level isolation contract
# ─────────────────────────────────────────────────────────────────────────────
# Each task or parallel group runs in an isolated subagent context. The
# orchestrator never sees the subagent's transcript, generated code, or diff —
# only the SubagentOutput summary. Inputs are equally bounded.
#
# SubagentInput is what the subagent gets.
# SubagentOutput is what the subagent emits back.
# dispatch_task_isolated enforces the contract: violations raise IsolationViolation.

import json as _json
from typing import Any, Literal, cast


class IsolationViolation(RuntimeError):
    """Raised when a subagent response includes fields outside SubagentOutput,
    or when its summary_lines exceed the G3 cap. The orchestrator refuses to
    merge violating outputs.
    """


# Public schema: these are the ONLY fields the orchestrator considers.
SUBAGENT_OUTPUT_FIELDS = frozenset(
    {
        "status",
        "artifact_path",
        "touched_files",
        "sha",
        "summary_lines",
        "dependency_notes",
        "token_count",
        "completion_state",
        "confidence",
        "retry_count",
        # G9 transparency triplet — emitted by cmd_task (renmark-execute --task)
        # and accepted here so executor outputs can expose all six G9 fields.
        "validation_status",
        "parser_success",
        "schema_compliance",
    }
)

SUBAGENT_OUTPUT_STATUS_VALUES = {"PASS", "FAIL", "SKIP"}
SUBAGENT_OUTPUT_COMPLETION_STATES = {"complete", "partial", "failed"}
SUBAGENT_OUTPUT_CONFIDENCE_VALUES = {"low", "medium", "high"}
SUBAGENT_OUTPUT_VALIDATION_STATUSES = {"validated", "unvalidated", "failed"}

# G3 caps — kept in sync with renmark.summary.MAX_SUMMARY_LINES /
# MAX_CHARS_PER_LINE and renmark.schemas.validate_subagent_output.
SUBAGENT_MAX_SUMMARY_LINES = 5
SUBAGENT_MAX_CHARS_PER_LINE = 1200


@dataclass(frozen=True)
class SubagentInput:
    """The ONLY fields a per-task subagent receives. Anything else is a leak.

    ``required_skills`` carries skill NAMES only. It is rendered as bounded
    metadata references (name + ``${CLAUDE_PLUGIN_ROOT}`` pointer + non-body
    metadata) — never a SKILL.md body. The subagent loads the body itself
    from the pointer; the packet stays metadata-only (dynamic skill loading).

    ``role`` is the resolved subagent role profile name (from
    ``renmark.subagent_profiles.PROFILES``). It defaults to ``"general-purpose"``
    so every existing construction remains valid. Specialized roles carry a
    narrow ``context_scope`` which drives packet shaping and future Agency Mode
    routing — general-purpose is the fallback only.
    """

    task_spec: str
    required_files: list[str] = field(default_factory=list)
    upstream_artifact_pointers: list[str] = field(default_factory=list)
    dependency_summaries: list[str] = field(default_factory=list)
    verifier_expectations: str = ""
    required_skills: list[str] = field(default_factory=list)
    role: str = "general-purpose"

    def to_dict(self) -> dict[str, Any]:
        # Function-local import mirrors the schemas import below, avoiding any
        # context ↔ dispatch import cycle.
        from renmark import context

        skill_refs: list[dict[str, object]] = []
        for n in self.required_skills:
            meta = context.skill_metadata(n)
            if meta is None:
                skill_refs.append({"name": n, "pointer": context.skill_pointer(n)})
            else:
                skill_refs.append(
                    {
                        "name": n,
                        "pointer": context.skill_pointer(n),
                        "metadata": meta,
                    }
                )
        return {
            "task_spec": self.task_spec,
            "required_files": list(self.required_files),
            "upstream_artifact_pointers": list(self.upstream_artifact_pointers),
            "dependency_summaries": list(self.dependency_summaries),
            "verifier_expectations": self.verifier_expectations,
            "required_skills": skill_refs,
            "role": self.role,
        }

    def to_json(self) -> str:
        return _json.dumps(self.to_dict(), indent=2)


@dataclass(frozen=True)
class SubagentOutput:
    """The ONLY fields a subagent may emit. Validated by dispatch_task_isolated."""

    status: Literal["PASS", "FAIL", "SKIP"]
    artifact_path: str
    touched_files: list[str] = field(default_factory=list)
    sha: str | None = None
    summary_lines: list[str] = field(default_factory=list)
    dependency_notes: str = ""
    token_count: int = 0
    completion_state: Literal["complete", "partial", "failed"] = "complete"
    confidence: Literal["low", "medium", "high"] = "medium"
    retry_count: int = 0
    # G9 transparency: pessimistic defaults — an output that doesn't declare
    # validation explicitly is treated as unvalidated, never as validated.
    validation_status: Literal["validated", "unvalidated", "failed"] = "unvalidated"
    parser_success: bool = True
    schema_compliance: bool = True

    def __post_init__(self) -> None:
        # G3 cap: ≤ 5 lines AND ≤ 1200 chars per line. Both checks live here so
        # parse_subagent_response cannot let a 5-line × 5000-char payload through.
        if len(self.summary_lines) > SUBAGENT_MAX_SUMMARY_LINES:
            raise IsolationViolation(
                f"SubagentOutput.summary_lines has {len(self.summary_lines)} entries; "
                f"max {SUBAGENT_MAX_SUMMARY_LINES} (G3)"
            )
        for i, line in enumerate(self.summary_lines):
            if not isinstance(line, str):
                raise IsolationViolation(f"SubagentOutput.summary_lines[{i}] is {type(line).__name__}; expected str")
            if len(line) > SUBAGENT_MAX_CHARS_PER_LINE:
                raise IsolationViolation(
                    f"SubagentOutput.summary_lines[{i}] is {len(line)} chars; max {SUBAGENT_MAX_CHARS_PER_LINE} (G3)"
                )
        if self.status not in SUBAGENT_OUTPUT_STATUS_VALUES:
            raise IsolationViolation(f"SubagentOutput.status={self.status!r} not in {SUBAGENT_OUTPUT_STATUS_VALUES}")
        if self.completion_state not in SUBAGENT_OUTPUT_COMPLETION_STATES:
            raise IsolationViolation(f"SubagentOutput.completion_state={self.completion_state!r} invalid")
        if self.confidence not in SUBAGENT_OUTPUT_CONFIDENCE_VALUES:
            raise IsolationViolation(f"SubagentOutput.confidence={self.confidence!r} invalid")
        if self.validation_status not in SUBAGENT_OUTPUT_VALIDATION_STATUSES:
            raise IsolationViolation(f"SubagentOutput.validation_status={self.validation_status!r} invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "artifact_path": self.artifact_path,
            "touched_files": list(self.touched_files),
            "sha": self.sha,
            "summary_lines": list(self.summary_lines),
            "dependency_notes": self.dependency_notes,
            "token_count": self.token_count,
            "completion_state": self.completion_state,
            "confidence": self.confidence,
            "retry_count": self.retry_count,
            "validation_status": self.validation_status,
            "parser_success": self.parser_success,
            "schema_compliance": self.schema_compliance,
        }


def parse_subagent_response(response: dict[str, Any] | str) -> SubagentOutput:
    """Parse a subagent's response into a SubagentOutput, refusing any
    payload that includes fields outside SUBAGENT_OUTPUT_FIELDS.

    Raises IsolationViolation on leakage (extra fields like 'transcript',
    'generated_code', 'diff', 'reasoning' etc.).
    """
    if isinstance(response, str):
        try:
            payload = _json.loads(response)
        except _json.JSONDecodeError as exc:
            raise IsolationViolation(f"subagent response is not valid JSON: {exc}") from exc
    else:
        payload = response

    if not isinstance(payload, dict):
        raise IsolationViolation(f"subagent response must be a JSON object; got {type(payload).__name__}")

    extra_fields = set(payload.keys()) - SUBAGENT_OUTPUT_FIELDS
    if extra_fields:
        raise IsolationViolation(
            f"subagent response includes forbidden fields {sorted(extra_fields)}. "
            "Only these fields are permitted: " + ", ".join(sorted(SUBAGENT_OUTPUT_FIELDS))
        )

    missing = {"status", "artifact_path"} - set(payload.keys())
    if missing:
        raise IsolationViolation(f"subagent response missing required fields: {sorted(missing)}")

    # Only pass through known fields (defensive — extra_fields check should
    # have caught everything, but guard against future refactors).
    filtered = {k: v for k, v in payload.items() if k in SUBAGENT_OUTPUT_FIELDS}
    # G9: a response that omits confidence is treated as low-confidence —
    # never silently promoted to the optimistic dataclass default.
    if "confidence" not in filtered:
        filtered["confidence"] = "low"

    # Structural validation AFTER the G11 leakage + required-field checks above
    # (those raise their own contract-pinned messages first). This catches
    # wrong-typed / out-of-enum fields the dataclass __post_init__ would only
    # partially cover. Function-local import avoids the schemas ↔ dispatch
    # circular import (schemas imports dispatch).
    from renmark import schemas

    issues = schemas.validate_subagent_output(filtered)
    if issues:
        raise IsolationViolation(f"invalid subagent output: {issues}")

    return SubagentOutput(**filtered)


def build_subagent_input(
    task: Task,
    *,
    dependency_summaries: list[str] | None = None,
    upstream_artifact_pointers: list[str] | None = None,
    required_skills: list[str] | None = None,
    role: str | None = None,
) -> SubagentInput:
    """Construct the bounded input for a single task's subagent.

    Pulls only the task spec + explicit file paths from the Task dataclass.
    No other Task fields cross the boundary. ``required_skills`` are skill
    NAMES; they are validated as metadata-only at build time (an inlined
    SKILL.md body is rejected) and rendered as pointers, never bodies.

    ``role`` names a profile from ``renmark.subagent_profiles.PROFILES``. When
    ``None`` (the common case), the role is resolved automatically from the task
    via ``subagent_profiles.resolve_profile``. Pass an explicit role only when
    the caller has already determined the correct profile. The resolved role is
    stored on the ``SubagentInput`` and does NOT otherwise change what crosses
    the boundary — the packet stays metadata-only; ``context.assert_metadata_only``
    is still enforced."""
    # Function-local import mirrors the schemas import in parse_subagent_response,
    # avoiding any context ↔ dispatch import cycle.
    from renmark import context

    context.assert_metadata_only(required_skills or [])

    if role is None:
        from renmark import subagent_profiles

        role = subagent_profiles.resolve_profile(task)

    return SubagentInput(
        task_spec=task.spec,
        required_files=[task.target, *list(task.context_files or [])],
        upstream_artifact_pointers=list(upstream_artifact_pointers or []),
        dependency_summaries=list(dependency_summaries or []),
        verifier_expectations=task.verifier or "",
        required_skills=list(required_skills or []),
        role=role,
    )


def build_workflow_fanout_args(
    wave: list[Task],
    *,
    dependency_summaries: list[str] | None = None,
    upstream_artifact_pointers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Shape the `args` payload for a `Workflow` tool fan-out over a wave.

    For each task in ``wave`` whose executor is a Claude-model executor
    (``claude_agent.is_claude_executor``), builds its bounded
    ``SubagentInput`` via ``build_subagent_input`` and appends its
    ``.to_dict()`` to the result, preserving wave order. Codex (and any
    other non-Claude executor) tasks are skipped — they never go through
    the Workflow/Agent path.

    This is pure packet-shaping: it does not call the `Workflow` tool
    itself (Python has no access to it) and does not alter the isolation
    contract — it only reuses ``build_subagent_input`` per task.
    """
    from renmark import subagent_profiles

    args: list[dict[str, Any]] = []
    for t in wave:
        if not claude_agent.is_claude_executor(t.executor):
            continue
        inp = build_subagent_input(
            t,
            dependency_summaries=dependency_summaries,
            upstream_artifact_pointers=upstream_artifact_pointers,
        )
        payload = inp.to_dict()
        # Pre-resolve agent_type so the Workflow script never needs to call back
        # into Python — it reads this field directly to pass agentType on agent().
        payload["agent_type"] = subagent_profiles.native_agent_type(inp.role)
        args.append(payload)
    return args


# ─────────────────────────────────────────────────────────────────────────────
# Host-native dispatch transport (Claude Code / Codex)
# ─────────────────────────────────────────────────────────────────────────────

HostName = Literal["claude", "codex"]
HostDispatchStrategy = Literal["none", "single", "fanout"]

# A task packet larger than this is not a bounded subagent prompt. Refuse it
# instead of truncating task intent or silently leaking more context.
MAX_HOST_DISPATCH_PROMPT_CHARS = 32_000


@dataclass(frozen=True)
class HostDispatchCall:
    """One host-tool invocation shaped from one or more G11 task packets."""

    task_indices: tuple[int, ...]
    tool: str
    arguments: dict[str, Any]
    model_route: dict[str, str] | None = None


@dataclass(frozen=True)
class HostDispatchPlan:
    """Pure transport plan; no host tool has been invoked.

    ``task_packets`` is host-independent and therefore is the semantic parity
    surface.  ``calls`` adapts those packets to the selected host. Ledgering,
    wave-summary persistence, response parsing, and verifier execution remain
    downstream and identical for both hosts.
    """

    host: HostName
    strategy: HostDispatchStrategy
    task_packets: tuple[dict[str, Any], ...]
    calls: tuple[HostDispatchCall, ...]
    wait_tool: str | None = None
    followup_tool: str | None = None


def render_bounded_subagent_prompt(
    inp: SubagentInput,
    *,
    reasoning_instruction: str = "",
) -> str:
    """Render the canonical task packet + output contract for either host.

    Only :class:`SubagentInput` fields cross the boundary. The response schema
    is the same :class:`SubagentOutput` schema consumed by
    :func:`parse_subagent_response`; code, diffs, transcripts, and reasoning
    remain forbidden.
    """

    packet = inp.to_dict()
    prompt = (
        "Complete one isolated renmark task using only the bounded packet below.\n"
        "Do not use or request orchestrator conversation history. Do not commit.\n\n"
        "SUBAGENT_INPUT_JSON\n"
        f"{_json.dumps(packet, indent=2, sort_keys=True)}\n"
        "END_SUBAGENT_INPUT_JSON\n\n"
        "Return ONLY valid JSON matching SubagentOutput: status (PASS|FAIL|SKIP), "
        "artifact_path, touched_files, sha, summary_lines (at most 5), "
        "dependency_notes, token_count, completion_state "
        "(complete|partial|failed), confidence (low|medium|high), retry_count, "
        "validation_status (validated|unvalidated|failed), parser_success, and "
        "schema_compliance. Generated code belongs in the target/artifact, never "
        "in the response. Never return transcript, diff, generated_code, or reasoning."
    )
    if reasoning_instruction.strip():
        prompt += f"\n\nCANONICAL_REASONING_INSTRUCTION\n{reasoning_instruction.strip()}"
    if len(prompt) > MAX_HOST_DISPATCH_PROMPT_CHARS:
        raise IsolationViolation(
            f"host dispatch prompt is {len(prompt)} chars; max "
            f"{MAX_HOST_DISPATCH_PROMPT_CHARS} (bounded-input contract)"
        )
    return prompt


def build_host_dispatch_plan(
    wave: list[Task],
    *,
    host: HostName | str,
    dependency_summaries: list[str] | None = None,
    upstream_artifact_pointers: list[str] | None = None,
    reasoning_instruction: str = "",
) -> HostDispatchPlan:
    """Map host-agent tasks in ``wave`` to a host-native transport contract.

    Claude uses one ``Agent`` call for a single task and one ``Workflow`` call
    for a fan-out. Codex uses one ``spawn_agent`` call per independent task,
    followed by ``wait_agent``; a bounded correction may use
    ``followup_task``. Codex spawns always use ``fork_turns='none'``.

    ``executor: codex`` tasks are intentionally excluded: they remain on the
    deterministic ``renmark-execute`` subprocess path on both hosts. This
    function performs no dispatch and no ledger/state writes.
    """

    normalized = str(host).strip().lower()
    if normalized not in {"claude", "codex"}:
        raise ValueError(f"unsupported host {host!r}; expected 'claude' or 'codex'")
    host_name = cast(HostName, normalized)

    host_tasks = [task for task in wave if claude_agent.is_claude_executor(task.executor)]
    inputs = [
        build_subagent_input(
            task,
            dependency_summaries=dependency_summaries,
            upstream_artifact_pointers=upstream_artifact_pointers,
        )
        for task in host_tasks
    ]
    packets = tuple(inp.to_dict() for inp in inputs)
    if not host_tasks:
        return HostDispatchPlan(host=host_name, strategy="none", task_packets=packets, calls=())

    strategy: HostDispatchStrategy = "single" if len(host_tasks) == 1 else "fanout"
    if host_name == "claude":
        calls = _build_claude_host_calls(
            host_tasks,
            inputs,
            reasoning_instruction=reasoning_instruction,
        )
        return HostDispatchPlan(
            host=host_name,
            strategy=strategy,
            task_packets=packets,
            calls=calls,
        )

    calls = _build_codex_host_calls(
        host_tasks,
        inputs,
        reasoning_instruction=reasoning_instruction,
    )
    return HostDispatchPlan(
        host=host_name,
        strategy=strategy,
        task_packets=packets,
        calls=calls,
        wait_tool="wait_agent",
        followup_tool="followup_task",
    )


def _build_claude_host_calls(
    tasks: list[Task],
    inputs: list[SubagentInput],
    *,
    reasoning_instruction: str,
) -> tuple[HostDispatchCall, ...]:
    from renmark import subagent_profiles

    if len(tasks) > 1:
        args: list[dict[str, Any]] = []
        for inp in inputs:
            payload = inp.to_dict()
            payload["agent_type"] = subagent_profiles.native_agent_type(inp.role)
            args.append(payload)
        return (
            HostDispatchCall(
                task_indices=tuple(task.index for task in tasks),
                tool="Workflow",
                arguments={"args": args},
            ),
        )

    task = tasks[0]
    inp = inputs[0]
    arguments: dict[str, Any] = {
        "description": f"renmark task {task.index}: {task.title[:60]}",
        "prompt": render_bounded_subagent_prompt(
            inp,
            reasoning_instruction=reasoning_instruction,
        ),
    }
    agent_type = subagent_profiles.native_agent_type(inp.role)
    if agent_type is not None:
        arguments["subagent_type"] = agent_type
    if task.executor == "fable":
        arguments["model"] = "fable"
    return (
        HostDispatchCall(
            task_indices=(task.index,),
            tool="Agent",
            arguments=arguments,
        ),
    )


def _build_codex_host_calls(
    tasks: list[Task],
    inputs: list[SubagentInput],
    *,
    reasoning_instruction: str,
) -> tuple[HostDispatchCall, ...]:
    from renmark import codex_routing

    calls: list[HostDispatchCall] = []
    for task, inp in zip(tasks, inputs, strict=True):
        native = codex_routing.build_native_dispatch(
            task,
            role=inp.role,
            prompt=render_bounded_subagent_prompt(
                inp,
                reasoning_instruction=reasoning_instruction,
            ),
        )
        calls.append(
            HostDispatchCall(
                task_indices=(task.index,),
                tool=native.spawn_tool,
                arguments=dict(native.spawn_args),
                model_route={
                    "model": native.route.model,
                    "reasoning_effort": native.route.reasoning_effort,
                    "tier": native.route.tier,
                    "reason": native.route.reason,
                },
            )
        )
    return tuple(calls)


def dispatch_task_isolated(
    task: Task,
    *,
    dependency_summaries: list[str] | None = None,
    upstream_artifact_pointers: list[str] | None = None,
    subagent_runner: Callable[[SubagentInput], dict[str, Any] | str],
) -> SubagentOutput:
    """Run one task in an isolated subagent context with strict I/O bounds.

    ``subagent_runner`` is a callable that takes a SubagentInput and returns
    a dict[str, Any] or JSON string representing the subagent's response. This is the
    injection point for the actual executor (codex subprocess, Agent tool
    call, or a test mock). Whatever it returns is then validated through
    parse_subagent_response — extra fields raise IsolationViolation.
    """
    inp = build_subagent_input(
        task,
        dependency_summaries=dependency_summaries,
        upstream_artifact_pointers=upstream_artifact_pointers,
    )
    response = subagent_runner(inp)
    return parse_subagent_response(response)


# ─────────────────────────────────────────────────────────────────────────────
# R-0.2/WP-5e — Inspector finding -> repair work order (ADR-046)
# ─────────────────────────────────────────────────────────────────────────────
#
# Per .renmark/plans/r-0.2/inspector-repair-separation-design.md §4 (Decision
# §2, ADR-046 in .renmark/memory/decisions.md): any Inspector finding with a
# FAIL verdict or severity >= Major must produce a SEPARATE, logged repair
# work order — never an in-context fix by the Inspector itself. This section
# answers the design doc's open question #1 (repair work order schema) and
# implements the pure data-transformation function only: Inspector finding
# in, repair work order out. Wiring this into codereview/verify skill prose
# and actual Governor routing/dispatch is explicitly deferred (design doc
# §7.4 lists "Full repair orchestration implementation" as WP-5+ follow-up);
# do not read this as sanctioning a change to plugin/skills/**.
#
# Schema decision (open question #1): a NEW `RepairWorkOrder` dataclass, not
# a reused `Task`. `Task` is shaped for the plan-authoring/wave-dispatch
# lifecycle (index, mode, model, parallel_group, verifier_timeout_s,
# serves/PRD traceability) — none of which apply to a repair born from an
# inspection finding. A repair work order instead needs an explicit
# back-pointer to its source finding (file + id, never the full finding body
# — G3/G11 bounded-summary/pointer discipline) plus severity and
# acceptance_criteria fields Task has no equivalent for. Reusing Task would
# force either abusing unrelated fields (e.g. stuffing the source-finding
# pointer into `spec` text) or leaving provenance implicit. `scope` reuses
# `fast_path.WorkerScope` UNCHANGED (per design doc §9, "Reused" — WP-5a's
# `AgentDispatch.scope` field is the same type), so once a repair work order
# is actually routed to a Worker it plugs straight into WP-1/WP-5a's existing
# scope-enforcement machinery without inventing a parallel shape.

_SEVERITY_RANK = {"info": 0, "minor": 1, "major": 2, "critical": 3}
REPAIR_SEVERITY_THRESHOLD = "major"


@dataclass(frozen=True)
class InspectorFinding:
    """One Inspector-role finding, bounded to what a repair work order needs.

    ``source_file`` + ``finding_id`` are the pointer back to the full
    inspection report (e.g. a ``.renmark/reviews/*.review.md`` or ``.json``
    artifact) — the finding's full body never crosses into the repair work
    order (context-hygiene: pointer, not content).
    """

    finding_id: str
    source_file: str
    verdict: Literal["PASS", "FAIL"]
    severity: Literal["info", "minor", "major", "critical"]
    target: str
    title: str = ""


@dataclass(frozen=True)
class RepairWorkOrder:
    """A repair work order routed through the Governor to a Worker role.

    Fields per design doc §4.1: ``work_order_id``, ``source_inspection_id``
    (pointer, not content), ``severity``, ``scope``, ``description``,
    ``acceptance_criteria``. Construction is restricted to major/critical
    severity — ``build_repair_work_order`` is the only sanctioned factory.
    """

    work_order_id: str
    source_inspection_id: str  # "<source_file>#<finding_id>"
    severity: Literal["major", "critical"]
    scope: fast_path.WorkerScope
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.severity not in ("major", "critical"):
            raise ValueError(
                f"RepairWorkOrder.severity={self.severity!r} must be 'major' or "
                "'critical' — repair work orders are only emitted for "
                "FAIL/severity>=Major findings (ADR-046)"
            )
        if not self.acceptance_criteria:
            raise ValueError(
                "RepairWorkOrder.acceptance_criteria must be non-empty — "
                "design doc §4.1 requires 'how to verify the repair succeeded'"
            )


def build_repair_work_order(
    finding: InspectorFinding,
    *,
    work_order_id: str,
    description: str = "",
    acceptance_criteria: list[str] | None = None,
) -> RepairWorkOrder | None:
    """Pure data transform: Inspector finding -> RepairWorkOrder, or None.

    Returns ``None`` when ``finding`` does NOT meet ADR-046's trigger
    (verdict != "FAIL" AND severity < "major") — a PASS/low-severity finding
    must never produce a repair work order. This function performs no I/O,
    no dispatch, and no Governor/ledger interaction; it only shapes data.
    Wiring the returned work order into an actual dispatch is a separate,
    larger integration left for later per the design doc.
    """
    severity_rank = _SEVERITY_RANK.get(finding.severity, 0)
    triggers = finding.verdict == "FAIL" or severity_rank >= _SEVERITY_RANK[REPAIR_SEVERITY_THRESHOLD]
    if not triggers:
        return None

    effective_severity = finding.severity if severity_rank >= _SEVERITY_RANK[REPAIR_SEVERITY_THRESHOLD] else "major"

    scope = fast_path.WorkerScope(allowed_paths=frozenset({finding.target}))
    return RepairWorkOrder(
        work_order_id=work_order_id,
        source_inspection_id=f"{finding.source_file}#{finding.finding_id}",
        severity=cast(Literal["major", "critical"], effective_severity),
        scope=scope,
        description=description or f"Repair: {finding.title or finding.finding_id}",
        acceptance_criteria=list(
            acceptance_criteria or [f"Re-run Inspector check for {finding.finding_id}; verdict must be PASS"]
        ),
    )
