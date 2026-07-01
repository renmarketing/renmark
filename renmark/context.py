"""Context taxonomy + dynamic-skill-loading primitives for renmark.

This module names and classifies the *kinds* of context a renmark agent can
hold, and provides the primitives for **dynamic skill loading** — the property
that a skill's metadata is known upfront while its full body is fetched only on
demand.  It is the taxonomy layer beneath the production dispatch packet
(:class:`renmark.dispatch.SubagentInput`); it deliberately does NOT define a
competing packet dataclass.

The four context kinds:

- ``STATIC`` — always-present rule surfaces (``CLAUDE.md`` / ``AGENTS.md``).
  These are in the agent's context by default; nothing loads them.
- ``DYNAMIC`` — skill bodies (``plugin/skills/<name>/SKILL.md``) and the shared
  contract fragments (``plugin/skills/_shared/*.md``).  Their *metadata* is known
  upfront (via :mod:`renmark.skillmeta`); their *bodies* are pulled on demand and
  are NEVER pre-loaded.  This on-demand property is the whole point of dynamic
  skill loading — it is what keeps orchestrator/subagent context lean.
- ``MEMORY`` — durable project memory under ``.renmark/memory/`` that survives
  ``/clear``.
- ``TASK_LOCAL`` — the ephemeral per-subagent dispatch packet, alive only for the
  duration of one task.

Design constraints (mirroring :mod:`renmark.mode` / :mod:`renmark.skillmeta`):
- stdlib-only — NO third-party imports.
- ``from __future__ import annotations``; frozen dataclasses; full type hints.
- Read/classify functions never raise (``classify_path``, ``skill_metadata``,
  ``all_skill_metadata``, ``upfront_kinds_for_skill``).  Body loaders
  (``load_skill_body`` / ``load_fragment``) DO raise ``FileNotFoundError`` when
  the file is absent — a missing on-demand body is a real error, not silent
  state.  The guardrail ``assert_metadata_only`` raises ``ValueError`` by design.
- ``renmark.skillmeta`` and ``renmark.lifecycle`` are imported LAZILY inside the
  functions that need them (mirroring the function-local ``from renmark import
  schemas`` pattern in :mod:`renmark.dispatch`), to keep this module free of any
  import-cycle risk.  ``plugin_root`` is always passed explicitly to the body
  loaders so the module stays pure and testable — it never guesses a path.
"""

from __future__ import annotations

import enum
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "FRAGMENT_NAMES",
    "TAXONOMY",
    "ContextKind",
    "ContextSource",
    "all_skill_metadata",
    "assert_metadata_only",
    "classify_path",
    "fragment_names",
    "fragment_pointer",
    "load_fragment",
    "load_skill_body",
    "skill_metadata",
    "skill_pointer",
    "upfront_kinds_for_skill",
]


class ContextKind(enum.Enum):
    """The four kinds of context a renmark agent can hold.

    See the module docstring for the semantics of each member.
    """

    STATIC = "static"
    DYNAMIC = "dynamic"
    MEMORY = "memory"
    TASK_LOCAL = "task_local"


@dataclass(frozen=True)
class ContextSource:
    """Descriptor for one kind of context source.

    ``kind`` — the :class:`ContextKind` this source describes; in
    :data:`TAXONOMY` it always equals the dict key.
    ``label`` — short human-readable name.
    ``persistence`` — one of ``"always"`` / ``"on-demand"`` / ``"durable"`` /
    ``"ephemeral"``, describing the lifetime of this context in the agent.
    ``load_policy`` — one-line description of when/how this context enters context.
    ``examples`` — representative path patterns for this kind.
    """

    kind: ContextKind
    label: str
    persistence: str  # "always" | "on-demand" | "durable" | "ephemeral"
    load_policy: str
    examples: tuple[str, ...]


# The canonical taxonomy: one entry per ContextKind.  Each ContextSource.kind
# equals its dict key (guarded by a test in Task 4).
TAXONOMY: dict[ContextKind, ContextSource] = {
    ContextKind.STATIC: ContextSource(
        kind=ContextKind.STATIC,
        label="Static rules",
        persistence="always",
        load_policy="Always present in context; never explicitly loaded.",
        examples=("CLAUDE.md", "AGENTS.md"),
    ),
    ContextKind.DYNAMIC: ContextSource(
        kind=ContextKind.DYNAMIC,
        label="Dynamic skill bodies + shared fragments",
        persistence="on-demand",
        load_policy=(
            "Metadata known upfront; SKILL.md / _shared/*.md bodies fetched only "
            "on demand — bodies are never pre-loaded."
        ),
        examples=(
            "plugin/skills/<name>/SKILL.md",
            "plugin/skills/_shared/<fragment>.md",
        ),
    ),
    ContextKind.MEMORY: ContextSource(
        kind=ContextKind.MEMORY,
        label="Durable project memory",
        persistence="durable",
        load_policy="Persisted memory that survives /clear; loaded when relevant.",
        examples=(
            ".renmark/memory/INDEX.md",
            ".renmark/memory/project.md",
            ".renmark/memory/routing.md",
        ),
    ),
    ContextKind.TASK_LOCAL: ContextSource(
        kind=ContextKind.TASK_LOCAL,
        label="Per-subagent dispatch packet",
        persistence="ephemeral",
        load_policy=(
            "The bounded packet handed to one subagent; alive only for that task."
        ),
        examples=("SubagentInput (renmark.dispatch)",),
    ),
}


# The ``_shared`` contract fragment stems (basename without the ``.md``), the
# single source of truth for what lives under ``plugin/skills/_shared/``.
FRAGMENT_NAMES: tuple[str, ...] = (
    "reasoning-contract",
    "next-steps",
    "handoff-menu",
    "scope-contract",
    "headless-contract",
    "prd-alignment",
    "reuse-check",
    "context-taxonomy",
)


def classify_path(path: str | os.PathLike[str]) -> ContextKind:
    """Classify *path* into a :class:`ContextKind` by pure heuristic.

    Rules (first match wins):
    - basename ``CLAUDE.md`` / ``AGENTS.md`` → ``STATIC``
    - under ``plugin/skills/`` ending in ``SKILL.md`` → ``DYNAMIC``
    - under ``plugin/skills/_shared/`` ending in ``.md`` → ``DYNAMIC``
    - path containing ``.renmark/memory/`` → ``MEMORY``
    - everything else (including ``""``) → ``TASK_LOCAL``

    Never raises — a non-path-like or empty input degrades to ``TASK_LOCAL``.
    """
    try:
        s = os.fspath(path)
    except TypeError:
        return ContextKind.TASK_LOCAL
    # Normalise separators so Windows-style paths classify identically.
    norm = s.replace("\\", "/")
    base = norm.rsplit("/", 1)[-1]

    if base in ("CLAUDE.md", "AGENTS.md"):
        return ContextKind.STATIC
    if "plugin/skills/_shared/" in norm and norm.endswith(".md"):
        return ContextKind.DYNAMIC
    if "plugin/skills/" in norm and base == "SKILL.md":
        return ContextKind.DYNAMIC
    if ".renmark/memory/" in norm:
        return ContextKind.MEMORY
    return ContextKind.TASK_LOCAL


def skill_metadata(name: str) -> dict[str, object] | None:
    """Return a lightweight metadata dict for skill *name*, or ``None``.

    Reuses the :data:`renmark.skillmeta.SKILLS` registry — it NEVER reads a
    SKILL.md body.  The returned dict is::

        {"name", "domain", "next_steps_class", "cites", "has_handoff",
         "disable_model_invocation"}

    Returns ``None`` for an unknown (or non-string) skill.  Never raises.
    """
    from renmark import skillmeta

    meta = skillmeta.get(name)
    if meta is None:
        return None
    return {
        "name": name,
        "domain": meta.domain,
        "next_steps_class": meta.next_steps_class,
        "cites": meta.cites,
        "has_handoff": meta.has_handoff,
        "disable_model_invocation": meta.disable_model_invocation,
    }


def all_skill_metadata() -> dict[str, dict[str, object]]:
    """Return :func:`skill_metadata` for every registered skill.

    Keyed by skill name.  Never reads a SKILL.md body; never raises.
    """
    from renmark import skillmeta

    out: dict[str, dict[str, object]] = {}
    for name in skillmeta.SKILLS:
        md = skill_metadata(name)
        if md is not None:
            out[name] = md
    return out


def fragment_names() -> tuple[str, ...]:
    """Return the ``_shared`` fragment stems (from :data:`FRAGMENT_NAMES`)."""
    return FRAGMENT_NAMES


def skill_pointer(name: str) -> str:
    """Return the on-demand *pointer* to a skill body (NOT the body itself).

    The literal ``${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`` — the reference
    a dispatch packet carries so the subagent can fetch the body on demand.
    """
    return f"${{CLAUDE_PLUGIN_ROOT}}/skills/{name}/SKILL.md"


def fragment_pointer(name: str) -> str:
    """Return the on-demand *pointer* to a ``_shared`` fragment (NOT the body)."""
    return f"${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/{name}.md"


def load_skill_body(plugin_root: str | os.PathLike[str], name: str) -> str:
    """Read and return the body of ``<plugin_root>/skills/<name>/SKILL.md``.

    This is the on-demand load — call it only when the body is actually needed.
    Raises :class:`FileNotFoundError` if the SKILL.md does not exist.
    """
    return (Path(plugin_root) / "skills" / name / "SKILL.md").read_text(
        encoding="utf-8"
    )


def load_fragment(plugin_root: str | os.PathLike[str], name: str) -> str:
    """Read and return ``<plugin_root>/skills/_shared/<name>.md``.

    On-demand load; raises :class:`FileNotFoundError` if the fragment is absent.
    """
    return (Path(plugin_root) / "skills" / "_shared" / f"{name}.md").read_text(
        encoding="utf-8"
    )


def upfront_kinds_for_skill(skill: str) -> frozenset[ContextKind]:
    """Return the context kinds pre-loaded upfront for *skill*.

    Always ``frozenset({ContextKind.STATIC, ContextKind.MEMORY})``.  ``DYNAMIC``
    skill bodies and the ``TASK_LOCAL`` dispatch packet are deliberately EXCLUDED
    — dynamic bodies are never pre-loaded (that is the entire point of dynamic
    skill loading), and the task packet is constructed per-dispatch.

    The preamble tier is resolved defensively via
    :data:`renmark.lifecycle.PREAMBLE_TIER_BY_SKILL` (unknown skill → ``"full"``)
    purely for illustration — for this MVP the returned set is STATIC+MEMORY
    regardless of tier.  Never raises.
    """
    try:
        from renmark import lifecycle

        # Defensive/illustrative tier lookup: unknown skill degrades to "full".
        _tier = lifecycle.PREAMBLE_TIER_BY_SKILL.get(skill, "full")
    except Exception:
        _tier = "full"
    del _tier  # tier does not change the returned set in this MVP.
    return frozenset({ContextKind.STATIC, ContextKind.MEMORY})


def assert_metadata_only(skills: Iterable[str]) -> None:
    """Assert every entry in *skills* is a bare skill-name-shaped reference.

    This is the dynamic-loading guardrail: a dispatch packet may carry required
    *skill names* (metadata), never inlined full skill *bodies*.  Raises
    :class:`ValueError` if any entry looks like a body rather than a name —
    heuristically, if it contains a newline, exceeds ~80 characters, or contains
    a triple-backtick fence.
    """
    for item in skills:
        text = str(item)
        if "\n" in text or len(text) > 80 or "```" in text:
            preview = text[:40].replace("\n", "\\n")
            raise ValueError(
                "assert_metadata_only: expected a bare skill-name reference, got "
                f"what looks like a full body ({preview!r}...): dispatch packets "
                "carry skill-name metadata only, never inlined skill bodies."
            )
