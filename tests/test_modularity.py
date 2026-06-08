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

import ast
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


def _func_with_measured_code_lines(n: int) -> str:
    """A module with one function ``f`` whose MEASURED code lines equal ``n``.

    The analyzer counts the ``def`` signature line plus each body code line (it
    spans the function's own start through ``end_lineno``, nested defs excluded),
    so for a measured total of ``n`` we emit the signature line plus ``n - 1``
    single-line body assignments. ``n`` must be >= 1.
    """
    assert n >= 1
    body = "\n".join(f"    s{i} = {i}" for i in range(n - 1))
    if body:
        return f"def f():\n{body}\n"
    return "def f(): pass\n"


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


def test_func_loc_exactly_warn_is_warn(tmp_path: Path) -> None:
    """EXACTLY at the warn threshold trips warn (>= boundary, off-by-one guard)."""
    repo = tmp_path / "repo"
    _write(repo, "src/warnfn.py", _func_with_measured_code_lines(FUNC_LOC_WARN))
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_func_loc_just_over_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/longfn.py", _func_with_measured_code_lines(FUNC_LOC_WARN + 1))
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_func_loc_exactly_major_is_danger(tmp_path: Path) -> None:
    """EXACTLY at the major threshold trips danger (>= boundary, off-by-one guard)."""
    repo = tmp_path / "repo"
    _write(repo, "src/majorfn.py", _func_with_measured_code_lines(FUNC_LOC_MAJOR))
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_func_loc_just_over_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/hugefn.py", _func_with_measured_code_lines(FUNC_LOC_MAJOR + 1))
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_func_loc_just_under_warn_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/okfn.py", _func_with_measured_code_lines(FUNC_LOC_WARN - 1))
    assert _gaps_for(repo, title_contains="Long function") == []


def test_func_loc_signature_counted_and_nested_def_excluded(tmp_path: Path) -> None:
    """Major1 regression: the signature line is counted; nested defs are NOT.

    The outer function owns its ``def`` line + 1 body statement = 2 lines; the
    nested ``inner`` def's lines belong to ``inner``, not the outer. With the
    pre-fix bug the outer would have either dropped its signature or swallowed
    ``inner``'s body. We assert the measured outer LOC by tuning thresholds via
    a body sized to sit exactly on FUNC_LOC_WARN once the signature is added and
    the nested block is excluded.
    """
    # outer owns: def line (1) + (WARN-1) body assignments = WARN measured.
    # A fat nested def whose body is huge must NOT inflate the outer count.
    outer_body = "\n".join(f"    a{i} = {i}" for i in range(FUNC_LOC_WARN - 1))
    nested = "\n".join("        " + f"b{i} = {i}" for i in range(FUNC_LOC_MAJOR + 50))
    src = f"def outer():\n{outer_body}\n    def inner():\n{nested}\n"
    repo = tmp_path / "repo"
    _write(repo, "src/nestfn.py", src)
    gaps = _gaps_for(repo, title_contains="Long function")
    # outer sits at exactly WARN (warn band); inner is far over MAJOR (danger).
    outer_gaps = [g for g in gaps if "outer()" in g.title]
    inner_gaps = [g for g in gaps if "inner()" in g.title]
    assert len(outer_gaps) == 1
    assert outer_gaps[0].severity == "warn", "outer must NOT swallow inner's body"
    assert len(inner_gaps) == 1
    assert inner_gaps[0].severity == "danger"


def test_func_loc_decorator_lines_counted(tmp_path: Path) -> None:
    """Major1 regression: decorator lines are part of the function's own span."""
    repo = tmp_path / "repo"
    # 2 decorator lines + def line + (WARN-3) body = WARN measured → warn band.
    body = "\n".join(f"    s{i} = {i}" for i in range(FUNC_LOC_WARN - 3))
    src = f"import functools\n\n@functools.cache\n@staticmethod\ndef f():\n{body}\n"
    _write(repo, "src/decofn.py", src)
    gaps = [g for g in _gaps_for(repo, title_contains="Long function") if "f()" in g.title]
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


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


# ── Exact-boundary (== threshold) off-by-one guards ────────────────────────────


def test_module_loc_exactly_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/m.py", _module_of_code_lines(MODULE_LOC_WARN))
    gaps = _gaps_for(repo, title_contains="Oversized module")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_module_loc_exactly_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/m.py", _module_of_code_lines(MODULE_LOC_MAJOR))
    gaps = _gaps_for(repo, title_contains="Oversized module")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_fanout_exactly_warn_is_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/f.py", _module_with_imports(FANOUT_WARN))
    gaps = _gaps_for(repo, title_contains="import fan-out")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_fanout_exactly_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/f.py", _module_with_imports(FANOUT_MAJOR))
    gaps = _gaps_for(repo, title_contains="import fan-out")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_cyclomatic_exactly_warn_is_warn(tmp_path: Path) -> None:
    # value = #ifs + 1; value == CYCLO_WARN ⇒ ifs = CYCLO_WARN - 1.
    repo = tmp_path / "repo"
    _write(repo, "src/c.py", _func_with_flat_ifs(CYCLO_WARN - 1))
    gaps = _gaps_for(repo, title_contains="cyclomatic")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_cyclomatic_exactly_major_is_danger(tmp_path: Path) -> None:
    # value == CYCLO_MAJOR ⇒ ifs = CYCLO_MAJOR - 1.
    repo = tmp_path / "repo"
    _write(repo, "src/c.py", _func_with_flat_ifs(CYCLO_MAJOR - 1))
    gaps = _gaps_for(repo, title_contains="cyclomatic")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


def test_cognitive_exactly_warn_is_warn(tmp_path: Path) -> None:
    # flat ifs: cognitive == #ifs; cognitive == COGNITIVE_WARN ⇒ ifs = COGNITIVE_WARN.
    repo = tmp_path / "repo"
    _write(repo, "src/cw.py", _func_with_flat_ifs(COGNITIVE_WARN))
    gaps = _gaps_for(repo, title_contains="cognitive")
    assert len(gaps) == 1
    assert gaps[0].severity == "warn"


def test_cognitive_exactly_major_is_danger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/cm.py", _func_with_flat_ifs(COGNITIVE_MAJOR))
    gaps = _gaps_for(repo, title_contains="cognitive")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


# ── Major3: comment-only generated markers suppress; docstring mentions do NOT ──


def test_docstring_mention_of_generated_is_still_analyzed(tmp_path: Path) -> None:
    """A hand-written module whose DOCSTRING says 'generated by' is STILL flagged.

    This is the verified false-negative from the review: a real module that
    merely mentions a generated-marker phrase in prose/docstring must not be
    suppressed. The long function inside must still produce a Long-function gap.
    """
    repo = tmp_path / "repo"
    long_body = "\n".join(f"    s{i} = {i}" for i in range(FUNC_LOC_MAJOR + 10))
    src = (
        '"""This report was generated by hand. Do not edit casually — but it IS\n'
        'maintained by humans, so the analyzer must still inspect it."""\n'
        f"def big():\n{long_body}\n"
    )
    _write(repo, "src/has_prose.py", src)
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1, "a docstring mention must NOT suppress the file"
    assert gaps[0].severity == "danger"


def test_comment_header_generated_file_is_suppressed(tmp_path: Path) -> None:
    """A true ``# Code generated by ...`` comment-header file IS suppressed."""
    repo = tmp_path / "repo"
    long_body = "\n".join(f"    s{i} = {i}" for i in range(FUNC_LOC_MAJOR + 10))
    src = (
        "# Code generated by protoc. DO NOT EDIT.\n"
        f"def big():\n{long_body}\n"
    )
    _write(repo, "src/pb.py", src)
    assert analyze(repo) == [], "a comment-header generated file must be suppressed"


def test_string_literal_mention_of_generated_is_still_analyzed(tmp_path: Path) -> None:
    """A marker phrase inside a string assignment (not a comment) does NOT suppress."""
    repo = tmp_path / "repo"
    long_body = "\n".join(f"    s{i} = {i}" for i in range(FUNC_LOC_MAJOR + 10))
    src = 'BANNER = "automatically generated header text"\n' + f"def big():\n{long_body}\n"
    _write(repo, "src/strlit.py", src)
    gaps = _gaps_for(repo, title_contains="Long function")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"


# ── Minor1: only 'tests'/'__tests__' dirs suppress, not 'test' (production) ─────


def test_src_test_singular_dir_is_analyzed(tmp_path: Path) -> None:
    """``src/test/foo.py`` is a production package — it must be analyzed, not skipped."""
    repo = tmp_path / "repo"
    _write(repo, "src/test/foo.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))
    gaps = _gaps_for(repo, title_contains="Oversized module")
    assert len(gaps) == 1
    assert gaps[0].severity == "danger"
    assert "test/foo.py" in gaps[0].title


def test_tests_dir_is_suppressed(tmp_path: Path) -> None:
    """``tests/foo.py`` under a real test tree is suppressed."""
    repo = tmp_path / "repo"
    _write(repo, "tests/foo.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))
    assert analyze(repo) == []


def test_dunder_tests_dir_is_suppressed(tmp_path: Path) -> None:
    """``__tests__/foo.py`` (JS-style) under a test tree is suppressed."""
    repo = tmp_path / "repo"
    _write(repo, "__tests__/foo.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))
    assert analyze(repo) == []


# ── Never-raise on a walk/read failure (monkeypatched) ─────────────────────────


def test_never_raises_on_walk_failure(tmp_path: Path, monkeypatch) -> None:
    """If the file walk explodes, analyze() degrades to [] rather than raising."""
    repo = tmp_path / "repo"
    _write(repo, "src/big.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))

    def _boom(_repo: Path) -> list:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(modularity, "_walk_python_files", _boom)
    assert analyze(repo) == []  # must not raise


def test_never_raises_on_per_file_read_failure(tmp_path: Path, monkeypatch) -> None:
    """A read failure on one file is swallowed; the scan does not raise."""
    repo = tmp_path / "repo"
    _write(repo, "src/big.py", _module_of_code_lines(MODULE_LOC_MAJOR + 1))

    def _boom(_path: Path, _repo: Path) -> list:
        raise OSError("permission denied")

    monkeypatch.setattr(modularity, "_analyze_file", _boom)
    assert analyze(repo) == []  # the per-file try/except swallows it


# ── Branch-math fixtures: BoolOp, comprehension-if, match/case, try/except ──────


def _cyclomatic_of(src: str) -> int:
    """Parse ``src`` (one top-level ``def f``) and return its cyclomatic count."""
    tree = ast.parse(src)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    return modularity._cyclomatic(func)


def _cognitive_of(src: str) -> int:
    tree = ast.parse(src)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    return modularity._cognitive(func)


def test_boolop_longer_chain_scores_higher_cyclomatic() -> None:
    """Major2 sanity: a longer ``and`` chain must score strictly higher."""
    short = _cyclomatic_of("def f(a, b):\n    return a and b\n")
    long = _cyclomatic_of("def f(a, b, c, d):\n    return a and b and c and d\n")
    assert long > short, "a longer boolean chain must increase cyclomatic count"
    # 2 operands → +1 branch (base 1 + 1 = 2); 4 operands → +3 (base 1 + 3 = 4).
    assert short == 2
    assert long == 4


def test_boolop_longer_chain_scores_higher_cognitive() -> None:
    """Major2 fix: cognitive must also reward a longer boolean chain."""
    short = _cognitive_of("def f(a, b):\n    return a and b\n")
    long = _cognitive_of("def f(a, b, c, d):\n    return a and b and c and d\n")
    assert long > short, "a longer boolean chain must increase cognitive score"
    assert short == 1  # 2 operands → 1 branch
    assert long == 3  # 4 operands → 3 branches


def test_comprehension_if_counted() -> None:
    """A comprehension ``if`` is a decision point for both metrics."""
    src = "def f(xs):\n    return [x for x in xs if x > 0]\n"
    assert _cyclomatic_of(src) == 2  # base 1 + one comprehension if
    assert _cognitive_of(src) == 1


def test_match_case_counted() -> None:
    """Each ``match`` ``case`` clause is a branch (Python 3.10+)."""
    src = (
        "def f(x):\n"
        "    match x:\n"
        "        case 1:\n"
        "            return 'a'\n"
        "        case 2:\n"
        "            return 'b'\n"
        "        case _:\n"
        "            return 'c'\n"
    )
    # cyclomatic: base 1 + 3 case clauses = 4.
    assert _cyclomatic_of(src) == 4
    # cognitive: each case is a nesting construct at the top level → 1 each = 3.
    assert _cognitive_of(src) == 3


def test_try_except_counted() -> None:
    """Each ``except`` handler is a branch for both metrics."""
    src = (
        "def f():\n"
        "    try:\n"
        "        return g()\n"
        "    except ValueError:\n"
        "        return 1\n"
        "    except KeyError:\n"
        "        return 2\n"
    )
    # cyclomatic: base 1 + 2 except handlers = 3.
    assert _cyclomatic_of(src) == 3
    # cognitive: 2 except handlers at top level → 1 each = 2.
    assert _cognitive_of(src) == 2
