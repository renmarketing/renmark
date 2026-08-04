<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-08-04 @ 495962d -->

# Dev standards — renmark

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

**276 modularity gaps** (19 major, 257 warn) — file-level size/complexity breaches. Advisory: these never block init.

- 🚨 **High cyclomatic complexity: `renmark/doctor.py` → `main()` (23 branches)** — `main()` in `renmark/doctor.py` has a cyclomatic branch count of 23 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `main()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/doctor.py` → `main()` (score 33)** — `main()` in `renmark/doctor.py` has a nesting-weighted cognitive-complexity score of 33 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `main()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High import fan-out: `renmark/behavior.py` (31 imports)** — `renmark/behavior.py` has 31 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `renmark/behavior.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **Long function: `renmark/behavior.py` → `_selector_trajectory_payload()` (110 code lines)** — `_selector_trajectory_payload()` in `renmark/behavior.py` spans 110 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `_selector_trajectory_payload()` into well-named helpers. Advisory._
- 🚨 **High cognitive complexity: `renmark/parser.py` → `parse_package_plan()` (score 33)** — `parse_package_plan()` in `renmark/parser.py` has a nesting-weighted cognitive-complexity score of 33 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `parse_package_plan()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/schemas.py` → `validate_delivery_state()` (26 branches)** — `validate_delivery_state()` in `renmark/schemas.py` has a cyclomatic branch count of 26 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `validate_delivery_state()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/schemas.py` → `validate_delivery_state()` (score 43)** — `validate_delivery_state()` in `renmark/schemas.py` has a nesting-weighted cognitive-complexity score of 43 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `validate_delivery_state()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High import fan-out: `renmark/init.py` (26 imports)** — `renmark/init.py` has 26 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `renmark/init.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/hygiene.py` → `validate_registry_compliance()` (21 branches)** — `validate_registry_compliance()` in `renmark/hygiene.py` has a cyclomatic branch count of 21 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `validate_registry_compliance()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/hygiene.py` → `validate_registry_compliance()` (score 36)** — `validate_registry_compliance()` in `renmark/hygiene.py` has a nesting-weighted cognitive-complexity score of 36 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `validate_registry_compliance()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High cyclomatic complexity: `renmark/hygiene.py` → `scan_artifacts()` (30 branches)** — `scan_artifacts()` in `renmark/hygiene.py` has a cyclomatic branch count of 30 (threshold 20). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `scan_artifacts()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- 🚨 **High cognitive complexity: `renmark/hygiene.py` → `scan_artifacts()` (score 72)** — `scan_artifacts()` in `renmark/hygiene.py` has a nesting-weighted cognitive-complexity score of 72 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `scan_artifacts()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High import fan-out: `renmark/cli/_engine.py` (60 imports)** — `renmark/cli/_engine.py` has 60 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `renmark/cli/_engine.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **Long function: `renmark/cli/_engine.py` → `main()` (237 code lines)** — `main()` in `renmark/cli/_engine.py` spans 237 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `main()` into well-named helpers. Advisory._
- 🚨 **High cognitive complexity: `renmark/cli/_wave_loop.py` → `_run_waves()` (score 30)** — `_run_waves()` in `renmark/cli/_wave_loop.py` has a nesting-weighted cognitive-complexity score of 30 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_run_waves()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- 🚨 **High import fan-out: `renmark/cli/_dispatch_flags.py` (30 imports)** — `renmark/cli/_dispatch_flags.py` has 30 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `renmark/cli/_dispatch_flags.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **High import fan-out: `renmark/cli/commands.py` (26 imports)** — `renmark/cli/commands.py` has 26 import statements (threshold 25). High fan-out signals a module coupled to many others — a change-amplifier and a refactoring hazard. _Reduce coupling in `renmark/cli/commands.py`: extract a narrower interface, group related imports behind a facade, or move logic closer to its dependencies. Advisory._
- 🚨 **Long function: `renmark/cli/_codex_runner.py` → `_execute_task_codex()` (152 code lines)** — `_execute_task_codex()` in `renmark/cli/_codex_runner.py` spans 152 code lines (threshold 100). Long functions are hard to read in one pass and usually do more than one thing. _Extract cohesive blocks of `_execute_task_codex()` into well-named helpers. Advisory._
- 🚨 **High cognitive complexity: `renmark/cli/_codex_runner.py` → `_execute_task_codex()` (score 32)** — `_execute_task_codex()` in `renmark/cli/_codex_runner.py` has a nesting-weighted cognitive-complexity score of 32 (threshold 30). Deep nesting is disproportionately hard for a human to follow. _Flatten nesting in `_execute_task_codex()`: invert conditions to return early, extract nested blocks into helpers, and reduce branching depth. Advisory._
- ⚠ **High cyclomatic complexity: `renmark/loop.py` → `_coerce_int()` (11 branches)** — `_coerce_int()` in `renmark/loop.py` has a cyclomatic branch count of 11 (threshold 10). Many decision points mean many paths to test and many ways to be wrong. _Reduce branching in `_coerce_int()`: early returns, guard clauses, table/dispatch dictionaries, or splitting the function. Advisory._
- _… +256 more (re-run for the full list)_


_Run `python -m renmark.init --deep` for deeper checks (commit-message style, etc.)._