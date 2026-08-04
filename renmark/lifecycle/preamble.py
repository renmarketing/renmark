"""Skill preamble, context checkpoints, and additive preamble notes.

Split out of ``renmark/lifecycle/stage.py`` per
`.renmark/rethink/renmark-architecture/target-blueprint.md` §1.2. Behavior is
unchanged -- these are the same functions, relocated verbatim.

``skill_preamble()`` is the single-call Step-0 helper every SKILL.md invokes;
the ``_with_*_note`` helpers are its additive, degrade-gracefully decorators.
"""

from __future__ import annotations

from pathlib import Path

from ..hosts import HostKind, capabilities_for
from .stage import (
    _AGENCY_AWARE_SKILLS,
    _AGENCY_HINT_MARKER,
    _CONTEXT_BYPASS_SKILLS,
    _MODE_DEFAULT_SKILLS,
    _MODE_DIRECTIVE,
    _MODE_PROMPT_SKILLS,
    PREAMBLE_TIER_BY_SKILL,
    SYNTHESIS_SKILLS,
    _choose_mode_hint,
    _lifecycle_host,
    domain_of,
)


def preamble_tier(skill: str) -> str:
    """Return the preamble tier for a skill ('minimal' | 'standard' | 'full').

    Unknown skills default to 'full'. Never raises.
    """
    return PREAMBLE_TIER_BY_SKILL.get(skill, "full")


def persist_compact_checkpoint(
    repo: Path | str,
    skill: str,
    reason: str,
    host: str | HostKind | None = None,
) -> None:
    """Write a compact checkpoint to .renmark/state/compact_checkpoint.json.

    Called by skill_preamble before emitting a context gate message so the
    user can resume after a host-supported context reset. Never raises. Hosts
    without a manual resume command persist ``resume_cmd: null``.
    """
    import json as _json

    from .. import state as _state  # lazy — avoid circular import at module load

    try:
        host_capabilities = capabilities_for(_lifecycle_host(host))
        state_path = _state.state_dir(repo) / "compact_checkpoint.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            _json.dumps(
                {
                    "skill": skill,
                    "reason": reason,
                    "resume_cmd": (
                        "/renmark:resume"
                        if host_capabilities.supports_resume
                        else None
                    ),
                    "timestamp": _state.now_iso(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def milestone_context_checkpoint(
    repo: Path | str,
    *,
    skill: str,
    estimated_tokens: int | None = None,
    host: str | HostKind | None = None,
) -> str | None:
    """At an approved Agency milestone boundary, recommend a compact checkpoint
    ONLY when a real context-size signal has been provided and it has reached
    the configured threshold. Never fires on every milestone — only when
    `estimated_tokens` is given and crosses `config.compact_gate_tokens(repo)`.
    No SDK/launcher exists in this codebase to send /compact programmatically
    (see the ORCHESTRATION-BASELINE-2026-08 audit) — this returns a manual
    instruction string, never fabricated automation. Never raises.
    """
    from .. import config as _config  # lazy — avoid circular import at module load

    try:
        if estimated_tokens is None:
            return None

        threshold = _config.compact_gate_tokens(repo)
        if threshold == 0 or estimated_tokens < threshold:
            return None

        persist_compact_checkpoint(repo, skill, reason="milestone-boundary", host=host)
        return (
            f"Context at milestone boundary: ~{estimated_tokens} tokens (threshold {threshold}). "
            "Checkpoint written to .renmark/state/compact_checkpoint.json. "
            "Run: /compact — then run: /renmark:resume"
        )
    except Exception:
        return None


def skill_preamble(
    repo: Path | str,
    skill: str,
    host: str | HostKind | None = None,
) -> str | None:
    """Single-call Step-0 boilerplate for every SKILL.md.

    Performs the calls every skill used to inline by hand, gated by tier:
        - ALL tiers: record invocation (load-bearing cross-domain detection for
          the NEXT skill — runs unconditionally so minimal-tier skills still
          register their domain in last-skill state).
        - minimal: returns None immediately; no budget check, no fragments.
        - standard: cross-domain/compact hint only; no fable synthesis hint.
        - full (default): cross-domain/compact hint + fable synthesis hint.

    Cross-domain detection for the CURRENT skill requires context_budget_check
    to read last-skill state BEFORE record_skill_invocation overwrites it, so
    for standard/full tier the budget check runs first. record_skill_invocation
    is then called unconditionally to keep the state file current for the next
    skill — this is the load-bearing ordering invariant.

    Returns the hint string the skill should surface to the user, or None when
    no hint is needed. Domain is resolved from `DOMAIN_BY_SKILL` — callers do
    not need to pass it, so the per-skill prose can't drift. Host resolution is
    explicit argument → ``RENMARK_HOST`` → backward-compatible Claude default.
    Hosts that do not support manual clear/resume commands record the domain
    transition and continue without presenting an unusable gate.
    """
    # Imported lazily to avoid a state ↔ lifecycle circular import at module load.
    from .. import state as _state

    domain = domain_of(skill)
    tier = preamble_tier(skill)
    host_capabilities = capabilities_for(_lifecycle_host(host))

    if tier == "minimal":
        # INVARIANT: record_skill_invocation runs for ALL tiers so that the next
        # skill can detect cross-domain transitions even when this one is minimal.
        _state.record_skill_invocation(repo, skill, domain)
        return _with_agency_note(repo, skill, _with_headless_note(repo, None))

    # For standard/full: budget check MUST read last-skill state before
    # record_skill_invocation overwrites it — ordering is load-bearing.
    # Read last-skill state once here so prev_domain is available for the gate message.
    last = _state.last_skill_invocation(repo)
    verdict = _state.context_budget_check(repo, skill, domain)

    fragments: list[str] = []
    if verdict == "clear" and skill not in _CONTEXT_BYPASS_SKILLS:
        prev_domain = last.get("domain", "?") if last else "?"
        if not host_capabilities.supports_clear:
            # Codex and unknown hosts have no user-runnable /clear + resume
            # pair. Treat the transition as observed, record it below, and
            # continue without manufacturing an unsupported command gate.
            verdict = None
        else:
            persist_compact_checkpoint(repo, skill, reason="clear", host=host)
        # Headless: skip the interactive gate so non-interactive runs are not blocked.
        from .. import config as _config
        if verdict == "clear" and _config.is_headless(repo):
            # Record now — headless runs proceed automatically past the gate.
            _state.record_skill_invocation(repo, skill, domain)
            return _with_agency_note(
                repo, skill,
                _with_mode_note(
                    repo, skill,
                    _with_headless_note(
                        repo,
                        f"context: cross-domain transition into `{domain}` "
                        f"(prev: `{prev_domain}`) "
                        "\u2014 headless mode: skipping interactive gate, proceeding automatically",
                    ),
                ),
            )
        # Interactive: return the gate prefix WITHOUT recording the invocation.
        # Not recording keeps the gate live on re-entry — the user must choose
        # explicitly before the skill proceeds.
        if verdict == "clear":
            return (
                f"CONTEXT_GATE_CLEAR: cross-domain transition detected "
                f"(prev: `{prev_domain}` \u2192 `{domain}`).\n"
                "State persisted to .renmark/state/compact_checkpoint.json.\n"
                "Present the user with AskUserQuestion before proceeding with this skill:\n"
                '  header: "Context hygiene"\n'
                '  question: "Domain change detected. Run /clear to start fresh '
                '(memory survives), or continue with accumulated context?"\n'
                "  options:\n"
                "    1. Stop here \u2014 I will run /clear then /renmark:resume (Recommended)\n"
                "    2. Continue in same context (this step only)\n"
                "    3. Queue this as next task after current work finishes\n"
                "    4. Cancel"
            )

    # Record the invocation here — after the gate, so a gated-then-stopped skill
    # does not corrupt the domain state for subsequent cross-domain detection.
    _state.record_skill_invocation(repo, skill, domain)

    if verdict == "clear" and host_capabilities.supports_clear:
        # Must be a bypass skill (finish/approve/resume) — advisory only.
        fragments.append(
            f"context: cross-domain transition into `{domain}` — consider `/clear` "
            "before continuing (`.renmark/memory/` survives clears)"
        )
    elif verdict == "compact" and host_capabilities.supports_compact:
        fragments.append("context: approaching budget — consider `/compact` before continuing")

    if tier == "full" and skill in SYNTHESIS_SKILLS:
        # Imported lazily to keep capability resolution off the module-load path.
        from .. import capabilities as _capabilities

        if _capabilities.top_tier(Path(repo)) == "fable":
            fragments.append(
                "declared top tier: fable — for best ideation/strategy results "
                "run this session on Fable 5 (/model fable)"
            )

    base = " | ".join(fragments) if fragments else None
    return _with_agency_note(repo, skill, _with_mode_note(repo, skill, _with_headless_note(repo, base)))


def _with_mode_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
    """ADDITIVE: append the operating-mode directive to ``hint``.

    Runs strictly AFTER the existing tier logic and the headless note — never
    reorders the record-before-check invariant. DEGRADES GRACEFULLY: any
    exception in mode resolution falls back to ``hint`` unchanged, so mode is a
    pure enhancement and never a hard dependency of the preamble.

    - Mode SET  → append the Agency/Orchestrator directive line.
    - Mode UNSET + entry-point skill → append a choose-mode instruction.
    - Mode UNSET + non-entry skill → no mode line (returns ``hint`` unchanged).
    """
    try:
        from .. import mode as _mode

        current = _mode.read_mode(repo)
        if current is None and skill in _MODE_DEFAULT_SKILLS:
            resolved = _mode.default_delivery_state_for_skill(skill)
            _mode.write_delivery_state(repo, resolved)
            current = resolved.delivery_mode
        if current is not None:
            line = _MODE_DIRECTIVE.get(current)
            if line is None:  # unrecognised (read_mode shouldn't yield this)
                return hint
        elif skill in _MODE_PROMPT_SKILLS:
            line = _choose_mode_hint(skill)
        else:
            return hint
    except Exception:
        return hint
    return line if hint is None else f"{hint} | {line}"


def _with_agency_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
    """ADDITIVE: append an Agency Mode hint to ``hint`` when agency is active.

    Only surfaces the hint for AGENCY-AWARE pipeline skills (the spine —
    start/prd/roadmap/finish/resume — plus feature/plan/orchestrate/verify/
    codereview) — all other skills are passed through unchanged regardless of
    agency state.

    When agency is INACTIVE the return value is byte-identical to ``hint``
    (the inactive-path guarantee). DEGRADES GRACEFULLY: any exception in
    agency/context resolution falls back to ``hint`` unchanged, so agency is
    a pure enhancement and never a hard dependency of the preamble.

    Follows the same additive pattern as :func:`_with_mode_note` and
    :func:`_with_headless_note`.
    """
    if skill not in _AGENCY_AWARE_SKILLS:
        return hint
    try:
        from .. import agency as _agency
        from .. import context as _context
        from .. import mode as _mode

        # Canonical delivery.json wins over the legacy agency overlay. This
        # prevents split-brain hints after an explicit Orchestrator choice.
        if _mode.read_mode(repo) == "orchestrator":
            return hint
        if not _agency.is_active(repo):
            return hint
        state = _agency.read_agency(repo)
        pointer = _context.fragment_pointer("agency-delivery")
        line = (
            f"{_AGENCY_HINT_MARKER} — phase {state.current_phase}, "
            f"milestone {state.current_milestone}. Contract: {pointer}"
        )
    except Exception:
        return hint
    return line if hint is None else f"{hint} | {line}"


def _with_headless_note(repo: Path | str, hint: str | None) -> str | None:
    """ADDITIVE: append a headless-mode note to ``hint`` when headless is active.

    Runs strictly AFTER the existing tier logic — never reorders the
    record-before-check invariant above. When headless is off this is a
    pass-through (returns ``hint`` unchanged, including None). When on it
    appends one line; if ``hint`` was None the note becomes the whole return.
    Never raises — config helpers are themselves no-raise.
    """
    from .. import config as _config

    try:
        if not _config.is_headless(repo):
            return hint
        note = f"headless mode active (source: {_config.headless_source(repo)})"
    except Exception:
        return hint
    return note if hint is None else f"{hint} | {note}"
