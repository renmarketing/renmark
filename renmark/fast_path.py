"""R-0.1 Bounded Small-Task Fast Path — classification + scope enforcement.

Implements the two design docs this module is built from, and nothing they
didn't already specify:

- ``.bootstrap-renmark/milestones/R-0.1/classification-design.md`` (WP-1):
  :func:`classify_fast_path` — a pure, deterministic, no-model-call function
  answering "does this candidate change qualify for the fast path."
- ``.bootstrap-renmark/milestones/R-0.1/scope-enforcement-design.md`` (WP-2):
  :class:`WorkerScope` + :func:`verify_worker_scope` — Layer B, the
  deterministic post-execution check comparing a Worker's DECLARED scope
  against its ACTUAL git diff, never against self-reported ``touched_files``
  (``renmark.dispatch.SubagentOutput.touched_files``). Layer A (the host's
  live permission prompt) is not — and cannot be — implemented here; see the
  design doc §2 for why.

Both functions are pure and side-effect-free except ``verify_worker_scope``'s
single read-only ``git diff`` subprocess call, mirroring the never-raises,
degrade-to-conservative style already used by ``renmark.subagent_gate`` and
``renmark.release._git_stdout``.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from renmark.parser import Task

# ── WP-1: fast-path classification ───────────────────────────────────────────

MAX_FAST_PATH_FILES = 2
_CHAIN_OPERATORS = ("&&", "||", ";", "|")


@dataclass(frozen=True)
class ClassificationVerdict:
    """Result of the 5-signal fast-path eligibility check.

    ``eligible`` is the routing decision. ``failed_signals`` names every
    signal that failed (not just the first) so the ledger/audit record is a
    complete, one-line-per-decision justification, per classification-
    design.md §4 ("a one-line justification (which signal(s), if any,
    failed) for the ledger").
    """

    eligible: bool
    failed_signals: tuple[str, ...] = field(default_factory=tuple)

    def reason(self) -> str:
        if self.eligible:
            return "all 5 signals passed"
        return "failed: " + ", ".join(self.failed_signals)


def classify_fast_path(tasks: Iterable[Task]) -> ClassificationVerdict:
    """Classify a candidate wave of tasks against the 5 fast-path signals.

    Per classification-design.md §2 — ALL signals must pass for eligibility.
    An empty ``tasks`` is not eligible (nothing to fast-path).
    """
    tasks = list(tasks)
    failed: list[str] = []

    if not tasks:
        return ClassificationVerdict(eligible=False, failed_signals=("empty_task_set",))

    # Signal 1: declared scope size — at most MAX_FAST_PATH_FILES distinct,
    # explicitly-named targets (no glob/directory wildcards).
    targets = {t.target for t in tasks}
    if len(targets) > MAX_FAST_PATH_FILES or any(
        "*" in t or "?" in t or t.endswith("/") for t in targets
    ):
        failed.append("scope_size")

    # Signal 2: action type — add/modify only. The Task model itself can only
    # express mode "A" (create) or "B" (modify) — delete/rename cannot be
    # planned as a Task at all, so this signal is structural, not a runtime
    # check (a rogue delete, per R-0.0's Scenario C, is caught by
    # verify_worker_scope instead, not here).
    if any(t.mode not in ("A", "B") for t in tasks):
        failed.append("action_type")

    # Signal 3: no renmark/** or plugin/** target.
    if any(t.target.startswith(("renmark/", "plugin/")) for t in tasks):
        failed.append("production_target")

    # Signal 4: no cross-file dependency — a task's context_files must not
    # overlap this wave's target set. Same invariant as
    # renmark.dispatch.validate_wave's "context_files" check, evaluated here
    # as a verdict rather than a raise (validate_wave is not reused directly
    # because it raises on the FIRST violation; classification wants the
    # full failed-signal list).
    if any(set(t.context_files) & targets for t in tasks):
        failed.append("cross_file_dependency")

    # Signal 5: verifier is a single deterministic command, not a multi-stage
    # chain (no shell chaining operators).
    if any(
        not t.verifier.strip() or any(op in t.verifier for op in _CHAIN_OPERATORS)
        for t in tasks
    ):
        failed.append("verifier_not_single_command")

    return ClassificationVerdict(eligible=not failed, failed_signals=tuple(failed))


# ── WP-2: Worker scope enforcement (Layer B) ─────────────────────────────────


@dataclass(frozen=True)
class WorkerScope:
    """A fast-path Worker's declared scope, per scope-enforcement-design.md §3.

    Populated exactly once at dispatch time from a passing
    :class:`ClassificationVerdict`'s task set — never renegotiated mid-task.
    """

    allowed_paths: frozenset[str]
    allowed_actions: frozenset[str] = frozenset({"A", "M"})  # git status codes: Added, Modified


@dataclass(frozen=True)
class ScopeViolation:
    status_code: str
    path: str
    kind: str  # "out_of_scope" | "disallowed_action"


@dataclass(frozen=True)
class ScopeVerdict:
    passed: bool
    violations: tuple[ScopeViolation, ...] = field(default_factory=tuple)


def worker_scope_from_verdict(verdict: ClassificationVerdict, tasks: Iterable[Task]) -> WorkerScope:
    """Build the declared scope for a dispatch that passed classification."""
    if not verdict.eligible:
        raise ValueError("cannot build a WorkerScope from a non-eligible ClassificationVerdict")
    return WorkerScope(allowed_paths=frozenset(t.target for t in tasks))


def _git_diff_name_status(repo: Path, base_sha: str) -> list[tuple[str, str]] | None:
    """Return [(status_code, path), ...] for ``base_sha..HEAD``, or None on
    any git/subprocess failure (never raises — mirrors
    ``renmark.release._git_stdout``'s degrade-to-None style)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-status", f"{base_sha}..HEAD"],
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    pairs: list[tuple[str, str]] = []
    for line in proc.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        # Rename lines are "R100\told\tnew" — normalize the status to "R".
        status = parts[0][0]
        path = parts[-1]
        pairs.append((status, path))
    return pairs


def verify_worker_scope(scope: WorkerScope, repo: Path, base_sha: str) -> ScopeVerdict:
    """Layer B: compare ``scope`` against the REAL git diff, never against a
    Worker's self-reported ``touched_files``.

    Per scope-enforcement-design.md §4: any path outside ``allowed_paths`` is
    a violation regardless of action; a delete ("D") or rename ("R") is
    always a violation on the fast path, regardless of whether the path is
    in ``allowed_paths``.

    A git failure (unreadable repo, bad base_sha) degrades to a FAILING
    verdict, not a silent pass — an unverifiable scope must never be treated
    as a clean one.
    """
    pairs = _git_diff_name_status(repo, base_sha)
    if pairs is None:
        return ScopeVerdict(
            passed=False,
            violations=(ScopeViolation(status_code="?", path="<unverifiable>", kind="diff_unavailable"),),
        )

    violations: list[ScopeViolation] = []
    for status_code, path in pairs:
        if status_code in ("D", "R"):
            violations.append(ScopeViolation(status_code=status_code, path=path, kind="disallowed_action"))
            continue
        if path not in scope.allowed_paths:
            violations.append(ScopeViolation(status_code=status_code, path=path, kind="out_of_scope"))

    return ScopeVerdict(passed=not violations, violations=tuple(violations))
