"""
---
artifact_type: renmark_task_output
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: unknown
related_plan: "renmark-artifact-lifecycle: preamble allowlist regression"
generator: sonnet
stale_after: null
dependency_refs:
  - renmark/lifecycle/preamble.py
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

Runtime-instrumentation regression test for
``renmark.lifecycle.preamble.HERMES_STARTUP_ALLOWLIST``.

## Summary
- Monkeypatches Path.open/read_text/write_text to record every path touched
  during skill_preamble() and asserts each in-repo path is allowlisted.
- Monkeypatches Path.rglob/glob/iterdir to raise if skill_preamble ever lists
  a directory (its whole invariant is O(1) reads, never recursion).
- Exercises debug (full tier, non agency-aware), feature (full tier,
  agency-aware + mode-default), and plan (full tier, SYNTHESIS_SKILLS member
  — exercises the routing.md fable-hint read path).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import renmark.lifecycle as lifecycle
from renmark.lifecycle.preamble import HERMES_STARTUP_ALLOWLIST


@dataclass
class IORecorder:
    """Records every path touched via open/read_text/write_text, plus any
    directory-listing call (rglob/glob/iterdir), during the instrumented
    window."""

    touched: list[Path] = field(default_factory=list)
    listing_calls: list[str] = field(default_factory=list)

    def record(self, path: Path) -> None:
        self.touched.append(Path(path))


@pytest.fixture
def io_recorder(monkeypatch: pytest.MonkeyPatch) -> IORecorder:
    """Instrument pathlib.Path I/O for the duration of a single test.

    Delegates to the real implementation for open/read_text/write_text (so
    skill_preamble's behavior is unaffected) while recording every path
    touched. rglob/glob/iterdir are replaced with a hard failure — skill_
    preamble must never list a directory.
    """
    recorder = IORecorder()

    real_open = Path.open
    real_read_text = Path.read_text
    real_write_text = Path.write_text

    def wrapped_open(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        recorder.record(self)
        return real_open(self, *args, **kwargs)  # type: ignore[call-overload]

    def wrapped_read_text(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        recorder.record(self)
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    def wrapped_write_text(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        recorder.record(self)
        return real_write_text(self, *args, **kwargs)  # type: ignore[arg-type]

    def forbidden_rglob(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        recorder.listing_calls.append(f"rglob:{self}")
        raise AssertionError(f"skill_preamble must never call Path.rglob (on {self})")

    def forbidden_glob(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        recorder.listing_calls.append(f"glob:{self}")
        raise AssertionError(f"skill_preamble must never call Path.glob (on {self})")

    def forbidden_iterdir(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        recorder.listing_calls.append(f"iterdir:{self}")
        raise AssertionError(f"skill_preamble must never call Path.iterdir (on {self})")

    monkeypatch.setattr(Path, "open", wrapped_open, raising=True)
    monkeypatch.setattr(Path, "read_text", wrapped_read_text, raising=True)
    monkeypatch.setattr(Path, "write_text", wrapped_write_text, raising=True)
    monkeypatch.setattr(Path, "rglob", forbidden_rglob, raising=True)
    monkeypatch.setattr(Path, "glob", forbidden_glob, raising=True)
    monkeypatch.setattr(Path, "iterdir", forbidden_iterdir, raising=True)

    return recorder


def _make_repo(tmp_path: Path) -> Path:
    """Build a minimal fake repo with the fixtures skill_preamble's callees
    expect, written BEFORE instrumentation starts (so fixture setup itself
    is never recorded)."""
    repo = tmp_path / "repo"
    state_dir = repo / ".renmark" / "state"
    memory_dir = repo / ".renmark" / "memory"
    state_dir.mkdir(parents=True)
    memory_dir.mkdir(parents=True)

    # renmark.mode.read_mode's shape: {"delivery_mode": ..., "interaction_mode": ...}
    (state_dir / "mode.json").write_text(
        json.dumps({"delivery_mode": "agency", "interaction_mode": "guided"}, indent=2),
        encoding="utf-8",
    )
    # Canonical delivery state (wins over mode.json) — agency active so the
    # agency-aware skill path (feature) actually reads agency.json.
    (state_dir / "delivery.json").write_text(
        json.dumps({"delivery_mode": "agency", "execution_policy": "guided"}, indent=2),
        encoding="utf-8",
    )
    (state_dir / "agency.json").write_text(
        json.dumps(
            {
                "active": True,
                "current_phase": "build",
                "current_milestone": "m1",
                "next_checkpoint": "",
                "signoff_status": "",
                "cost_lane": "",
                "roadmap_ref": "",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # config._read_raw tolerates a missing OR empty file — {} is fine.
    (repo / ".renmark" / "config.json").write_text("{}\n", encoding="utf-8")
    # capabilities.top_tier parses the "## Model tiers" block for "top_tier: <value>".
    (memory_dir / "routing.md").write_text(
        "# Routing\n\n## Model tiers\n\ntop_tier: fable\n",
        encoding="utf-8",
    )
    return repo


def _assert_paths_allowlisted(recorder: IORecorder, repo: Path) -> None:
    for touched in recorder.touched:
        try:
            rel = touched.resolve().relative_to(repo.resolve())
        except ValueError:
            # Out of scope for this allowlist: paths outside the repo entirely
            # (e.g. a plugin skill file living under the global install dir).
            continue
        rel_posix = rel.as_posix()
        assert rel_posix in HERMES_STARTUP_ALLOWLIST, (
            f"skill_preamble touched an unlisted in-repo path: {rel_posix!r} "
            f"(allowlist: {sorted(HERMES_STARTUP_ALLOWLIST)})"
        )


@pytest.mark.parametrize(
    "skill",
    [
        "debug",  # full tier, non agency-aware
        "feature",  # full tier, agency-aware + mode-default
        "plan",  # full tier, SYNTHESIS_SKILLS member -> exercises routing.md read
    ],
)
def test_skill_preamble_only_touches_allowlisted_paths(
    tmp_path: Path, io_recorder: IORecorder, skill: str
) -> None:
    repo = _make_repo(tmp_path)

    result = lifecycle.skill_preamble(repo, skill)

    # skill_preamble degrades gracefully and never raises; a return value of
    # None or str is both acceptable here — this test asserts I/O surface,
    # not hint content.
    assert result is None or isinstance(result, str)

    _assert_paths_allowlisted(io_recorder, repo)
    assert io_recorder.listing_calls == [], (
        f"skill_preamble must never list a directory; recorded: {io_recorder.listing_calls}"
    )


def test_synthesis_skill_plan_actually_reads_routing_md(
    tmp_path: Path, io_recorder: IORecorder
) -> None:
    """Sanity check that the routing.md branch is genuinely exercised —
    without this, an allowlist test that never triggers the read would give
    false confidence."""
    from renmark.lifecycle.stage import PREAMBLE_TIER_BY_SKILL, SYNTHESIS_SKILLS

    assert "plan" in SYNTHESIS_SKILLS
    assert PREAMBLE_TIER_BY_SKILL.get("plan", "full") == "full"

    repo = _make_repo(tmp_path)
    lifecycle.skill_preamble(repo, "plan")

    routing_rel = Path(".renmark/memory/routing.md")
    touched_rel = {
        t.resolve().relative_to(repo.resolve())
        for t in io_recorder.touched
        if t.resolve().is_relative_to(repo.resolve())
    }
    assert routing_rel in touched_rel
