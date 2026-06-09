"""Backlog item state — the deterministic, persistent ledger of work items that
renmark surfaces for human review, approval, and disposition.

A *backlog item* is a unit of proposed/tracked work (a bug, an idea, a research
finding, a QA gap, a user request) that moves through a small, explicit status
machine and — when it spawns a managed branch — must end in exactly one
*disposition* (the no-orphan-branch invariant: every managed branch is either
merged-and-deleted, abandoned-and-deleted, or deliberately kept).

Design contract (mirrors ``renmark/loop.py``):

- **Never raises into the caller.** Every IO / parse / coerce step is wrapped; a
  missing or corrupt item file degrades to ``None`` (or is skipped), never an
  exception. An unknown ``status`` coerces to ``"needs review"`` so a malformed
  item lands back in the human-review queue rather than crashing the caller.
- **Deterministic / testable.** No ``datetime.now()``, no ``random``, no git,
  no network. Callers pass timestamps (``created_at`` / ``updated_at``); ids are
  derived purely from the existing files on disk.
- **JSON-trivial.** Every :class:`BacklogItem` field is ``str`` (no ints/bools/
  nested structures), so ``json.dumps`` / ``json.loads`` round-trips with no
  custom serializer — exactly like :class:`renmark.loop.LoopState`.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .state import state_dir

# ── Vocabularies ───────────────────────────────────────────────────────────────

#: The closed status machine an item moves through. ``"needs review"`` is the
#: default landing state; an unknown/corrupt persisted status coerces back to it.
STATUSES: tuple[str, ...] = (
    "needs review",
    "needs approval",
    "approved",
    "in progress",
    "blocked",
    "completed",
    "rejected",
)

#: ``risk`` is an OPEN free-string field, NOT an enum. Expected values:
#:   "low" | "medium" | "high"
#: Callers may write anything; readers must not assume the set is closed.
#:
#: ``source`` is likewise an OPEN free-string field, NOT an enum. Expected values:
#:   "user" | "qa" | "research" | "bug" | "idea"
#: Both fields are coerced to ``str`` on read but never validated against a set.

#: Terminal end-states for a *managed branch* spawned by an item. The
#: no-orphan-branch invariant: every managed branch ends in EXACTLY one of these
#: — merged then deleted, abandoned then deleted, or deliberately kept around.
DISPOSITIONS: tuple[str, ...] = (
    "merged-deleted",
    "abandoned-deleted",
    "kept",
)

#: Default status applied to a fresh item and to any item whose persisted
#: ``status`` is unknown / non-str (mirrors the loop.py coerce discipline).
_DEFAULT_STATUS: str = "needs review"

#: Glob + filename pattern for item files inside :func:`backlog_dir`.
_ITEM_GLOB: str = "BL-*.json"

#: Extracts the zero-padded numeric part of a ``BL-NNNN`` id / filename.
_ID_NUM_RE = re.compile(r"^BL-(?P<num>\d+)$")


# ── Backlog item ───────────────────────────────────────────────────────────────


@dataclass
class BacklogItem:
    """One backlog item. Persisted to ``.renmark/state/backlog/<id>.json``.

    Every field is a ``str`` so the dataclass round-trips through ``json`` with
    no custom serializer (kept JSON-trivial, exactly like
    :class:`renmark.loop.LoopState`). ``status`` is constrained to
    :data:`STATUSES`; ``disposition`` (when set) to :data:`DISPOSITIONS`. All
    other fields are free strings.
    """

    id: str
    title: str
    status: str = _DEFAULT_STATUS  # one of STATUSES
    source: str = ""  # free string; see expected values above
    risk: str = ""  # free string; "low" | "medium" | "high"
    summary: str = ""
    evidence_path: str = ""
    recommended_action: str = ""
    served_requirements: str = ""
    pending_decision: str = ""
    branch: str = ""
    loop_id: str = ""
    disposition: str = ""  # "" while open; one of DISPOSITIONS once terminal
    created_at: str = ""
    updated_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=False)


# ── Paths ────────────────────────────────────────────────────────────────────


def backlog_dir(repo: str | Path) -> Path:
    """Return ``.renmark/state/backlog/`` for ``repo`` (parent created lazily by
    :func:`renmark.state.state_dir`; the backlog subdir itself is created on
    write, not here)."""
    return state_dir(repo) / "backlog"


def _item_json_path(repo: str | Path, item_id: str) -> Path:
    return backlog_dir(repo) / f"{item_id}.json"


# ── ID allocation ──────────────────────────────────────────────────────────────


def next_id(repo: str | Path) -> str:
    """Return the next free ``BL-NNNN`` id (zero-padded to 4 digits).

    Scans existing ``BL-*.json`` files in :func:`backlog_dir`, finds the highest
    numeric suffix, and returns one past it (starting at ``"BL-0001"`` when the
    directory is empty or absent). A filename that does not match ``BL-<digits>``
    is skipped rather than raising. Never raises.
    """
    highest = 0
    directory = backlog_dir(repo)
    try:
        names = [p.stem for p in directory.glob(_ITEM_GLOB)] if directory.exists() else []
    except OSError:
        names = []
    for stem in names:
        match = _ID_NUM_RE.match(stem)
        if not match:
            continue
        try:
            value = int(match.group("num"))
        except (ValueError, TypeError):
            continue
        if value > highest:
            highest = value
    return f"BL-{highest + 1:04d}"


# ── Read / write ───────────────────────────────────────────────────────────────


def _coerce_str(value: object) -> str:
    """Coerce ``value`` to a string field value; ``None`` → ``""``; non-str →
    ``str(...)``. Never raises (mirrors loop.py's ``_coerce_str``)."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:  # pragma: no cover - str() on a pathological object
        return ""


def _coerce_status(value: object) -> str:
    """Coerce a persisted ``status`` to a known value. Unknown / non-str →
    :data:`_DEFAULT_STATUS` so a malformed item returns to the review queue
    rather than crashing the caller (mirrors loop.py's ``_coerce_status``)."""
    if isinstance(value, str) and value in STATUSES:
        return value
    return _DEFAULT_STATUS


def _coerce_disposition(value: object) -> str:
    """Coerce a persisted ``disposition``. ``""`` (open) and any known
    :data:`DISPOSITIONS` value pass through; anything else degrades to ``""``
    (treated as still-open rather than a bogus terminal state)."""
    if isinstance(value, str) and (value == "" or value in DISPOSITIONS):
        return value
    return ""


def _coerce_item(data: dict[str, object]) -> BacklogItem:
    """Build a :class:`BacklogItem` from arbitrary JSON, coercing every field to
    its expected type. Unknown keys are dropped; an unknown ``status`` degrades
    to ``"needs review"``; an unknown ``disposition`` degrades to ``""``. The
    ``id`` falls back to the empty string when absent (the caller / filename is
    the real source of truth). Never raises."""
    item = BacklogItem(id="", title="")
    item.id = _coerce_str(data.get("id"))
    item.title = _coerce_str(data.get("title"))
    item.status = _coerce_status(data.get("status"))
    item.source = _coerce_str(data.get("source"))
    item.risk = _coerce_str(data.get("risk"))
    item.summary = _coerce_str(data.get("summary"))
    item.evidence_path = _coerce_str(data.get("evidence_path"))
    item.recommended_action = _coerce_str(data.get("recommended_action"))
    item.served_requirements = _coerce_str(data.get("served_requirements"))
    item.pending_decision = _coerce_str(data.get("pending_decision"))
    item.branch = _coerce_str(data.get("branch"))
    item.loop_id = _coerce_str(data.get("loop_id"))
    item.disposition = _coerce_disposition(data.get("disposition"))
    item.created_at = _coerce_str(data.get("created_at"))
    item.updated_at = _coerce_str(data.get("updated_at"))
    return item


def read_item(repo: str | Path, item_id: str) -> BacklogItem | None:
    """Return the persisted :class:`BacklogItem`, or ``None`` if absent/corrupt.

    Never raises: a missing file, unreadable bytes, invalid JSON, or a non-dict
    payload all yield ``None``. An unknown ``status`` is coerced to
    ``"needs review"`` and unknown fields are dropped so schema drift can't crash
    the constructor.
    """
    path = _item_json_path(repo, item_id)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return _coerce_item(data)
    except (TypeError, ValueError):
        return None


def write_item(repo: str | Path, item: BacklogItem) -> Path | None:
    """Persist ``item`` to ``.renmark/state/backlog/<id>.json``.

    Best-effort atomic replace (NO fsync): writes a sibling ``.tmp`` then
    ``Path.replace`` over the target, so a crash between writes never leaves a
    half-written file (mirrors :func:`renmark.loop.write_loop`). Creates the
    backlog directory if needed. Returns the written path, or ``None`` on any IO
    failure — never raises into the caller.
    """
    path = _item_json_path(repo, item.id)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(item.to_json(), encoding="utf-8")
        tmp.replace(path)  # atomic on the same filesystem
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return None
    return path


def list_items(repo: str | Path) -> list[BacklogItem]:
    """Return every readable backlog item, newest-first.

    Sorted by ``created_at`` then ``id`` (both descending), so the most recently
    created items lead and ties break deterministically on id. Unreadable /
    corrupt files are skipped (each via :func:`read_item`, which never raises).
    Never raises.
    """
    directory = backlog_dir(repo)
    items: list[BacklogItem] = []
    try:
        paths = sorted(directory.glob(_ITEM_GLOB)) if directory.exists() else []
    except OSError:
        return []
    for path in paths:
        item = read_item(repo, path.stem)
        if item is not None:
            items.append(item)
    items.sort(key=lambda it: (it.created_at, it.id), reverse=True)
    return items


# ── Managed branches ───────────────────────────────────────────────────────────


def managed_branch_name(item_id: str, slug: str) -> str:
    """Build the managed branch name ``feature/backlog-<item_id>-<safe-slug>``.

    ``item_id`` is lowercased; ``slug`` is sanitised to a safe path component the
    same way as :func:`renmark.loop.loop_id` (lowercased, non-alphanumerics
    collapsed to ``-``, trimmed). A blank slug degrades to ``item``. Never raises.
    """
    safe_id = str(item_id).strip().lower()
    safe_slug = re.sub(r"[^a-z0-9]+", "-", str(slug).strip().lower()).strip("-")
    safe_slug = safe_slug or "item"
    return f"feature/backlog-{safe_id}-{safe_slug}"


# ── Outcome helpers ────────────────────────────────────────────────────────────


def completion_report(*, goal_reached: bool, iteration: int, max_iterations: int) -> str:
    """Human-readable one-line outcome for a backlog item's loop run.

    Returns the goal-reached line when ``goal_reached`` is true, otherwise the
    stopped/unverified line. Pure string formatting — never raises.
    """
    if goal_reached:
        return f"Goal reached in {iteration}/{max_iterations} iterations."
    return f"Stopped after {iteration}/{max_iterations} iterations. Goal not fully verified."


def status_for_outcome(*, goal_reached: bool) -> str:
    """Map a loop outcome to the backlog status it should adopt: ``"completed"``
    when the goal was reached, else ``"blocked"``. Never raises."""
    return "completed" if goal_reached else "blocked"


def is_terminal_disposition(value: str) -> bool:
    """Return ``True`` iff ``value`` is one of the terminal :data:`DISPOSITIONS`
    (the no-orphan-branch end-states). Never raises."""
    return value in DISPOSITIONS


__all__ = [
    "DISPOSITIONS",
    "STATUSES",
    "BacklogItem",
    "backlog_dir",
    "completion_report",
    "is_terminal_disposition",
    "list_items",
    "managed_branch_name",
    "next_id",
    "read_item",
    "status_for_outcome",
    "write_item",
]
