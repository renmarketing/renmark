"""Escalation-only LLM-as-judge tier for behavioral verification.

The judge answers a single, expensive question: *given the skill's contract,
does the with-skill behavior differ from the baseline in the way the contract
promises?* It is a semantic comparator, not a diff — it reads the baseline
output, the golden (expected) output, the actual with-skill output, and the
skill's stated contract, and returns a structured :class:`Verdict`.

This tier is **escalation-only** and costs money on every call
(:data:`JUDGE_EST_COST_USD`), so it is never invoked from import side effects —
it runs only when :func:`judge_behavior` is called explicitly.

Like the rest of the renmark runtime, this Python process cannot itself call a
Claude model (that is the host's job — see ``renmark.providers.claude_agent``).
So the live model call is routed through an injectable ``subagent_runner``
callable: a function that takes a fully-composed prompt string and returns the
model's raw response string. The default runner raises :class:`JudgeUnavailable`
(the host must inject a real one); tests inject a mock. Whatever the runner
returns is parsed defensively — on any parse failure, timeout, or runner error
the verdict is marked ``validation_status="unvalidated"`` and never silently
promoted to a ``pass``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Approximate cost of a single judge invocation (frontier-tier model, one
# comparison turn). Exposed so callers can budget/gate before escalating.
JUDGE_EST_COST_USD: float = 0.15

Outcome = Literal["pass", "fail"]
Confidence = Literal["low", "medium", "high"]
ValidationStatus = Literal["validated", "unvalidated", "failed"]

_VALID_OUTCOMES: frozenset[str] = frozenset({"pass", "fail"})
_VALID_CONFIDENCE: frozenset[str] = frozenset({"low", "medium", "high"})

# The callable contract for the live model call. Takes a composed prompt
# string, returns the model's raw response string. This is the sole injection
# point for the real executor (a host Agent call) or a test mock.
SubagentRunner = Callable[[str], str]


class JudgeUnavailable(RuntimeError):
    """Raised by the default runner because this Python process cannot call a
    Claude model directly. The host must inject a real ``subagent_runner``.

    Callers of :func:`judge_behavior` never see this: it is caught and mapped
    to a ``validation_status="unvalidated"`` verdict, so an unwired judge is
    explicitly unvalidated rather than silently passing.
    """


@dataclass(frozen=True)
class Verdict:
    """The structured semantic verdict returned by :func:`judge_behavior`.

    - ``outcome``: ``"pass"`` if the with-skill behavior honors the contract
      relative to the baseline, ``"fail"`` otherwise. On any parse/runner
      failure the outcome defaults to ``"fail"`` (never a silent ``pass``).
    - ``confidence``: the judge's self-reported confidence in the outcome.
    - ``validation_status``: ``"validated"`` when a live model response was
      parsed successfully; ``"unvalidated"`` on parse failure, timeout, or an
      unavailable/failed runner; ``"failed"`` reserved for hard schema errors.
    - ``rationale``: a short human-readable explanation.
    """

    outcome: Outcome
    confidence: Confidence
    validation_status: ValidationStatus
    rationale: str


def _default_subagent_runner(prompt: str) -> str:
    """Default runner — refuses, because Python cannot call Claude here.

    The host (orchestrate skill) injects a real runner that issues an Agent
    tool call; tests inject a mock. This default deliberately raises so the
    verdict is marked unvalidated rather than silently passing.
    """
    raise JudgeUnavailable(
        "no subagent_runner injected: the judge's live model call must be routed "
        "through the host (renmark.providers.claude_agent) or a test mock"
    )


def _build_prompt(
    *,
    skill: str,
    prompt: str,
    baseline: str,
    golden: str,
    actual: str,
    contract: str,
) -> str:
    """Compose the judge prompt comparing with-skill behavior to the baseline.

    The judge is asked to return ONLY a JSON object so the response can be
    parsed defensively.
    """
    return (
        "You are an impartial behavioral judge. Compare the WITH-SKILL output "
        "against the BASELINE, given the skill's CONTRACT and the GOLDEN "
        "(expected) output. Decide whether the with-skill behavior honors the "
        "contract.\n\n"
        f"SKILL: {skill}\n\n"
        f"SKILL CONTRACT (what the skill promises to change):\n{contract}\n\n"
        f"PROMPT (the shared input given to both):\n{prompt}\n\n"
        f"BASELINE OUTPUT (skill disabled):\n{baseline}\n\n"
        f"GOLDEN / EXPECTED OUTPUT:\n{golden}\n\n"
        f"ACTUAL WITH-SKILL OUTPUT:\n{actual}\n\n"
        "Respond with ONLY a JSON object, no prose before or after, of the form:\n"
        '{"outcome": "pass"|"fail", "confidence": "low"|"medium"|"high", '
        '"rationale": "<one or two sentences>"}\n'
        "Use \"pass\" only if the with-skill output honors the contract relative "
        "to the baseline. When uncertain, prefer \"fail\" with low confidence."
    )


def _parse_response(response: str) -> Verdict:
    """Parse the model response into a Verdict, defensively.

    Accepts a JSON object (optionally wrapped in ```json fences or surrounded
    by stray prose — the first balanced ``{...}`` span is extracted). On any
    failure returns an unvalidated, ``fail`` verdict rather than raising.
    """
    text = response.strip() if isinstance(response, str) else ""
    if not text:
        return Verdict(
            outcome="fail",
            confidence="low",
            validation_status="unvalidated",
            rationale="empty model response",
        )

    payload = _extract_json_object(text)
    if payload is None:
        return Verdict(
            outcome="fail",
            confidence="low",
            validation_status="unvalidated",
            rationale="could not parse a JSON object from the model response",
        )

    raw_outcome = str(payload.get("outcome", "")).strip().lower()
    raw_conf = str(payload.get("confidence", "")).strip().lower()
    rationale = str(payload.get("rationale", "")).strip() or "no rationale provided"

    if raw_outcome not in _VALID_OUTCOMES:
        # A response we cannot trust the verdict of is unvalidated, not a pass.
        return Verdict(
            outcome="fail",
            confidence="low",
            validation_status="unvalidated",
            rationale=f"unrecognized outcome {raw_outcome!r} in model response",
        )

    confidence: Confidence = raw_conf if raw_conf in _VALID_CONFIDENCE else "low"  # type: ignore[assignment]
    outcome: Outcome = raw_outcome  # type: ignore[assignment]

    return Verdict(
        outcome=outcome,
        confidence=confidence,
        validation_status="validated",
        rationale=rationale,
    )


def _extract_json_object(text: str) -> dict[str, object] | None:
    """Best-effort extraction of the first top-level JSON object from text.

    Handles bare JSON, ```json fenced blocks, and objects surrounded by prose.
    Returns None if nothing parseable is found.
    """
    # Fast path: the whole string is a JSON object.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    # Strip a leading ```json / ``` fence if present.
    fenced = text
    if "```" in fenced:
        parts = fenced.split("```")
        for part in parts:
            candidate = part
            if candidate.lstrip().lower().startswith("json"):
                candidate = candidate.lstrip()[len("json"):]
            candidate = candidate.strip()
            if candidate.startswith("{"):
                fenced = candidate
                break

    # Scan for the first balanced {...} span.
    start = fenced.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(fenced)):
        ch = fenced[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                span = fenced[start : i + 1]
                try:
                    obj = json.loads(span)
                except (json.JSONDecodeError, ValueError):
                    return None
                return obj if isinstance(obj, dict) else None
    return None


def judge_behavior(
    repo: Path,
    *,
    skill: str,
    prompt: str,
    baseline: str,
    golden: str,
    actual: str,
    contract: str,
    subagent_runner: SubagentRunner | None = None,
) -> Verdict:
    """Semantically compare with-skill behavior against the baseline.

    Escalation-only: this makes one live frontier-model call (approx
    :data:`JUDGE_EST_COST_USD`) via ``subagent_runner``, which defaults to the
    real (host-injected) runner. Tests inject a mock. The call is fenced so
    that any runner error, timeout, or unparseable response yields a
    ``validation_status="unvalidated"`` verdict — never a silent ``pass``.

    Parameters
    ----------
    repo:
        The project root (reserved for future per-repo judge config /
        logging; the current implementation does not read from disk).
    skill:
        The skill under test, e.g. ``"renmark:brainstorm"``.
    prompt:
        The shared input given to both the baseline and with-skill runs.
    baseline:
        The output produced with the skill disabled.
    golden:
        The expected/reference output.
    actual:
        The output produced with the skill enabled.
    contract:
        The skill's stated behavioral contract (what it promises to change).
    subagent_runner:
        Callable taking the composed prompt string and returning the model's
        raw response string. Defaults to the host runner (which raises if not
        wired), mapped to an unvalidated verdict.
    """
    runner: SubagentRunner = subagent_runner or _default_subagent_runner
    judge_prompt = _build_prompt(
        skill=skill,
        prompt=prompt,
        baseline=baseline,
        golden=golden,
        actual=actual,
        contract=contract,
    )

    try:
        response = runner(judge_prompt)
    except JudgeUnavailable as exc:
        return Verdict(
            outcome="fail",
            confidence="low",
            validation_status="unvalidated",
            rationale=f"judge runner unavailable: {exc}",
        )
    except Exception as exc:  # any runner failure is unvalidated, not a pass
        return Verdict(
            outcome="fail",
            confidence="low",
            validation_status="unvalidated",
            rationale=f"judge runner error: {type(exc).__name__}: {exc}",
        )

    return _parse_response(response)
