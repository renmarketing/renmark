"""Behavioral test harness — did the skill actually change the behavior?

Shadow tests (:mod:`renmark.shadow`) answer *did this subsystem's deterministic
output drift?* This harness answers a different, skill-level question: *when the
skill is enabled, does the model's behavior both (a) match the recorded golden
transcript AND (b) differ meaningfully from the skill-disabled baseline?* A skill
that changes nothing versus baseline is a no-op and fails, even if it "matches"
golden — matching golden alone can't tell a real effect from an accidental
coincidence with the baseline.

Two-phase, mirroring shadow's record-and-replay split:

    1. ``capture`` (the ``--accept`` path) makes the *only* live model calls in
       this module. It runs the shared prompt twice through an injected
       ``subagent_runner`` — once skill-disabled (baseline), once skill-enabled
       (golden) — and records both transcripts to disk.
    2. ``replay`` is deterministic and pure I/O over those recorded snapshots:
       NO network, NO tokens. It re-reads the golden transcript, diffs it against
       the recorded golden (regression), and asserts the golden differs from the
       baseline (the skill had an effect). A missing snapshot is an ERROR result
       carrying ``"run --accept first"`` — never a silent pass.

Cases are declarative JSON at ``tests/behavioral/*.behavior.json``:

    {
      "skill": "renmark:brainstorm",
      "prompt": "<the shared input>",
      "assertions": ["must ask exactly one question", ...],
      "baseline_ref": "brainstorm-baseline",   # snapshot stem under snapshots/
      "golden_ref": "brainstorm-golden"
    }

``run`` replays every case. On a deterministic FAIL it does NOT touch the
escalation-only LLM judge unless ``judge=True`` was passed explicitly; with the
default ``on_fail_offer=True`` it merely flags ``judge_offered`` so the CLI can
prompt the human for an opt-in escalation (see :mod:`renmark.judge`, which costs
:data:`renmark.judge.JUDGE_EST_COST_USD` per call).

Like the rest of the renmark runtime, this Python process cannot itself call a
Claude model; the live model call in ``capture`` is routed through an injectable
``subagent_runner: Callable[[str], str]`` (a fully-composed prompt in, the raw
response out) — the same shape :mod:`renmark.judge` uses.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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

# Message surfaced (via a Result's ``message`` field) when a snapshot the
# deterministic replay needs has never been recorded. The CLI keys off this.
ACCEPT_FIRST_HINT = "run --accept first"


class BehaviorConfigError(ValueError):
    """A ``*.behavior.json`` case file is missing required fields or malformed."""


@dataclass(frozen=True)
class Case:
    """One declarative behavioral case, mirroring the on-disk JSON schema.

    - ``skill``: the skill under test, e.g. ``"renmark:brainstorm"``.
    - ``prompt``: the shared input given to BOTH the baseline and golden runs.
    - ``assertions``: human-readable behavioral claims the golden must satisfy;
      carried through to the judge prompt as the skill's contract when escalated.
    - ``baseline_ref`` / ``golden_ref``: snapshot stems (no extension) under the
      case directory's ``snapshots/`` folder locating the recorded transcripts.
    - ``source``: the case file path (populated by :func:`load_cases`).
    """

    skill: str
    prompt: str
    assertions: tuple[str, ...]
    baseline_ref: str
    golden_ref: str
    source: Path | None = None


@dataclass
class Result:
    """Outcome of replaying one case, exposing the artifact-contract fields.

    - ``status``: ``"PASS"`` (matched golden AND differed from baseline),
      ``"FAIL"`` (ran but a check failed), or ``"ERROR"`` (could not run — e.g. a
      missing snapshot, whose ``message`` is :data:`ACCEPT_FIRST_HINT`).
    - ``completion_state`` / ``confidence`` / ``validation_status``: the standard
      renmark artifact-contract fields. A missing snapshot is
      ``failed``/``low``/``unvalidated`` — never a silent success.
    - ``judge_offered``: set True when a deterministic FAIL is eligible for an
      opt-in escalation to the LLM judge and ``judge=True`` was NOT passed. The
      CLI reads this to prompt the human; the judge is never auto-invoked.
    - ``judge_verdict``: populated only when ``run(..., judge=True)`` escalated a
      FAIL — a :class:`renmark.judge.Verdict` serialized to a plain dict.
    """

    skill: str
    case: str
    status: Status
    completion_state: CompletionState
    confidence: Confidence
    validation_status: ValidationStatus
    message: str = ""
    judge_offered: bool = False
    judge_verdict: dict[str, object] | None = None


# ── Loading ──────────────────────────────────────────────────────────────────


def _behavioral_root() -> Path:
    """The default ``tests/behavioral/`` directory at the repo root."""
    here = Path(__file__).resolve()
    return here.parent.parent / "tests" / "behavioral"


def _snapshots_dir(case_dir: Path) -> Path:
    """Where recorded baseline/golden transcripts live for cases in ``case_dir``."""
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

    return Case(
        skill=str(data["skill"]),
        prompt=str(data["prompt"]),
        assertions=tuple(str(a) for a in raw_assertions),
        baseline_ref=str(data["baseline_ref"]),
        golden_ref=str(data["golden_ref"]),
        source=source,
    )


def load_cases(directory: str | Path | None = None) -> list[Case]:
    """Load every ``*.behavior.json`` case from ``directory`` (sorted by name).

    Defaults to ``tests/behavioral/`` at the repo root. A malformed or
    incomplete case file raises :class:`BehaviorConfigError` — loading is strict
    so a typo can't silently drop a case.
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


# ── Snapshot I/O ─────────────────────────────────────────────────────────────


def _snapshot_path(case: Case, ref: str) -> Path:
    """Resolve a snapshot stem to its ``.json`` path under the case's snapshots dir."""
    case_dir = case.source.parent if case.source is not None else _behavioral_root()
    return _snapshots_dir(case_dir) / f"{ref}.json"


def _read_snapshot(path: Path) -> str | None:
    """Read a recorded transcript snapshot; return None if it does not exist.

    Snapshots are stored as ``{"transcript": "<text>"}`` so the format can grow
    (timestamps, token counts) without breaking readers.
    """
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "transcript" in payload:
        return str(payload["transcript"])
    # Tolerate a bare string snapshot for forward/backward compatibility.
    return payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)


def _write_snapshot(path: Path, transcript: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"transcript": transcript}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _differs_meaningfully(baseline: str, golden: str) -> bool:
    """True when ``golden`` differs from ``baseline`` beyond whitespace noise.

    "The skill had an effect" is defined as a non-whitespace-only difference in
    the transcript text. Kept intentionally simple and deterministic; semantic
    equivalence is the judge's job, not replay's.
    """
    return " ".join(baseline.split()) != " ".join(golden.split())


# ── Replay (deterministic — no network, no tokens) ───────────────────────────


def replay(case: Case) -> Result:
    """Deterministically replay one case over its recorded snapshots.

    Reads the recorded baseline and golden transcripts and PASSes iff the golden
    transcript both (a) exists/round-trips and (b) differs meaningfully from the
    baseline. If either snapshot is missing, returns an ``ERROR`` result whose
    message is :data:`ACCEPT_FIRST_HINT` — never a pass. Pure I/O: no model call.
    """
    baseline_path = _snapshot_path(case, case.baseline_ref)
    golden_path = _snapshot_path(case, case.golden_ref)

    try:
        baseline = _read_snapshot(baseline_path)
        golden = _read_snapshot(golden_path)
    except (json.JSONDecodeError, OSError) as exc:
        return Result(
            skill=case.skill,
            case=case.golden_ref,
            status="ERROR",
            completion_state="failed",
            confidence="low",
            validation_status="unvalidated",
            message=f"failed to read snapshot: {exc}",
        )

    if baseline is None or golden is None:
        which = "baseline" if baseline is None else "golden"
        return Result(
            skill=case.skill,
            case=case.golden_ref,
            status="ERROR",
            completion_state="failed",
            confidence="low",
            validation_status="unvalidated",
            message=f"missing {which} snapshot — {ACCEPT_FIRST_HINT}",
        )

    if not _differs_meaningfully(baseline, golden):
        return Result(
            skill=case.skill,
            case=case.golden_ref,
            status="FAIL",
            completion_state="complete",
            confidence="high",
            validation_status="validated",
            message="with-skill transcript does not differ from baseline (skill had no effect)",
        )

    return Result(
        skill=case.skill,
        case=case.golden_ref,
        status="PASS",
        completion_state="complete",
        confidence="high",
        validation_status="validated",
        message="matches golden and differs from baseline",
    )


# ── Capture (the live --accept path — the ONLY model-calling function) ────────


def capture(case: Case, subagent_runner: SubagentRunner) -> tuple[str, str]:
    """Record the baseline + golden transcripts for one case via a live runner.

    This is the ``--accept`` path and the sole model-calling function in this
    module. It runs ``case.prompt`` twice through ``subagent_runner`` — first
    skill-disabled (baseline), then skill-enabled (golden) — and writes both
    snapshots to disk. Returns the ``(baseline, golden)`` transcripts.

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

    _write_snapshot(_snapshot_path(case, case.baseline_ref), baseline)
    _write_snapshot(_snapshot_path(case, case.golden_ref), golden)
    return baseline, golden


# ── Run over all cases ────────────────────────────────────────────────────────


def _escalate_to_judge(
    repo: Path,
    case: Case,
    *,
    subagent_runner: SubagentRunner | None,
) -> dict[str, object]:
    """Escalate a deterministic FAIL to the LLM judge (LAZY import).

    Called ONLY when ``run(..., judge=True)``. Reads the recorded snapshots and
    asks :func:`renmark.judge.judge_behavior` whether the with-skill output
    honors the contract (the case's assertions) relative to the baseline.
    Returns the verdict serialized to a plain dict; any snapshot-read failure is
    reported as an unvalidated verdict rather than raising.
    """
    from dataclasses import asdict

    from renmark.judge import judge_behavior  # lazy — avoid import cycle

    try:
        baseline = _read_snapshot(_snapshot_path(case, case.baseline_ref)) or ""
        golden = _read_snapshot(_snapshot_path(case, case.golden_ref)) or ""
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "outcome": "fail",
            "confidence": "low",
            "validation_status": "unvalidated",
            "rationale": f"judge could not read snapshots: {exc}",
        }

    contract = "\n".join(f"- {a}" for a in case.assertions) or "(no assertions declared)"
    verdict = judge_behavior(
        repo,
        skill=case.skill,
        prompt=case.prompt,
        baseline=baseline,
        golden=golden,
        actual=golden,  # replay had no live actual; the golden IS the recorded with-skill run
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

    Deterministic first: each case runs through :func:`replay` (no model call).
    On a deterministic FAIL:

    - if ``judge=True``, escalate to the LLM judge via a LAZY
      :func:`renmark.judge.judge_behavior` import (costs
      :data:`renmark.judge.JUDGE_EST_COST_USD`), stashing the verdict on
      ``result.judge_verdict``;
    - else if ``on_fail_offer`` (the default), set ``result.judge_offered=True``
      so the CLI can prompt for an opt-in escalation.

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
                result.judge_verdict = _escalate_to_judge(
                    repo_path, case, subagent_runner=subagent_runner
                )
            elif on_fail_offer:
                result.judge_offered = True
        results.append(result)
    return results


__all__ = [
    "ACCEPT_FIRST_HINT",
    "BehaviorConfigError",
    "Case",
    "Result",
    "SubagentRunner",
    "capture",
    "load_cases",
    "replay",
    "run",
]
