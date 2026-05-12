"""Unit tests for renmark.apply."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from renmark import apply as apply_mod
from renmark.apply import (
    ApplyError,
    apply_mode_a,
    apply_mode_b,
    strip_markdown_fences,
)


def test_strip_fences_round_trip() -> None:
    raw = "```python\nprint('x')\n```\n"
    assert strip_markdown_fences(raw).strip() == "print('x')"


def test_strip_fences_no_fence() -> None:
    raw = "print('x')\n"
    assert strip_markdown_fences(raw).strip() == "print('x')"


def test_mode_a_writes_valid_python(tmp_path: Path) -> None:
    body = "PI = 3.14\nE = 2.718\n"
    res = apply_mode_a(tmp_path, "src/constants.py", body)
    target = tmp_path / "src" / "constants.py"
    assert target.is_file()
    assert target.read_text().strip() == body.strip()
    assert res.bytes_written > 0


def test_mode_a_rejects_bad_python(tmp_path: Path) -> None:
    bad = "def x(:\n  pass\n"
    with pytest.raises(ApplyError, match="syntax check"):
        apply_mode_a(tmp_path, "bad.py", bad)
    # And the target file must NOT exist after failure.
    assert not (tmp_path / "bad.py").exists()


def test_mode_a_rejects_empty(tmp_path: Path) -> None:
    with pytest.raises(ApplyError, match="empty"):
        apply_mode_a(tmp_path, "a.py", "   \n\n  ")


def test_mode_a_rejects_escaping_target(tmp_path: Path) -> None:
    with pytest.raises(ApplyError, match="escapes"):
        apply_mode_a(tmp_path, "../escapes.py", "x = 1\n")


def test_mode_a_unknown_extension_accepted(tmp_path: Path) -> None:
    res = apply_mode_a(tmp_path, "data.xyz", "anything goes here\n")
    assert (tmp_path / "data.xyz").read_text() == "anything goes here\n"
    assert res.bytes_written > 0


def test_mode_b_applies_clean_diff(tmp_path: Path) -> None:
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir(parents=True)
    target.write_text("def greet():\n    return 'hi'\n")
    diff = textwrap.dedent(
        """\
        --- src/app.py
        +++ src/app.py
        @@ -1,2 +1,2 @@
         def greet():
        -    return 'hi'
        +    return 'hi world'
        """
    )
    apply_mode_b(tmp_path, "src/app.py", diff)
    assert "hi world" in target.read_text()


def test_mode_b_rejects_non_diff(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("x = 1\n")
    with pytest.raises(ApplyError, match="not a unified diff"):
        apply_mode_b(tmp_path, "a.py", "just prose, not a diff")


def test_mode_b_rejects_diff_touching_other_files(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("x = 1\n")
    diff = textwrap.dedent(
        """\
        --- a.py
        +++ b.py
        @@ -1,1 +1,1 @@
        -x = 1
        +x = 2
        """
    )
    with pytest.raises(ApplyError, match="exactly one file"):
        apply_mode_b(tmp_path, "a.py", diff)


def test_mode_b_rejects_when_target_missing(tmp_path: Path) -> None:
    diff = "--- nope.py\n+++ nope.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"
    with pytest.raises(ApplyError, match="does not exist"):
        apply_mode_b(tmp_path, "nope.py", diff)


def test_mode_b_dry_run_rejects_garbage_hunk(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("alpha\nbeta\n")
    # Hunk claims to remove "zzz" which isn't there.
    diff = textwrap.dedent(
        """\
        --- a.py
        +++ a.py
        @@ -1,1 +1,1 @@
        -zzz
        +yyy
        """
    )
    with pytest.raises(ApplyError, match="dry-run"):
        apply_mode_b(tmp_path, "a.py", diff)
    # Target should be unchanged.
    assert target.read_text() == "alpha\nbeta\n"
