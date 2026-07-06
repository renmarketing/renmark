"""Dev-standards scanning and health-gap detection for renmark.

Extracted from :mod:`renmark.init` to keep that module within the 1000-line
modularity threshold.  All public symbols here are re-exported by
:mod:`renmark.init` for backward compatibility.

CLI:
    Not a standalone CLI — imported by renmark.init.

Public API:
    Standard, Gap, StandardsScan       — data classes
    scan_standards()                   — detect standards + run health checks
    evaluate_health()                  — return sorted list of Gap objects
    render_dev_gates_line()            — single-line summary for CLAUDE.md stub
    render_standards_md()              — render the full dev-standards.md body
    write_standards_md()               — write .renmark/memory/dev-standards.md
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .init import FileInfo

# Cap how many modularity gaps to list in dev-standards.md (majors first,
# then warns). Remainder is summarised as a "+N more" note so the rendered
# section can't be flooded by a 100+ gap scan.
MODULARITY_GAPS_RENDER_CAP = 20

# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class Standard:
    """One detected dev standard (test, lint, type-check, etc.)."""

    name: str  # canonical key: "test", "lint", "format", "typecheck", "ci", ...
    command: str | None  # invocation, e.g. "pytest -q" — None if not directly runnable
    config_file: str | None  # where it was detected (relative path)
    detail: str = ""  # extra info for dev-standards.md


@dataclass
class Gap:
    """One standards-health gap with a tighten-this recommendation."""

    severity: str  # "danger", "warn", "info"
    title: str
    detail: str
    recommendation: str


@dataclass
class StandardsScan:
    """Result of scanning the repo for dev standards + health gaps.

    ``gaps`` are the standards-health gaps (linter/CI/tests/secrets …).
    ``modularity_gaps`` are file-level modularity breaches from
    :mod:`renmark.modularity` — kept in a SEPARATE list so the always-loaded
    stub and the bounded ``HEALTH:`` stdout line can summarize them as counts
    rather than dumping 100+ per-gap entries. Both feed the total gap count.
    """

    standards: list[Standard] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    modularity_gaps: list[Gap] = field(default_factory=list)
    deep: bool = False


# ── Internal helpers ──────────────────────────────────────────────────────────


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _parse_pyproject_table(repo: Path, table: str) -> str | None:
    """Cheap presence check for a `[tool.X]` or `[project.scripts]` table in pyproject.toml."""
    p = repo / "pyproject.toml"
    if not p.exists():
        return None
    text = _read_text_safe(p)
    return text if re.search(rf"^\[{re.escape(table)}\]", text, re.MULTILINE) else None


def _package_json(repo: Path) -> dict[str, Any] | None:
    p = repo / "package.json"
    if not p.exists():
        return None
    try:
        obj = json.loads(_read_text_safe(p))
    except json.JSONDecodeError:
        return None
    # A non-object package.json (someone wrote a list or scalar by mistake)
    # would type-check through cast() but crash at downstream .get() calls.
    if not isinstance(obj, dict):
        return None
    return cast(dict[str, Any], obj)


def _detect_test(repo: Path) -> Standard | None:
    pkg = _package_json(repo)
    if pkg:
        scripts = pkg.get("scripts", {}) or {}
        for key in ("test", "test:unit"):
            if key in scripts:
                return Standard("test", f"npm run {key}", "package.json", scripts[key])
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for fw, cmd in (("vitest", "vitest run"), ("jest", "jest"), ("mocha", "mocha")):
            if fw in deps:
                return Standard("test", cmd, "package.json", f"{fw} in deps but no test script")
    if _parse_pyproject_table(repo, "tool.pytest.ini_options") or (repo / "pytest.ini").exists():
        return Standard(
            "test",
            "pytest -q",
            "pyproject.toml" if _parse_pyproject_table(repo, "tool.pytest.ini_options") else "pytest.ini",
            "",
        )
    pyproj = repo / "pyproject.toml"
    if pyproj.exists():
        text = _read_text_safe(pyproj)
        if re.search(r'"pytest', text) or re.search(r"^pytest", text, re.MULTILINE):
            return Standard("test", "pytest -q", "pyproject.toml", "pytest in deps")
    if (repo / "go.mod").exists():
        return Standard("test", "go test ./...", "go.mod", "")
    if (repo / "Cargo.toml").exists():
        return Standard("test", "cargo test", "Cargo.toml", "")
    return None


def _detect_lint(repo: Path) -> Standard | None:
    if _parse_pyproject_table(repo, "tool.ruff") or (repo / "ruff.toml").exists() or (repo / ".ruff.toml").exists():
        return Standard(
            "lint",
            "ruff check",
            "ruff.toml" if (repo / "ruff.toml").exists() else "pyproject.toml",
            "",
        )
    if _parse_pyproject_table(repo, "tool.flake8") or (repo / ".flake8").exists() or (repo / "setup.cfg").exists():
        return Standard("lint", "flake8", ".flake8", "")
    for f in (
        ".eslintrc",
        ".eslintrc.json",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.yaml",
        "eslint.config.js",
        "eslint.config.mjs",
    ):
        if (repo / f).exists():
            return Standard("lint", "eslint .", f, "")
    if (repo / ".rubocop.yml").exists():
        return Standard("lint", "rubocop", ".rubocop.yml", "")
    if (repo / "Cargo.toml").exists():
        return Standard("lint", "cargo clippy -- -D warnings", "Cargo.toml", "implicit (clippy)")
    if (repo / "go.mod").exists():
        return Standard("lint", "go vet ./...", "go.mod", "implicit (go vet)")
    return None


def _detect_format(repo: Path) -> Standard | None:
    if _parse_pyproject_table(repo, "tool.black"):
        return Standard("format", "black .", "pyproject.toml", "")
    if _parse_pyproject_table(repo, "tool.ruff.format") or _parse_pyproject_table(repo, "tool.ruff"):
        # Ruff's format subcommand
        return Standard("format", "ruff format", "pyproject.toml", "")
    for f in (
        ".prettierrc",
        ".prettierrc.json",
        ".prettierrc.js",
        "prettier.config.js",
        ".prettierrc.yaml",
    ):
        if (repo / f).exists():
            return Standard("format", "prettier --write .", f, "")
    pkg = _package_json(repo)
    if pkg and "prettier" in {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}:
        return Standard("format", "prettier --write .", "package.json", "prettier in deps")
    if (repo / "rustfmt.toml").exists() or (repo / "Cargo.toml").exists():
        return Standard(
            "format",
            "cargo fmt",
            "rustfmt.toml" if (repo / "rustfmt.toml").exists() else "Cargo.toml",
            "",
        )
    if (repo / "go.mod").exists():
        return Standard("format", "gofmt -w .", "go.mod", "implicit (gofmt)")
    return None


def _detect_typecheck(repo: Path) -> Standard | None:
    if _parse_pyproject_table(repo, "tool.mypy") or (repo / "mypy.ini").exists():
        cfg = "mypy.ini" if (repo / "mypy.ini").exists() else "pyproject.toml"
        return Standard("typecheck", "mypy .", cfg, "")
    if (repo / "pyrightconfig.json").exists():
        return Standard("typecheck", "pyright", "pyrightconfig.json", "")
    tsconfig = repo / "tsconfig.json"
    if tsconfig.exists():
        text = _read_text_safe(tsconfig)
        strict = '"strict": true' in text or '"strict":true' in text
        detail = "strict mode" if strict else "tsconfig present but `strict` not enabled"
        return Standard("typecheck", "tsc --noEmit", "tsconfig.json", detail)
    return None


def _detect_ci(repo: Path) -> Standard | None:
    workflows_dir = repo / ".github" / "workflows"
    workflows: list[str] = []
    if workflows_dir.exists():
        for f in sorted(workflows_dir.iterdir()):
            if f.suffix in (".yml", ".yaml"):
                text = _read_text_safe(f)
                m = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
                workflows.append(m.group(1).strip().strip("\"'") if m else f.stem)
        if workflows:
            return Standard("ci", None, ".github/workflows/", f"GitHub Actions: {', '.join(workflows)}")
    if (repo / ".gitlab-ci.yml").exists():
        return Standard("ci", None, ".gitlab-ci.yml", "GitLab CI")
    if (repo / ".circleci" / "config.yml").exists():
        return Standard("ci", None, ".circleci/config.yml", "CircleCI")
    return None


def _detect_precommit(repo: Path) -> Standard | None:
    if (repo / ".pre-commit-config.yaml").exists():
        text = _read_text_safe(repo / ".pre-commit-config.yaml")
        hooks = re.findall(r"^\s*-\s*id:\s*([\w.-]+)", text, re.MULTILINE)
        return Standard(
            "precommit",
            "pre-commit run --all-files",
            ".pre-commit-config.yaml",
            f"hooks: {', '.join(hooks[:6])}" if hooks else "",
        )
    if (repo / ".husky").exists() and (repo / ".husky").is_dir():
        return Standard("precommit", None, ".husky/", "Husky hooks")
    return None


def _detect_env_schema(repo: Path) -> Standard | None:
    for fn in (".env.example", ".env.template", ".env.sample"):
        p = repo / fn
        if p.exists():
            keys = [m.group(1) for m in re.finditer(r"^([A-Z_][A-Z0-9_]*)=", _read_text_safe(p), re.MULTILINE)]
            if len(keys) > 20:
                detail = f"{len(keys)} keys (first 20: {', '.join(keys[:20])}, …)"
            else:
                detail = f"keys: {', '.join(keys)}" if keys else "empty"
            return Standard("env", None, fn, detail)
    return None


def _detect_db(repo: Path) -> Standard | None:
    if (repo / "alembic.ini").exists():
        return Standard("db", "alembic upgrade head", "alembic.ini", "Alembic migrations")
    if (repo / "prisma" / "schema.prisma").exists():
        return Standard("db", "prisma migrate dev", "prisma/schema.prisma", "Prisma")
    if (repo / "drizzle.config.ts").exists() or (repo / "drizzle.config.js").exists():
        return Standard("db", "drizzle-kit migrate", "drizzle.config.ts", "Drizzle ORM")
    if (repo / "knexfile.js").exists() or (repo / "knexfile.ts").exists():
        return Standard("db", "knex migrate:latest", "knexfile.js", "Knex")
    return None


def _detect_local_dev(repo: Path) -> Standard | None:
    pkg = _package_json(repo)
    if pkg:
        scripts = pkg.get("scripts", {}) or {}
        for key in ("dev", "start"):
            if key in scripts:
                return Standard("dev", f"npm run {key}", "package.json", scripts[key])
    mk = repo / "Makefile"
    if mk.exists():
        targets = re.findall(r"^([a-zA-Z_][\w-]*):", _read_text_safe(mk), re.MULTILINE)
        for t in ("dev", "run", "start", "serve"):
            if t in targets:
                return Standard("dev", f"make {t}", "Makefile", f"targets: {', '.join(targets[:8])}")
        if targets:
            return Standard("dev", f"make {targets[0]}", "Makefile", f"targets: {', '.join(targets[:8])}")
    if (repo / "docker-compose.yml").exists() or (repo / "compose.yml").exists():
        cfg = "docker-compose.yml" if (repo / "docker-compose.yml").exists() else "compose.yml"
        return Standard("dev", "docker compose up", cfg, "")
    return None


def _detect_style(repo: Path) -> Standard | None:
    p = repo / ".editorconfig"
    if not p.exists():
        return None
    text = _read_text_safe(p)
    indent_size = re.search(r"^indent_size\s*=\s*(\d+)", text, re.MULTILINE)
    indent_style = re.search(r"^indent_style\s*=\s*(\w+)", text, re.MULTILINE)
    max_line = re.search(r"^max_line_length\s*=\s*(\d+)", text, re.MULTILINE)
    parts = []
    if indent_style:
        parts.append(f"indent={indent_style.group(1)}{(' ' + indent_size.group(1)) if indent_size else ''}")
    if max_line:
        parts.append(f"max_line={max_line.group(1)}")
    return Standard("style", None, ".editorconfig", ", ".join(parts) or "see file")


def _detect_deps_policy(repo: Path) -> Standard | None:
    bits: list[str] = []
    if (repo / ".github" / "dependabot.yml").exists():
        bits.append("dependabot")
    if (repo / "renovate.json").exists() or (repo / ".github" / "renovate.json").exists():
        bits.append("renovate")
    lockfiles = []
    for lf in (
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
        "Cargo.lock",
        "go.sum",
    ):
        if (repo / lf).exists():
            lockfiles.append(lf)
    if lockfiles:
        bits.append(f"lockfile: {', '.join(lockfiles)}")
    if not bits:
        return None
    return Standard("deps", None, "—", "; ".join(bits))


def _count_test_files(repo: Path, files: list[FileInfo]) -> int:
    """Count files that look like tests (test_*.py, *.test.ts, *_test.go, *_spec.rb)."""
    count = 0
    for f in files:
        rel = f.rel
        name = Path(rel).name
        if (
            name.startswith("test_")
            or name.endswith(("_test.py", "_test.go", "_spec.rb"))
            or ".test." in name
            or ".spec." in name
            or "/tests/" in rel
            or "/test/" in rel
            or "/__tests__/" in rel
        ):
            count += 1
    return count


def _check_secrets_risk(repo: Path, gaps: list[Gap]) -> None:
    """Append a Gap if .env is committed and not gitignored."""
    if not (repo / ".env").exists():
        return
    gi = repo / ".gitignore"
    gitignored = gi.exists() and ".env" in _read_text_safe(gi).splitlines()
    if not gitignored:
        gaps.append(
            Gap(
                "danger",
                "Secrets risk: `.env` is committed (not gitignored)",
                "`.env` exists in the repo and is not in `.gitignore`. Real credentials may be checked in.",
                "Add `.env` to `.gitignore`, run `git rm --cached .env`, and rotate any leaked credentials.",
            )
        )


def _check_package_managers(repo: Path, gaps: list[Gap]) -> None:
    """Append a Gap if multiple JS package manager lockfiles coexist."""
    lockfiles_present = [lf for lf in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml") if (repo / lf).exists()]
    if len(lockfiles_present) > 1:
        gaps.append(
            Gap(
                "danger",
                f"Multiple JS package managers: {', '.join(lockfiles_present)}",
                "Each lockfile implies a different installer. Concurrent use causes ghost dependencies and silent breakage.",
                "Pick one — delete the others. Common choice: keep `package-lock.json` (npm).",
            )
        )


def _check_type_checking(by_name: dict[str, Standard], files: list[FileInfo], gaps: list[Gap]) -> None:
    """Append Gaps for missing or non-strict type checking."""
    if "typecheck" not in by_name:
        has_typed_lang = any(f.lang in ("python", "typescript") for f in files)
        if has_typed_lang:
            gaps.append(
                Gap(
                    "warn",
                    "No type checker configured",
                    "No mypy/pyright/tsc-strict detected. Type errors only show up at runtime.",
                    "For Python: `pip install mypy && echo '[tool.mypy]\\nstrict = true' >> pyproject.toml`. "
                    'For TS: set `"strict": true` in `tsconfig.json`.',
                )
            )
    else:
        # tsconfig present but not strict
        tc = by_name["typecheck"]
        if tc.config_file == "tsconfig.json" and "strict mode" not in tc.detail:
            gaps.append(
                Gap(
                    "warn",
                    "TypeScript not in strict mode",
                    '`tsconfig.json` exists but `"strict": true` is not set. Type guarantees are weak.',
                    'Set `"strict": true` in `tsconfig.json`. Expect a backlog of fixes the first run.',
                )
            )


def _check_test_coverage(by_name: dict[str, Standard], n_source_files: int, n_tests: int, gaps: list[Gap]) -> None:
    """Append Gaps for zero tests or a configured-but-empty test suite."""
    if n_source_files >= 10 and n_tests == 0:
        gaps.append(
            Gap(
                "warn",
                f"No tests detected ({n_source_files} source files, 0 test files)",
                "Multi-file project with zero test files. Every change is a bet.",
                "Add the first test before the next feature. Even one smoke test changes the trajectory.",
            )
        )
    if "test" in by_name and n_tests == 0 and n_source_files >= 3:
        gaps.append(
            Gap(
                "warn",
                "Test framework configured but no test files",
                f"`{by_name['test'].command}` is set up, but the test directory is empty.",
                "Either add tests, or remove the unused test framework so the README doesn't lie.",
            )
        )


def _check_quality_enforcement(by_name: dict[str, Standard], n_source_files: int, gaps: list[Gap]) -> None:
    """Append Gaps for lint/CI/pre-commit enforcement gaps."""
    if "lint" in by_name and "precommit" not in by_name and "ci" not in by_name:
        gaps.append(
            Gap(
                "warn",
                "Linter not wired to pre-commit or CI",
                f"`{by_name['lint'].command}` is configured, but nothing enforces it before commit or in CI.",
                "Add a pre-commit hook (`.pre-commit-config.yaml`) or a CI workflow that runs it.",
            )
        )
    if n_source_files >= 10 and "ci" not in by_name:
        gaps.append(
            Gap(
                "warn",
                "No CI configured",
                f"{n_source_files} source files and no `.github/workflows/`, `.gitlab-ci.yml`, or CircleCI config.",
                "Add a minimal CI workflow that runs tests + lint on every PR.",
            )
        )
    if "precommit" not in by_name and "ci" not in by_name and n_source_files >= 5:
        gaps.append(
            Gap(
                "warn",
                "Nothing enforces quality (no pre-commit hooks AND no CI)",
                "Whatever you configure locally won't run automatically — both pre-commit and CI are missing.",
                "Pick one — pre-commit for fast local checks, CI for team-wide gates. Both is best.",
            )
        )


def _check_project_basics(repo: Path, pkg: object, n_source_files: int, gaps: list[Gap]) -> None:
    """Append Gaps for missing lockfile, .gitignore, or README."""
    if pkg is not None and not any((repo / lf).exists() for lf in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")):
        gaps.append(
            Gap(
                "warn",
                "Missing lockfile for `package.json`",
                "Dependencies are unpinned at the lockfile level — fresh `npm install` may resolve different versions.",
                "Run `npm install` (or yarn/pnpm) and commit the resulting lockfile.",
            )
        )
    if not (repo / ".gitignore").exists() and n_source_files >= 3:
        gaps.append(
            Gap(
                "info",
                "No `.gitignore`",
                "Without `.gitignore`, build artifacts, caches, and secrets risk being committed.",
                "Add a stack-appropriate `.gitignore` (renmark's `/renmark:setup` will create one).",
            )
        )
    if not (repo / "README.md").exists() and not (repo / "README").exists() and n_source_files >= 5:
        gaps.append(
            Gap(
                "info",
                "No README",
                "Anyone new to the repo has no entry point.",
                "Add a `README.md` with: what this is, how to run it locally, how to run tests.",
            )
        )


def _check_commit_style(repo: Path, deep: bool, gaps: list[Gap]) -> None:
    """Append a Gap for inconsistent commit message style (deep mode only)."""
    if not deep:
        return
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "-20", "--pretty=%s"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            subjects = [s for s in out.stdout.splitlines() if s]
            conv = sum(
                1
                for s in subjects
                if re.match(
                    r"^(feat|fix|chore|docs|refactor|test|build|ci|perf|style|revert)(\(\w+\))?!?:",
                    s,
                )
            )
            if subjects and conv / max(len(subjects), 1) < 0.3 and conv > 0:
                gaps.append(
                    Gap(
                        "info",
                        "Inconsistent commit message style",
                        f"Of the last {len(subjects)} commits, only {conv} follow conventional-commits format.",
                        "Pick a convention (conventional-commits or freeform) and enforce via commitlint or PR review.",
                    )
                )
    except (FileNotFoundError, subprocess.SubprocessError):
        pass


def evaluate_health(repo: Path, standards: list[Standard], files: list[FileInfo], deep: bool) -> list[Gap]:
    """Run the gap detectors and return a list of Gap objects, severity-sorted."""
    by_name = {s.name: s for s in standards}
    gaps: list[Gap] = []
    n_source_files = len(files)
    pkg = _package_json(repo)
    n_tests = _count_test_files(repo, files)

    _check_secrets_risk(repo, gaps)
    _check_package_managers(repo, gaps)
    if "lint" not in by_name:
        gaps.append(
            Gap(
                "warn",
                "No linter configured",
                "No ruff/flake8/eslint/rubocop/clippy/go-vet detected. Style and obvious bugs go uncaught.",
                "Add a linter — for Python: `pip install ruff && echo '[tool.ruff]' >> pyproject.toml`; "
                "for JS/TS: `npm i -D eslint && npx eslint --init`.",
            )
        )
    _check_type_checking(by_name, files, gaps)
    _check_test_coverage(by_name, n_source_files, n_tests, gaps)
    _check_quality_enforcement(by_name, n_source_files, gaps)
    _check_project_basics(repo, pkg, n_source_files, gaps)
    _check_commit_style(repo, deep, gaps)

    order = {"danger": 0, "warn": 1, "info": 2}
    gaps.sort(key=lambda g: order.get(g.severity, 99))
    return gaps


def scan_standards(repo: Path, files: list[FileInfo], deep: bool = False) -> StandardsScan:
    detectors = (
        _detect_test,
        _detect_lint,
        _detect_format,
        _detect_typecheck,
        _detect_ci,
        _detect_precommit,
        _detect_env_schema,
        _detect_db,
        _detect_local_dev,
        _detect_style,
        _detect_deps_policy,
    )
    standards = [s for s in (d(repo) for d in detectors) if s is not None]
    gaps = evaluate_health(repo, standards, files, deep)
    # Additive: merge in file-level modularity breaches (separate list so the
    # bounded stub / HEALTH line summarize them as counts, not a 100+ dump).
    # analyze() never raises and returns [] on failure — keep init zero-LLM.
    from . import modularity

    modularity_gaps = modularity.analyze(repo)
    return StandardsScan(standards=standards, gaps=gaps, modularity_gaps=modularity_gaps, deep=deep)


# ── Standards rendering ───────────────────────────────────────────────────────


_SEVERITY_PREFIX = {"danger": "🚨", "warn": "⚠", "info": "ℹ"}


def render_dev_gates_line(standards: StandardsScan) -> str | None:
    """A single line for the CLAUDE.md stub, listing the most-important commands.

    Returns None if there are no gates worth surfacing in the always-loaded
    context (greenfield project with no standards).
    """
    by_name = {s.name: s for s in standards.standards}
    parts: list[str] = []
    for key, label in (("test", "test"), ("lint", "lint"), ("typecheck", "types")):
        s = by_name.get(key)
        if s and s.command:
            parts.append(f"{label} `{s.command}`")
    ci = by_name.get("ci")
    if ci:
        # ci.detail is like "GitHub Actions: build, test, deploy"
        wf_part = ci.detail.split(":", 1)[1].strip() if ":" in ci.detail else ci.detail
        parts.append(f"CI: {wf_part}")
    return "**Dev gates:** " + " · ".join(parts) if parts else None


def _render_modularity_section(modularity_gaps: list[Gap]) -> list[str]:
    """Render the modularity gaps as a bounded, grouped subsection.

    Majors (``danger``) are listed first, then warns, capped at
    ``MODULARITY_GAPS_RENDER_CAP`` total with a ``+N more`` note for the
    remainder. Returns ``[]`` when there are no modularity gaps so the section
    is omitted entirely (no empty heading).
    """
    if not modularity_gaps:
        return []
    order = {"danger": 0, "warn": 1, "info": 2}
    ordered = sorted(modularity_gaps, key=lambda g: order.get(g.severity, 99))
    n_major = sum(1 for g in modularity_gaps if g.severity == "danger")
    n_warn = sum(1 for g in modularity_gaps if g.severity == "warn")
    out: list[str] = []
    out.append("## Modularity")
    out.append("")
    out.append(
        f"**{len(modularity_gaps)} modularity gap{'s' if len(modularity_gaps) != 1 else ''}** "
        f"({n_major} major, {n_warn} warn) — file-level size/complexity breaches. "
        "Advisory: these never block init."
    )
    out.append("")
    shown = ordered[:MODULARITY_GAPS_RENDER_CAP]
    for g in shown:
        prefix = _SEVERITY_PREFIX.get(g.severity, "•")
        out.append(f"- {prefix} **{g.title}** — {g.detail} _{g.recommendation}_")
    remaining = len(ordered) - len(shown)
    if remaining > 0:
        out.append(f"- _… +{remaining} more (re-run for the full list)_")
    out.append("")
    return out


def _strip_header_lines(text: str) -> str:
    """Strip the two leading '<!-- Managed by ... -->' / '<!-- Last refreshed ... -->' lines."""
    lines = text.splitlines()
    body_start = 0
    for i, ln in enumerate(lines[:5]):
        if ln.strip().startswith("<!--") and ("Managed by" in ln or "Last refreshed" in ln):
            body_start = i + 1
            continue
        if ln.strip() == "":
            body_start = i + 1
            continue
        break
    return "\n".join(lines[body_start:]).strip()


def render_standards_md(repo_name: str, today: str, git_sha: str | None, standards: StandardsScan) -> str:
    sha = git_sha or "no-git"
    out: list[str] = []
    out.append("<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->")
    out.append(f"<!-- Last refreshed: {today} @ {sha} -->")
    out.append("")
    out.append(f"# Dev standards — {repo_name}")
    out.append("")
    out.append(
        "What this project enforces about itself, detected from configuration files. "
        "Read this before making non-trivial changes so you don't break gates that "
        "are silently checking your work."
    )
    out.append("")

    # ── Detected standards
    if standards.standards:
        out.append("## Detected standards")
        out.append("")
        out.append("| Standard | Command | Detected in | Notes |")
        out.append("|---|---|---|---|")
        for s in standards.standards:
            cmd = f"`{s.command}`" if s.command else "—"
            cfg = f"`{s.config_file}`" if s.config_file else "—"
            detail = (s.detail or "—").replace("|", "\\|")
            out.append(f"| {s.name} | {cmd} | {cfg} | {detail} |")
        out.append("")
    else:
        out.append("## Detected standards")
        out.append("")
        out.append("_None detected._ This is either a greenfield project or one without enforced standards.")
        out.append("")

    # ── Standards health
    out.append("## Standards health")
    out.append("")
    if not standards.gaps:
        out.append("✅ **No gaps detected.** Linter, type checker, tests, and CI are all wired up.")
    else:
        counts = {"danger": 0, "warn": 0, "info": 0}
        for g in standards.gaps:
            counts[g.severity] = counts.get(g.severity, 0) + 1
        summary = ", ".join(f"{n} {sev}" for sev, n in counts.items() if n)
        out.append(
            f"**{len(standards.gaps)} gap{'s' if len(standards.gaps) != 1 else ''} detected** ({summary}). Tightening recommendations below."
        )
        out.append("")
        for g in standards.gaps:
            prefix = _SEVERITY_PREFIX.get(g.severity, "•")
            out.append(f"### {prefix} {g.title}")
            out.append("")
            out.append(g.detail)
            out.append("")
            out.append(f"**Recommendation:** {g.recommendation}")
            out.append("")

    # ── Modularity (own subsection, majors first, bounded list)
    out.extend(_render_modularity_section(standards.modularity_gaps))

    if not standards.deep:
        out.append("")
        out.append("_Run `python -m renmark.init --deep` for deeper checks (commit-message style, etc.)._")

    return "\n".join(out)


def write_standards_md(repo: Path, repo_name: str, today: str, git_sha: str | None, standards: StandardsScan) -> str:
    """Write .renmark/memory/dev-standards.md. Returns 'created' / 'refreshed' / 'unchanged'."""
    mem_dir = repo / ".renmark" / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    target = mem_dir / "dev-standards.md"
    new_text = render_standards_md(repo_name, today, git_sha, standards)

    if target.exists():
        existing = target.read_text(encoding="utf-8", errors="replace")
        if _strip_header_lines(existing) == _strip_header_lines(new_text):
            return "unchanged"
        target.write_text(new_text, encoding="utf-8")
        return "refreshed"

    target.write_text(new_text, encoding="utf-8")
    return "created"
