<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-06-09 @ 968fa02 -->

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

**133 modularity gaps** (21 major, 112 warn) — file-level size/complexity breaches. Advisory: these never block init.

- 🚨 **High cognitive complexity: `renmark/memory.py` → `_parse_learning_entries()` (score 32)** — `_parse_learning_entries()` in `renmark/memory.py` has a nesting-weighted cognitive-complexity score of 32 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_parse_learning_entries()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/release.py` → `main()` (26 branches)** — `main()` in `renmark/release.py` has a cyclomatic branch count of 26 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `main()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/release.py` → `main()` (score 48)** — `main()` in `renmark/release.py` has a nesting-weighted cognitive-complexity score of 48 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `main()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/bootstrap.py` → `bootstrap()` (108 code lines)** — `bootstrap()` in `renmark/bootstrap.py` spans 108 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `bootstrap()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/bootstrap.py` → `bootstrap()` (22 branches)** — `bootstrap()` in `renmark/bootstrap.py` has a cyclomatic branch count of 22 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `bootstrap()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/shadow.py` → `main()` (score 31)** — `main()` in `renmark/shadow.py` has a nesting-weighted cognitive-complexity score of 31 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `main()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/summary.py` → `read_metadata()` (score 34)** — `read_metadata()` in `renmark/summary.py` has a nesting-weighted cognitive-complexity score of 34 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `read_metadata()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Oversized module: `renmark/init.py` (1229 code lines)** — `renmark/init.py` has 1229 code lines (threshold 1000). Large modules are hard to navigate, review, and test, and tend to accrete unrelated responsibilities. _Split `renmark/init.py` into focused modules along its natural seams (one cohesive responsibility per file). Advisory — never auto-refactored._
- 🚨 **High cognitive complexity: `renmark/init.py` → `_file_purpose()` (score 30)** — `_file_purpose()` in `renmark/init.py` has a nesting-weighted cognitive-complexity score of 30 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_file_purpose()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/init.py` → `evaluate_health()` (166 code lines)** — `evaluate_health()` in `renmark/init.py` spans 166 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `evaluate_health()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/init.py` → `evaluate_health()` (39 branches)** — `evaluate_health()` in `renmark/init.py` has a cyclomatic branch count of 39 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `evaluate_health()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/init.py` → `evaluate_health()` (score 45)** — `evaluate_health()` in `renmark/init.py` has a nesting-weighted cognitive-complexity score of 45 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `evaluate_health()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/parser.py` → `parse_plan()` (26 branches)** — `parse_plan()` in `renmark/parser.py` has a cyclomatic branch count of 26 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `parse_plan()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/parser.py` → `parse_plan()` (score 87)** — `parse_plan()` in `renmark/parser.py` has a nesting-weighted cognitive-complexity score of 87 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `parse_plan()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/cli/_engine.py` → `execute_plan()` (214 code lines)** — `execute_plan()` in `renmark/cli/_engine.py` spans 214 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `execute_plan()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/cli/_engine.py` → `execute_plan()` (40 branches)** — `execute_plan()` in `renmark/cli/_engine.py` has a cyclomatic branch count of 40 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `execute_plan()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/cli/_engine.py` → `execute_plan()` (score 73)** — `execute_plan()` in `renmark/cli/_engine.py` has a nesting-weighted cognitive-complexity score of 73 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `execute_plan()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/cli/_engine.py` → `_execute_task_codex()` (195 code lines)** — `_execute_task_codex()` in `renmark/cli/_engine.py` spans 195 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `_execute_task_codex()` into well-named helpers. Advisory._
- 🚨 **Long function: `renmark/cli/commands.py` → `cmd_task()` (104 code lines)** — `cmd_task()` in `renmark/cli/commands.py` spans 104 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `cmd_task()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/providers/nim.py` → `complete()` (21 branches)** — `complete()` in `renmark/providers/nim.py` has a cyclomatic branch count of 21 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `complete()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- _… +113 more (re-run for the full list)_


_Run `python -m renmark.init --deep` for deeper checks (commit-message style, etc.)._