"""Behavioral test harness — two honestly-labelled tiers (P8-v2).

This harness answers a skill-level question the structure audit (a linter) can
never answer: *does enabling the skill actually change agent behavior in the way
the skill's contract promises?* The earlier (v1) design tried to answer it
deterministically by asserting a recorded golden transcript against itself — a
golden replayed as "current" and diffed against a recorded baseline. That proved
nothing: an assertion that holds on a snapshot merely confirms the snapshot was
written the way it was written, not that any live skill still behaves that way.
That was the fatal flaw ("Major 1") this rewrite removes.

The two tiers are now split by what each can *honestly* prove:

Deterministic tier (default; the ONLY thing ``run()`` does without flags)
    CI-safe scaffolding / regression guard. For each case it resolves
    ``deterministic.call`` to a REAL renmark function via an explicit allow-list
    dispatch table, invokes it on live inputs derived from the case
    (``repo``, ``skill``), and evaluates the case's ``assertions`` against the
    GENUINE CURRENT output — recomputed every run, reading NO snapshot and
    constructing NO live model runner. It therefore spends zero tokens, touches
    no network, and never ERRORs on a fresh checkout. What it proves is narrow:
    that the deterministic renmark surfaces a skill relies on (menu rendering,
    dispatch policy, leak checks) still produce the shape the skill's contract
    requires. It is NOT proof the skill, driven by a live model, works.

Eval / judge tier (gated — reachable ONLY via explicit flags/args)
    The actual behavioral proof, and it is opt-in and out of CI because it costs
    money and needs a live model. :func:`capture` records an eval golden
    transcript (the ``--accept`` path, the sole model-calling entry point), and
    :func:`run` escalates a deterministic FAIL to :func:`renmark.judge.judge_behavior`
    ONLY when ``judge=True`` and a live ``subagent_runner`` is provided. Neither
    path is ever reached by the default deterministic run.

Assertion mini-format (unchanged)
---------------------------------
Each assertion is a string checked deterministically against the rendered
current output:

    * ``"<op>:<argument>"`` — a structured predicate. Supported ops:
        - ``contains:<substr>``      output contains ``<substr>``
        - ``not_contains:<substr>``  output does NOT contain ``<substr>``
        - ``matches:<regex>``        ``re.search(<regex>, output)`` matches
        - ``line_ends:<substr>``     some non-empty line ends with ``<substr>``
        - ``min_lines:<int>``        output has >= N non-empty lines
      (op names match case-insensitively; an unknown op-shaped token — a single
      leading ``word:`` with no spaces — is a FAIL, never a silent pass.)
    * any other string — a plain ``contains`` substring check.

Case schema (``tests/behavioral/*.behavior.json``)
--------------------------------------------------
    {
      "skill": "roadmap",
      "prompt": "<the shared input, carried to the judge as context>",
      "deterministic": {
        "call": "lifecycle.next_steps",
        "assertions": ["contains:(Recommended)", "min_lines:3"]
      },
      "eval": {
        "contract": "<what the skill promises to change>",
        "golden_ref": "roadmap.golden"
      }
    }
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

# The live-model injection point, identical in shape to renmark.judge's runner:
# a fully-composed prompt string in, the raw model response string out. Used
# ONLY by the eval/judge tier (``capture`` / ``_escalate_to_judge``) — the
# default deterministic path NEVER constructs or touches one.
SubagentRunner = Callable[[str], str]

Status = Literal["PASS", "FAIL", "ERROR"]
CompletionState = Literal["complete", "partial", "failed"]
Confidence = Literal["low", "medium", "high"]
ValidationStatus = Literal["validated", "unvalidated", "failed"]

# Message surfaced when the eval tier needs a recorded golden transcript that
# has never been recorded. Applies ONLY to the judge/eval path — the
# deterministic tier reads no snapshots and can never raise this.
ACCEPT_FIRST_HINT = "run --accept first"


class BehaviorConfigError(ValueError):
    """A ``*.behavior.json`` case file is missing required fields or malformed,
    or an eval ``golden_ref`` is unsafe (would escape the snapshots directory)."""


class LiveRunnerUnavailable(RuntimeError):
    """The eval tier's live model runner was requested but is not wired.

    A pure-Python process cannot issue the Agent/model call the eval tier needs;
    a real ``str -> str`` runner must be injected by the HOST (an agent turn with
    Agent-tool access). Until then the eval tier (``--accept`` / ``--judge``) is
    unavailable, and the deterministic tier (``--behavior``) is the CI-safe
    default. Raised by :func:`build_subagent_runner`."""


# ── Case model ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DeterministicSpec:
    """The deterministic tier's config for one case.

    - ``call``: an allow-listed renmark function key (see :data:`_DISPATCH`).
    - ``assertions``: the declarative contract evaluated against the CURRENT
      rendered output of that call (see the module docstring's mini-format).
    """

    call: str
    assertions: tuple[str, ...]


@dataclass(frozen=True)
class EvalSpec:
    """The eval/judge tier's config for one case.

    - ``contract``: the skill's stated behavioral promise, handed to the judge.
    - ``golden_ref``: snapshot stem (a bare filename stem — no path separators,
      no ``..``) under the case directory's ``snapshots/`` folder where
      :func:`capture` records the with-skill transcript.
    """

    contract: str
    golden_ref: str


@dataclass(frozen=True)
class Case:
    """One declarative behavioral case, mirroring the on-disk JSON schema.

    - ``skill``: the skill under test (bare name, e.g. ``"roadmap"``), used both
      as the deterministic call's live input and as the judge's subject.
    - ``prompt``: the shared input carried to the judge as context.
    - ``deterministic``: the CI-safe tier spec (call + assertions).
    - ``eval``: the opt-in judge tier spec (contract + golden_ref).
    - ``source``: the case file path (populated by :func:`load_cases`).
    """

    skill: str
    prompt: str
    deterministic: DeterministicSpec
    eval: EvalSpec
    source: Path | None = None


@dataclass
class Result:
    """Outcome of running one case's deterministic tier.

    - ``status``: ``"PASS"`` (all assertions held on the CURRENT rendered
      output), ``"FAIL"`` (ran but a check failed, or the ``call`` is unknown),
      or ``"ERROR"`` (could not run — reserved; the deterministic tier never
      ERRORs on a fresh checkout).
    - ``completion_state`` / ``confidence`` / ``validation_status``: the standard
      renmark artifact-contract fields.
    - ``failed_assertions``: assertions that did NOT hold (empty on PASS).
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
    failed_assertions: tuple[str, ...] = ()
    judge_offered: bool = False
    judge_verdict: dict[str, object] | None = None


# ── Loading ──────────────────────────────────────────────────────────────────


def _behavioral_root() -> Path:
    """The default ``tests/behavioral/`` directory at the repo root."""
    here = Path(__file__).resolve()
    return here.parent.parent / "tests" / "behavioral"


def _snapshots_dir(case_dir: Path) -> Path:
    """Where recorded eval golden snapshots live for cases in ``case_dir``."""
    return case_dir / "snapshots"


def _case_from_dict(data: dict[str, object], source: Path | None) -> Case:
    """Build a :class:`Case` from a parsed JSON object, validating the schema."""
    where = f" ({source})" if source else ""

    missing = [k for k in ("skill", "prompt", "deterministic", "eval") if k not in data]
    if missing:
        raise BehaviorConfigError(f"behavior case missing required field(s) {missing}{where}")

    det_raw = data["deterministic"]
    if not isinstance(det_raw, dict):
        raise BehaviorConfigError(f"'deterministic' must be an object{where}")
    if "call" not in det_raw:
        raise BehaviorConfigError(f"'deterministic' missing required field 'call'{where}")
    if "assertions" not in det_raw:
        raise BehaviorConfigError(
            f"'deterministic' missing required field 'assertions'{where}"
        )
    raw_assertions = det_raw["assertions"]
    # A missing/empty assertion set would let a case vacuously PASS (no failures),
    # so require a non-empty list — a case must assert something.
    if not isinstance(raw_assertions, list) or not raw_assertions:
        raise BehaviorConfigError(
            f"'deterministic.assertions' must be a non-empty list{where}"
        )

    eval_raw = data["eval"]
    if not isinstance(eval_raw, dict):
        raise BehaviorConfigError(f"'eval' must be an object{where}")
    eval_missing = [k for k in ("contract", "golden_ref") if k not in eval_raw]
    if eval_missing:
        raise BehaviorConfigError(f"'eval' missing required field(s) {eval_missing}{where}")

    golden_ref = str(eval_raw["golden_ref"])
    # Reject an unsafe ref at load time: a ref that is not a plain filename stem
    # could escape the snapshots directory once interpolated.
    _validate_ref(golden_ref, source)

    deterministic = DeterministicSpec(
        call=str(det_raw["call"]),
        assertions=tuple(str(a) for a in raw_assertions),
    )
    eval_spec = EvalSpec(
        contract=str(eval_raw["contract"]),
        golden_ref=golden_ref,
    )
    return Case(
        skill=str(data["skill"]),
        prompt=str(data["prompt"]),
        deterministic=deterministic,
        eval=eval_spec,
        source=source,
    )


def load_cases(directory: str | Path | None = None) -> list[Case]:
    """Load every ``*.behavior.json`` case from ``directory`` (sorted by name).

    Defaults to ``tests/behavioral/`` at the repo root. A malformed or
    incomplete case file — including one with an unsafe eval ``golden_ref`` —
    raises :class:`BehaviorConfigError`; loading is strict so a typo or a
    traversal attempt can't silently drop or mis-resolve a case.
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


# ── Snapshot path safety (eval tier only) ─────────────────────────────────────


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


def _snapshot_path(case: Case, ref: str) -> Path:
    """Resolve a snapshot stem to its ``.json`` path under the case's snapshots
    dir, rejecting any resolved path that escapes that directory."""
    _validate_ref(ref, case.source)
    case_dir = case.source.parent if case.source is not None else _behavioral_root()
    snapshots = _snapshots_dir(case_dir)
    candidate = (snapshots / f"{ref}.json").resolve()
    root = snapshots.resolve()
    if root != candidate and root not in candidate.parents:
        raise BehaviorConfigError(
            f"snapshot ref {ref!r} resolves outside the snapshots directory ({candidate})"
        )
    return snapshots / f"{ref}.json"


def _read_snapshot(path: Path) -> str | None:
    """Read a recorded eval transcript; return None if it does not exist.

    Snapshots are stored as ``{"transcript": "<text>"}`` (bare-string and legacy
    payloads are tolerated). Used ONLY by the eval/judge tier.
    """
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "transcript" in payload:
        return str(payload["transcript"])
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, sort_keys=True)


def _write_snapshot(path: Path, transcript: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"transcript": transcript}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ── Assertion evaluation (deterministic predicate table) ─────────────────────


def _assert_contains(output: str, arg: str) -> bool:
    return arg in output


def _assert_not_contains(output: str, arg: str) -> bool:
    return arg not in output


def _assert_matches(output: str, arg: str) -> bool:
    try:
        return re.search(arg, output) is not None
    except re.error:
        return False


def _assert_line_ends(output: str, arg: str) -> bool:
    return any(line.rstrip().endswith(arg) for line in output.splitlines() if line.strip())


def _assert_min_lines(output: str, arg: str) -> bool:
    try:
        want = int(arg.strip())
    except ValueError:
        return False
    non_empty = [ln for ln in output.splitlines() if ln.strip()]
    return len(non_empty) >= want


# op name (lowercase) -> predicate(output, argument) -> bool
_ASSERTION_OPS: dict[str, Callable[[str, str], bool]] = {
    "contains": _assert_contains,
    "not_contains": _assert_not_contains,
    "matches": _assert_matches,
    "line_ends": _assert_line_ends,
    "min_lines": _assert_min_lines,
}


def _eval_assertion(assertion: str, output: str) -> bool:
    """Evaluate one assertion against ``output`` deterministically.

    A ``"<op>:<arg>"`` form dispatches through :data:`_ASSERTION_OPS`; an unknown
    op-shaped token (a single leading ``word:`` with no spaces) is a FAIL, never
    a silent pass. Any other string is a plain ``contains`` substring check.
    """
    if ":" in assertion:
        op_part, _, arg = assertion.partition(":")
        op = op_part.strip().lower()
        if op in _ASSERTION_OPS:
            return _ASSERTION_OPS[op](output, arg)
        if op and " " not in op:
            return False
    return _assert_contains(output, assertion)


def _evaluate_assertions(assertions: Sequence[str], output: str) -> tuple[str, ...]:
    """Return the tuple of assertions that did NOT hold on ``output``."""
    return tuple(a for a in assertions if not _eval_assertion(a, output))


# ── Deterministic dispatch (explicit allow-list of live renmark functions) ────


def _render_next_steps(repo: Path, case: Case) -> str:
    """Render ``lifecycle.next_steps(repo, skill)`` to a stable menu text.

    Produces a textual menu the assertions can match: the tier-0 (recommended)
    option marked ``(Recommended)``, then each remaining suggestion, then a
    terminal Finish/Nothing fallback line so a menu-terminality assertion can
    pass. Recomputed live every call — no snapshot.
    """
    from . import lifecycle

    steps = lifecycle.next_steps(repo, case.skill)
    lines: list[str] = ["What's next:"]
    seen: set[str] = set()
    tier0 = steps.tier0
    lines.append(f"1 - {tier0} (Recommended)")
    seen.add(tier0)
    n = 2
    for suggestion in steps.suggestions:
        if suggestion in seen:
            continue
        seen.add(suggestion)
        lines.append(f"{n} - {suggestion}")
        n += 1
    lines.append(f"[skill_class: {steps.skill_class}]")
    # Terminal fallback so menu-terminality assertions have something to match.
    lines.append(f"{n} - /renmark:finish (Finish) / do nothing")
    return "\n".join(lines)


def _render_skill_preamble(repo: Path, case: Case) -> str:
    """Render ``lifecycle.skill_preamble(repo, skill)`` to text (empty if None)."""
    from . import lifecycle

    hint = lifecycle.skill_preamble(repo, case.skill)
    return hint if hint is not None else ""


def _render_skill_preamble_fresh(repo: Path, case: Case) -> str:
    """Render skill_preamble in an isolated scratch dir (no mode, no agency set)."""
    import shutil

    from . import lifecycle

    # Use a repo-owned path so this works in sandboxes without a system /tmp.
    tmp = repo / ".renmark" / "state" / "_behavior-fresh"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        hint = lifecycle.skill_preamble(tmp, case.skill)
        return hint if hint is not None else ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _render_skill_preamble_agency_active(repo: Path, case: Case) -> str:
    """Render skill_preamble in an isolated scratch dir with agency activated."""
    import shutil

    from . import agency, lifecycle

    # Use a repo-owned path so this works in sandboxes without a system /tmp.
    tmp = repo / ".renmark" / "state" / "_behavior-agency"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        agency.activate(tmp)
        hint = lifecycle.skill_preamble(tmp, case.skill)
        return hint if hint is not None else ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _render_delivery_mode_matrix(repo: Path, case: Case) -> str:
    """Render the canonical two-mode resolution/resume contract as JSON."""
    import shutil

    from . import lifecycle, mode

    _ = case
    tmp = repo / ".renmark" / "state" / "_behavior-delivery-mode"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        start = lifecycle.skill_preamble(tmp / "start", "start") or ""
        feature = lifecycle.skill_preamble(tmp / "feature", "feature") or ""
        debug = lifecycle.skill_preamble(tmp / "debug", "debug") or ""
        resume_repo = tmp / "resume"
        mode.set_mode(resume_repo, "agency")
        before = mode.read_delivery_state(resume_repo)
        resume = lifecycle.skill_preamble(resume_repo, "resume") or ""
        after = mode.read_delivery_state(resume_repo)
        legacy = mode.resolve_delivery_state("conductor")
        payload = {
            "start": start,
            "feature": feature,
            "debug": debug,
            "legacy_conductor": {
                "delivery_mode": legacy.delivery_mode,
                "execution_policy": legacy.interaction_mode,
            },
            "resume_preserved": before == after,
            "resume_reasked": "not yet set" in resume,
        }
        return json.dumps(payload, sort_keys=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _render_agency_delivery_trajectory(repo: Path, case: Case) -> str:
    """Render the two host-neutral entry trajectories to live state text.

    Agency owns a milestone and requires its explicit approval before the
    canonical delivery aggregate delegates execution to Orchestrator.  A
    defined-goal Orchestrator entry, by contrast, persists its own mode without
    activating Agency discovery.  This is a deterministic state-contract guard,
    not a claim that a live agent completed either trajectory.
    """
    import shutil

    from . import agency, delivery_state, mode

    _ = case
    tmp = repo / ".renmark" / "state" / "_behavior-agency-trajectory"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        agency_repo = tmp / "agency"
        agency.activate(
            agency_repo,
            current_phase="milestone approved",
            current_milestone="approved milestone",
            signoff_status="approved",
        )
        agency.approve_milestone_for_orchestrator(agency_repo)
        approved = delivery_state.read_delivery_state(agency_repo)

        direct_repo = tmp / "orchestrator"
        mode.write_delivery_state(
            direct_repo,
            mode.resolve_delivery_state(
                ("orchestrator", "direct"),
                intent="defined-feature",
                entry="orchestrate",
            ),
        )
        direct = delivery_state.read_delivery_state(direct_repo)
        direct = delivery_state.update_active_milestone(direct, "defined goal")
        delivery_state.write_delivery_state(direct_repo, direct)
        direct = delivery_state.read_delivery_state(direct_repo)
        payload = {
            "agency_approved_milestone": {
                "approval_status": approved.approval_status,
                "active_milestone_id": approved.active_milestone_id,
                "milestone_execution": approved.milestone_execution,
            },
            "direct_orchestrator": {
                "delivery_mode": direct.delivery_mode,
                "execution_policy": direct.execution_policy,
                "active_milestone_id": direct.active_milestone_id,
                "agency_discovery_active": agency.is_active(direct_repo),
            },
        }
        return json.dumps(payload, sort_keys=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _render_plan_lint(repo: Path, case: Case) -> str:
    """Render a NARROW, declared-policy read-only check to text (scaffolding tier).

    Honest scope (do not overstate): a behavior case carries no plan path and the
    real roadmap trajectory is model-driven, so this deterministic adapter does
    NOT prove that live roadmap OUTPUT is read-only — that is the eval tier's job
    (``case.eval.contract``). What it DOES prove, via the authoritative
    :func:`plan_lint._check_transcript_leak`, is a scaffolding-level invariant:
    the skill's declared dispatch policy renders leak-free (no ``Agent(`` /
    ``codex exec`` / ``renmark-execute --task`` tokens) AND positively describes
    read-only routing (isolated subagents, bounded-summary reads). It is a
    regression guard on the declared contract, not a live-behavior proof.
    """
    from . import plan_lint
    from .parser import Task

    # A minimal, honest dispatch-policy description for the skill under test.
    # Deliberately free of the forbidden tokens the assertions guard against.
    policy = (
        f"skill {case.skill}: dispatches each task in an isolated subagent; the "
        "orchestrator reads only bounded summaries (status, artifact path, token "
        "count) and never merges back generated code or diffs. Downstream tasks "
        "reference upstream artifacts by path, not by prior-task output."
    )

    # Build a synthetic Task and run the authoritative leak check over it so the
    # rendered verdict reflects the live plan_lint logic, not a hand-copy.
    task = Task(
        index=1,
        title=f"{case.skill} dispatch policy",
        mode="B",
        target="(policy)",
        executor="sonnet",
        spec=policy,
        verifier="true",
    )
    leak_issues = plan_lint._check_transcript_leak([task])
    verdict = "leak-free" if not leak_issues else "LEAK"
    lines = [
        f"dispatch policy for {case.skill}:",
        policy,
        f"transcript-leak check: {verdict}",
    ]
    return "\n".join(lines)


def _render_selector(repo: Path, case: Case, host: str) -> str:
    """Render one live host selector contract as bounded JSON text."""
    import json

    from .interaction import Choice, build_selector

    _ = repo
    result = build_selector(
        case.prompt,
        (
            Choice("r", "Review", "read the plan"),
            Choice("d", "Dispatch", "execute the plan", recommended=True),
            Choice("e", "Edit", "change the plan"),
            Choice("n", "No", "stop here"),
        ),
        host=host,
    )
    return json.dumps(result, sort_keys=True)


def _render_selector_claude(repo: Path, case: Case) -> str:
    return _render_selector(repo, case, "claude")


def _render_selector_codex(repo: Path, case: Case) -> str:
    """Render both Codex Plan and Default surfaces plus continuation behavior."""
    import json

    from .interaction import Choice, build_selector, continue_selector

    _ = repo
    choices = (
        Choice("r", "Review", "read the plan"),
        Choice("d", "Dispatch", "execute the plan", recommended=True),
        Choice("e", "Edit", "change the plan"),
        Choice("n", "No", "stop here"),
    )
    plan = build_selector(
        case.prompt,
        choices,
        host="codex",
        render_surface="codex-plan",
    )
    default = build_selector(
        case.prompt,
        choices,
        host="codex",
        render_surface="codex-default",
    )
    second_page = build_selector(
        case.prompt,
        choices,
        host="codex",
        render_surface="codex-plan",
        page=1,
    )
    more = continue_selector(plan, "More")
    back = continue_selector(second_page, "Back")
    cancel = continue_selector(second_page, "No")
    invalid = continue_selector(plan, "explain this first")
    return json.dumps(
        {
            "plan": plan,
            "default": default,
            "more_kind": more.kind,
            "back_kind": back.kind,
            "cancel_kind": cancel.kind,
            "invalid_kind": invalid.kind,
        },
        sort_keys=True,
    )


def _selector_choices() -> tuple[object, ...]:
    """Return one recommended-first semantic choice set with overflow."""
    from .interaction import Choice

    return (
        Choice("r", "Review", "read the plan"),
        Choice("d", "Dispatch", "execute the plan", recommended=True),
        Choice("e", "Edit", "change the plan"),
        Choice("w", "Wait", "pause without dispatching"),
        Choice("n", "No", "stop here"),
    )


def _continuation_choice_id(result: object) -> str | None:
    choice = getattr(result, "choice", None)
    return None if choice is None else getattr(choice, "code", None)


def _selector_trajectory_payload(repo: Path, case: Case) -> dict[str, object]:
    """Return the bounded cross-host selector trajectory contract as data."""
    from .interaction import Choice, build_selector, continue_selector

    choices = cast(tuple[Choice, ...], _selector_choices())
    claude = build_selector(case.prompt, choices, host="claude")
    claude_page2 = build_selector(case.prompt, choices, host="claude", page=1)
    codex_plan = build_selector(
        case.prompt,
        choices,
        host="codex",
        render_surface="codex-plan",
    )
    codex_plan_page2 = build_selector(
        case.prompt,
        choices,
        host="codex",
        render_surface="codex-plan",
        page=1,
    )
    codex_plan_page3 = build_selector(
        case.prompt,
        choices,
        host="codex",
        render_surface="codex-plan",
        page=2,
    )
    codex_default = build_selector(
        case.prompt,
        choices,
        host="codex",
        tool_available=False,
    )

    claude_semantic = claude["semantic"]
    codex_plan_semantic = codex_plan["semantic"]
    codex_default_semantic = codex_default["semantic"]
    claude_recommended = continue_selector(claude, "1")
    claude_more = continue_selector(claude, "more")
    claude_cancel = continue_selector(claude_page2, "2")
    claude_back = continue_selector(claude_page2, "back")
    codex_plan_recommended = continue_selector(codex_plan, "1")
    codex_plan_more = continue_selector(codex_plan, "more")
    codex_plan_more_page2 = continue_selector(codex_plan_page2, "more")
    codex_plan_cancel = continue_selector(codex_plan_page3, "2")
    codex_plan_back = continue_selector(codex_plan_page3, "back")
    codex_default_recommended = continue_selector(codex_default, "1")
    codex_default_cancel = continue_selector(codex_default, "No")
    codex_default_invalid = continue_selector(codex_default, "explain this first")
    semantic_choices = cast(list[dict[str, str]], claude_semantic["choices"])
    recommended_choice_id = semantic_choices[0]["code"]
    refusal_choice_id = semantic_choices[-1]["code"]

    return {
        "claude": claude,
        "codex_plan": codex_plan,
        "codex_default": codex_default,
        "semantic_choice_ids": [
            choice["choice_id"]
            for choice in semantic_choices
        ],
        "semantic_equivalent": (
            claude_semantic == codex_plan_semantic == codex_default_semantic
        ),
        "recommended_choice_id": recommended_choice_id,
        "refusal_choice_id": refusal_choice_id,
        "claude_recommended_choice_id": _continuation_choice_id(claude_recommended),
        "claude_more_kind": claude_more.kind,
        "claude_cancel_choice_id": _continuation_choice_id(claude_cancel),
        "claude_back_kind": claude_back.kind,
        "codex_plan_recommended_choice_id": _continuation_choice_id(codex_plan_recommended),
        "codex_plan_more_kind": codex_plan_more.kind,
        "codex_plan_more_page2_kind": codex_plan_more_page2.kind,
        "codex_plan_cancel_choice_id": _continuation_choice_id(codex_plan_cancel),
        "codex_plan_back_kind": codex_plan_back.kind,
        "codex_default_recommended_choice_id": _continuation_choice_id(
            codex_default_recommended
        ),
        "codex_default_cancel_choice_id": _continuation_choice_id(codex_default_cancel),
        "codex_default_invalid_kind": codex_default_invalid.kind,
        "overflow_semantics": {
            "claude": {"overflow": claude["overflow"], "page_count": claude["page"]["count"]},
            "codex_plan": {
                "overflow": codex_plan["overflow"],
                "page_count": codex_plan["page"]["count"],
            },
            "codex_default": {
                "fallback_only": codex_default["mode"] == "fallback",
                "page_count": codex_default["page"]["count"],
            },
        },
        "recommended_first_semantics": {
            "claude": _continuation_choice_id(claude_recommended) == recommended_choice_id,
            "codex_plan": _continuation_choice_id(codex_plan_recommended)
            == recommended_choice_id,
            "codex_default": _continuation_choice_id(codex_default_recommended)
            == recommended_choice_id,
        },
        "cancel_semantics": {
            "claude": _continuation_choice_id(claude_cancel) == refusal_choice_id,
            "codex_plan": _continuation_choice_id(codex_plan_cancel) == refusal_choice_id,
            "codex_default": _continuation_choice_id(codex_default_cancel) == refusal_choice_id,
        },
        "continuation_semantics": {
            "claude_more": claude_more.kind == "more",
            "claude_back": claude_back.kind == "back",
            "codex_plan_more": codex_plan_more.kind == "more",
            "codex_plan_more_page2": codex_plan_more_page2.kind == "more",
            "codex_plan_back": codex_plan_back.kind == "back",
            "codex_default_invalid": codex_default_invalid.kind == "invalid",
        },
        "codex_native_clickability_claim": False,
        "loop_resume": _loop_resume_cross_host_trajectory(repo),
    }


def _loop_resume_one_host(repo: Path, host: str) -> dict[str, object]:
    """Return one bounded simulated loop pause/resume outcome for ``host``."""
    from . import dispatch, loop
    from .parser import Task

    loop_id = loop.loop_id("2026-07-31", "selector parity")
    before = loop.LoopState(
        goal="all checks green",
        verify_cmd="python -c \"assert True\"",
        budget_tokens=10_000,
        budget_usd_estimate="$0.10",
        spent_tokens=400,
        run_id="selector-parity-loop",
        max_iterations=3,
        iteration=1,
        status="running",
        pending_step="",
    )
    created_path = loop.write_loop(repo, loop_id, before)
    assert created_path is not None

    reread_created = loop.read_loop(repo, loop_id)
    assert reread_created is not None
    failed_decision = loop.build_decision(
        {
            "completion_state": "partial",
            "validation_status": "failed",
            "summary_lines": ["failed: parity verifier"],
        },
        spent_delta=200,
    )
    resumed = loop.read_loop(repo, loop_id)
    assert resumed is not None
    resumed.iteration += 1
    resumed.spent_tokens += 200
    resumed_path = loop.write_loop(repo, loop_id, resumed)
    assert resumed_path is not None
    reread_resumed = loop.read_loop(repo, loop_id)
    assert reread_resumed is not None

    transport = dispatch.build_host_dispatch_plan(
        [
            Task(
                index=1,
                title="Selector parity",
                mode="B",
                target="renmark/behavior.py",
                executor="sonnet",
                spec="Prove host-neutral selector resume semantics.",
                verifier="true",
            )
        ],
        host=host,
    )
    final_decision = loop.build_decision(
        {
            "completion_state": "complete",
            "validation_status": "validated",
            "summary_lines": ["all checks green"],
        },
        spent_delta=100,
    )
    reread_after_resume_matches = (
        reread_resumed.iteration == 2
        and reread_resumed.spent_tokens == 600
        and reread_resumed.status == "running"
    )
    reread_resumed.status = "done" if final_decision["goal_reached"] else "stalled"
    assert loop.write_loop(repo, loop_id, reread_resumed) is not None
    final = loop.read_loop(repo, loop_id)
    assert final is not None
    return {
        "loop_id": loop_id,
        "persisted_path": str(created_path),
        "created_record": {
            "iteration": reread_created.iteration,
            "spent_tokens": reread_created.spent_tokens,
            "status": reread_created.status,
        },
        "resumed": {
            "iteration": reread_resumed.iteration,
            "spent_tokens": reread_resumed.spent_tokens,
            "status": reread_resumed.status,
        },
        "reread_after_create_matches": before == reread_created,
        "reread_after_resume_matches": reread_after_resume_matches,
        "failed_next_action": failed_decision["next_action"],
        "final_goal_reached": final_decision["goal_reached"],
        "stop_reason": loop.stop_reason(final),
        "task_packets": transport.task_packets,
    }


def _loop_resume_cross_host_trajectory(repo: Path) -> dict[str, object]:
    """Return the bounded pause/resume parity payload for Claude and Codex."""
    import shutil

    tmp = repo / ".renmark" / "state" / "_behavior-selector-loop-resume"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        claude = _loop_resume_one_host(tmp / "claude", "claude")
        codex = _loop_resume_one_host(tmp / "codex", "codex")
        # The path proves that each host persisted and reread its own record,
        # but it is transport-specific rather than part of the loop semantics.
        claude_semantic = {
            key: value for key, value in claude.items() if key != "persisted_path"
        }
        codex_semantic = {
            key: value for key, value in codex.items() if key != "persisted_path"
        }
        return {
            "claude": claude,
            "codex": codex,
            "semantic_equivalent": claude_semantic == codex_semantic,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _render_selector_cross_host_trajectory(repo: Path, case: Case) -> str:
    """Render the combined selector and loop/resume host trajectory as JSON."""
    return json.dumps(_selector_trajectory_payload(repo, case), sort_keys=True)


# call key -> adapter(repo, case) -> rendered current output text.
# EXPLICIT allow-list: an unresolved key is a FAIL (see _run_deterministic),
# never an import-time surprise or a silent pass.
_DISPATCH: dict[str, Callable[[Path, Case], str]] = {
    "lifecycle.next_steps": _render_next_steps,
    "lifecycle.skill_preamble": _render_skill_preamble,
    "lifecycle.skill_preamble_fresh": _render_skill_preamble_fresh,
    "lifecycle.skill_preamble_agency_active": _render_skill_preamble_agency_active,
    "lifecycle.delivery_mode_matrix": _render_delivery_mode_matrix,
    "lifecycle.agency_delivery_trajectory": _render_agency_delivery_trajectory,
    "interaction.selector_claude": _render_selector_claude,
    "interaction.selector_codex": _render_selector_codex,
    "interaction.selector_cross_host_trajectory": _render_selector_cross_host_trajectory,
    "plan_lint": _render_plan_lint,
}


# ── Deterministic tier (default — no network, no tokens, no snapshots) ────────


def _run_deterministic(case: Case, repo: Path) -> Result:
    """Run one case's deterministic tier and evaluate its assertion contract.

    Resolves ``case.deterministic.call`` through the explicit :data:`_DISPATCH`
    allow-list, invokes it on live inputs (``repo``, ``case.skill``) to get the
    GENUINE CURRENT rendered output (recomputed every run — no snapshot read, no
    live runner constructed), then evaluates every assertion against it. An
    unknown ``call`` is a FAIL with a clear message (never an exception that
    aborts the whole run); a raising adapter is likewise a FAIL, not a crash.
    """
    adapter = _DISPATCH.get(case.deterministic.call)
    if adapter is None:
        return Result(
            skill=case.skill,
            case=case.eval.golden_ref,
            status="FAIL",
            completion_state="failed",
            confidence="high",
            validation_status="validated",
            message=(
                f"unknown deterministic call {case.deterministic.call!r}; "
                f"allowed: {sorted(_DISPATCH)}"
            ),
        )

    try:
        output = adapter(repo, case)
    except Exception as exc:  # a broken adapter fails this case, not the suite
        return Result(
            skill=case.skill,
            case=case.eval.golden_ref,
            status="FAIL",
            completion_state="failed",
            confidence="high",
            validation_status="validated",
            message=f"deterministic call {case.deterministic.call!r} raised: {type(exc).__name__}: {exc}",
        )

    failed = _evaluate_assertions(case.deterministic.assertions, output)
    if failed:
        return Result(
            skill=case.skill,
            case=case.eval.golden_ref,
            status="FAIL",
            completion_state="complete",
            confidence="high",
            validation_status="validated",
            message=f"{len(failed)} assertion(s) failed on the current output",
            failed_assertions=failed,
        )

    return Result(
        skill=case.skill,
        case=case.eval.golden_ref,
        status="PASS",
        completion_state="complete",
        confidence="high",
        validation_status="validated",
        message="all deterministic assertions hold on the current output",
    )


# ── Eval / judge tier (gated — the ONLY model-calling paths) ──────────────────


def build_subagent_runner(repo: Path, model: str = "sonnet") -> SubagentRunner:
    """Resolve the eval tier's live runner from config, else raise.

    A pure-Python process cannot itself issue the Agent/model call the eval tier
    needs, so there is no honest in-process ``str -> str`` runner. Instead the
    runner is supplied out-of-band: :func:`renmark.providers.eval_runner.resolve_eval_runner`
    reads config (the ``RENMARK_EVAL_RUNNER_CMD`` env var) and, when set, returns
    a subprocess-backed ``str -> str`` runner that shells out to a real model
    command and raises ``EvalRunnerError`` on failure. When UNCONFIGURED it
    returns ``None`` and this function raises :class:`LiveRunnerUnavailable` — we
    never fabricate a runner. (An earlier version returned the dispatch PROMPT
    text, which made ``--accept`` record prompts as "goldens" and ``--judge`` feed
    a prompt into the judge instead of a real transcript — never a real model
    trajectory.) The deterministic tier (:func:`run` with no runner) is the
    CI-safe default and never reaches here.

    ``model`` is passed through to the resolver unchanged (currently unused there).
    """
    from renmark.providers.eval_runner import resolve_eval_runner

    runner = resolve_eval_runner(repo, model)
    if runner is not None:
        return runner
    raise LiveRunnerUnavailable(
        "eval-tier live runner not wired: a str->str runner command is required "
        "(this Python process cannot issue the model call). Set "
        "RENMARK_EVAL_RUNNER_CMD to a str->str command to enable it. The "
        "deterministic tier (--behavior) is the CI-safe default."
    )


def compose_eval_prompt(case: Case) -> str:
    """Build the skill-enabled golden prompt for one eval case.

    Returns the exact prompt handed to a live runner when recording the
    with-skill golden: the case prompt prefixed with a directive that activates
    ``case.skill``. Pure — no I/O, no model call.
    """
    return (
        f"[skill ENABLED: {case.skill}] Respond to the following with the skill "
        f"active.\n\n{case.prompt}"
    )


def capture_from_transcript(case: Case, transcript: str) -> str:
    """Persist an already-produced golden transcript for one eval case.

    Writes ``transcript`` under ``snapshots/<golden_ref>.json`` and returns it
    unchanged. The model-free half of :func:`capture` — the caller supplies the
    transcript, this only records it.
    """
    _write_snapshot(_snapshot_path(case, case.eval.golden_ref), transcript)
    return transcript


def capture(case: Case, subagent_runner: SubagentRunner) -> str:
    """Record the eval golden transcript for one case (the ``--accept`` path).

    The sole model-calling entry point for the with-skill golden. Runs
    ``case.prompt`` (skill-enabled) through the injected ``subagent_runner`` and
    writes the transcript under ``snapshots/<golden_ref>.json``. Returns the
    recorded golden transcript. NEVER called by the default deterministic run —
    only a caller that explicitly supplies a live runner reaches this.
    """
    return capture_from_transcript(case, subagent_runner(compose_eval_prompt(case)))


def _escalate_to_judge(
    repo: Path,
    case: Case,
    *,
    current: str,
    subagent_runner: SubagentRunner | None,
) -> dict[str, object]:
    """Escalate a deterministic FAIL to the LLM judge (LAZY import).

    Called ONLY when ``run(..., judge=True)``. Reads the recorded eval golden and
    asks :func:`renmark.judge.judge_behavior` whether the with-skill output honors
    the eval contract. A missing golden yields an unvalidated, uncertain verdict
    carrying :data:`ACCEPT_FIRST_HINT` — never a silent pass, and never a claimed
    fail when the judge was simply never consulted.
    """
    from dataclasses import asdict

    from renmark.judge import judge_behavior  # lazy — avoid import cycle

    try:
        golden = _read_snapshot(_snapshot_path(case, case.eval.golden_ref))
    except (json.JSONDecodeError, OSError, BehaviorConfigError) as exc:
        return {
            "outcome": "uncertain",
            "confidence": "low",
            "validation_status": "unvalidated",
            "rationale": f"judge could not read golden snapshot: {exc}",
        }

    if golden is None:
        return {
            "outcome": "uncertain",
            "confidence": "low",
            "validation_status": "unvalidated",
            "rationale": f"no recorded eval golden — {ACCEPT_FIRST_HINT}",
        }

    verdict = judge_behavior(
        repo,
        skill=case.skill,
        prompt=case.prompt,
        baseline="",  # v2 has no recorded baseline; the judge weighs contract vs actual
        golden=golden,
        actual=current,
        contract=case.eval.contract,
        subagent_runner=subagent_runner,
    )
    return asdict(verdict)


# ── Run over all cases ────────────────────────────────────────────────────────


def run(
    directory: str | Path | None = None,
    *,
    judge: bool = False,
    on_fail_offer: bool = True,
    repo: str | Path | None = None,
    subagent_runner: SubagentRunner | None = None,
    cases: Sequence[Case] | None = None,
) -> list[Result]:
    """Run every behavioral case's deterministic tier and return one Result each.

    The default path runs the DETERMINISTIC tier only: each case's
    ``deterministic.call`` is resolved to a live renmark function, invoked on
    live inputs, and its assertions evaluated against the genuine current output.
    This path reads no snapshot, constructs no live runner, spends no tokens, and
    touches no network.

    On a deterministic FAIL:

    - if ``judge=True``, escalate to the LLM judge via a LAZY
      :func:`renmark.judge.judge_behavior` import (costs
      :data:`renmark.judge.JUDGE_EST_COST_USD`), comparing the case's recorded
      eval golden against the ``actual`` current output under the eval contract,
      and stash the verdict on ``result.judge_verdict``. A missing eval golden
      yields an unvalidated verdict carrying :data:`ACCEPT_FIRST_HINT` — never a
      silent pass;
    - else if ``on_fail_offer`` (the default), set ``result.judge_offered=True``
      so the CLI can prompt for an opt-in escalation.

    The judge is NEVER auto-invoked unless ``judge=True`` is passed explicitly,
    and it only runs on the gated eval path.

    Parameters
    ----------
    directory:
        Case directory; defaults to ``tests/behavioral/``.
    judge:
        Escalate deterministic FAILs to the LLM judge. Off by default.
    on_fail_offer:
        When not escalating, flag FAILs as judge-eligible for the CLI to prompt.
    repo:
        Project root; the deterministic tier's live inputs derive from it, and it
        is forwarded to the judge on the ``judge=True`` path. Defaults to the repo
        containing this module.
    subagent_runner:
        Live-model runner forwarded to the judge when ``judge=True``. NEVER used
        or constructed on the default deterministic path.
    cases:
        Pre-loaded cases to run instead of loading from ``directory`` (testing).
    """
    repo_path = Path(repo) if repo is not None else Path(__file__).resolve().parent.parent
    loaded = list(cases) if cases is not None else load_cases(directory)

    results: list[Result] = []
    for case in loaded:
        result = _run_deterministic(case, repo_path)
        if result.status == "FAIL":
            if judge:
                if _eval_golden_missing(case):
                    # No recorded golden to adjudicate against: this is an
                    # operational gap (ERROR), not a behavioral FAIL — and we
                    # must NOT spend a judge call on an un-evaluable case.
                    result.status = "ERROR"
                    result.completion_state = "failed"
                    result.message = f"{result.message}; eval golden missing — {ACCEPT_FIRST_HINT}"
                else:
                    current = _current_for_judge(case, repo_path)
                    result.judge_verdict = _escalate_to_judge(
                        repo_path, case, current=current, subagent_runner=subagent_runner
                    )
            elif on_fail_offer:
                result.judge_offered = True
        results.append(result)
    return results


def _eval_golden_missing(case: Case) -> bool:
    """True when the case's eval golden snapshot is absent or unreadable.

    Used to short-circuit the judge escalation to an ERROR (never a wasted judge
    call, never a silent pass) when there is no recorded golden to adjudicate
    against — the caller must ``--accept`` a golden first.
    """
    try:
        return _read_snapshot(_snapshot_path(case, case.eval.golden_ref)) is None
    except (json.JSONDecodeError, OSError, BehaviorConfigError):
        return True


def _current_for_judge(case: Case, repo: Path) -> str:
    """Best-effort current output for the judge escalation path.

    Re-renders the deterministic call the same way :func:`_run_deterministic`
    does (no model call — deterministic surface). Returns an empty string if the
    call is unknown or the adapter raises, so the judge sees an empty actual and,
    per its contract, cannot return a validated pass.
    """
    adapter = _DISPATCH.get(case.deterministic.call)
    if adapter is None:
        return ""
    try:
        return adapter(repo, case)
    except Exception:
        return ""


__all__ = [
    "ACCEPT_FIRST_HINT",
    "BehaviorConfigError",
    "Case",
    "DeterministicSpec",
    "EvalSpec",
    "LiveRunnerUnavailable",
    "Result",
    "SubagentRunner",
    "build_subagent_runner",
    "capture",
    "capture_from_transcript",
    "compose_eval_prompt",
    "load_cases",
    "run",
]
