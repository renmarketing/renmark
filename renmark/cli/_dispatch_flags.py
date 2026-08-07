"""CLI flag-handler cluster: the ``main()`` sub-command dispatch chain.

Extracted from ``_engine.py`` as a pure structural move (target-blueprint.md
§1.1) — every function below is byte-identical in behavior to its previous
definition in ``_engine.py``, which re-exports them for backward compatibility.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from renmark import hygiene
from renmark import lifecycle as _lifecycle
from renmark import task_tracking as _task_tracking

from .commands import (
    cmd_analytics,
    cmd_heartbeat,
    cmd_heartbeat_check_cron,
    cmd_logs,
    cmd_review_package,
    cmd_roadmap,
    cmd_scan,
    cmd_task,
    cmd_task_brief,
    cmd_usage,
)


def _get_engine() -> Any:
    """Lazy accessor for _engine symbols (avoids circular import at module level)."""
    from . import _engine

    return _engine


def _print(msg: str = "") -> None:
    _get_engine()._print(msg)


def _cmd_behavior(repo: Path, *, accept: bool, judge: bool) -> int:
    """Behavioral-suite lane: run the deterministic tier, record eval goldens, or judge FAILs.

    Bounded output (a few lines): one status line per case plus a totals line.

    Two honestly-labelled tiers (P8-v2):

    - Default ``--behavior``: the DETERMINISTIC tier ONLY. Calls ``behavior.run``
      without constructing or passing any live subagent runner, guaranteeing zero
      token spend and no network in CI. Exit non-zero on any FAIL/ERROR.
    - ``--behavior --accept``: the eval tier's live capture path. Constructs a live
      runner via ``behavior.build_subagent_runner`` and calls ``behavior.capture``
      per case to record its golden transcript (a deliberate live step).
    - ``--behavior --judge``: escalate deterministic FAILs to the LLM judge by
      passing ``judge=True`` AND the live runner into ``behavior.run``. Without it a
      deterministic FAIL prints a cost-noted OFFER (never auto-spends) unless headless.
    """
    from .. import behavior as _behavior
    from .. import config as _config

    behavioral_dir = str(repo / "tests" / "behavioral")

    if accept:
        return _behavior_accept(repo, behavioral_dir)

    headless = _config.is_headless(repo)

    # Default / --judge: deterministic tier. On the default path we pass NO live
    # runner, so run() spends zero tokens and touches no network. Only --judge
    # constructs the live runner and forwards it so a FAIL can escalate — but the
    # eval-tier live runner is host-injected and may be unavailable, in which case
    # we degrade honestly to the deterministic tier rather than fake it.
    runner = None
    judge_unavailable = False
    if judge:
        try:
            runner = _behavior.build_subagent_runner(repo)
        except _behavior.LiveRunnerUnavailable as exc:
            _print(f"  eval tier unavailable: {exc}")
            _print("  running the deterministic tier only.")
            judge = False
            judge_unavailable = True
    try:
        results = _behavior.run(
            behavioral_dir, judge=judge, repo=repo, subagent_runner=runner
        )
    except _behavior.BehaviorConfigError as exc:
        _print(f"ERROR loading behavioral cases: {exc}")
        return 2

    failed = 0
    offered = False
    for r in results:
        if r.status != "PASS":
            failed += 1
        msg = r.message[:60] if r.message else ""
        _print(f"  {r.status:<5} {r.skill}/{r.case:<24} {msg}")
        if r.judge_offered and not (judge or headless or judge_unavailable):
            offered = True

    _print(f"behavior: {len(results) - failed}/{len(results)} passed, {failed} failed")
    if offered:
        _print(
            f"  {failed} FAIL(s) eligible for LLM-judge review (~${_judge_est_cost():.2f}); "
            f"re-run with --behavior --judge to escalate. Not auto-invoked."
        )
    elif judge_unavailable and failed:
        # Don't point the user back at --judge: the live runner is host-injected
        # and just reported unavailable, so escalation isn't possible from here.
        _print(f"  {failed} FAIL(s); LLM-judge escalation unavailable from this CLI (host runner not wired).")
    return 0 if failed == 0 else 10


def _behavior_accept(repo: Path, behavioral_dir: str) -> int:
    """Record eval-tier golden transcripts (the ``--behavior --accept`` path).

    A deliberate live step: constructs a live subagent runner via
    ``behavior.build_subagent_runner`` and calls ``behavior.capture`` for each
    case to write its ``snapshots/<golden_ref>.json`` golden. Bounded output.
    """
    from .. import behavior as _behavior

    try:
        cases = _behavior.load_cases(behavioral_dir)
    except _behavior.BehaviorConfigError as exc:
        _print(f"ERROR loading behavioral cases: {exc}")
        return 2

    try:
        runner = _behavior.build_subagent_runner(repo)
    except _behavior.LiveRunnerUnavailable as exc:
        _print(f"eval tier unavailable — cannot record goldens: {exc}")
        return 3
    recorded = 0
    failed = 0
    for case in cases:
        try:
            _behavior.capture(case, runner)
        except Exception as exc:  # a bad case shouldn't abort the whole capture
            failed += 1
            _print(f"  ERROR {case.skill}/{case.eval.golden_ref:<24} {type(exc).__name__}: {exc}")
            continue
        recorded += 1
        _print(f"  RECORD {case.skill}/{case.eval.golden_ref}")

    _print(f"behavior --accept: {recorded}/{len(cases)} golden transcripts recorded, {failed} failed")
    return 0 if failed == 0 else 10


def _judge_est_cost() -> float:
    """Lazy accessor for the judge's estimated per-call cost (avoids eager import)."""
    from ..judge import JUDGE_EST_COST_USD

    return JUDGE_EST_COST_USD


_DELIVERY_STATE_MILESTONE_DISPLAY_LIMIT = 48


def _bounded_delivery_state_display(value: object, limit: int) -> str:
    """Bound a resume-facing value without changing its persisted identity."""
    rendered = str(value)
    if len(rendered) <= limit:
        return rendered
    return f"{rendered[: limit - 3]}..."


def _delivery_state_line(repo: Path) -> str:
    """Return a bounded read-only current-state summary for deterministic inspection."""
    from ..delivery_state import read_delivery_state_with_report
    from ..lifecycle import read_legacy_delivery_summary

    state, report = read_delivery_state_with_report(repo)
    drift_count: str | int = "n/a"

    # If canonical delivery state is absent/corrupt, fall back to the existing
    # legacy projection helper rather than inventing a second projection path.
    if report.state != "loaded":
        legacy = read_legacy_delivery_summary(repo)
        state = legacy.canonical_delivery
        drift_count = len(legacy.drift_repair_notes)
        freshness = report.state
    else:
        legacy = read_legacy_delivery_summary(repo)
        drift_count = len(legacy.drift_repair_notes)
        freshness = "loaded"

    milestone = _bounded_delivery_state_display(
        state.active_milestone_id or "(none)",
        _DELIVERY_STATE_MILESTONE_DISPLAY_LIMIT,
    )
    contract = state.contract_version or "(unknown)"
    return (
        "delivery_state "
        f"delivery_mode={state.delivery_mode} "
        f"execution_policy={state.execution_policy} "
        f"active_milestone={milestone} "
        f"contract_version={contract} "
        f"freshness={freshness} "
        f"drift_count={drift_count}"
    )


# ---------------------------------------------------------------------------
# Sub-command dispatch helpers — group the main() dispatch chain into logical
# clusters. Each returns int (the exit code) when it handled the flag, or
# None when the flag is not set (pass through to the next group).
# ---------------------------------------------------------------------------


def _dispatch_query_flags(
    args: argparse.Namespace, ap: argparse.ArgumentParser, repo: Path
) -> int | None:
    """Handle --usage/--analytics/--roadmap/--logs/--scan/--behavior/--task."""
    if args.delivery_state:
        print(_delivery_state_line(repo))
        return 0
    if args.usage:
        return cmd_usage(repo)
    if args.analytics:
        return cmd_analytics(repo)
    if args.roadmap:
        return cmd_roadmap(repo)
    if args.logs:
        return cmd_logs(repo, n=args.logs_n)
    if args.scan:
        return cmd_scan(repo, propose=args.propose, emit_cron=args.emit_cron)
    if args.heartbeat:
        return cmd_heartbeat(
            repo,
            emit_cron=args.heartbeat_emit_cron,
            auto_resume=args.heartbeat_auto_resume,
            interval_minutes=args.heartbeat_interval,
        )
    if args.heartbeat_check_cron:
        return cmd_heartbeat_check_cron()
    if args.behavior:
        return _cmd_behavior(repo, accept=args.accept, judge=args.judge)
    if args.task:
        if not args.output:
            ap.error("--task requires --output ARTIFACT_PATH")
        return cmd_task(args.task, args.output, repo=repo)
    return None


def _dispatch_proactive_mode_flags(
    args: argparse.Namespace, ap: argparse.ArgumentParser, repo: Path
) -> int | None:
    """Handle --set-proactive/--set-headless/--set-mode."""
    if args.set_proactive is not None:
        raw = args.set_proactive.strip().lower()
        if raw not in ("true", "false"):
            ap.error("--set-proactive expects 'true' or 'false'")
        from .. import config as _config

        value = raw == "true"
        _config.set_proactive(repo, value)
        state_str = "on" if value else "off"
        print(f"renmark: proactive auto-routing {state_str} ({repo}/.renmark/config.json)")
        return 0
    if args.set_headless is not None:
        raw = args.set_headless.strip().lower()
        if raw not in ("true", "false"):
            ap.error("--set-headless expects 'true' or 'false'")
        from .. import config as _config

        value = raw == "true"
        _config.set_headless(repo, value)
        state_str = "on" if value else "off"
        print(f"renmark: headless mode {state_str} ({repo}/.renmark/config.json)")
        return 0
    if args.set_mode is not None:
        from .. import delivery_state as _delivery_state
        from .. import mode as _mode

        mode_path = _mode.delivery_state_path(repo)
        try:
            _mode.set_mode(repo, args.set_mode)
        except ValueError as exc:
            ap.error(str(exc))
        except (OSError, _delivery_state.DeliveryStateBloatError) as exc:
            print(
                f"renmark: failed to persist operating mode to {mode_path}: {exc}",
                file=sys.stderr,
            )
            return 1
        state = _mode.read_delivery_state(repo)
        policy = state.interaction_mode if state is not None else "unknown"
        print(
            f"renmark: delivery mode set to {args.set_mode} "
            f"(execution policy: {policy}; {mode_path})"
        )
        return 0
    return None


def _dispatch_agency_flags(args: argparse.Namespace, repo: Path) -> int | None:
    """Handle --agency-status/--activate-agency/--deactivate-agency."""
    if args.agency_status:
        from renmark import agency as _agency

        state = _agency.read_agency(repo)
        status = "active" if state.active else "inactive"
        print(f"agency: {status}")
        if state.active:
            print(f"  phase: {state.current_phase or '(not set)'}")
            print(f"  milestone: {state.current_milestone or '(not set)'}")
            print(f"  signoff: {state.signoff_status or '(not set)'}")
        return 0
    if args.activate_agency:
        from renmark import agency as _agency
        from renmark import delivery_state as _delivery_state
        from renmark import mode as _mode

        agency_path = _agency.agency_state_path(repo)
        try:
            _agency.activate(repo)
            _mode.set_mode(repo, "agency")
        except (
            OSError,
            _agency.AgencyBloatError,
            _delivery_state.DeliveryStateBloatError,
        ) as exc:
            print(
                f"renmark: failed to activate Agency Mode at {agency_path}: {exc}",
                file=sys.stderr,
            )
            return 1
        print(f"renmark: Agency Mode activated ({agency_path})")
        return 0
    if args.deactivate_agency:
        from renmark import agency as _agency
        from renmark import delivery_state as _delivery_state
        from renmark import mode as _mode

        agency_path = _agency.agency_state_path(repo)
        try:
            _agency.deactivate(repo)
            _mode.set_mode(repo, "orchestrator")
        except (
            OSError,
            _agency.AgencyBloatError,
            _delivery_state.DeliveryStateBloatError,
        ) as exc:
            print(
                f"renmark: failed to deactivate Agency Mode at {agency_path}: {exc}",
                file=sys.stderr,
            )
            return 1
        print(f"renmark: Agency Mode deactivated ({agency_path})")
        return 0
    return None


def _dispatch_mode_read_flags(
    args: argparse.Namespace, ap: argparse.ArgumentParser, repo: Path
) -> int | None:
    """Handle --get-mode/--clear-mode."""
    if args.get_mode:
        from .. import mode as _mode

        state = _mode.read_delivery_state(repo)
        if state is None:
            print("unset")
        else:
            print(f"{state.delivery_mode} ({state.interaction_mode})")
        return 0
    if args.clear_mode:
        from .. import mode as _mode

        mode_path = _mode.delivery_state_path(repo)
        try:
            _mode.clear_mode(repo)
        except OSError as exc:
            print(
                f"renmark: failed to clear operating mode at {mode_path}: {exc}",
                file=sys.stderr,
            )
            return 1
        print(f"renmark: delivery mode cleared ({mode_path})")
        return 0
    return None


def _dispatch_compact_flags(args: argparse.Namespace, repo: Path) -> int | None:
    """Handle --compact-checkpoint/--get-compact-gate-tokens/--set-compact-gate-tokens."""
    if args.compact_checkpoint:
        _lifecycle.persist_compact_checkpoint(repo, skill="manual", reason="compact")
        print("Compact checkpoint written to .renmark/state/compact_checkpoint.json.")
        print("Run these commands to safely reduce context:")
        print("  1. /compact")
        print("  2. /renmark:resume")
        return 0
    if args.get_compact_gate_tokens:
        from renmark import config as _config

        val = _config.compact_gate_tokens(repo)
        if val == 0:
            print("compact_gate_tokens: 0 (gate disabled)")
        else:
            print(f"compact_gate_tokens: {val}")
        return 0
    if args.set_compact_gate_tokens is not None:
        if args.set_compact_gate_tokens < 0:
            print(
                f"error: compact_gate_tokens must be >= 0 "
                f"(got {args.set_compact_gate_tokens})",
                file=sys.stderr,
            )
            return 1
        from renmark import config as _config

        _config.set_compact_gate_tokens(repo, args.set_compact_gate_tokens)
        if args.set_compact_gate_tokens == 0:
            print("compact_gate_tokens set to 0 (gate disabled)")
        else:
            print(f"compact_gate_tokens set to {args.set_compact_gate_tokens}")
        return 0
    return None


def _dispatch_task_tracking_flags(args: argparse.Namespace, repo: Path) -> int | None:
    """Handle --task-create/--task-in-progress/--task-complete (REQ-31 Codex
    live-session task tracking; cross-host-native-tool-leverage Release 4).

    Wraps renmark.task_tracking for a live, interactive Codex session, which has
    no native TaskCreate/TaskUpdate tool of its own. Tags every task it creates
    with source="codex-live" to distinguish from the pre-existing headless
    renmark-execute subprocess path (source="codex-headless").
    """
    if args.task_create:
        rec = _task_tracking.create_or_reuse_task(
            repo,
            args.task_create,
            title=args.title or "",
            role=args.role or "",
            scope=args.scope or "",
            verification_expectation=args.verification_expectation or "",
            parent_id=args.parent_id,
            source="codex-live",
        )
        print(f"task {rec.task_id} tracked (status={rec.status})")
        return 0
    if args.task_in_progress:
        try:
            rec = _task_tracking.mark_in_progress(repo, args.task_in_progress)
        except _task_tracking.UnknownTaskError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"task {rec.task_id} in_progress")
        return 0
    if args.task_complete:
        try:
            rec = _task_tracking.complete_task(
                repo,
                args.task_complete,
                artifact_path=args.artifact_path or "",
                result_summary=args.result_summary or "",
            )
        except (_task_tracking.UnknownTaskError, _task_tracking.MissingEvidenceError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"task {rec.task_id} completed (artifact={rec.artifact_path})")
        return 0
    return None


def _dispatch_artifact_hygiene_flags(
    args: argparse.Namespace, repo: Path
) -> int | None:
    """Handle --artifact-hygiene/--artifact-hygiene-apply."""
    if args.artifact_hygiene:
        hygiene.main(
            ["all", "--repo", str(repo)]
            + (["--apply"] if args.artifact_hygiene_apply else [])
        )
        hygiene.main(["budget", "--repo", str(repo)])
        hygiene.main(["validate", "--repo", str(repo)])
        return 0
    return None


def _dispatch_handoff_flags(
    args: argparse.Namespace, ap: argparse.ArgumentParser, repo: Path
) -> int | None:
    """Handle --task-brief/--review-package."""
    if args.task_brief:
        plan_path, task_index_str = args.task_brief
        try:
            task_index = int(task_index_str)
        except ValueError:
            ap.error(f"--task-brief TASK_INDEX must be an integer, got {task_index_str!r}")
        return cmd_task_brief(plan_path, task_index, repo=repo)
    if args.review_package:
        base_ref, head_ref = args.review_package
        return cmd_review_package(base_ref, head_ref, repo=repo)
    return None
