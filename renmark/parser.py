"""Plan file parser for nim-execute.

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


class PlanError(ValueError):
    """Raised when a plan file is malformed."""


@dataclass
class Task:
    index: int                       # 1-based as written in the plan
    title: str
    mode: str                        # "A" or "B"
    target: str
    context_files: list[str] = field(default_factory=list)
    model: str | None = None
    verifier: str = ""
    verifier_timeout_s: int = 60
    spec: str = ""
    executor: str = "nim"            # "nim" (default) or "codex"


_HEADER_RE = re.compile(r"^###\s+Task\s+(\d+)\s*:\s*(.+?)\s*$")
_FIELD_RE = re.compile(r"^-\s+\*\*([a-z_]+):\*\*\s*(.*?)\s*$")
_LIST_RE = re.compile(r"^\[(.*)\]$")


def parse_plan(path: str | Path) -> list[Task]:
    """Parse a plan file and return validated tasks.

    Raises PlanError on any structural problem.
    """
    p = Path(path)
    if not p.is_file():
        raise PlanError(f"plan file not found: {path}")
    lines = p.read_text(encoding="utf-8").splitlines()

    tasks: list[Task] = []
    current: dict | None = None
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
            raise PlanError(
                f"task {current.get('index', '?')} (ending at line {end_line}): {e}"
            ) from None
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

        if current is None:
            continue

        if reading_spec:
            stripped = raw.strip()
            if stripped.startswith("### Task ") or (
                raw.startswith("## ") and not raw.startswith("### ")
            ):
                _close_current(line_no - 1)
                continue
            if spec_lines is None:
                spec_lines = []
            if raw.startswith("  "):
                spec_lines.append(raw[2:])
            else:
                spec_lines.append(raw)
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
        elif key == "context_files":
            current["context_files"] = _parse_list(value)
        elif key == "verifier_timeout_s":
            try:
                current["verifier_timeout_s"] = int(value)
            except ValueError as e:
                raise PlanError(
                    f"line {line_no}: verifier_timeout_s must be int, got {value!r}"
                ) from e
        elif key in ("mode", "target", "model", "verifier", "executor"):
            current[key] = value
        else:
            raise PlanError(f"line {line_no}: unknown field {key!r}")

    _close_current(line_no)

    if not tasks:
        raise PlanError("plan has no tasks (no '### Task N:' headers found)")

    _validate_indices(tasks)
    return tasks


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


def _build_task(d: dict) -> Task:
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

    executor = (d.get("executor") or "nim").strip().lower()
    if executor not in ("nim", "codex"):
        raise PlanError(f"executor must be 'nim' or 'codex', got {executor!r}")

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
        executor=executor,
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
        raise PlanError(
            f"task indices must be contiguous starting at 1; got {actual}"
        )
