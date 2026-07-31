"""Plan file parser for renmark-execute.

Parses markdown plan files of the form:

    ### Task N: <title>
    - **mode:** A | B
    - **target:** path/to/file
    - **context_files:** []
    - **model:** optional
    - **verifier:** shell command
    - **verifier_timeout_s:** 60
    - **spec:**
      free prose
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from renmark.delivery_state import stable_milestone_id, stable_work_package_id


class PlanError(ValueError):
    """Raised when a plan file is malformed."""


@dataclass
class Task:
    index: int  # 1-based as written in the plan
    title: str
    mode: str  # "A" or "B"
    target: str
    context_files: list[str] = field(default_factory=list)
    model: str | None = None
    verifier: str = ""
    verifier_timeout_s: int = 60
    spec: str = ""
    executor: str = "codex"  # "haiku" | "codex" | "sonnet" | "opus" | <litellm-string>
    # Phase 1 fields (v0.0.3+):
    complexity: str = "medium"  # "simple" | "medium" | "hard"
    parallel_group: int | None = (
        None  # tasks sharing a group run concurrently; default None = serial (each in its own group = index)
    )
    est_tokens: int | None = None  # planner estimate (informational)
    est_cost_usd: float | None = None  # planner estimate (informational)
    serves: str | None = None  # optional PRD traceability note, e.g. "REQ-3" or "new"
    # Subagent routing (v0.31+): optional scoped role profile + a justification
    # used by the subagent-justification gate. ``role_reason`` is what clears a
    # ``general-purpose`` challenge for a task the gate would otherwise flag.
    role: str | None = None
    role_reason: str = ""


@dataclass(frozen=True)
class WorkPackage:
    """A bounded milestone work package; separate from legacy ``Task``."""

    id: str
    goal: str
    expected_outcome: str
    acceptance_evidence: list[str]
    dependencies: list[str]
    risks: list[str]
    allowed_surfaces: list[str]
    cost_lane: str
    demo_point: str
    signoff_policy: str
    status: str = "pending"


@dataclass(frozen=True)
class Milestone:
    id: str
    goal: str
    expected_outcome: str
    work_packages: list[WorkPackage]


@dataclass(frozen=True)
class PackagePlan:
    mode: str
    milestones: list[Milestone]


_HEADER_RE = re.compile(r"^###\s+Task\s+(\d+)\s*:\s*(.+?)\s*$")
# Loose pattern: a "### Task <digits>" heading that does NOT match the strict
# _HEADER_RE is a malformed numbered header and must raise. The digit is
# required so prose headings ("### Task overview", "### Task description")
# stay legal preamble; a word-numbered typo ("### Task Four:") is therefore
# absorbed silently — the contiguous-index check still catches the gap.
_LOOSE_TASK_RE = re.compile(r"^###\s*Task\s*\d", re.IGNORECASE)
_FIELD_RE = re.compile(r"^-\s+\*\*([a-z_]+):\*\*\s*(.*?)\s*$")
_LIST_RE = re.compile(r"^\[(.*)\]$")
_MILESTONE_RE = re.compile(r"^#{1,3}\s+Milestone(?:\s+[^:]*)?\s*:\s*(.+?)\s*$", re.IGNORECASE)
_PACKAGE_RE = re.compile(r"^#{2,4}\s+(?:Work[- ]?Package|Package)(?:\s+[^:]*)?\s*:\s*(.+?)\s*$", re.IGNORECASE)


def parse_plan(path: str | Path) -> list[Task]:
    """Parse a plan file and return validated tasks.

    Raises PlanError on any structural problem.
    """
    p = Path(path)
    if not p.is_file():
        raise PlanError(f"plan file not found: {path}")
    lines = p.read_text(encoding="utf-8").splitlines()

    tasks: list[Task] = []
    current: dict[str, Any] | None = None
    spec_lines: list[str] | None = None
    reading_spec = False
    line_no = 0

    def _close_current(end_line: int) -> None:
        nonlocal current, spec_lines, reading_spec
        if current is None:
            return
        if spec_lines is not None:
            current["spec"] = "\n".join(spec_lines).strip()
        try:
            tasks.append(_build_task(current))
        except PlanError as e:
            raise PlanError(f"task {current.get('index', '?')} (ending at line {end_line}): {e}") from None
        current = None
        spec_lines = None
        reading_spec = False

    for raw in lines:
        line_no += 1
        header = _HEADER_RE.match(raw)
        if header:
            _close_current(line_no - 1)
            current = {
                "index": int(header.group(1)),
                "title": header.group(2),
                "context_files": [],
                "model": None,
                "verifier_timeout_s": 60,
                "spec": "",
            }
            spec_lines = None
            reading_spec = False
            continue

        # A line that looks like a task header but doesn't match the strict
        # format (missing colon, no space after ###, etc.) is malformed — raise
        # rather than silently absorbing it into the previous task's spec.
        if _LOOSE_TASK_RE.match(raw) and not _HEADER_RE.match(raw):
            raise PlanError(f"malformed task header at line {line_no}: {raw!r}")

        if current is None:
            continue

        if reading_spec:
            if not _handle_spec_line(raw, line_no, current, spec_lines if spec_lines is not None else [], reading_spec):
                _close_current(line_no - 1)
            continue

        field_m = _FIELD_RE.match(raw)
        if not field_m:
            if raw.startswith("## ") and not raw.startswith("### "):
                _close_current(line_no - 1)
            continue

        key, value = field_m.group(1), field_m.group(2)
        if key == "spec":
            reading_spec = True
            spec_lines = [value] if value else []
        else:
            _dispatch_field(key, value, line_no, current)

    _close_current(line_no)

    if not tasks:
        raise PlanError("plan has no tasks (no '### Task N:' headers found)")

    _validate_indices(tasks)
    return tasks


def parse_package_plan(path: str | Path) -> PackagePlan:
    """Parse a milestone package plan without changing the legacy Task parser.

    Each milestone and package heading supplies a human title.  ``id`` fields
    are optional and normalize deterministically from those titles; callers
    therefore resume by stable IDs rather than transient task indices.
    """
    p = Path(path)
    if not p.is_file():
        raise PlanError(f"plan file not found: {path}")
    mode = "orchestrator"
    milestones: list[dict[str, Any]] = []
    current_milestone: dict[str, Any] | None = None
    current_package: dict[str, Any] | None = None
    for line_no, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^-\s+\*\*(?:resume_)?index:\*\*", raw, re.IGNORECASE):
            raise PlanError(
                f"index-only resume metadata is forbidden at line {line_no}; "
                "use stable milestone/package IDs"
            )
        milestone_match = _MILESTONE_RE.match(raw)
        package_match = _PACKAGE_RE.match(raw)
        if milestone_match:
            title = milestone_match.group(1)
            current_milestone = {
                "id": stable_milestone_id(title),
                "goal": title,
                "expected_outcome": title,
                "work_packages": [],
            }
            milestones.append(current_milestone)
            current_package = None
            continue
        if package_match:
            if current_milestone is None:
                raise PlanError(f"work package at line {line_no} has no milestone")
            title = package_match.group(1)
            current_package = {
                "id": stable_work_package_id(current_milestone["id"], title),
                "goal": title, "expected_outcome": title,
                "acceptance_evidence": ["defined"], "dependencies": ["none"], "risks": ["none"],
                "allowed_surfaces": ["implementation"], "cost_lane": "standard",
                "demo_point": "verification", "signoff_policy": "owner", "status": "pending",
            }
            current_milestone["work_packages"].append(current_package)
            continue
        field = _FIELD_RE.match(raw)
        if not field:
            continue
        key, value = field.group(1), field.group(2)
        if key == "mode":
            mode = value.strip().lower()
            continue
        if current_package is not None:
            if current_milestone is None:
                raise PlanError(f"work package at line {line_no} has no milestone")
            target: dict[str, Any] = current_package
        elif current_milestone is not None:
            target = current_milestone
        else:
            continue
        if key == "id":
            if current_package is not None:
                target[key] = stable_work_package_id(current_milestone["id"], value)
            else:
                target[key] = stable_milestone_id(value)
        elif key in {"acceptance_evidence", "dependencies", "risks", "allowed_surfaces"}:
            target[key] = _parse_list(value)
        else:
            target[key] = value.strip()
    # Imported here to preserve the existing schemas -> dispatch -> parser
    # dependency direction used by the legacy Task backend.
    from renmark.schemas import validate_milestone_document

    raw_document = {"milestones": milestones}
    issues = validate_milestone_document(raw_document)
    if issues:
        raise PlanError("invalid package plan: " + "; ".join(issues))
    parsed = [
        Milestone(
            id=m["id"],
            goal=m["goal"],
            expected_outcome=m["expected_outcome"],
            work_packages=[WorkPackage(**wp) for wp in m["work_packages"]],
        )
        for m in milestones
    ]
    if mode not in {"agency", "orchestrator"}:
        raise PlanError("package plan mode must be agency or orchestrator")
    return PackagePlan(mode=mode, milestones=parsed)


_PLAN_INT_FIELDS: frozenset[str] = frozenset({"verifier_timeout_s", "parallel_group", "est_tokens"})
_PLAN_FLOAT_FIELDS: frozenset[str] = frozenset({"est_cost_usd"})
_PLAN_STR_FIELDS: frozenset[str] = frozenset({
    "mode", "target", "model", "verifier", "executor", "complexity",
    "serves", "role", "role_reason",
})


def _dispatch_field(key: str, value: str, line_no: int, current: dict[str, Any]) -> None:
    """Populate *current* task dict from a parsed field key/value pair.

    Raises PlanError on unknown or malformed fields.  The ``spec`` key is
    handled by the caller (it also manages ``reading_spec`` / ``spec_lines``
    state that lives outside this helper).
    """
    if key == "context_files":
        current["context_files"] = _parse_list(value)
        return
    if key in _PLAN_INT_FIELDS:
        try:
            current[key] = int(value)
        except ValueError as e:
            raise PlanError(f"line {line_no}: {key} must be int, got {value!r}") from e
        return
    if key in _PLAN_FLOAT_FIELDS:
        try:
            current[key] = float(value)
        except ValueError as e:
            raise PlanError(f"line {line_no}: {key} must be float, got {value!r}") from e
        return
    if key in _PLAN_STR_FIELDS:
        current[key] = value
        return
    raise PlanError(f"line {line_no}: unknown field {key!r}")


def _handle_spec_line(
    raw: str,
    line_no: int,
    current: dict[str, Any],
    spec_lines: list[str],
    reading_spec: bool,
) -> bool:
    """Process one line while in spec-reading mode.

    Appends *raw* to *spec_lines* (stripping a 2-space indent when present).
    Returns ``False`` when a new section or task heading is detected — the
    caller must then invoke ``_close_current``; returns ``True`` otherwise
    (spec reading should continue).
    """
    stripped = raw.strip()
    if stripped.startswith("### Task ") or (
        raw.startswith("## ") and not raw.startswith("### ")
    ):
        return False
    if raw.startswith("  "):
        spec_lines.append(raw[2:])
    else:
        spec_lines.append(raw)
    return True


def _parse_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw in ("", "[]"):
        return []
    m = _LIST_RE.match(raw)
    if not m:
        raise PlanError(f"context_files must be a bracketed list, got {raw!r}")
    inner = m.group(1).strip()
    if not inner:
        return []
    items = [item.strip().strip('"').strip("'") for item in inner.split(",")]
    return [i for i in items if i]


def _build_task(d: dict[str, Any]) -> Task:
    required = ("mode", "target", "verifier")
    for k in required:
        v = d.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise PlanError(f"missing required field: {k}")

    mode = d["mode"].strip().upper()
    if mode == "C":
        raise PlanError("mode C (cross-file) is forbidden; decompose into A/B tasks")
    if mode not in ("A", "B"):
        raise PlanError(f"invalid mode {mode!r}; must be A or B")

    target = d["target"].strip()
    if not target:
        raise PlanError("target is empty")
    if ".." in Path(target).parts:
        raise PlanError(f"target path must not contain '..': {target}")
    if Path(target).is_absolute():
        raise PlanError(f"target must be repo-relative, got absolute: {target}")

    verifier = d["verifier"].strip()
    if not verifier:
        raise PlanError("verifier is empty")

    spec = d.get("spec", "").strip()
    if not spec:
        raise PlanError("spec is empty")

    executor = (d.get("executor") or "codex").strip().lower()
    # Allow haiku, codex, sonnet, opus, or any provider-string of form "<provider>/<model>".
    # nim was removed in v0.2.0 — use haiku for simple tasks instead.
    if executor not in ("haiku", "codex", "sonnet", "opus", "fable") and "/" not in executor:
        raise PlanError(
            f"executor must be one of haiku, codex, sonnet, opus, fable, or a provider/model string, got {executor!r}"
        )

    complexity = (d.get("complexity") or "medium").strip().lower()
    if complexity not in ("simple", "medium", "hard"):
        raise PlanError(f"complexity must be simple, medium, or hard, got {complexity!r}")

    return Task(
        index=d["index"],
        title=d["title"].strip(),
        mode=mode,
        target=target,
        context_files=d["context_files"],
        model=(d["model"].strip() if d.get("model") else None),
        verifier=verifier,
        verifier_timeout_s=d["verifier_timeout_s"],
        spec=spec,
        complexity=complexity,
        parallel_group=d.get("parallel_group"),
        est_tokens=d.get("est_tokens"),
        est_cost_usd=d.get("est_cost_usd"),
        executor=executor,
        serves=(d["serves"].strip() if d.get("serves") else None),
        role=(d["role"].strip() if d.get("role") else None),
        role_reason=(d["role_reason"].strip() if d.get("role_reason") else ""),
    )


def _validate_indices(tasks: list[Task]) -> None:
    seen: set[int] = set()
    for t in tasks:
        if t.index in seen:
            raise PlanError(f"duplicate task index: {t.index}")
        seen.add(t.index)
    expected = list(range(1, len(tasks) + 1))
    actual = sorted(t.index for t in tasks)
    if actual != expected:
        raise PlanError(f"task indices must be contiguous starting at 1; got {actual}")
