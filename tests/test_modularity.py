"""Unit tests for renmark.modularity — the advisory code-health analyzer.

Hermetic: every test writes tiny synthetic ``.py`` files into ``tmp_path`` and
calls :func:`renmark.modularity.analyze`. Thresholds are imported as module
constants so tuning them never silently breaks (or silently passes) these tests.

For each of the 5 metrics we assert the band boundaries:

- JUST OVER the warn threshold → a Gap with ``severity == "warn"``
- JUST OVER the major threshold → a Gap with ``severity == "danger"``
- JUST UNDER the warn threshold → NO gap for that metric

Plus false-positive suppression, the never-raise contract, and a cognitive-vs-
cyclomatic sanity check that nesting is weighted.
"""

from __future__ import annotations

from pathlib import Path

from renmark import modularity
from renmark.modularity import (
    COGNITIVE_MAJOR,
    COGNITIVE_WARN,
    CYCLO_MAJOR,
    CYCLO_WARN,
    FANOUT_MAJOR,
    FANOUT_WARN,
    FUNC_LOC_MAJOR,
    FUNC_LOC_WARN,
    MODULE_LOC_MAJOR,
    MODULE_LOC_WARN,
    analyze,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _write(repo: Path, rel: str, body: str) -> Path:
    """Write ``body`` to ``repo/rel`` (creating parents) and return the path."""
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _gaps_for(repo: Path, *, title_contains: str) -> list:
    """Gaps whose title contains ``title_contains`` (one metric's gaps)."""
    return [g for g in analyze(repo) if title_contains in g.title]


def _module_of_code_lines(n: int) -> str:
    """A module whose code-line count is exactly ``n`` (one assignment per line).

    No docstring, no blanks, no comments — every physical line is a code line.
    """
    return "\n".join(f"v{i} = {i}" for i in range(n)) + "\n"


def _func_with_body_code_lines(n: int) -> str:
    """A module with one function ``f`` whose BODY has exactly ``n`` code lines.

    The ``def`` signature line is not counted by the analyzer (it spans the
    function's first body statement onward), so the file is the signature plus
    ``n`` body assignment statements.
    """
    body = "\n".join(f"    s{i} = {i}" for i in range(n))
    return f"def f():\n{body}\n"


def _func_with_flat_ifs(n: int) -> str:
    """A function with ``n`` sibling (non-nested) ``if`` statements.

    Cyclomatic = n + 1 (base 1 + one per ``if``). Cognitive = n (each flat
    ``if`` adds ``1 + 0`` nesting). Each body is a single ``pass``.
    """
    lines = ["def f():"]
    for i in range(n):
        lines.append(f"    if v{i}:")
        lines.append("        pass")
    return "\n".join(lines) + "\n"


def _func_with_nested_ifs(depth: int) -> str:
    """A function with ``if`` statements nested ``depth`` levels deep.

    Cyclomatic = depth + 1 (one decision point per ``if``, flat or nested).
    Cognitive is nesting-weighted: level k (0-indexed) adds ``1 + k``, so total
    cognitive = sum(1..depth) = depth*(depth+1)/2 — far above the raw branch
    count. This is the lever that distinguishes cognitive from cyclomatic.
    """
    lines = ["def f():"]
    for k in range(depth):
        lines.append("    " * (k + 1) + f"if c{k}:")
    lines.append("    " * (depth + 1) + "pass")
    return "\n".join(lines) + "\n"


def _module_with_imports(n: int) -> str:
    """A module with ``n`` distinct import statements and nothing else of note."""
    return "\n".join(f"import os as o{i}" for i in range(n)) + "\n"


# ── Metric 1: module LOC ───────────────────────────────────────────────────────


def test_module_loc_just_over_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/big.py", _module_of_code_lines(MODULE_LOC_WARN + 1))
    gaps = _gaps_for(repo, title_contains="Oversized module")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_module_loc_just_over_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/huge.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))
    gaps = _gaps_for(repo, title_contains="Oversized module")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_module_loc_just_under_warn_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/ok.py", _module_of_code_lines(MODULE_LOC_WARN - 1))
    assert _gaps_for(repo, title_contains="Oversized module") == []


# ── Metric 2: function length ──────────────────────────────────────────────────


def test_func_loc_just_over_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/longfn.py", _func_with_body_code_lines(FUNC_LOC_WARN + 1))
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_func_loc_just_over_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/hugefn.py", _func_with_body_code_lines(FUNC_LOC_MAJOR + 1))
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_func_loc_just_under_warn_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/okfn.py", _func_with_body_code_lines(FUNC_LOC_WARN - 1))
    assert _gaps_for(repo, title_contains="Long function") == []


# ── Metric 3: cyclomatic complexity ────────────────────────────────────────────
# cyclomatic = (#ifs) + 1, so #ifs == value - 1.


def test_cyclomatic_just_over_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    # value = CYCLO_WARN + 1  ⇒  ifs = CYCLO_WARN
    _write(repo, "src/cyclo_w.py", _func_with_flat_ifs(CYCLO_WARN))
    gaps = _gaps_for(repo, title_contains="cyclomatic")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_cyclomatic_just_over_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    # value = CYCLO_MAJOR + 1  ⇒  ifs = CYCLO_MAJOR
    _write(repo, "src/cyclo_m.py", _func_with_flat_ifs(CYCLO_MAJOR))
    gaps = _gaps_for(repo, title_contains="cyclomatic")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_cyclomatic_just_under_warn_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    # value = CYCLO_WARN - 1  ⇒  ifs = CYCLO_WARN - 2
    _write(repo, "src/cyclo_ok.py", _func_with_flat_ifs(CYCLO_WARN - 2))
    assert _gaps_for(repo, title_contains="cyclomatic") == []


# ── Metric 4: import fan-out ───────────────────────────────────────────────────


def test_fanout_just_over_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/coupled_w.py", _module_with_imports(FANOUT_WARN + 1))
    gaps = _gaps_for(repo, title_contains="import fan-out")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_fanout_just_over_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/coupled_m.py", _module_with_imports(FANOUT_MAJOR + 1))
    gaps = _gaps_for(repo, title_contains="import fan-out")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_fanout_just_under_warn_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/coupled_ok.py", _module_with_imports(FANOUT_WARN - 1))
    assert _gaps_for(repo, title_contains="import fan-out") == []


# ── Metric 5: cognitive complexity ─────────────────────────────────────────────
# flat ifs: cognitive == #ifs (each adds 1 + 0). So #ifs == value.


def test_cognitive_just_over_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/cog_w.py", _func_with_flat_ifs(COGNITIVE_WARN + 1))
    gaps = _gaps_for(repo, title_contains="cognitive")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_cognitive_just_over_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/cog_m.py", _func_with_flat_ifs(COGNITIVE_MAJOR + 1))
    gaps = _gaps_for(repo, title_contains="cognitive")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_cognitive_just_under_warn_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    # COGNITIVE_WARN - 1 flat ifs.  cyclomatic = (WARN-1)+1 = WARN, which is
    # itself at the cyclomatic-warn boundary, but here we only assert there is
    # no COGNITIVE gap. (COGNITIVE_WARN=15 > CYCLO_WARN=10, so a cyclo gap may
    # legitimately appear — we scope the assertion to the cognitive metric.)
    _write(repo, "src/cog_ok.py", _func_with_flat_ifs(COGNITIVE_WARN - 1))
    assert _gaps_for(repo, title_contains="cognitive") == []


# ── Cognitive vs cyclomatic: nesting is weighted ───────────────────────────────


def test_nesting_trips_cognitive_below_flat_branch_count(tmp_path: Path) -> None:
    """A deeply-nested function trips cognitive at a lower raw-branch count.

    With ``depth`` nested ``if``s the raw branch count (cyclomatic) is only
    ``depth + 1``, but cognitive is ``depth*(depth+1)/2``. We pick the smallest
    depth whose nesting-weighted score clears COGNITIVE_WARN while its raw
    branch count stays at or below CYCLO_WARN — proving cognitive penalizes
    nesting that cyclomatic ignores.
    """
    # smallest depth with depth*(depth+1)/2 > COGNITIVE_WARN
    depth = 1
    while depth * (depth + 1) // 2 <= COGNITIVE_WARN:
        depth += 1
    raw_branches = depth + 1  # cyclomatic value for nested ifs

    repo = tmp_path / "repo"
    _write(repo, "src/nested.py", _func_with_nested_ifs(depth))

    cog = _gaps_for(repo, title_contains="cognitive")
    assert len(cog) == 1, "deep nesting must trip cognitive complexity"

    # Sanity: the SAME raw branch count laid out FLAT must NOT trip cognitive,
    # because flat ifs add only 1 each (no nesting weight). raw_branches flat
    # ifs ⇒ cognitive == raw_branches; this stays under COGNITIVE_WARN.
    assert raw_branches <= COGNITIVE_WARN, (
        "test fixture invalid: flat equivalent would itself exceed cognitive warn"
    )
    repo_flat = tmp_path / "repo_flat"
    _write(repo_flat, "src/flat.py", _func_with_flat_ifs(raw_branches))
    assert _gaps_for(repo_flat, title_contains="cognitive") == [], (
        "the same branch count laid out flat must NOT trip cognitive — "
        "this is the proof that nesting is weighted"
    )


# ── False-positive suppression ─────────────────────────────────────────────────


def test_oversized_file_under_tests_path_not_flagged(tmp_path: Path) -> None:
    """A huge file under a ``tests/`` tree is suppressed entirely."""
    repo = tmp_path / "repo"
    # Way over the major module threshold, but under tests/ → no gaps at all.
    _write(repo, "tests/test_huge.py", _module_of_code_lines(MODULE_LOC_MAJOR + 50))
    assert analyze(repo) == []


def test_init_py_excluded_from_fanout(tmp_path: Path) -> None:
    """An ``__init__.py`` with > FANOUT_MAJOR imports is NOT flagged for fan-out.

    Re-export hubs legitimately import a lot. The module is still otherwise
    valid; we assert specifically that no fan-out gap is emitted.
    """
    repo = tmp_path / "repo"
    _write(repo, "src/__init__.py", _module_with_imports(FANOUT_MAJOR + 5))
    assert _gaps_for(repo, title_contains="import fan-out") == []


# ── Never-raise contract ───────────────────────────────────────────────────────


def test_syntax_error_file_skipped_valid_files_still_analyzed(tmp_path: Path) -> None:
    """A SyntaxError file is skipped; analyze() does not raise and still flags valid files."""
    repo = tmp_path / "repo"
    # Unparseable file in the tree.
    _write(repo, "src/broken.py", "def f(:\n    this is not python\n")
    # A valid file that SHOULD be flagged (over module-LOC major).
    _write(repo, "src/valid_huge.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))

    gaps = analyze(repo)  # must not raise
    oversized = [g for g in gaps if "Oversized module" in g.title]
    assert len(oversized) == 1
    assert oversized[0].severity == "danger"
    # And the breach is attributed to the valid file, not the broken one.
    assert "valid_huge.py" in oversized[0].title


def test_empty_repo_returns_no_gaps(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert analyze(repo) == []


def test_analyze_accepts_str_path(tmp_path: Path) -> None:
    """analyze() accepts a str path as well as a Path."""
    repo = tmp_path / "repo"
    _write(repo, "src/big.py", _module_of_code_lines(MODULE_LOC_WARN + 1))
    gaps = analyze(str(repo))
    assert any("Oversized module" in g.title for g in gaps)
