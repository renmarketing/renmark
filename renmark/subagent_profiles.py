"""Specialized subagent role profiles for the renmark dispatch system.

renmark prefers specialized profiles over generic general-purpose assignment.
``general-purpose`` is the FALLBACK ONLY — every other profile is narrower,
cheaper-capable (Haiku for read-only/docs/audit roles, Sonnet for code/tests/review),
and declares a deliberately narrow ``context_scope`` so the dispatch packet
carries less context.

The UI may still surface Claude's built-in "general-purpose" label, but renmark
tracks and logs the intended role from this module, which drives packet shaping
and future Agency Mode routing. Specialized profiles declared here are reused by
the Agency Mode (forthcoming).

Design contract:
- Pure data — no LLM calls, no I/O, no side effects.
- ``resolve_profile`` and ``profile_tier`` never raise into the caller.
- On any error both return the safe fallback (``"general-purpose"`` / ``"sonnet"``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Profile dataclass ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProfileSpec:
    """Specification for a single subagent role.

    Fields
    ------
    role:
        Stable name key; must match the key in ``PROFILES``.
    model_tier:
        Cheapest-capable model tier for this role (``"haiku"`` / ``"sonnet"``
        / ``"codex"`` / ``"opus"``). Dispatch uses this when no explicit
        executor is specified.
    allowed_targets:
        Glob pattern or human-readable description of which file/path targets
        this role is authorized to touch. Informational for now; enforced in
        future Agency Mode.
    output_format:
        Expected output structure (e.g. ``"structured JSON per G11"``).
    stop_condition:
        When the subagent in this role is considered done.
    verification:
        What the orchestrator checks to verify success for this role.
    context_scope:
        ``"narrow"`` = the dispatch packet carries only task-local context;
        ``"broad"`` = general-purpose fallback, wider context permitted.
    """

    role: str
    model_tier: str
    allowed_targets: str
    output_format: str
    stop_condition: str
    verification: str
    context_scope: str


# ── Profile registry ──────────────────────────────────────────────────────────


PROFILES: dict[str, ProfileSpec] = {
    # ── Documentation / markdown edits ───────────────────────────────────────
    "docs-editor": ProfileSpec(
        role="docs-editor",
        model_tier="haiku",
        allowed_targets="**/*.md, plugin/skills/**/*.md, docs/**",
        output_format="structured JSON per G11; touched_files + summary_lines only",
        stop_condition="all target .md files updated, no code files touched",
        verification="diff contains only .md changes; no .py / .sh touched",
        context_scope="narrow",
    ),
    # ── Core Python / shell implementation ───────────────────────────────────
    "code-implementer": ProfileSpec(
        role="code-implementer",
        model_tier="sonnet",
        allowed_targets="renmark/**/*.py, bin/*, *.py",
        output_format="structured JSON per G11; artifact_path + sha + summary_lines",
        stop_condition="target file written, py_compile passes, verifier expectation met",
        verification="py_compile clean; no unexpected files outside target scope",
        context_scope="narrow",
    ),
    # ── Test scaffolding / pytest ─────────────────────────────────────────────
    "test-writer": ProfileSpec(
        role="test-writer",
        model_tier="codex",
        allowed_targets="tests/test_*.py, tests/*_test.py",
        output_format="structured JSON per G11; artifact_path + summary_lines",
        stop_condition="test file written; pytest -q on the new file passes",
        verification="pytest exit-code 0 on new file; no production code touched",
        context_scope="narrow",
    ),
    # ── Code / plan review ────────────────────────────────────────────────────
    "reviewer": ProfileSpec(
        role="reviewer",
        model_tier="sonnet",
        allowed_targets=".renmark/reviews/**/*.md (read-only review of any file)",
        output_format="structured review JSON: findings list + severity + summary_lines",
        stop_condition="review artifact written to .renmark/reviews/; no production file edited",
        verification="review artifact exists; no production files in touched_files",
        context_scope="narrow",
    ),
    # ── Audit / inventory reads ───────────────────────────────────────────────
    "audit-reader": ProfileSpec(
        role="audit-reader",
        model_tier="haiku",
        allowed_targets=".renmark/audits/** (read-only; writes audit artifacts only)",
        output_format="audit JSON or .md artifact in .renmark/audits/; summary_lines ≤ 5",
        stop_condition="audit artifact written; no source files modified",
        verification="only .renmark/audits/ files in touched_files; no .py edits",
        context_scope="narrow",
    ),
    # ── Release / finish lane ─────────────────────────────────────────────────
    "release-manager": ProfileSpec(
        role="release-manager",
        model_tier="sonnet",
        allowed_targets="CHANGELOG.md, pyproject.toml, plugin/commands/*.md, .renmark/state/**",
        output_format="structured JSON per G11; version bump diff + summary_lines",
        stop_condition="version bumped in pyproject.toml; CHANGELOG entry appended; lifecycle.json updated",
        verification="version string incremented; CHANGELOG entry present; lifecycle stage = ready-to-release",
        context_scope="narrow",
    ),
    # ── Research / web / library lookups ─────────────────────────────────────
    "researcher": ProfileSpec(
        role="researcher",
        model_tier="sonnet",
        allowed_targets=".renmark/research/**/*.md (writes research artifacts only)",
        output_format="research artifact in .renmark/research/; compact summary_lines ≤ 5",
        stop_condition="research artifact written with provenance metadata",
        verification="artifact exists at .renmark/research/<topic>.md; no source edits",
        context_scope="narrow",
    ),
    # ── Finish-lane specialist (verify + QA + ship gates) ────────────────────
    "finish-lane-specialist": ProfileSpec(
        role="finish-lane-specialist",
        model_tier="sonnet",
        allowed_targets=".renmark/reviews/**, .renmark/state/lifecycle.json, CHANGELOG.md",
        output_format="structured JSON per G11; gate verdict + summary_lines ≤ 5",
        stop_condition="all finish-lane checks passed; lifecycle gate advanced or blocked with reason",
        verification="lifecycle.json stage advanced; no unreviewed open blockers",
        context_scope="narrow",
    ),
    # ── Fallback — do NOT use unless no specialized profile matches ───────────
    "general-purpose": ProfileSpec(
        role="general-purpose",
        model_tier="sonnet",
        allowed_targets="any (fallback — no target restriction)",
        output_format="structured JSON per G11",
        stop_condition="task spec fulfilled",
        verification="verifier expectation met; subagent output valid per G11",
        context_scope="broad",
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────


def resolve_profile(task: Any) -> str:
    """Infer the best-fit role name from a Task (or any task-shaped object/dict).

    Accepts objects with attributes *or* plain dicts. Heuristic priority order:

    1. ``tests/`` path prefix OR ``test_*`` / ``*_test.*`` filename → ``"test-writer"``
    2. ``.md`` suffix OR path under ``plugin/skills/`` / ``docs/`` → ``"docs-editor"``
    3. title / task kind mentioning ``review`` → ``"reviewer"``
    4. title / task kind mentioning ``audit`` or ``audit-read`` → ``"audit-reader"``
    5. target under ``renmark/`` or ``bin/`` (core code) → ``"code-implementer"``
    6. fallback → ``"general-purpose"``

    Never raises: any exception returns ``"general-purpose"``.
    """
    try:
        target = _get_field(task, "target", "")
        title = _get_field(task, "title", "") or _get_field(task, "spec", "")
        kind = _get_field(task, "kind", "")

        target = (target or "").strip()
        title = (title or "").strip().lower()
        kind = (kind or "").strip().lower()

        # ── 1. Test files ─────────────────────────────────────────────────────
        if _is_test_target(target):
            return "test-writer"

        # ── 2. Docs / markdown / skill files ─────────────────────────────────
        if _is_doc_target(target):
            return "docs-editor"

        # ── 3. Review ─────────────────────────────────────────────────────────
        if "review" in title or "review" in kind:
            return "reviewer"

        # ── 4. Audit ─────────────────────────────────────────────────────────
        if "audit" in title or "audit" in kind:
            return "audit-reader"

        # ── 5. Core code ──────────────────────────────────────────────────────
        if _is_core_code_target(target):
            return "code-implementer"

        # ── 6. Fallback ───────────────────────────────────────────────────────
        return "general-purpose"
    except Exception:
        return "general-purpose"


def profile_tier(role: str) -> str:
    """Return the ``model_tier`` for *role*, or ``"sonnet"`` if unknown.

    Never raises.
    """
    try:
        spec = PROFILES.get(role)
        return spec.model_tier if spec is not None else "sonnet"
    except Exception:
        return "sonnet"


def profile_of(role: str) -> ProfileSpec | None:
    """Safe lookup — returns ``None`` when *role* is not in ``PROFILES``."""
    try:
        return PROFILES.get(role)
    except Exception:
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_field(task: Any, field: str, default: str) -> str:
    """Retrieve a field from an object-or-dict, returning *default* on miss."""
    try:
        if isinstance(task, dict):
            return str(task.get(field, default))
        return str(getattr(task, field, default))
    except Exception:
        return default


def _is_test_target(target: str) -> bool:
    """True when *target* looks like a test file path."""
    if not target:
        return False
    from pathlib import Path

    p = Path(target)
    norm = target.replace("\\", "/")
    # Under tests/ directory
    if norm.startswith("tests/") or "/tests/" in norm:
        return True
    # Filename patterns test_*.py or *_test.py / *_test.ts etc.
    name = p.name
    if name.startswith("test_"):
        return True
    stem = p.stem
    return stem.endswith("_test")


def _is_doc_target(target: str) -> bool:
    """True when *target* is a Markdown file or lives under plugin/skills/ or docs/."""
    if not target:
        return False
    from pathlib import Path

    norm = target.replace("\\", "/")
    if Path(target).suffix.lower() == ".md":
        return True
    if norm.startswith("plugin/skills/") or "/plugin/skills/" in norm:
        return True
    return norm.startswith("docs/") or "/docs/" in norm


def _is_core_code_target(target: str) -> bool:
    """True when *target* is a Python/shell file under renmark/ or bin/."""
    if not target:
        return False
    from pathlib import Path

    norm = target.replace("\\", "/")
    norm_stripped = norm.lstrip("./")
    code_suffixes = {".py", ".pyi", ".sh", ".bash"}
    suffix = Path(target).suffix.lower()
    if suffix not in code_suffixes and suffix != "":
        return False
    core_roots = ("renmark/", "bin/")
    return any(norm_stripped.startswith(root) for root in core_roots)
