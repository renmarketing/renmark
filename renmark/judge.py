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

Three-state outcome vocabulary
------------------------------
:data:`Outcome` is ``"pass" | "fail" | "uncertain"``. The distinction matters:
``"fail"`` is a *decision* — the judge read the evidence and concluded the
contract was not honored — while ``"uncertain"`` means *we do not know*. Every
path where the judge's answer could not be trusted (empty response, unparseable
JSON, unrecognized ``outcome``/``confidence`` token, missing rationale, an
unavailable runner, or any runner exception) now yields ``"uncertain"``, not a
counterfeit ``"fail"``. Only a fully parsed response whose recognized outcome is
literally ``"fail"`` produces a validated ``"fail"``. ``validation_status`` is
orthogonal and unchanged: those same untrusted paths stay ``"unvalidated"``.

Redaction contract
------------------
The judge must not be told what the Worker thought of its own output. Before any
string composition, dict-shaped ``golden``/``actual`` payloads pass through
:func:`_redact_worker_fields`, which strips Worker-authored self-assessment,
confidence, identity, and preferred-verdict keys (see
:data:`_WORKER_REDACTED_KEYS`). This is a *data-assembly-time* filter, not a
post-hoc scrub of the rendered prompt — a rendered-string filter cannot tell a
Worker's self-assessment from legitimate output text. Plain ``str`` payloads
pass through unchanged: the caller owns their provenance.

Order randomization
-------------------
Positional bias is a known LLM-judge failure mode. The BASELINE-vs-ACTUAL
comparison — the only pairwise call path in this module — accepts a keyword-only
``swap_order`` that flips which of the two is presented first. Both remain
explicitly labeled; only position changes. :class:`Verdict` deliberately does
NOT gain a ``swapped`` field (its four fields are frozen for compatibility);
callers that randomize record the choice alongside the verdict via
:func:`resolve_swap_order` and :class:`JudgeCallRecord`.

Non-goal
--------
This module never writes to ``ledger.InspectionReport.verdict``. A judge result
is *reference-only evidence* — it is attached, via :class:`JudgeEvidenceRef`, to
an inspection report that an independent Inspector authored, and it never
overrides that Inspector's verdict.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Approximate cost of a single judge invocation (frontier-tier model, one
# comparison turn). Exposed so callers can budget/gate before escalating.
JUDGE_EST_COST_USD: float = 0.15

Outcome = Literal["pass", "fail", "uncertain"]
Confidence = Literal["low", "medium", "high"]
ValidationStatus = Literal["validated", "unvalidated", "failed"]

_VALID_OUTCOMES: frozenset[str] = frozenset({"pass", "fail", "uncertain"})
_VALID_CONFIDENCE: frozenset[str] = frozenset({"low", "medium", "high"})

# Worker-authored keys that must never reach the judge: they let the Worker
# lobby for its own verdict. Matched case-insensitively at every dict depth.
_WORKER_REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "self_assessment",
        "worker_confidence",
        "dispatch_identity",
        "preferred_verdict",
        "claimed_status",
    }
)

# Payload types accepted for ``golden``/``actual``: a pre-rendered string (used
# as-is) or a structured dict (redacted, then JSON-serialized).
JudgePayload = str | dict[str, object]

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
      relative to the baseline; ``"fail"`` only when the judge actually decided
      it does not; ``"uncertain"`` when the answer could not be trusted (parse
      failure, unrecognized token, missing rationale, runner error). No path
      ever yields a silent ``pass``.
    - ``confidence``: the judge's self-reported confidence in the outcome.
    - ``validation_status``: ``"validated"`` when a live model response was
      parsed successfully; ``"unvalidated"`` on parse failure, timeout, or an
      unavailable/failed runner; ``"failed"`` reserved for hard schema errors.
    - ``rationale``: a short human-readable explanation.

    These four fields are frozen for backward compatibility. Anything a caller
    wants to record *about the call* (such as whether presentation order was
    swapped) belongs in :class:`JudgeCallRecord`, not here, and never smuggled
    into ``rationale``.
    """

    outcome: Outcome
    confidence: Confidence
    validation_status: ValidationStatus
    rationale: str


@dataclass(frozen=True)
class JudgeCallRecord:
    """What a caller records *about* one judge call, beside the verdict itself.

    :class:`Verdict` intentionally does not carry ``swapped``. A caller that
    randomizes presentation order (see :func:`resolve_swap_order`) records the
    choice here so a later analysis can detect positional bias, without
    widening ``Verdict`` or polluting ``Verdict.rationale``.
    """

    swapped: bool
    outcome: Outcome
    confidence: Confidence


@dataclass(frozen=True)
class JudgeEvidenceRef:
    """A judge verdict as *reference-only evidence* attached to an inspection.

    This is the type ``ledger.InspectionReport.judge_evidence`` points at. It is
    deliberately defined here, not in ``ledger``: the ledger depends on the
    judge's vocabulary, never the reverse, and this module must never write to
    ``InspectionReport.verdict``. A judge is a second opinion — an attachment to
    an independent Inspector's verdict, never an override of it.

    ``subject_ref`` identifies what was judged (a task id, artifact path, or
    other stable pointer). ``swapped`` records whether BASELINE/ACTUAL order was
    flipped for this call, so positional bias stays auditable.
    """

    subject_ref: str
    outcome: Outcome
    confidence: Confidence
    validation_status: ValidationStatus
    rationale: str
    swapped: bool = False

    @classmethod
    def from_verdict(
        cls, subject_ref: str, verdict: Verdict, *, swapped: bool = False
    ) -> JudgeEvidenceRef:
        """Build an evidence ref from a :class:`Verdict` plus its call context.

        ``swapped`` is not recoverable from the verdict (by design), so the
        caller that chose the order supplies it.
        """
        return cls(
            subject_ref=subject_ref,
            outcome=verdict.outcome,
            confidence=verdict.confidence,
            validation_status=verdict.validation_status,
            rationale=verdict.rationale,
            swapped=swapped,
        )


def resolve_swap_order(seed: object | None = None) -> bool:
    """Decide whether to swap BASELINE/ACTUAL presentation order for one call.

    With a *seed*, the choice is deterministic and stable across processes (a
    SHA-256 of the seed's ``repr``, not Python's salted ``hash``), so a run can
    be replayed exactly. With ``seed=None`` the choice is drawn fresh from the
    OS entropy pool.

    The caller decides, records (see :class:`JudgeCallRecord`), and then passes
    the result as ``judge_behavior(..., swap_order=...)`` — this helper never
    calls the judge itself.
    """
    if seed is None:
        return hashlib.sha256(_os_urandom(16)).digest()[0] % 2 == 1
    digest = hashlib.sha256(repr(seed).encode("utf-8")).digest()
    return digest[0] % 2 == 1


def _os_urandom(n: int) -> bytes:
    """Indirection over ``os.urandom`` so tests can patch entropy deterministically."""
    import os

    return os.urandom(n)


def _redact_worker_fields(data: dict[str, object]) -> dict[str, object]:
    """Strip Worker-authored self-assessment keys from a payload, recursively.

    Removes every key in :data:`_WORKER_REDACTED_KEYS` (case-insensitive) at any
    nesting depth, including inside lists of dicts. Called at data-assembly time,
    before the prompt string is composed — a filter over the rendered prompt
    could not distinguish a Worker's self-assessment from legitimate output text.

    Returns a new dict; the input is never mutated.
    """
    return _redact_value(data)  # type: ignore[return-value]


def _redact_value(value: object) -> object:
    """Recursive worker of :func:`_redact_worker_fields` over dicts/lists/scalars."""
    if isinstance(value, dict):
        return {
            key: _redact_value(inner)
            for key, inner in value.items()
            if str(key).strip().lower() not in _WORKER_REDACTED_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


def _render_payload(value: JudgePayload) -> str:
    """Render a judge payload for prompt inclusion, redacting dict payloads.

    ``str`` passes through unchanged (the caller owns its provenance); a dict is
    redacted via :func:`_redact_worker_fields` and then ``json.dumps``-ed with
    sorted keys for a stable, diffable prompt.
    """
    if isinstance(value, dict):
        return json.dumps(_redact_worker_fields(value), indent=2, sort_keys=True, default=str)
    return value


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
    golden: JudgePayload,
    actual: JudgePayload,
    contract: str,
    swap_order: bool = False,
) -> str:
    """Compose the judge prompt comparing with-skill behavior to the baseline.

    The judge is asked to return ONLY a JSON object so the response can be
    parsed defensively.

    ``golden``/``actual`` accept a pre-rendered ``str`` or a dict; dicts are
    redacted (:func:`_redact_worker_fields`) and JSON-serialized here, at
    data-assembly time, so no Worker self-assessment ever reaches the model.

    ``swap_order=True`` presents ACTUAL before BASELINE instead of the reverse.
    Both blocks keep their explicit labels — only position changes — so the
    caller can average out the judge's positional bias across calls.
    """
    golden_text = _render_payload(golden)
    actual_text = _render_payload(actual)

    baseline_block = f"BASELINE OUTPUT (skill disabled):\n{baseline}\n\n"
    actual_block = f"ACTUAL WITH-SKILL OUTPUT:\n{actual_text}\n\n"
    first, second = (
        (actual_block, baseline_block) if swap_order else (baseline_block, actual_block)
    )

    return (
        "You are an impartial behavioral judge. Compare the WITH-SKILL output "
        "against the BASELINE, given the skill's CONTRACT and the GOLDEN "
        "(expected) output. Decide whether the with-skill behavior honors the "
        "contract.\n\n"
        f"SKILL: {skill}\n\n"
        f"SKILL CONTRACT (what the skill promises to change):\n{contract}\n\n"
        f"PROMPT (the shared input given to both):\n{prompt}\n\n"
        f"{first}"
        f"GOLDEN / EXPECTED OUTPUT:\n{golden_text}\n\n"
        f"{second}"
        "Respond with ONLY a JSON object, no prose before or after, of the form:\n"
        '{"outcome": "pass"|"fail"|"uncertain", "confidence": "low"|"medium"|"high", '
        '"rationale": "<one or two sentences>"}\n'
        'Use "pass" only if the with-skill output honors the contract relative '
        'to the baseline. Use "fail" only if you are confident it does not. If '
        "the evidence is genuinely ambiguous or insufficient to decide, use "
        '"uncertain" with low confidence rather than guessing.'
    )


def _parse_response(response: str) -> Verdict:
    """Parse the model response into a Verdict, defensively.

    Accepts a JSON object (optionally wrapped in ```json fences or surrounded
    by stray prose — the first balanced ``{...}`` span is extracted). On any
    failure returns an unvalidated, ``uncertain`` verdict rather than raising:
    a response we could not read is not a judge decision, so it must not be
    reported as ``"fail"`` — and never as a silent ``"pass"``.
    """
    text = response.strip() if isinstance(response, str) else ""
    if not text:
        return Verdict(
            outcome="uncertain",
            confidence="low",
            validation_status="unvalidated",
            rationale="empty model response",
        )

    payload = _extract_json_object(text)
    if payload is None:
        return Verdict(
            outcome="uncertain",
            confidence="low",
            validation_status="unvalidated",
            rationale="could not parse a JSON object from the model response",
        )

    raw_outcome = str(payload.get("outcome", "")).strip().lower()
    rationale = str(payload.get("rationale", "")).strip()

    if raw_outcome not in _VALID_OUTCOMES:
        # A response we cannot trust the verdict of is unvalidated and
        # uncertain — not a pass, and not a fail the judge never decided.
        return Verdict(
            outcome="uncertain",
            confidence="low",
            validation_status="unvalidated",
            rationale=f"unrecognized outcome {raw_outcome!r} in model response",
        )

    # Confidence: a MISSING key may default to "low", but a PRESENT-but-bogus
    # value must NOT validate — silently coercing it would let a malformed
    # payload become a validated pass, breaking the hard contract that a
    # malformed response never becomes a silent pass.
    confidence: Confidence = "low"
    if "confidence" in payload:
        raw_conf = str(payload.get("confidence", "")).strip().lower()
        if raw_conf not in _VALID_CONFIDENCE:
            return Verdict(
                outcome="uncertain",
                confidence="low",
                validation_status="unvalidated",
                rationale=f"unrecognized confidence {raw_conf!r} in model response",
            )
        confidence = raw_conf  # type: ignore[assignment]

    # Rationale is a required field: a missing or empty one leaves the verdict
    # non-authoritative — uncertain and unvalidated, never a validated pass.
    if not rationale:
        return Verdict(
            outcome="uncertain",
            confidence="low",
            validation_status="unvalidated",
            rationale="missing or empty rationale in model response",
        )

    outcome: Outcome = raw_outcome  # type: ignore[assignment]

    return Verdict(
        outcome=outcome,
        confidence=confidence,
        validation_status="validated",
        rationale=rationale,
    )


def compose_judge_prompt(
    *,
    skill: str,
    prompt: str,
    baseline: str,
    golden: JudgePayload,
    actual: JudgePayload,
    contract: str,
    swap_order: bool = False,
) -> str:
    """Public wrapper: compose the judge prompt for a host-driven agent turn.

    Delegates to the private :func:`_build_prompt`. Exposed so the
    ``/renmark:eval`` skill can compose the judge prompt, issue the live model
    call itself (as an agent turn), and parse the result via
    :func:`parse_judge_verdict` — without reaching into a private helper.
    Produces byte-identical output to what :func:`judge_behavior` sends for the
    same arguments.

    Redaction contract: ``golden``/``actual`` may be a pre-rendered ``str``
    (passed through unchanged — the caller owns its provenance) or a dict, which
    is redacted of Worker-authored self-assessment/confidence/identity/preferred-
    verdict keys (:data:`_WORKER_REDACTED_KEYS`) *before* string composition and
    then JSON-serialized. Redaction is never a post-hoc pass over the rendered
    prompt.

    ``swap_order=True`` presents ACTUAL before BASELINE (both still labeled) to
    counter judge positional bias; see :func:`resolve_swap_order`.
    """
    return _build_prompt(
        skill=skill,
        prompt=prompt,
        baseline=baseline,
        golden=golden,
        actual=actual,
        contract=contract,
        swap_order=swap_order,
    )


def parse_judge_verdict(response: str) -> Verdict:
    """Public wrapper: parse a raw judge model response into a :class:`Verdict`.

    Delegates to the private :func:`_parse_response`. Exposed so the
    ``/renmark:eval`` skill can parse the response from its own agent-turn
    model call. Parses defensively — on any failure it yields an unvalidated,
    ``uncertain`` verdict rather than raising, and never a silent ``pass``.
    """
    return _parse_response(response)


def _strip_code_fence(text: str) -> str:
    """Return the JSON content inside a ```json … ``` fence, or *text* unchanged.

    Iterates over the segments produced by splitting on ``` and returns the
    first segment whose non-whitespace content starts with ``{`` (after
    stripping an optional ``json`` language tag).  If no fenced block is
    found the original string is returned as-is.
    """
    if "```" not in text:
        return text
    for part in text.split("```"):
        candidate = part
        if candidate.lstrip().lower().startswith("json"):
            candidate = candidate.lstrip()[len("json"):]
        candidate = candidate.strip()
        if candidate.startswith("{"):
            return candidate
    return text


def _find_balanced_brace(text: str) -> str | None:
    """Return the first balanced ``{…}`` substring in *text*, or ``None``.

    Uses a character-by-character state machine that tracks string literals
    (including escape sequences) so that braces inside strings are ignored.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


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

    stripped = _strip_code_fence(text)
    candidate = _find_balanced_brace(stripped)
    if candidate is None:
        return None
    try:
        obj = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def judge_behavior(
    repo: Path,
    *,
    skill: str,
    prompt: str,
    baseline: str,
    golden: JudgePayload,
    actual: JudgePayload,
    contract: str,
    subagent_runner: SubagentRunner | None = None,
    swap_order: bool = False,
) -> Verdict:
    """Semantically compare with-skill behavior against the baseline.

    Escalation-only: this makes one live frontier-model call (approx
    :data:`JUDGE_EST_COST_USD`) via ``subagent_runner``, which defaults to the
    real (host-injected) runner. Tests inject a mock. The call is fenced so
    that any runner error, timeout, or unparseable response yields an
    ``outcome="uncertain"``, ``validation_status="unvalidated"`` verdict — a
    runner failure means "we do not know", not "the judge decided fail", and
    never a silent ``pass``.

    The return type stays :class:`Verdict` (four fields, unchanged) even when
    ``swap_order`` is used: existing callers are unaffected. A caller that wants
    the swap on record pairs the verdict with :class:`JudgeCallRecord` or
    :meth:`JudgeEvidenceRef.from_verdict`.

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
        The expected/reference output — a ``str`` (used as-is) or a dict, which
        is redacted of Worker self-assessment keys and JSON-serialized.
    actual:
        The output produced with the skill enabled; same ``str``/dict contract
        and redaction as ``golden``.
    contract:
        The skill's stated behavioral contract (what it promises to change).
    subagent_runner:
        Callable taking the composed prompt string and returning the model's
        raw response string. Defaults to the host runner (which raises if not
        wired), mapped to an uncertain, unvalidated verdict.
    swap_order:
        When ``True``, present ACTUAL before BASELINE (both still labeled) to
        counter positional bias. Decide it with :func:`resolve_swap_order` and
        record it beside the verdict — it is not stored on :class:`Verdict`.
    """
    runner: SubagentRunner = subagent_runner or _default_subagent_runner
    judge_prompt = _build_prompt(
        skill=skill,
        prompt=prompt,
        baseline=baseline,
        golden=golden,
        actual=actual,
        contract=contract,
        swap_order=swap_order,
    )

    try:
        response = runner(judge_prompt)
    except JudgeUnavailable as exc:
        return Verdict(
            outcome="uncertain",
            confidence="low",
            validation_status="unvalidated",
            rationale=f"judge runner unavailable: {exc}",
        )
    except Exception as exc:
        # Any runner failure is unknown, not a decision: uncertain +
        # unvalidated, never a fail the judge never rendered, never a pass.
        return Verdict(
            outcome="uncertain",
            confidence="low",
            validation_status="unvalidated",
            rationale=f"judge runner error: {type(exc).__name__}: {exc}",
        )

    return _parse_response(response)
