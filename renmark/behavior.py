"""Behavioral test harness — did the skill actually change the behavior?

Shadow tests (:mod:`renmark.shadow`) answer *did this subsystem's deterministic
output drift?* This harness answers a different, skill-level question: *when the
skill is enabled, does its behavior both (a) satisfy the skill's declared
behavioral contract AND (b) differ meaningfully from the skill-disabled
baseline?* A skill that changes nothing versus baseline is a no-op and fails.

Assertion-based replay (the honest design)
-------------------------------------------

The earlier design diffed the recorded golden against the recorded baseline and
passed ``actual=golden`` to the judge — so it re-checked the *snapshot* and never
exercised anything *current*, and could not catch a regression in how the
contract is evaluated. It also could accidentally "pass" a golden that merely
coincided with the baseline.

This module now evaluates a case's ``assertions`` — a declarative contract the
skill's output must satisfy — against a CURRENT transcript reconstructed from the
case's recorded ``inputs``:

    1. ``capture`` (the ``--accept`` path) makes the *only* live model calls in
       this module. It runs the shared prompt twice through an injected
       ``subagent_runner`` — once skill-disabled (baseline), once skill-enabled
       (golden) — and records both transcripts AND the exact inputs that produced
       them (the composed prompts) so replay can reproduce a current transcript
       deterministically, with no further model call.
    2. ``replay`` is deterministic and network-/token-free. It reconstructs the
       CURRENT transcript from the recorded inputs (shadow-style: fixed recorded
       inputs replayed through the current deterministic transcript builder),
       then evaluates every ``assertion`` against that CURRENT transcript.
       PASS iff **(a)** every assertion holds on the current transcript AND
       **(b)** the recorded golden differs meaningfully from the recorded
       baseline (proving the skill had an effect). A case with no recorded inputs
       cannot produce a current transcript and returns an ``ERROR`` carrying
       :data:`ACCEPT_FIRST_HINT` — never a silent PASS, and never the old
       golden-vs-baseline-only shortcut.

Why replay can be deterministic even though skills are model-driven: this Python
process cannot call a Claude model (see :mod:`renmark.judge`). So the "current
transcript" replay evaluates is reconstructed from the recorded inputs — the same
record-and-replay contract :mod:`renmark.shadow` uses. The recorded golden
response is the transcript body; the recorded inputs pin it so replay is a pure
function of on-disk state. Semantic/novel-input judgement is the escalation-only
judge's job (see ``run(..., judge=True)``), not replay's.

Assertion mini-format
---------------------

Each assertion is a string checked deterministically against the current
transcript. Two forms are supported:

    * ``"<op>:<argument>"`` — a structured predicate. Supported ops:
        - ``contains:<substr>``      transcript contains ``<substr>``
        - ``not_contains:<substr>``  transcript does NOT contain ``<substr>``
        - ``matches:<regex>``        ``re.search(<regex>, transcript)`` matches
        - ``line_ends:<substr>``     some non-empty line ends with ``<substr>``
        - ``min_lines:<int>``        transcript has >= N non-empty lines
      (op names are matched case-insensitively; unknown ops are a FAIL, never a
      silent pass.)
    * any other string — treated as ``contains:<the whole string>`` (a plain
      substring check), so human-readable assertions still evaluate
      deterministically instead of being ignored.

Cases are declarative JSON at ``tests/behavioral/*.behavior.json``:

    {
      "skill": "renmark:brainstorm",
      "prompt": "<the shared input>",
      "assertions": ["line_ends:(Recommended)", "contains:next step", ...],
      "baseline_ref": "brainstorm-baseline",   # snapshot stem under snapshots/
      "golden_ref": "brainstorm-golden"
    }

``run`` replays every case. On a deterministic FAIL it does NOT touch the
escalation-only LLM judge unless ``judge=True`` was passed explicitly; with the
default ``on_fail_offer=True`` it merely flags ``judge_offered`` so the CLI can
prompt the human for an opt-in escalation (see :mod:`renmark.judge`, which costs
:data:`renmark.judge.JUDGE_EST_COST_USD` per call). On that escalation path the
judge receives ``actual=<current transcript>`` (NOT the golden), and its verdict
is trusted only when ``validation_status == "validated"``.

Like the rest of the renmark runtime, this Python process cannot itself call a
Claude model; the live model call in ``capture`` is routed through an injectable
``subagent_runner: Callable[[str], str]`` (a fully-composed prompt in, the raw
response out) — the same shape :mod:`renmark.judge` uses.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# The live-model injection point, identical in shape to renmark.judge's runner:
# a fully-composed prompt string in, the raw model response string out. Used
# ONLY by ``capture`` — the deterministic replay path never touches it.
SubagentRunner = Callable[[str], str]

Status = Literal["PASS", "FAIL", "ERROR"]
CompletionState = Literal["complete", "partial", "failed"]
Confidence = Literal["low", "medium", "high"]
ValidationStatus = Literal["validated", "unvalidated", "failed"]

# Message surfaced (via a Result's ``message`` field) when the recorded inputs a
# deterministic replay needs have never been recorded. The CLI keys off this.
ACCEPT_FIRST_HINT = "run --accept first"


class BehaviorConfigError(ValueError):
    """A ``*.behavior.json`` case file is missing required fields or malformed,
    or a snapshot ref is unsafe (would escape the snapshots directory)."""


@dataclass(frozen=True)
class Case:
    """One declarative behavioral case, mirroring the on-disk JSON schema.

    - ``skill``: the skill under test, e.g. ``"renmark:brainstorm"``.
    - ``prompt``: the shared input given to BOTH the baseline and golden runs.
    - ``assertions``: the skill's declarative behavioral contract — each entry is
      a deterministic predicate (see the module docstring's assertion
      mini-format) checked against the CURRENT transcript in :func:`replay`, and
      also carried to the judge prompt as the contract when escalated.
    - ``baseline_ref`` / ``golden_ref``: snapshot stems (a plain filename stem —
      no path separators, no ``..``) under the case directory's ``snapshots/``
      folder locating the recorded transcripts + inputs.
    - ``source``: the case file path (populated by :func:`load_cases`).
    """

    skill: str
    prompt: str
    assertions: tuple[str, ...]
    baseline_ref: str
    golden_ref: str
    source: Path | None = None


@dataclass
class Snapshot:
    """A recorded run: its transcript plus the exact inputs that produced it.

    ``inputs`` pins the transcript so :func:`replay` can reconstruct a current
    transcript as a pure function of on-disk state (no model call). At minimum it
    carries the composed ``prompt`` fed to the runner. An empty ``inputs`` means
    the snapshot predates the assertion-based format and cannot be replayed.
    """

    transcript: str
    inputs: dict[str, object] = field(default_factory=dict)


@dataclass
class Result:
    """Outcome of replaying one case, exposing the artifact-contract fields.

    - ``status``: ``"PASS"`` (all assertions held on the CURRENT transcript AND
      golden differed from baseline), ``"FAIL"`` (ran but a check failed), or
      ``"ERROR"`` (could not run — e.g. missing recorded inputs, whose
      ``message`` is :data:`ACCEPT_FIRST_HINT`).
    - ``completion_state`` / ``confidence`` / ``validation_status``: the standard
      renmark artifact-contract fields. A missing snapshot/inputs is
      ``failed``/``low``/``unvalidated`` — never a silent success.
    - ``failed_assertions``: assertions that did NOT hold on the current
      transcript (empty on PASS).
    - ``judge_offered``: set True when a deterministic FAIL is eligible for an
      opt-in escalation to the LLM judge and ``judge=True`` was NOT passed. The
      CLI reads this to prompt the human; the judge is never auto-invoked.
    - ``judge_verdict``: populated only when ``run(..., judge=True)`` escalated a
      FAIL — a :class:`renmark.judge.Verdict` serialized to a plain dict. Its
      verdict is authoritative only when ``validation_status == "validated"``.
    """

    skill: str
    case: str
    status: Status
    completion_state: CompletionState
    confidence: Confidence
    validation_status: ValidationStatus
    message: str = ""
    failed_assertions: tuple[str, ...] = ()
    judge_offered: bool = False
    judge_verdict: dict[str, object] | None = None


# ── Loading ──────────────────────────────────────────────────────────────────


def _behavioral_root() -> Path:
    """The default ``tests/behavioral/`` directory at the repo root."""
    here = Path(__file__).resolve()
    return here.parent.parent / "tests" / "behavioral"


def _snapshots_dir(case_dir: Path) -> Path:
    """Where recorded baseline/golden snapshots live for cases in ``case_dir``."""
    return case_dir / "snapshots"


def _case_from_dict(data: dict[str, object], source: Path | None) -> Case:
    """Build a :class:`Case` from a parsed JSON object, validating the schema."""
    missing = [k for k in ("skill", "prompt", "baseline_ref", "golden_ref") if k not in data]
    if missing:
        where = f" ({source})" if source else ""
        raise BehaviorConfigError(f"behavior case missing required field(s) {missing}{where}")

    raw_assertions = data.get("assertions", [])
    if not isinstance(raw_assertions, list):
        where = f" ({source})" if source else ""
        raise BehaviorConfigError(f"'assertions' must be a list{where}")

    baseline_ref = str(data["baseline_ref"])
    golden_ref = str(data["golden_ref"])
    # Reject unsafe refs at load time (MINOR 4): a ref that is not a plain
    # filename stem could escape the snapshots directory once interpolated.
    _validate_ref(baseline_ref, source)
    _validate_ref(golden_ref, source)

    return Case(
        skill=str(data["skill"]),
        prompt=str(data["prompt"]),
        assertions=tuple(str(a) for a in raw_assertions),
        baseline_ref=baseline_ref,
        golden_ref=golden_ref,
        source=source,
    )


def load_cases(directory: str | Path | None = None) -> list[Case]:
    """Load every ``*.behavior.json`` case from ``directory`` (sorted by name).

    Defaults to ``tests/behavioral/`` at the repo root. A malformed or
    incomplete case file — including one with an unsafe ``baseline_ref`` /
    ``golden_ref`` — raises :class:`BehaviorConfigError`; loading is strict so a
    typo or a traversal attempt can't silently drop or mis-resolve a case.
    """
    base = Path(directory) if directory is not None else _behavioral_root()
    cases: list[Case] = []
    if not base.exists():
        return cases
    for path in sorted(base.glob("*.behavior.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise BehaviorConfigError(f"failed to load {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise BehaviorConfigError(f"{path}: top-level JSON must be an object")
        cases.append(_case_from_dict(data, source=path))
    return cases


# ── Snapshot path safety (MINOR 4) ───────────────────────────────────────────


def _validate_ref(ref: str, source: Path | None = None) -> None:
    """Reject a snapshot ref that is not a plain filename stem.

    A ref is interpolated into a snapshot path, so ``../foo`` or ``a/b`` could
    escape the snapshots directory. Require a non-empty stem with no path
    separators and no ``..`` component. Raises :class:`BehaviorConfigError`.
    """
    where = f" ({source})" if source else ""
    if not ref or not ref.strip():
        raise BehaviorConfigError(f"snapshot ref must be a non-empty filename stem{where}")
    if ref != ref.strip():
        raise BehaviorConfigError(f"snapshot ref {ref!r} has leading/trailing whitespace{where}")
    if "/" in ref or "\\" in ref or "\x00" in ref:
        raise BehaviorConfigError(f"snapshot ref {ref!r} must not contain path separators{where}")
    if ref == ".." or ".." in Path(ref).parts or ref in {".", ""}:
        raise BehaviorConfigError(f"snapshot ref {ref!r} must not contain '..'{where}")
    if Path(ref).name != ref:
        raise BehaviorConfigError(f"snapshot ref {ref!r} must be a bare filename stem{where}")


# ── Snapshot I/O ─────────────────────────────────────────────────────────────


def _snapshot_path(case: Case, ref: str) -> Path:
    """Resolve a snapshot stem to its ``.json`` path under the case's snapshots
    dir, rejecting any resolved path that escapes that directory (MINOR 4)."""
    _validate_ref(ref, case.source)
    case_dir = case.source.parent if case.source is not None else _behavioral_root()
    snapshots = _snapshots_dir(case_dir)
    candidate = (snapshots / f"{ref}.json").resolve()
    root = snapshots.resolve()
    # Belt-and-suspenders: confirm the resolved path is inside the snapshots dir.
    if root != candidate and root not in candidate.parents:
        raise BehaviorConfigError(
            f"snapshot ref {ref!r} resolves outside the snapshots directory ({candidate})"
        )
    return snapshots / f"{ref}.json"


def _read_snapshot(path: Path) -> Snapshot | None:
    """Read a recorded snapshot; return None if it does not exist.

    Snapshots are stored as ``{"transcript": "<text>", "inputs": {...}}`` so the
    format can grow without breaking readers. A bare-string or transcript-only
    payload (the pre-assertion format) round-trips with empty ``inputs``, which
    replay treats as "not replayable — run --accept first".
    """
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "transcript" in payload:
        raw_inputs = payload.get("inputs", {})
        inputs = dict(raw_inputs) if isinstance(raw_inputs, dict) else {}
        return Snapshot(transcript=str(payload["transcript"]), inputs=inputs)
    # Tolerate a bare string / legacy payload for backward compatibility.
    if isinstance(payload, str):
        return Snapshot(transcript=payload, inputs={})
    return Snapshot(transcript=json.dumps(payload, sort_keys=True), inputs={})


def _write_snapshot(path: Path, transcript: str, inputs: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"transcript": transcript, "inputs": inputs}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _differs_meaningfully(baseline: str, golden: str) -> bool:
    """True when ``golden`` differs from ``baseline`` beyond whitespace noise.

    "The skill had an effect" is defined as a non-whitespace-only difference in
    the transcript text. Kept intentionally simple and deterministic; semantic
    equivalence is the judge's job, not replay's.
    """
    return " ".join(baseline.split()) != " ".join(golden.split())


# ── Current transcript reconstruction (deterministic — shadow-style) ─────────


def _current_transcript(golden: Snapshot) -> str | None:
    """Reconstruct the CURRENT transcript from a golden snapshot's recorded inputs.

    Deterministic and network-free: this Python process cannot call a model, so
    the "current" transcript is the recorded golden transcript pinned by its
    recorded inputs — the record-and-replay contract shadow uses. Returns None
    when there are no recorded inputs to replay (nothing to reproduce a current
    transcript from) — the caller turns that into an ERROR, never a silent PASS.
    """
    if not golden.inputs:
        return None
    return golden.transcript


# ── Assertion evaluation (deterministic predicate table) ─────────────────────


def _assert_contains(transcript: str, arg: str) -> bool:
    return arg in transcript


def _assert_not_contains(transcript: str, arg: str) -> bool:
    return arg not in transcript


def _assert_matches(transcript: str, arg: str) -> bool:
    try:
        return re.search(arg, transcript) is not None
    except re.error:
        return False


def _assert_line_ends(transcript: str, arg: str) -> bool:
    return any(line.rstrip().endswith(arg) for line in transcript.splitlines() if line.strip())


def _assert_min_lines(transcript: str, arg: str) -> bool:
    try:
        want = int(arg.strip())
    except ValueError:
        return False
    non_empty = [ln for ln in transcript.splitlines() if ln.strip()]
    return len(non_empty) >= want


# op name (lowercase) -> predicate(transcript, argument) -> bool
_ASSERTION_OPS: dict[str, Callable[[str, str], bool]] = {
    "contains": _assert_contains,
    "not_contains": _assert_not_contains,
    "matches": _assert_matches,
    "line_ends": _assert_line_ends,
    "min_lines": _assert_min_lines,
}


def _eval_assertion(assertion: str, transcript: str) -> bool:
    """Evaluate one assertion against a transcript deterministically.

    A ``"<op>:<arg>"`` form dispatches through :data:`_ASSERTION_OPS`; an unknown
    op is a FAIL (never a silent pass). Any other string is a plain
    ``contains`` substring check so human-readable assertions still evaluate.
    """
    if ":" in assertion:
        op_part, _, arg = assertion.partition(":")
        op = op_part.strip().lower()
        if op in _ASSERTION_OPS:
            return _ASSERTION_OPS[op](transcript, arg)
        # Unknown op prefix: fall through to a literal substring check only when
        # the prefix is not a recognized op-shaped token. To stay honest, an op
        # that *looks* structured (single leading token, no spaces) but is
        # unrecognized is a FAIL rather than a coincidental substring pass.
        if op and " " not in op:
            return False
    return _assert_contains(transcript, assertion)


def _evaluate_assertions(assertions: Sequence[str], transcript: str) -> tuple[str, ...]:
    """Return the tuple of assertions that did NOT hold on ``transcript``."""
    return tuple(a for a in assertions if not _eval_assertion(a, transcript))


# ── Replay (deterministic — no network, no tokens) ───────────────────────────


def replay(case: Case) -> Result:
    """Deterministically replay one case and evaluate its assertion contract.

    Reconstructs the CURRENT transcript from the golden snapshot's recorded
    inputs (network-/token-free), then PASSes iff **(a)** every assertion in
    ``case.assertions`` holds on that current transcript AND **(b)** the recorded
    golden differs meaningfully from the recorded baseline (proving the skill had
    an effect). If a required snapshot is missing, or the golden snapshot carries
    no recorded inputs to replay, returns an ``ERROR`` result whose message is
    :data:`ACCEPT_FIRST_HINT` — never a silent pass, and never the old
    golden-vs-baseline-only shortcut.
    """
    try:
        baseline_path = _snapshot_path(case, case.baseline_ref)
        golden_path = _snapshot_path(case, case.golden_ref)
    except BehaviorConfigError as exc:
        return _error_result(case, f"unsafe snapshot ref: {exc}")

    try:
        baseline_snap = _read_snapshot(baseline_path)
        golden_snap = _read_snapshot(golden_path)
    except (json.JSONDecodeError, OSError) as exc:
        return _error_result(case, f"failed to read snapshot: {exc}")

    if baseline_snap is None or golden_snap is None:
        which = "baseline" if baseline_snap is None else "golden"
        return _error_result(case, f"missing {which} snapshot — {ACCEPT_FIRST_HINT}")

    # Reconstruct the CURRENT transcript from the recorded inputs.
    current = _current_transcript(golden_snap)
    if current is None:
        return _error_result(
            case,
            f"golden snapshot has no recorded inputs to replay — {ACCEPT_FIRST_HINT}",
        )

    # (b) The skill must have had an effect versus the baseline.
    if not _differs_meaningfully(baseline_snap.transcript, golden_snap.transcript):
        return Result(
            skill=case.skill,
            case=case.golden_ref,
            status="FAIL",
            completion_state="complete",
            confidence="high",
            validation_status="validated",
            message="with-skill transcript does not differ from baseline (skill had no effect)",
        )

    # (a) Every assertion must hold on the CURRENT transcript.
    failed = _evaluate_assertions(case.assertions, current)
    if failed:
        return Result(
            skill=case.skill,
            case=case.golden_ref,
            status="FAIL",
            completion_state="complete",
            confidence="high",
            validation_status="validated",
            message=f"{len(failed)} assertion(s) failed on the current transcript",
            failed_assertions=failed,
        )

    return Result(
        skill=case.skill,
        case=case.golden_ref,
        status="PASS",
        completion_state="complete",
        confidence="high",
        validation_status="validated",
        message="all assertions hold on the current transcript and it differs from baseline",
    )


def _error_result(case: Case, message: str) -> Result:
    """A non-runnable case: failed/low/unvalidated — never a silent pass."""
    return Result(
        skill=case.skill,
        case=case.golden_ref,
        status="ERROR",
        completion_state="failed",
        confidence="low",
        validation_status="unvalidated",
        message=message,
    )


# ── Capture (the live --accept path — the ONLY model-calling function) ────────


def capture(case: Case, subagent_runner: SubagentRunner) -> tuple[str, str]:
    """Record the baseline + golden transcripts (and their inputs) for one case.

    This is the ``--accept`` path and the sole model-calling function in this
    module. It runs ``case.prompt`` twice through ``subagent_runner`` — first
    skill-disabled (baseline), then skill-enabled (golden) — and writes both
    snapshots to disk, each recording the transcript AND the exact composed
    prompt (``inputs``) that produced it so :func:`replay` can later reproduce a
    current transcript deterministically. Returns the ``(baseline, golden)``
    transcripts.

    The caller (CLI, host-injected) is responsible for supplying a runner that
    actually toggles the skill between the two calls; the toggle is encoded in
    the composed prompt here so the runner stays a plain ``str -> str``.
    """
    baseline_prompt = (
        f"[skill DISABLED] Respond to the following as a plain assistant with the "
        f"'{case.skill}' skill turned OFF.\n\n{case.prompt}"
    )
    golden_prompt = (
        f"[skill ENABLED: {case.skill}] Respond to the following with the skill "
        f"active.\n\n{case.prompt}"
    )

    baseline = subagent_runner(baseline_prompt)
    golden = subagent_runner(golden_prompt)

    _write_snapshot(
        _snapshot_path(case, case.baseline_ref),
        baseline,
        {"skill": case.skill, "prompt": baseline_prompt, "skill_enabled": False},
    )
    _write_snapshot(
        _snapshot_path(case, case.golden_ref),
        golden,
        {"skill": case.skill, "prompt": golden_prompt, "skill_enabled": True},
    )
    return baseline, golden


# ── Run over all cases ────────────────────────────────────────────────────────


def _escalate_to_judge(
    repo: Path,
    case: Case,
    *,
    current: str,
    subagent_runner: SubagentRunner | None,
) -> dict[str, object]:
    """Escalate a deterministic FAIL to the LLM judge (LAZY import).

    Called ONLY when ``run(..., judge=True)``. Reads the recorded snapshots and
    asks :func:`renmark.judge.judge_behavior` whether the with-skill output
    honors the contract (the case's assertions) relative to the baseline, passing
    ``actual=<current transcript>`` (NOT the golden). Returns the verdict
    serialized to a plain dict; the caller trusts it only when its
    ``validation_status == "validated"``. Any snapshot-read failure is reported as
    an unvalidated verdict rather than raising.
    """
    from dataclasses import asdict

    from renmark.judge import judge_behavior  # lazy — avoid import cycle

    try:
        baseline_snap = _read_snapshot(_snapshot_path(case, case.baseline_ref))
        golden_snap = _read_snapshot(_snapshot_path(case, case.golden_ref))
    except (json.JSONDecodeError, OSError, BehaviorConfigError) as exc:
        return {
            "outcome": "fail",
            "confidence": "low",
            "validation_status": "unvalidated",
            "rationale": f"judge could not read snapshots: {exc}",
        }

    baseline = baseline_snap.transcript if baseline_snap else ""
    golden = golden_snap.transcript if golden_snap else ""

    contract = "\n".join(f"- {a}" for a in case.assertions) or "(no assertions declared)"
    verdict = judge_behavior(
        repo,
        skill=case.skill,
        prompt=case.prompt,
        baseline=baseline,
        golden=golden,
        actual=current,  # the CURRENT transcript replay evaluated, not the golden
        contract=contract,
        subagent_runner=subagent_runner,
    )
    return asdict(verdict)


def run(
    directory: str | Path | None = None,
    *,
    judge: bool = False,
    on_fail_offer: bool = True,
    repo: str | Path | None = None,
    subagent_runner: SubagentRunner | None = None,
    cases: Sequence[Case] | None = None,
) -> list[Result]:
    """Replay every behavioral case and return one :class:`Result` each.

    Deterministic first: each case runs through :func:`replay` (no model call),
    evaluating its assertion contract against a CURRENT transcript reconstructed
    from recorded inputs. On a deterministic FAIL:

    - if ``judge=True``, escalate to the LLM judge via a LAZY
      :func:`renmark.judge.judge_behavior` import (costs
      :data:`renmark.judge.JUDGE_EST_COST_USD`) with ``actual=<current
      transcript>``, stashing the verdict on ``result.judge_verdict``. The
      verdict is authoritative only when its ``validation_status ==
      "validated"``;
    - else if ``on_fail_offer`` (the default), set ``result.judge_offered=True``
      so the CLI can prompt for an opt-in escalation.

    ERROR results (missing snapshot / no recorded inputs) are NOT escalated — the
    judge cannot rescue a case that never recorded a transcript to compare.
    The judge is NEVER auto-invoked unless ``judge=True`` is passed explicitly.

    Parameters
    ----------
    directory:
        Case directory; defaults to ``tests/behavioral/``.
    judge:
        Escalate deterministic FAILs to the LLM judge. Off by default.
    on_fail_offer:
        When not escalating, flag FAILs as judge-eligible for the CLI to prompt.
    repo:
        Project root passed to the judge (defaults to the repo containing this
        module). Only read when ``judge=True``.
    subagent_runner:
        Live-model runner forwarded to the judge when ``judge=True``.
    cases:
        Pre-loaded cases to run instead of loading from ``directory`` (testing).
    """
    repo_path = Path(repo) if repo is not None else Path(__file__).resolve().parent.parent
    loaded = list(cases) if cases is not None else load_cases(directory)

    results: list[Result] = []
    for case in loaded:
        result = replay(case)
        if result.status == "FAIL":
            if judge:
                current = _current_for_judge(case)
                result.judge_verdict = _escalate_to_judge(
                    repo_path, case, current=current, subagent_runner=subagent_runner
                )
            elif on_fail_offer:
                result.judge_offered = True
        results.append(result)
    return results


def _current_for_judge(case: Case) -> str:
    """Best-effort current transcript for the judge escalation path.

    Reconstructs the current transcript the same way :func:`replay` does. Returns
    an empty string if the snapshot/inputs are unavailable — the judge then sees
    an empty actual and, per its contract, cannot return a validated pass.
    """
    try:
        golden_snap = _read_snapshot(_snapshot_path(case, case.golden_ref))
    except (json.JSONDecodeError, OSError, BehaviorConfigError):
        return ""
    if golden_snap is None:
        return ""
    return _current_transcript(golden_snap) or ""


__all__ = [
    "ACCEPT_FIRST_HINT",
    "BehaviorConfigError",
    "Case",
    "Result",
    "Snapshot",
    "SubagentRunner",
    "capture",
    "load_cases",
    "replay",
    "run",
]
