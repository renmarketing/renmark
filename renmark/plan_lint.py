"""Deterministic plan-validation engine shared by /renmark:check-plan and
/renmark:orchestrate pre-flight.

This module is the SINGLE authoritative implementation of the 8 checks that
``plugin/skills/check-plan/SKILL.md`` defines.  Both surfaces — the
``/renmark:check-plan`` skill and the orchestrate pre-flight gate — MUST run
``python -m renmark.plan_lint <plan.md>`` so they can never produce different
verdicts.  No LLM reasoning is used; every check is deterministic Python.

Public API
----------
``lint_plan(path) -> PlanLintReport``
    Run all checks against *path* and return a structured report.  Never
    raises — a ``PlanError`` from the parser is converted to a single BLOCK
    issue so callers always receive a valid report.

``PlanLintReport``
    Dataclass: ``verdict`` (PASS | WARN | BLOCK), ``issues`` (list[str]),
    ``task_count`` (int), ``executor_counts`` (dict[str, int]).

CLI
---
``python -m renmark.plan_lint <plan.md>``
    Prints the check-plan report format and exits 0 (PASS/WARN) or 1 (BLOCK).

Check severities (behaviour-preserving — mirrors the SKILL's definitions):
  BLOCK: 1 task-count >15, 2 missing/empty verifier, 3 duplicate target in
         parallel_group, 4 heavy-read G5 (>200-line context file with
         sonnet/opus executor), 5 transcript-leak G11 (denylist phrase in
         spec), 6 dependency-hygiene G11 (full-output reference without
         artifact path), 9 fable-undeclared REQ-2 (executor fable without
         a declared `top_tier: fable`), 10 fable-mechanical REQ-2 (executor
         fable on a simple/mechanical task).
  WARN:  2b test -f only verifier, 7 unbounded verifier output, 8 spec
         length >80 lines, 11 general-purpose without role_reason, and sanity
         extras (negative/absurd est_ fields).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from renmark.parser import PlanError, Task, parse_plan

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Verdict = str  # "PASS" | "WARN" | "BLOCK"


@dataclass
class PlanLintReport:
    """Result of running lint_plan()."""

    verdict: Verdict  # "PASS" | "WARN" | "BLOCK"
    issues: list[str] = field(default_factory=list)
    task_count: int = 0
    executor_counts: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_TASK_COUNT = 15
_MAX_SPEC_LINES = 80
_HEAVY_READ_LINE_THRESHOLD = 200
_MAX_EST_TOKENS = 200_000
_MAX_EST_COST_USD = 50.0

# Executors that BLOCK on heavy-read (G5); codex/haiku are exempt.
_HEAVY_READ_BLOCK_EXECUTORS = frozenset({"sonnet", "opus", "fable"})

# Transcript-leak denylist — verbatim from check-plan SKILL.md §2.5.
_TRANSCRIPT_LEAK_PHRASES = (
    "show me the code",
    "paste the diff",
    "return the contents",
    "include the full",
    "print the file",
    "explain the change in your response",
    "output the code",
)

# Dependency-hygiene heuristic patterns (G11).
_DEP_FULL_OUTPUT_RE = re.compile(
    r"depends\s+on\s+the\s+output\s+of\s+task\s+\d+|"
    r"uses\s+what\s+task\s+\d+\s+produced",
    re.IGNORECASE,
)

# Verifier-output-bound patterns (G3) — WARN triggers.
# We check for the presence of these tokens WITHOUT a downstream cap keyword.
# Shapes per check-plan SKILL §2.5 (refined at v0.10.0 codereview): `find`
# only without -name; `git log` accepts -n N / -nN / -N / --max-count as caps;
# node/python verifiers that print arbitrary computed output WARN unless
# capped — `py_compile` is the SKILL's sanctioned bounded form and is exempt.
_UNBOUNDED_VERIFIER_TOKENS = re.compile(
    r"\bcat\b"
    r"|\bfind\b(?!.*\s-name\b)"
    r"|git\s+diff(?!\s+--stat)(?!\s+\S+\s+\S+)"
    r"|git\s+log(?!\s+(?:-n\s*\d|-\d|--max-count))"
    r"|\b(?:node|python3?)\b(?!.*py_compile)"
)
_BOUND_CAPS = re.compile(r"\|\s*(head|tail|grep|wc|awk\s+['\"]NR|tee)\b|>\s*/dev/null")

# test -f only: matches verifier that is purely "test -f <path>" (possibly with
# an alias like "[ -f ... ]") with nothing else meaningful after.
_TEST_F_ONLY_RE = re.compile(r"^\s*(?:test\s+-[fF]\s+\S+|\[\s+-[fF]\s+\S+\s*\])\s*$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _count_lines(path_str: str, repo_root: Path) -> int | None:
    """Return the on-disk line count of *path_str* relative to *repo_root*.

    Returns None if the file cannot be read (not found, binary, etc.).
    """
    p = repo_root / path_str
    if not p.is_file():
        return None
    try:
        return len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return None


def _check_task_count(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 1 — task count ≤ 15."""
    if len(tasks) > _MAX_TASK_COUNT:
        return [
            (
                "BLOCK",
                f"Task count is {len(tasks)} (limit {_MAX_TASK_COUNT}). "
                "Split into part1/part2 plan files before orchestrate will accept this.",
            )
        ]
    return []


def _check_verifiers(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 2 — every task has a non-empty verifier (BLOCK); test -f only → WARN."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        v = (t.verifier or "").strip()
        if not v:
            issues.append(("BLOCK", f"Task {t.index}: verifier is missing or empty."))
        elif _TEST_F_ONLY_RE.match(v):
            issues.append(
                (
                    "WARN",
                    f"Task {t.index}: verifier proves file existence only (`{v}`). Consider adding a behavioral check.",
                )
            )
    return issues


def _check_parallel_group_targets(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 3 — no two tasks in the same parallel_group share a target."""
    issues: list[tuple[str, str]] = []
    groups: dict[int, dict[str, int]] = {}  # group → {target: first_task_index}
    for t in tasks:
        pg = t.parallel_group
        if pg is None:
            continue
        if pg not in groups:
            groups[pg] = {}
        if t.target in groups[pg]:
            first = groups[pg][t.target]
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: parallel_group {pg} already has task {first} "
                    f"targeting `{t.target}`. Parallel tasks must not share a target.",
                )
            )
        else:
            groups[pg][t.target] = t.index
    return issues


def _check_heavy_read(tasks: list[Task], repo_root: Path) -> list[tuple[str, str]]:
    """Check 4 — heavy-read G5: context file >200 lines with sonnet/opus → BLOCK."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if t.executor not in _HEAVY_READ_BLOCK_EXECUTORS:
            continue
        for cf in t.context_files:
            lc = _count_lines(cf, repo_root)
            if lc is not None and lc > _HEAVY_READ_LINE_THRESHOLD:
                issues.append(
                    (
                        "BLOCK",
                        f"Task {t.index}: reads `{cf}` ({lc} lines) with "
                        f"executor `{t.executor}`. Heavy reads belong in codex or haiku "
                        "(G5 / executor-dispatch-rule). Reassign the task to "
                        "`executor: codex`, or split the read into a codex pre-task "
                        "that produces a summary artifact.",
                    )
                )
    return issues


def _check_transcript_leak(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 5 — transcript-leak G11: denylist phrases in spec → BLOCK."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        spec_lower = t.spec.lower()
        for phrase in _TRANSCRIPT_LEAK_PHRASES:
            if phrase in spec_lower:
                issues.append(
                    (
                        "BLOCK",
                        f"Task {t.index}: spec contains the phrase `{phrase}`. "
                        "This implies the subagent will paste generated content into "
                        "its response, violating G11 task isolation. The artifact "
                        "lives in the file at the task's target; the orchestrator "
                        "reads only summary fields. Rewrite the spec to ask for "
                        "behaviour, not output.",
                    )
                )
    return issues


def _check_dependency_hygiene(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 6 — dependency-hygiene G11: full-output reference without artifact path."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if _DEP_FULL_OUTPUT_RE.search(t.spec):
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: spec references the full output of a prior task "
                    "without naming an artifact path or interface. Downstream tasks must "
                    "reference only `dependency_notes` from the prior wave's "
                    "`.renmark/state/wave-summaries/wave-X.json`, not what a prior task "
                    "did. Rewrite the spec to name the specific interface (function name, "
                    "file path, exported symbol) it depends on.",
                )
            )
    return issues


def _check_verifier_output_bound(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 7 — verifier-output-bound G3: unbounded stdout → WARN."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        v = (t.verifier or "").strip()
        if not v:
            continue  # already caught by check 2
        if _UNBOUNDED_VERIFIER_TOKENS.search(v) and not _BOUND_CAPS.search(v):
            issues.append(
                (
                    "WARN",
                    f"Task {t.index}: verifier may emit unbounded stdout (`{v}`). "
                    "Pipe through `head`, `tail`, or `grep` so verifiers answer "
                    "pass/fail in ≤ 3 lines of stdout.",
                )
            )
    return issues


def _check_spec_length(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 8 — spec length > 80 lines → WARN."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        n = len(t.spec.splitlines())
        if n > _MAX_SPEC_LINES:
            issues.append(
                (
                    "WARN",
                    f"Task {t.index}: spec is {n} lines (limit {_MAX_SPEC_LINES}). "
                    "Long specs hide multiple implicit tasks. Consider splitting into "
                    "2 atomic tasks, or extracting context into a sibling `.md` file "
                    "(`scope-contract.md` pattern).",
                )
            )
    return issues


def _check_fable_declared(tasks: list[Task], repo_root: Path) -> list[tuple[str, str]]:
    """Check 9 — fable-undeclared REQ-2: executor fable without `top_tier: fable` → BLOCK."""
    from . import capabilities

    issues: list[tuple[str, str]] = []
    fable_tasks = [t for t in tasks if t.executor == "fable"]
    if not fable_tasks:
        return issues
    if capabilities.top_tier(repo_root) != "fable":
        for t in fable_tasks:
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: executor `fable` but this project has not "
                    "declared `top_tier: fable`. Declare it in "
                    ".renmark/memory/routing.md (## Model tiers) or reassign to `opus`.",
                )
            )
    return issues


def _check_fable_mechanical(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 10 — fable-mechanical REQ-2: executor fable on a simple task → BLOCK."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if t.executor == "fable" and t.complexity == "simple":
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: executor `fable` on a simple/mechanical task — "
                    "REQ-2 prohibits fable for mechanical or bulk work regardless of "
                    "declaration. Route to haiku/codex.",
                )
            )
    return issues


def _check_role_profiles(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 11 — explicit roles must be registered; fallback needs a reason."""
    from . import subagent_profiles

    issues: list[tuple[str, str]] = []
    for task in tasks:
        role = (task.role or "").strip()
        if not role:
            continue
        if role not in subagent_profiles.PROFILES:
            issues.append(("BLOCK", f"Task {task.index}: unknown subagent role `{role}`."))
        elif role == "general-purpose" and not task.role_reason.strip():
            issues.append(
                (
                    "WARN",
                    f"Task {task.index}: general-purpose requires a role_reason explaining why no specialist fits.",
                )
            )
    return issues


def _check_sanity_extras(tasks: list[Task]) -> list[tuple[str, str]]:
    """Sanity extras — all WARN only, never BLOCK (behaviour-preserving)."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if t.est_tokens is not None:
            if t.est_tokens < 0:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_tokens is negative ({t.est_tokens}). Check planner estimate.",
                    )
                )
            elif t.est_tokens > _MAX_EST_TOKENS:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_tokens is {t.est_tokens} "
                        f"(> {_MAX_EST_TOKENS:,}). Consider splitting the task.",
                    )
                )
        if t.est_cost_usd is not None:
            if t.est_cost_usd < 0:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_cost_usd is negative ({t.est_cost_usd}). Check planner estimate.",
                    )
                )
            elif t.est_cost_usd > _MAX_EST_COST_USD:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_cost_usd is ${t.est_cost_usd:.2f} "
                        f"(> ${_MAX_EST_COST_USD:.2f}). Consider splitting the task.",
                    )
                )
    return issues


def _derive_verdict(raw_issues: list[tuple[str, str]]) -> Verdict:
    """Derive overall verdict from (severity, message) pairs."""
    severities = {sev for sev, _ in raw_issues}
    if "BLOCK" in severities:
        return "BLOCK"
    if "WARN" in severities:
        return "WARN"
    return "PASS"


def _build_executor_counts(tasks: list[Task]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t.executor] = counts.get(t.executor, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint_plan(path: str | Path) -> PlanLintReport:
    """Run all plan checks and return a ``PlanLintReport``.

    Never raises.  A ``PlanError`` from the parser surfaces as a single BLOCK
    issue so the caller always receives a valid report even for empty/corrupt
    plan files.
    """
    repo_root = Path.cwd()

    # Parse — any PlanError → one graceful BLOCK issue.
    try:
        tasks = parse_plan(path)
    except PlanError as exc:
        return PlanLintReport(
            verdict="BLOCK",
            issues=[f"BLOCK: plan parse error — {exc}"],
            task_count=0,
            executor_counts={},
        )
    except Exception as exc:
        return PlanLintReport(
            verdict="BLOCK",
            issues=[f"BLOCK: unexpected error reading plan — {exc}"],
            task_count=0,
            executor_counts={},
        )

    # Run all checks and collect (severity, message) pairs.
    raw: list[tuple[str, str]] = []
    raw.extend(_check_task_count(tasks))
    raw.extend(_check_verifiers(tasks))
    raw.extend(_check_parallel_group_targets(tasks))
    raw.extend(_check_heavy_read(tasks, repo_root))
    raw.extend(_check_transcript_leak(tasks))
    raw.extend(_check_dependency_hygiene(tasks))
    raw.extend(_check_verifier_output_bound(tasks))
    raw.extend(_check_spec_length(tasks))
    raw.extend(_check_fable_declared(tasks, repo_root))
    raw.extend(_check_fable_mechanical(tasks))
    raw.extend(_check_role_profiles(tasks))
    raw.extend(_check_sanity_extras(tasks))

    verdict = _derive_verdict(raw)
    # Format issues as "BLOCK: ..." / "WARN: ..." strings for the report.
    issues = [f"{sev}: {msg}" for sev, msg in raw]
    return PlanLintReport(
        verdict=verdict,
        issues=issues,
        task_count=len(tasks),
        executor_counts=_build_executor_counts(tasks),
    )


# ---------------------------------------------------------------------------
# CLI  (python -m renmark.plan_lint <plan.md>)
# ---------------------------------------------------------------------------


def _fmt_executor_counts(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    parts = []
    for name in sorted(counts):
        parts.append(f"{name}×{counts[name]}")
    return "  Executors: " + "  ".join(parts)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Exit 0 = PASS or WARN; 1 = BLOCK."""
    argv = sys.argv[1:] if argv is None else list(argv)

    if not argv or argv[0] in ("-h", "--help"):
        sys.stdout.write("usage: python -m renmark.plan_lint <plan.md>\n")
        return 0

    plan_path = argv[0]
    report = lint_plan(plan_path)

    # --- Header ---
    plan_name = Path(plan_path).name
    sys.stdout.write(f"check-plan: {plan_name}\n")
    sys.stdout.write(f"Tasks: {report.task_count}{_fmt_executor_counts(report.executor_counts)}\n")
    sys.stdout.write("\n")

    blocks = [msg for msg in report.issues if msg.startswith("BLOCK:")]
    warns = [msg for msg in report.issues if msg.startswith("WARN:")]

    if blocks:
        sys.stdout.write("BLOCK (must fix before running):\n")
        for b in blocks:
            # Strip the "BLOCK: " prefix so format matches SKILL's spec.
            sys.stdout.write(f"- {b[len('BLOCK: ') :]}\n")
        sys.stdout.write("\n")

    if warns:
        sys.stdout.write("WARN (review before running):\n")
        for w in warns:
            sys.stdout.write(f"- {w[len('WARN: ') :]}\n")
        sys.stdout.write("\n")

    if report.verdict in ("PASS", "WARN"):
        sys.stdout.write("PASS: structural constraints met\n")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
