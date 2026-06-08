"""Proportional-pipeline tier classifier — deterministic, zero-LLM, stdlib-only.

This is the **single source of truth** for "how big/risky is this change?" used
by two callers:

- the **feature router** — ``classify_plan(tasks)`` runs on the validated plan to
  pick the lite-vs-full lane before any heavy stage spends tokens.
- **codereview** — ``classify_diff(repo)`` runs on the working diff to pick the
  cheap in-context ``/review`` vs the full codex review.

Both return one of three **tiers**:

- ``"lite"``    — small, low-risk, doc/config-dominant. Cheap lane: cheap review,
  land on ``main``, no PR/codex/release ceremony. Chosen only when the signals
  are *confidently* small.
- ``"standard"`` — a moderate code change, the full pipeline. Also the **safe
  default**: any uncertainty, empty input, or failure degrades to ``"standard"``
  so we never accidentally drop a real change into the lite lane.
- ``"full"``    — a ``hard`` task, a core-module edit, many tasks, or a large
  diff: warrants the full pipeline + full codex review.

Design contract:

- Pure functions of their inputs (``classify_diff`` shells out to ``git`` but
  never mutates state).
- **Never raises into the caller.** Every git / IO / parse step is wrapped; on
  any failure or ambiguity the result is ``"standard"`` — never ``"lite"`` by
  accident.
- Every threshold is a documented, tunable module-level constant.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

from .parser import Task

# ── Tier type ──────────────────────────────────────────────────────────────────

#: The three proportional-pipeline tiers, in ascending weight.
Tier = Literal["lite", "standard", "full"]

#: Tier values as plain strings (for callers that want the set, e.g. validation).
TIER_LITE: Tier = "lite"
TIER_STANDARD: Tier = "standard"
TIER_FULL: Tier = "full"

#: The safe default — returned on ANY uncertainty, empty input, or failure.
#: Never ``"lite"`` by accident; never silently ``"full"`` either.
DEFAULT_TIER: Tier = "standard"

# ── Thresholds (tunable) ─────────────────────────────────────────────────────

#: Plan classification (``classify_plan``):
#: A plan with this many tasks or fewer MAY be ``lite`` (if no other signal
#: bumps it). Above it, the plan is at least ``standard``.
LITE_MAX_TASKS: int = 3

#: A plan with strictly more tasks than this is ``full`` regardless of content
#: (many moving parts = real change worth full review).
FULL_MIN_TASKS: int = 8

#: Summed planner ``est_tokens`` at/under this is "very small" and may stay
#: ``lite`` even for code (when no harder signal fires). ``None`` est_tokens are
#: treated as 0 (planner gave no estimate — size is governed by task count).
LITE_MAX_EST_TOKENS: int = 4_000

#: Summed planner ``est_tokens`` at/over this forces ``full`` (large change).
FULL_MIN_EST_TOKENS: int = 60_000

#: Diff classification (``classify_diff``):
#: A diff touching this many files or fewer MAY be ``lite``.
LITE_MAX_FILES: int = 3

#: A diff touching strictly more files than this is ``full``.
FULL_MIN_FILES: int = 10

#: Total lines changed (insertions + deletions) at/under this MAY be ``lite``.
LITE_MAX_LINES: int = 40

#: Total lines changed at/over this forces ``full`` (large diff).
FULL_MIN_LINES: int = 400

#: ``git`` subprocess timeout, seconds.
GIT_TIMEOUT_S: int = 10

# ── File-type signals (tunable) ──────────────────────────────────────────────

#: Suffixes treated as docs/config (lean toward ``lite``). ``.gitignore`` has no
#: "suffix" in the usual sense; it's matched by name in ``_is_doc_or_config``.
DOC_CONFIG_SUFFIXES: frozenset[str] = frozenset(
    {".md", ".txt", ".json", ".toml", ".gitignore", ".yaml", ".yml", ".cfg", ".ini"}
)

#: Exact basenames (no useful suffix) treated as doc/config.
DOC_CONFIG_BASENAMES: frozenset[str] = frozenset({".gitignore", ".gitattributes"})

#: Path fragments that mark a file as a template (doc/config-leaning).
TEMPLATE_MARKERS: tuple[str, ...] = ("template", "templates")

#: Core-module path roots: an edit under here is risk-bearing and forces
#: ``>= standard`` even when small. ``renmark/`` is the runtime package; touching
#: parser / lifecycle / dispatch / init / sizing etc. must never be ``lite``.
CORE_MODULE_ROOTS: tuple[str, ...] = ("renmark/", "bin/")

#: Code suffixes — presence of any of these makes a change "code-leaning".
CODE_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".sh", ".bash", ".rs", ".go", ".c", ".h"}
)


# ── Public API ──────────────────────────────────────────────────────────────


def classify_plan(tasks: list[Task]) -> Tier:
    """Classify a validated plan into a proportional-pipeline :data:`Tier`.

    Signals (all thresholds are module constants above):

    - any task with ``complexity == "hard"`` → never ``lite`` (>= ``standard``);
    - any **core-module** target (under :data:`CORE_MODULE_ROOTS`) → >= ``standard``;
    - many tasks (> :data:`FULL_MIN_TASKS`) or large summed ``est_tokens``
      (>= :data:`FULL_MIN_EST_TOKENS`) → ``full``;
    - small (<= :data:`LITE_MAX_TASKS` tasks), no ``hard``, no core-module, and
      doc/config-dominant **or** very small (summed ``est_tokens`` <=
      :data:`LITE_MAX_EST_TOKENS`) → ``lite``;
    - otherwise → ``standard``.

    Never raises: empty input or any unexpected shape yields
    :data:`DEFAULT_TIER` (``"standard"`` — the safe middle).
    """
    try:
        if not tasks:
            return DEFAULT_TIER

        n_tasks = len(tasks)
        has_hard = any(_task_complexity(t) == "hard" for t in tasks)
        targets = [_task_target(t) for t in tasks]
        has_core = any(_is_core_module(p) for p in targets)
        all_doc_config = bool(targets) and all(_is_doc_or_config(p) for p in targets)
        total_est = sum(_task_est_tokens(t) for t in tasks)

        # ── full: heaviest signals win first ──
        if has_hard:
            # hard never goes lite; escalate to full when also big/numerous,
            # else standard (the "never lite" floor).
            if n_tasks > FULL_MIN_TASKS or total_est >= FULL_MIN_EST_TOKENS or has_core:
                return TIER_FULL
            return TIER_STANDARD
        if n_tasks > FULL_MIN_TASKS:
            return TIER_FULL
        if total_est >= FULL_MIN_EST_TOKENS:
            return TIER_FULL

        # ── standard floor: core-module edits are risk-bearing ──
        if has_core:
            return TIER_STANDARD

        # ── lite: confidently small ──
        if n_tasks <= LITE_MAX_TASKS and (all_doc_config or total_est <= LITE_MAX_EST_TOKENS):
            return TIER_LITE

        # ── everything in between ──
        return TIER_STANDARD
    except Exception:  # never raise into the caller; degrade safe.
        return DEFAULT_TIER


def classify_diff(repo: Path | str, base_ref: str = "main") -> Tier:
    """Classify the working diff (``<base_ref>..HEAD``) into a :data:`Tier`.

    Runs ``git diff --stat <base_ref>..HEAD`` via :mod:`subprocess` and classifies
    by files-changed, lines-changed, and doc-vs-code mix using the same tier
    rules as :func:`classify_plan`:

    - any **core-module** file touched (under :data:`CORE_MODULE_ROOTS`) → >= ``standard``;
    - many files (> :data:`FULL_MIN_FILES`) or large line churn
      (>= :data:`FULL_MIN_LINES`) → ``full``;
    - few files (<= :data:`LITE_MAX_FILES`), small churn (<= :data:`LITE_MAX_LINES`),
      no core-module, and doc/config-dominant → ``lite``;
    - otherwise → ``standard``.

    Never raises: a missing git binary, a non-repo, an unknown ``base_ref``, a
    timeout, or an unparseable stat all degrade to :data:`DEFAULT_TIER`.
    """
    try:
        stat = _git_diff_stat(repo, base_ref)
        if stat is None:
            return DEFAULT_TIER
        files, total_lines = stat
        if not files:
            # No changes detected — nothing to escalate, but don't claim "lite"
            # confidently from an empty/odd diff; the safe middle is fine.
            return DEFAULT_TIER

        n_files = len(files)
        has_core = any(_is_core_module(p) for p in files)
        all_doc_config = all(_is_doc_or_config(p) for p in files)

        # ── full ──
        if n_files > FULL_MIN_FILES or total_lines >= FULL_MIN_LINES:
            return TIER_FULL

        # ── standard floor: core-module edits are risk-bearing ──
        if has_core:
            return TIER_STANDARD

        # ── lite: confidently small + doc/config-dominant ──
        if n_files <= LITE_MAX_FILES and total_lines <= LITE_MAX_LINES and all_doc_config:
            return TIER_LITE

        return TIER_STANDARD
    except Exception:  # never raise into the caller; degrade safe.
        return DEFAULT_TIER


# ── Internal: file-type predicates ──────────────────────────────────────────


def _is_doc_or_config(path: str) -> bool:
    """True if ``path`` is a doc / config / template file (lite-leaning)."""
    name = Path(path).name
    if name in DOC_CONFIG_BASENAMES:
        return True
    lowered = path.lower()
    if any(marker in lowered for marker in TEMPLATE_MARKERS):
        return True
    return Path(path).suffix.lower() in DOC_CONFIG_SUFFIXES


def _is_core_module(path: str) -> bool:
    """True if ``path`` is a core-module edit (forces >= standard).

    A code file under any :data:`CORE_MODULE_ROOTS` prefix. Doc/config files that
    merely live under those roots (e.g. ``renmark/README.md``) are not core.
    """
    norm = path.lstrip("./")
    if not any(norm.startswith(root) for root in CORE_MODULE_ROOTS):
        return False
    return Path(norm).suffix.lower() in CODE_SUFFIXES or Path(norm).suffix == ""


# ── Internal: Task field accessors (defensive — never raise) ─────────────────


def _task_complexity(task: Task) -> str:
    value = getattr(task, "complexity", "medium")
    return value.strip().lower() if isinstance(value, str) else "medium"


def _task_target(task: Task) -> str:
    value = getattr(task, "target", "")
    return value if isinstance(value, str) else ""


def _task_est_tokens(task: Task) -> int:
    value = getattr(task, "est_tokens", None)
    return value if isinstance(value, int) and value > 0 else 0


# ── Internal: git ─────────────────────────────────────────────────────────────


def _git_diff_stat(repo: Path | str, base_ref: str) -> tuple[list[str], int] | None:
    """Return ``(changed_files, total_lines_changed)`` for ``<base_ref>..HEAD``.

    Parses the trailing summary line of ``git diff --stat`` for line counts and
    each preceding ``path | N`` row for filenames. Returns ``None`` on any
    failure (no git, non-repo, unknown ref, timeout, empty output).
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "diff", "--stat", f"{base_ref}..HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if proc.returncode != 0:
        return None

    files: list[str] = []
    total_lines = 0
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "|" in line:
            # "path/to/file.py | 12 +++---"  → take the path before the pipe.
            path = line.split("|", 1)[0].strip()
            if path:
                files.append(path)
        elif "changed" in line and ("insertion" in line or "deletion" in line):
            total_lines += _parse_summary_line(line)
    return files, total_lines


def _parse_summary_line(line: str) -> int:
    """Extract insertions+deletions from a ``git diff --stat`` summary line.

    e.g. ``"3 files changed, 12 insertions(+), 4 deletions(-)"`` → ``16``.
    Returns ``0`` if no counts can be read.
    """
    total = 0
    for chunk in line.split(","):
        chunk = chunk.strip()
        if "insertion" in chunk or "deletion" in chunk:
            head = chunk.split()[0] if chunk.split() else ""
            if head.isdigit():
                total += int(head)
    return total
