<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-07-09 @ 3af1dce -->

# Dev standards — ai-system

What this project enforces about itself, detected from configuration files. Read this before making non-trivial changes so you don't break gates that are silently checking your work.

## Detected standards

| Standard | Command | Detected in | Notes |
|---|---|---|---|
| test | `pytest -q` | `pyproject.toml` | pytest in deps |
| lint | `ruff check` | `pyproject.toml` | — |
| format | `ruff format` | `pyproject.toml` | — |
| typecheck | `mypy .` | `pyproject.toml` | — |
| ci | — | `.github/workflows/` | GitHub Actions: test |
| env | — | `.env.example` | empty |

## Standards health

✅ **No gaps detected.** Linter, type checker, tests, and CI are all wired up.
## Modularity

**372 modularity gaps** (10 major, 362 warn) — file-level size/complexity breaches. Advisory: these never block init.

- 🚨 **High import fan-out: `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` (40 imports)** — `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` has 40 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **Long function: `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` → `execute_plan()` (117 code lines)** — `execute_plan()` in `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` spans 117 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `execute_plan()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` → `execute_plan()` (20 branches)** — `execute_plan()` in `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` has a cyclomatic branch count of 20 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `execute_plan()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` → `execute_plan()` (score 31)** — `execute_plan()` in `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` has a nesting-weighted cognitive-complexity score of 31 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `execute_plan()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` → `main()` (189 code lines)** — `main()` in `.claude/worktrees/heartbeat-proactive-scheduler/renmark/cli/_engine.py` spans 189 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `main()` into well-named helpers. Advisory._
- 🚨 **High import fan-out: `renmark/cli/_engine.py` (40 imports)** — `renmark/cli/_engine.py` has 40 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `renmark/cli/_engine.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **Long function: `renmark/cli/_engine.py` → `execute_plan()` (117 code lines)** — `execute_plan()` in `renmark/cli/_engine.py` spans 117 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `execute_plan()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/cli/_engine.py` → `execute_plan()` (20 branches)** — `execute_plan()` in `renmark/cli/_engine.py` has a cyclomatic branch count of 20 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `execute_plan()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/cli/_engine.py` → `execute_plan()` (score 31)** — `execute_plan()` in `renmark/cli/_engine.py` has a nesting-weighted cognitive-complexity score of 31 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `execute_plan()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/cli/_engine.py` → `main()` (189 code lines)** — `main()` in `renmark/cli/_engine.py` spans 189 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `main()` into well-named helpers. Advisory._
- ⚠ **Oversized module: `renmark/health.py` (587 code lines)** — `renmark/health.py` has 587 code lines (threshold 500). Large modules are hard to navigate, review, and test, and tend to accrete unrelated responsibilities. _Split `renmark/health.py` into focused modules along its natural seams (one cohesive responsibility per file). Advisory — never auto-refactored._
- ⚠ **High cyclomatic complexity: `renmark/health.py` → `_detect_test()` (14 branches)** — `_detect_test()` in `renmark/health.py` has a cyclomatic branch count of 14 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `_detect_test()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- ⚠ **High cognitive complexity: `renmark/health.py` → `_detect_test()` (score 20)** — `_detect_test()` in `renmark/health.py` has a nesting-weighted cognitive-complexity score of 20 (threshold 15). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_detect_test()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- ⚠ **High cyclomatic complexity: `renmark/health.py` → `_detect_lint()` (12 branches)** — `_detect_lint()` in `renmark/health.py` has a cyclomatic branch count of 12 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `_detect_lint()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- ⚠ **High cyclomatic complexity: `renmark/health.py` → `_detect_format()` (11 branches)** — `_detect_format()` in `renmark/health.py` has a cyclomatic branch count of 11 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `_detect_format()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- ⚠ **High cyclomatic complexity: `renmark/health.py` → `_detect_local_dev()` (11 branches)** — `_detect_local_dev()` in `renmark/health.py` has a cyclomatic branch count of 11 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `_detect_local_dev()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- ⚠ **High cognitive complexity: `renmark/health.py` → `_detect_local_dev()` (score 17)** — `_detect_local_dev()` in `renmark/health.py` has a nesting-weighted cognitive-complexity score of 17 (threshold 15). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_detect_local_dev()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- ⚠ **Long function: `renmark/health.py` → `render_standards_md()` (56 code lines)** — `render_standards_md()` in `renmark/health.py` spans 56 code lines (threshold 50). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `render_standards_md()` into well-named helpers. Advisory._
- ⚠ **High cyclomatic complexity: `renmark/health.py` → `render_standards_md()` (10 branches)** — `render_standards_md()` in `renmark/health.py` has a cyclomatic branch count of 10 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `render_standards_md()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- ⚠ **High cyclomatic complexity: `renmark/usage.py` → `read_limits()` (12 branches)** — `read_limits()` in `renmark/usage.py` has a cyclomatic branch count of 12 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `read_limits()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- _… +352 more (re-run for the full list)_


_Run `python -m renmark.init --deep` for deeper checks (commit-message style, etc.)._