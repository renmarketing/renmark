<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-07-02 @ 5d3f878 -->

# Dev standards — deterministic-first

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

**186 modularity gaps** (31 major, 155 warn) — file-level size/complexity breaches. Advisory: these never block init.

- 🚨 **High cognitive complexity: `renmark/memory.py` → `_parse_learning_entries()` (score 32)** — `_parse_learning_entries()` in `renmark/memory.py` has a nesting-weighted cognitive-complexity score of 32 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_parse_learning_entries()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/release.py` → `main()` (30 branches)** — `main()` in `renmark/release.py` has a cyclomatic branch count of 30 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `main()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/release.py` → `main()` (score 58)** — `main()` in `renmark/release.py` has a nesting-weighted cognitive-complexity score of 58 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `main()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/bootstrap.py` → `bootstrap()` (114 code lines)** — `bootstrap()` in `renmark/bootstrap.py` spans 114 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `bootstrap()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/bootstrap.py` → `bootstrap()` (25 branches)** — `bootstrap()` in `renmark/bootstrap.py` has a cyclomatic branch count of 25 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `bootstrap()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/bootstrap.py` → `bootstrap()` (score 35)** — `bootstrap()` in `renmark/bootstrap.py` has a nesting-weighted cognitive-complexity score of 35 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `bootstrap()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/shadow.py` → `main()` (score 31)** — `main()` in `renmark/shadow.py` has a nesting-weighted cognitive-complexity score of 31 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `main()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/summary.py` → `read_metadata()` (score 34)** — `read_metadata()` in `renmark/summary.py` has a nesting-weighted cognitive-complexity score of 34 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `read_metadata()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Oversized module: `renmark/init.py` (1270 code lines)** — `renmark/init.py` has 1270 code lines (threshold 1000). Large modules are hard to navigate, review, and test, and tend to accrete unrelated responsibilities. _Split `renmark/init.py` into focused modules along its natural seams (one cohesive responsibility per file). Advisory — never auto-refactored._
- 🚨 **High cyclomatic complexity: `renmark/init.py` → `_file_purpose()` (23 branches)** — `_file_purpose()` in `renmark/init.py` has a cyclomatic branch count of 23 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `_file_purpose()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/init.py` → `_file_purpose()` (score 63)** — `_file_purpose()` in `renmark/init.py` has a nesting-weighted cognitive-complexity score of 63 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_file_purpose()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **Long function: `renmark/init.py` → `evaluate_health()` (166 code lines)** — `evaluate_health()` in `renmark/init.py` spans 166 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `evaluate_health()` into well-named helpers. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/init.py` → `evaluate_health()` (39 branches)** — `evaluate_health()` in `renmark/init.py` has a cyclomatic branch count of 39 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `evaluate_health()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/init.py` → `evaluate_health()` (score 45)** — `evaluate_health()` in `renmark/init.py` has a nesting-weighted cognitive-complexity score of 45 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `evaluate_health()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/audit.py` → `no_raw_jsonl()` (score 36)** — `no_raw_jsonl()` in `renmark/audit.py` has a nesting-weighted cognitive-complexity score of 36 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `no_raw_jsonl()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/judge.py` → `_extract_json_object()` (score 47)** — `_extract_json_object()` in `renmark/judge.py` has a nesting-weighted cognitive-complexity score of 47 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_extract_json_object()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/lint.py` → `lint_frontmatter_values()` (score 40)** — `lint_frontmatter_values()` in `renmark/lint.py` has a nesting-weighted cognitive-complexity score of 40 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `lint_frontmatter_values()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cognitive complexity: `renmark/lifecycle.py` → `validate_artifact_refs()` (score 31)** — `validate_artifact_refs()` in `renmark/lifecycle.py` has a nesting-weighted cognitive-complexity score of 31 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `validate_artifact_refs()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/parser.py` → `parse_plan()` (28 branches)** — `parse_plan()` in `renmark/parser.py` has a cyclomatic branch count of 28 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `parse_plan()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/parser.py` → `parse_plan()` (score 90)** — `parse_plan()` in `renmark/parser.py` has a nesting-weighted cognitive-complexity score of 90 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `parse_plan()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- _… +166 more (re-run for the full list)_


_Run `python -m renmark.init --deep` for deeper checks (commit-message style, etc.)._