---
artifact_type: research
schema_version: 1
created_at: 2026-06-08T21:37:56+00:00
source_sha: null
related_plan: null
generator: brainstorm-research
stale_after: null
dependency_refs: []
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

## Goal

Design an ADVISORY, deterministic, zero-LLM, stdlib-only lens that surfaces
MODULARITY & SCALABILITY health (God-objects, long functions, high fan-out,
deep nesting, branchy code) the way it already surfaces standards-health gaps.

---

## THREAD A — External prior art (metrics, thresholds, pitfalls)

### Most signal-per-noise metrics (what the field actually relies on)

| Metric | What it catches | Tool(s) | Noise level |
|---|---|---|---|
| **Function length (LOC)** | long functions / doing-too-much | pylint `too-many-statements`, Sourcery, SonarQube | low — very intuitive |
| **Cyclomatic complexity (CC / McCabe)** | branchy, hard-to-test fns | radon CC, mccabe (flake8 `--max-complexity`), pylint `too-many-branches` | low-med |
| **Cognitive complexity** | nesting-weighted "hard to follow" | SonarQube S3776, Sourcery | low (best human-correlated) but needs nesting model |
| **Module LOC** | God-files | pylint `too-many-lines` (C0302) | low |
| **Class size / methods / attrs** | God-objects | pylint `too-many-public-methods`, `too-many-instance-attributes` | med (dataclass FP) |
| **Param count** | hidden coupling, missing struct | pylint `too-many-arguments` | low-med |
| **Nesting depth** | arrow-code | pylint `too-many-nested-blocks` | low |
| **Import fan-out (Ce / efferent coupling)** | a module that depends on everything | import-linter, pydeps, madge (JS), SonarQube | low — pure count |
| **Import fan-in (Ca / afferent coupling)** | change-blast radius / instability I=Ce/(Ca+Ce) | pydeps, SonarQube, Martin metrics | med — needs repo-wide graph |
| **Duplication** | copy-paste debt | jscpd, SonarQube, pylint `R0801` | med (hard w/o tokenizer) |
| **Dead code** | unused defs | vulture | high FP (dynamic dispatch) |
| **Maintainability Index** | composite headline number | radon MI, VS | med — composite hides cause; Halstead component contentious |

**Verdict on signal/noise:** the cheapest high-signal quartet is **function
length, cyclomatic-ish branch count, module LOC, and import fan-out** — all
exact integer counts, all defensible, all stdlib-`ast` computable. Cognitive
complexity (nesting-weighted) is the single best human-correlated metric and is
also computable from `ast` with modest effort. MI and cross-file fan-in are
nice-to-have but add formula-controversy / whole-repo-graph cost.

### Default thresholds (with sources)

| Threshold | Default | Source |
|---|---|---|
| pylint `max-args` (too-many-arguments) | **5** | pylint design checker |
| pylint `max-locals` | **15** | pylint |
| pylint `max-returns` | **6** | pylint |
| pylint `max-branches` (too-many-branches) | **12** | pylint |
| pylint `max-statements` (too-many-statements ≈ fn length) | **50** | pylint |
| pylint `max-attributes` (too-many-instance-attributes) | **7** | pylint (confirmed via R0902 docs) |
| pylint `max-public-methods` | **20** | pylint |
| pylint `min-public-methods` | **2** | pylint |
| pylint `max-parents` | **7** | pylint |
| pylint `max-bool-expr` | **5** | pylint |
| pylint `max-nested-blocks` | **5** | pylint |
| pylint `max-module-lines` (too-many-lines C0302) | **1000** | pylint |
| pylint / black line length | 100 / 88 | pylint=100, black=88 |
| mccabe / flake8 `--max-complexity` | **10** (canonical project setting; flake8 ships disabled) | mccabe, flake8 docs |
| radon CC rank A/B/C bands | A 1-5, B 6-10, C 11-20, D 21-30, E 31-40, F 41+ | radon intro docs |
| radon MI rank | A ≥20 (maintainable), B 10-19, C <10 (hard) | radon intro docs |
| SonarQube cognitive complexity (per function) | **15** | SonarSource S3776 |
| "long function" rule-of-thumb | ~50 LOC (matches pylint max-statements) | industry / SonarQube |

**Sources:** radon docs (radon.readthedocs.io/en/latest/intro.html);
pylint R0902 / R0913 message docs (pylint.readthedocs.io); SonarSource S3776
cognitive-complexity rule (sonarsource.com); flake8/mccabe docs; pydeps /
import-linter (efferent/afferent coupling, Robert Martin instability metric).

### How AI assistants surface this
- **CodeRabbit / Sourcery** — flag long functions, high cyclomatic/cognitive
  complexity, deep nesting, and suggest extract-method refactors inline on the diff.
- **Cursor / Copilot / Cody** — surface God-object / long-function smells
  qualitatively in chat review; no fixed deterministic threshold (LLM judgment).
- The deterministic tools (pylint/radon/Sonar) are the ones with hard numbers;
  the renmark lens should mirror THOSE numbers, not the LLM vibes.

### Top false-positive pitfalls (must be suppressed)
1. **Tests** — long parametrized test fns / many asserts trip length+branches. Skip `test_*.py`, `tests/`, `conftest.py`.
2. **Generated code** — migrations, protobuf `*_pb2.py`, `_version.py`, vendored. Skip by path/marker.
3. **`__init__.py`** — re-export hubs have huge import fan-out by design — exempt from fan-out.
4. **Data / config / constants modules** — big literal dicts inflate LOC but have no logic; weight by branch/CC, not raw LOC.
5. **Dataclasses / Pydantic / Enums / NamedTuple** — many fields ≠ God-object. pylint special-cases dataclasses (issue #9058). Don't count fields as attributes for `@dataclass`/`Enum`.
6. **Match statements / big dispatch dicts** — inflate branch count but are flat & readable; cognitive complexity (nesting-weighted) is fairer than raw CC here.
7. **Long files mostly docstring/comments** — count code lines, not raw lines.

### Stdlib `ast`-only feasibility (NO deps)

FEASIBLE with `ast` + `os.walk` (all exact, deterministic):
- module LOC (already have via `FileInfo.loc`), code-vs-comment split if needed
- def/class counts per file (`ast.FunctionDef`/`AsyncFunctionDef`/`ClassDef`)
- function length (lineno → end_lineno, py3.8+)
- param count (`len(node.args.args + kwonlyargs + posonlyargs)`)
- methods-per-class, instance-attrs (count `self.x =` assigns; detect `@dataclass`/`Enum` to suppress)
- **cyclomatic-ish** = 1 + count of `If/For/While/ExceptHandler/With/BoolOp(extra and/or)/comprehension-if/IfExp/match-case/assert` nodes in a fn
- **cognitive complexity** ≈ branch nodes weighted by `ast` nesting depth (track depth in a NodeVisitor) — the Sonar model is reproducible from `ast`
- **nesting depth** = max depth of nested If/For/While/With/Try via NodeVisitor
- **import fan-out** = count distinct `ast.Import`/`ast.ImportFrom` targets per file
- **import fan-in / cross-file coupling** = FEASIBLE but only by building a repo-wide
  graph: parse every file's imports, resolve to in-repo module paths, count
  reverse edges. Doable with `ast` over all files; O(files) more work + needs
  module-path resolution (dotted name → file). Worth it for "blast radius."

NOT feasible without deps / harder:
- true radon **Maintainability Index** (needs Halstead volume — Halstead is
  contentious; skip or approximate, don't claim parity)
- robust **duplication** detection (needs tokenizer/rolling hash — possible but noisy)
- accurate **dead-code** (vulture-grade needs whole-program reachability + dynamic-dispatch heuristics) — skip; too FP-prone for an advisory lens

---

## THREAD B — Internal: what renmark already has

### REUSE (exists today)
- **`renmark/init.py` Gap-emission pattern** — the new lens should mirror this EXACTLY:
  - `@dataclass Gap(severity: "danger"|"warn"|"info", title, detail, recommendation)`
  - detectors append `Gap(...)`; `evaluate_health()` aggregates + severity-sorts (`order = {danger:0, warn:1, info:2}`)
  - rendered into `dev-standards.md` "## Standards health" section
  - stdout one-liner pattern to copy verbatim:
    `HEALTH: {n} gap(s) ({k danger, k warn, k info}) — see \`.renmark/memory/dev-standards.md\``
    built from `counts = {danger:0,warn:0,info:0}` then `", ".join(f"{n} {sev}" ...)`.
  A modularity lens = a new family of `Gap`s (severity by threshold band) fed
  into the SAME `evaluate_health`/render/stdout machinery. Lowest-friction integration.
- **`FileInfo(path, rel, lang, loc, symbols)`** — `_walk_source_files()` already
  walks source files, computes `loc`, respects `_is_excluded()`. REUSE the walker
  + loc + exclusion as the file iterator for the lens.
- **`scan_repo()` / `evaluate_health(repo, standards, files, deep)`** — already
  takes `files: list[FileInfo]`; a modularity detector slots in beside the
  existing standards detectors with zero new plumbing.
- **`renmark/summary.write_artifact()`** — provenance/freshness metadata + G3
  summary-cap enforcement (note: cap is 5 lines). Use for any standalone artifact.
- **`renmark/sizing.py` constants style** — documented tunable module-level
  threshold constants + "never raise, degrade safe" doctrine. COPY the pattern
  (named constants, defensive try/except) for the lens's thresholds.

### MUST BUILD NEW
- **AST extraction itself.** Critical finding: `init._extract_symbols` is
  **REGEX-based** (`_PY_SYM`, `_JS_SYM` …) and init.py **never imports `ast`**.
  There is NO existing per-function length / param / branch / nesting / fan-out
  extraction anywhere. `sizing.py` works only off git-diff `--stat` line counts
  and `Task` fields — no source parsing. So the entire `ast`-walk (NodeVisitor
  computing fn length, CC, cognitive complexity, nesting, fan-out, class size)
  is net-new.
- **Threshold→severity banding** (map a metric value to danger/warn/info Gap).
- **False-positive suppression** (test/generated/`__init__`/dataclass/data-module skips) — new.
- **Optional repo-wide import graph** for fan-in — new (Python-only first).

### NOT relevant
- `renmark/lint.py` — lints PLUGIN files (skill frontmatter, citations, plugin.json),
  not code complexity. No reuse.

---

## Recommendation

Ship **4 core metrics** (highest signal, lowest noise, all pure-`ast`):
1. function length (warn >50 LOC, danger >~100)
2. cyclomatic-ish branch count per fn (warn >10, danger >20 — mccabe/radon bands)
3. module LOC / God-file (warn >500, danger >1000 — pylint max-module-lines)
4. import fan-out per file (warn band; `__init__.py` exempt)
Plus cognitive complexity (nesting-weighted, Sonar=15) as the 5th if budget allows —
best human-correlated metric and still `ast`-only.

**Where it lives:** build a NEW stdlib helper `renmark/modularity.py` (the
`ast` walker + thresholds, mirroring `sizing.py`'s constants/never-raise style),
then surface findings as `Gap`s through init.py's EXISTING
`evaluate_health` → `dev-standards.md` → `HEALTH:` stdout machinery. Reuses all
emission plumbing, stays advisory + deterministic, avoids a separate
`/renmark:hygiene` surface unless an on-demand deep report is wanted.

## Summary

- Ship 4-5 pure-ast metrics: fn length (>50/100), cyclomatic branch count (>10/20), module LOC (>500/1000), import fan-out (+cognitive complexity, Sonar=15); zero-dep, deterministic.
- Mirror these defaults: pylint max-statements=50, max-branches=12, max-args=5, max-attributes=7, max-module-lines=1000; mccabe=10; radon CC bands; Sonar cognitive=15.
- FP suppression mandatory: skip tests, generated code, __init__.py fan-out, dataclass/Enum field counts, big data/config modules; count code lines not raw.
- REUSE: init.py Gap dataclass + evaluate_health + dev-standards.md render + 'HEALTH:' stdout line; _walk_source_files/FileInfo.loc; sizing.py constants+never-raise style. MUST BUILD: the ast walker itself (init uses REGEX, never imports ast; sizing only reads git --stat).
- Recommend new renmark/modularity.py helper feeding Gaps into init's existing standards-health machinery (advisory), not a separate /hygiene surface.
