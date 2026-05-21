"""Shadow tests — record-and-replay regression detection for renmark
subsystems.

How it works:

    1. Each subsystem registers a deterministic ``replay(case)`` function
       that maps an input dict to an output dict. Pure, no side effects.
    2. Cases live in ``tests/shadow/cases/<subsystem>/case-*.json``.
    3. Baselines (last-known-good outputs) live in
       ``tests/shadow/baselines/<subsystem>/case-*.json``.
    4. ``shadow run`` replays every case through the current code and diffs
       against its baseline. Drift = exit 1.
    5. ``shadow accept`` re-records baselines after an intentional change.
       Forces the user to supply a ``-m`` message explaining WHY.

Use this before committing changes to load-bearing modules:

    python -m renmark.shadow run --subsystem dispatch
    python -m renmark.shadow accept --subsystem dispatch -m "tighten G3 cap"

Default ``run`` (no --subsystem) replays every registered subsystem.

Subsystems registered at v0.3.1:
    - dispatch    SubagentOutput parsing + validation
    - lifecycle   stage-transition state machine
    - summary     artifact metadata round-tripping
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# ── Registry ─────────────────────────────────────────────────────────────────

ReplayFn = Callable[[dict], dict]
_REGISTRY: dict[str, ReplayFn] = {}


def register(name: str) -> Callable[[ReplayFn], ReplayFn]:
    """Decorator: register a subsystem's replay function."""
    def deco(fn: ReplayFn) -> ReplayFn:
        _REGISTRY[name] = fn
        return fn
    return deco


def registered_subsystems() -> list[str]:
    return sorted(_REGISTRY.keys())


# ── Subsystem replay functions ───────────────────────────────────────────────


@register("dispatch")
def _replay_dispatch(case: dict) -> dict:
    """Input: {"response": <dict-or-string>}
    Output: SubagentOutput.to_dict() OR {"error": "...class.message"}"""
    from renmark.dispatch import parse_subagent_response, IsolationViolation

    response = case["response"]
    try:
        out = parse_subagent_response(response)
        return out.to_dict()
    except IsolationViolation as exc:
        return {"error": "IsolationViolation", "message": str(exc)}
    except Exception as exc:
        return {"error": type(exc).__name__, "message": str(exc)}


@register("lifecycle")
def _replay_lifecycle(case: dict) -> dict:
    """Input: {"calls": [{"stage": ..., "feature": ...}, ...]}
    Output: final lifecycle state (asdict) with last_updated stripped (non-deterministic).
    """
    from renmark import lifecycle as _lc
    from dataclasses import asdict

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        for call in case["calls"]:
            kwargs = dict(call)
            # artifact_update arrives as a list from JSON; convert to tuple.
            if isinstance(kwargs.get("artifact_update"), list):
                kwargs["artifact_update"] = tuple(kwargs["artifact_update"])
            _lc.write_lifecycle(repo, **kwargs)
        state = _lc.read_lifecycle(repo)
        d = asdict(state) if state else {}
        d.pop("last_updated", None)  # non-deterministic — strip
        return d


@register("summary")
def _replay_summary(case: dict) -> dict:
    """Input: {"metadata": {...}}
    Output: ArtifactMetadata serialized as a dict (deterministic — strip created_at).
    """
    from renmark.summary import ArtifactMetadata
    from dataclasses import asdict

    md_kwargs = dict(case["metadata"])
    # Inject a fixed created_at so output is deterministic.
    md_kwargs.setdefault("created_at", "2026-05-21T00:00:00+00:00")
    md = ArtifactMetadata(**md_kwargs)
    d = asdict(md)
    return d


# ── Run / accept ─────────────────────────────────────────────────────────────


@dataclass
class ShadowDiff:
    """One case's drift, if any. result is ``"match"``, ``"drift"``, or
    ``"missing-baseline"``."""
    subsystem: str
    case: str
    result: str
    expected: dict | None = None
    actual: dict | None = None
    error: str | None = None


def _shadow_root() -> Path:
    """The tests/shadow/ directory at the repo root."""
    here = Path(__file__).resolve()
    return here.parent.parent / "tests" / "shadow"


def _cases_dir(subsystem: str) -> Path:
    return _shadow_root() / "cases" / subsystem


def _baselines_dir(subsystem: str) -> Path:
    return _shadow_root() / "baselines" / subsystem


def list_cases(subsystem: str) -> list[Path]:
    return sorted(_cases_dir(subsystem).glob("case-*.json"))


def run_subsystem(subsystem: str) -> list[ShadowDiff]:
    """Replay every case for one subsystem, diff against baseline."""
    if subsystem not in _REGISTRY:
        raise KeyError(f"unknown subsystem {subsystem!r}; registered: {registered_subsystems()}")
    diffs: list[ShadowDiff] = []
    replay = _REGISTRY[subsystem]
    for case_path in list_cases(subsystem):
        case_name = case_path.stem
        baseline_path = _baselines_dir(subsystem) / case_path.name
        try:
            case_input = json.loads(case_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            diffs.append(ShadowDiff(subsystem, case_name, "error",
                                    error=f"failed to load case: {exc}"))
            continue

        try:
            actual = replay(case_input)
        except Exception as exc:
            diffs.append(ShadowDiff(subsystem, case_name, "error",
                                    error=f"replay raised {type(exc).__name__}: {exc}"))
            continue

        if not baseline_path.exists():
            diffs.append(ShadowDiff(subsystem, case_name, "missing-baseline",
                                    actual=actual))
            continue

        try:
            expected = json.loads(baseline_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            diffs.append(ShadowDiff(subsystem, case_name, "error",
                                    error=f"failed to load baseline: {exc}"))
            continue

        if _normalize(expected) == _normalize(actual):
            diffs.append(ShadowDiff(subsystem, case_name, "match"))
        else:
            diffs.append(ShadowDiff(subsystem, case_name, "drift",
                                    expected=expected, actual=actual))
    return diffs


def run_all() -> dict[str, list[ShadowDiff]]:
    return {sub: run_subsystem(sub) for sub in registered_subsystems()}


def accept_subsystem(subsystem: str, message: str) -> int:
    """Re-record baselines for a subsystem. Returns the number of baselines written."""
    if not message or not message.strip():
        raise ValueError("accept requires a non-empty message explaining the change")
    if subsystem not in _REGISTRY:
        raise KeyError(f"unknown subsystem {subsystem!r}")
    replay = _REGISTRY[subsystem]
    baselines_dir = _baselines_dir(subsystem)
    baselines_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for case_path in list_cases(subsystem):
        case_input = json.loads(case_path.read_text(encoding="utf-8"))
        actual = replay(case_input)
        baseline_path = baselines_dir / case_path.name
        baseline_path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
        count += 1

    # Prepend a CHANGES.md ledger entry below the header.
    changes_log = _shadow_root() / "CHANGES.md"
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    entry = f"## {ts} UTC — {subsystem}\n\n{message.strip()}\n\n"
    header = "# Shadow baseline changes\n\n"
    if changes_log.exists():
        existing = changes_log.read_text(encoding="utf-8")
        if existing.startswith(header):
            existing = existing[len(header):]
        changes_log.write_text(header + entry + existing, encoding="utf-8")
    else:
        changes_log.write_text(header + entry, encoding="utf-8")
    return count


# ── Helpers ──────────────────────────────────────────────────────────────────


def _normalize(value: Any) -> Any:
    """Sort dict keys recursively so ordering doesn't cause false drift."""
    if isinstance(value, dict):
        return {k: _normalize(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _format_dict_diff(expected: dict, actual: dict, indent: str = "    ") -> str:
    """Tiny per-key diff for human-readable run output."""
    lines: list[str] = []
    all_keys = sorted(set(expected.keys()) | set(actual.keys()))
    for k in all_keys:
        if k not in expected:
            lines.append(f"{indent}+ {k}: {actual[k]!r}")
        elif k not in actual:
            lines.append(f"{indent}- {k}: {expected[k]!r}")
        elif expected[k] != actual[k]:
            lines.append(f"{indent}~ {k}: {expected[k]!r} → {actual[k]!r}")
    return "\n".join(lines) or f"{indent}(structural diff; check full output)"


# ── CLI ──────────────────────────────────────────────────────────────────────


def _print_diffs(diffs: list[ShadowDiff], verbose: bool) -> int:
    drift_count = 0
    missing_count = 0
    error_count = 0
    for d in diffs:
        if d.result == "match":
            if verbose:
                sys.stdout.write(f"  ok    {d.subsystem}/{d.case}\n")
        elif d.result == "drift":
            drift_count += 1
            sys.stdout.write(f"  DRIFT {d.subsystem}/{d.case}\n")
            if isinstance(d.expected, dict) and isinstance(d.actual, dict):
                sys.stdout.write(_format_dict_diff(d.expected, d.actual) + "\n")
        elif d.result == "missing-baseline":
            missing_count += 1
            sys.stdout.write(f"  NEW   {d.subsystem}/{d.case} (no baseline — run accept)\n")
        elif d.result == "error":
            error_count += 1
            sys.stdout.write(f"  ERR   {d.subsystem}/{d.case}: {d.error}\n")
    return drift_count + missing_count + error_count


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.stderr.write(
            "usage: python -m renmark.shadow {run|accept|list} [--subsystem X] [-m MSG] [--verbose]\n"
        )
        return 2

    cmd = argv[0]
    subsystem: str | None = None
    message: str | None = None
    verbose = False
    i = 1
    while i < len(argv):
        if argv[i] == "--subsystem" and i + 1 < len(argv):
            subsystem = argv[i + 1]
            i += 2
        elif argv[i] == "-m" and i + 1 < len(argv):
            message = argv[i + 1]
            i += 2
        elif argv[i] == "--verbose":
            verbose = True
            i += 1
        else:
            sys.stderr.write(f"unknown arg: {argv[i]}\n")
            return 2

    if cmd == "list":
        for sub in registered_subsystems():
            n = len(list_cases(sub))
            sys.stdout.write(f"  {sub:12s}  {n} case{'s' if n != 1 else ''}\n")
        return 0

    if cmd == "run":
        targets = [subsystem] if subsystem else registered_subsystems()
        total_issues = 0
        for sub in targets:
            sys.stdout.write(f"\n→ shadow run: {sub}\n")
            try:
                diffs = run_subsystem(sub)
            except KeyError as exc:
                sys.stderr.write(f"  ERR {exc}\n")
                total_issues += 1
                continue
            total_issues += _print_diffs(diffs, verbose=verbose)
        if total_issues:
            sys.stderr.write(f"\nFAIL ({total_issues} drift/missing/error)\n")
            return 1
        sys.stdout.write(f"\nOK  all subsystems clean\n")
        return 0

    if cmd == "accept":
        if not subsystem:
            sys.stderr.write("accept requires --subsystem\n")
            return 2
        if not message:
            sys.stderr.write("accept requires -m MESSAGE explaining the change\n")
            return 2
        try:
            count = accept_subsystem(subsystem, message)
        except (KeyError, ValueError) as exc:
            sys.stderr.write(f"  ERR {exc}\n")
            return 1
        sys.stdout.write(f"OK  accepted {count} baseline{'s' if count != 1 else ''} for {subsystem}\n")
        return 0

    sys.stderr.write(f"unknown command: {cmd}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
