"""Unit tests for renmark.lifecycle.milestone_context_checkpoint."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark.config import set_compact_gate_tokens
from renmark import lifecycle


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return tmp_path


def _checkpoint_path(repo: Path) -> Path:
    return repo / ".renmark" / "state" / "compact_checkpoint.json"


def test_milestone_context_checkpoint_ignores_missing_estimate(repo: Path) -> None:
    set_compact_gate_tokens(repo, 80_000)

    signal = lifecycle.milestone_context_checkpoint(repo, skill="feature")

    assert signal is None
    assert not _checkpoint_path(repo).exists()


def test_milestone_context_checkpoint_below_threshold(repo: Path) -> None:
    set_compact_gate_tokens(repo, 80_000)

    signal = lifecycle.milestone_context_checkpoint(
        repo,
        skill="feature",
        estimated_tokens=79_999,
        host="claude",
    )

    assert signal is None
    assert not _checkpoint_path(repo).exists()


def test_milestone_context_checkpoint_at_threshold_writes_checkpoint(repo: Path) -> None:
    set_compact_gate_tokens(repo, 80_000)

    signal = lifecycle.milestone_context_checkpoint(
        repo,
        skill="feature",
        estimated_tokens=80_000,
        host="claude",
    )

    assert signal is not None
    assert "/compact" in signal
    assert "/renmark:resume" in signal
    assert _checkpoint_path(repo).exists()


def test_milestone_context_checkpoint_disabled_threshold(repo: Path) -> None:
    set_compact_gate_tokens(repo, 0)

    signal = lifecycle.milestone_context_checkpoint(
        repo,
        skill="feature",
        estimated_tokens=1_000_000,
        host="claude",
    )

    assert signal is None
    assert not _checkpoint_path(repo).exists()


def test_milestone_context_checkpoint_never_raises_on_checkpoint_failure(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_compact_gate_tokens(repo, 80_000)

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(lifecycle, "persist_compact_checkpoint", boom)

    signal = lifecycle.milestone_context_checkpoint(
        repo,
        skill="feature",
        estimated_tokens=80_000,
        host="claude",
    )

    assert signal is None
