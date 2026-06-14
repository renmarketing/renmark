"""Project-map generator — renmark's analog to Claude Code's native /init.

Scans the repo for file structure, modules, and public symbols, then writes:

- A tiny **stub** (~10 lines) into CLAUDE.md and AGENTS.md inside a managed
  ``<!-- BEGIN:project-stub -->`` block. Always-loaded context, kept small
  for context-window hygiene.
- The **full map** (directory tree, module table, command catalog) into
  ``.renmark/memory/project-map.md``. Not auto-loaded; read on demand.

Designed to be near-zero token cost when invoked by an agent: the agent
runs ``python -m renmark.init`` and only sees the one-line summary on
stdout. All scanning, regex, rendering, and file I/O is deterministic
Python — no LLM calls.

CLI:
    python -m renmark.init             # refresh (default)
    python -m renmark.init scan        # print scan summary only, no writes
    python -m renmark.init --full      # include private symbols (leading _)

The CLI self-bootstraps: if CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/ are
missing, ``run()`` scaffolds them from templates (existence-skip, zero-LLM)
before scanning, then back-fills any missing canonical ``BEGIN:<name>`` rule
blocks. ``/renmark:init`` therefore *initializes* a project rather than
dead-ending — matching Claude Code's native ``/init``.

Exit codes:
    0  success (whether or not anything was written)
    1  scaffold/template-availability failure — CLAUDE.md still absent, or the
       renmark templates directory could not be located (genuine internal fault)
    2  user-fixable document corruption — a CLAUDE.md/AGENTS.md has unbalanced
       managed markers (orphan/duplicate/out-of-order BEGIN/END), or bad CLI
       usage. The file is left untouched; resolve markers and re-run.

Stdout (success):
    OK  stub=<created|refreshed|unchanged> map=<created|refreshed|unchanged>
        blocks=<N|unchanged> modules=<N> commands=<N> langs=<py,ts,...>
        ref=YYYY-MM-DD@<sha>
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, cast

# ── Scan configuration ───────────────────────────────────────────────────────

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "target",
    "out",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    # renmark runtime — keep memory/, exclude state/debug/logs/baks/version
}

# .renmark subdirs that are runtime-only (do not scan into the map)
EXCLUDE_RENMARK_RUNTIME = {".renmark/state", ".renmark/debug", ".renmark/logs", ".renmark/baks", ".renmark/version"}

LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
}

STUB_BEGIN = "<!-- BEGIN:project-stub -->"
STUB_END = "<!-- END:project-stub -->"

# Cap how many symbols to list per file (most-significant first)
SYMBOLS_PER_FILE_CAP = 6
# Cap rows in the module table
MODULES_CAP_FULL = 40
# Cap top-level layout lines in the stub
LAYOUT_LINES_CAP = 7
# How many files to extract symbols from (largest first)
TOP_FILES_FOR_SYMBOLS = 20
# Cap how many modularity gaps to list in dev-standards.md (majors first,
# then warns). Remainder is summarized as a "+N more" note so the rendered
# section can't be flooded by a 100+ gap scan.
MODULARITY_GAPS_RENDER_CAP = 20


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class FileInfo:
    path: Path
    rel: str
    lang: str
    loc: int
    symbols: list[str] = field(default_factory=list)


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


@dataclass
class RepoScan:
    repo: Path
    project_name: str
    stack: str
    entry_points: list[str]
    top_dirs: list[tuple[str, str]]  # (dirname, one-line purpose)
    files: list[FileInfo]
    lang_counts: dict[str, int]
    commands: list[tuple[str, str]]  # (name, one-liner)
    git_sha: str | None
    today: str
    standards: StandardsScan | None = None


# ── Discovery helpers ────────────────────────────────────────────────────────


def _is_excluded(path: Path, repo: Path) -> bool:
    """True if any path component is in EXCLUDE_DIRS, or path is in renmark runtime."""
    try:
        rel = path.relative_to(repo)
    except ValueError:
        return True
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    rel_str = "/".join(parts)
    if any(rel_str == r or rel_str.startswith(r + "/") for r in EXCLUDE_RENMARK_RUNTIME):
        return True
    return bool(any(p.endswith(".egg-info") for p in parts))


def _git_short_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def _walk_source_files(repo: Path) -> list[FileInfo]:
    files: list[FileInfo] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if _is_excluded(path, repo):
            continue
        ext = path.suffix.lower()
        lang = LANG_BY_EXT.get(ext)
        if not lang:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        loc = text.count("\n") + 1
        rel = str(path.relative_to(repo)).replace("\\", "/")
        files.append(FileInfo(path=path, rel=rel, lang=lang, loc=loc))
    return files


def _detect_stack(repo: Path) -> str:
    parts: list[str] = []
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
        py_ver = m.group(1) if m else ""
        parts.append(f"Python {py_ver}".strip() + " (pyproject.toml)" if py_ver else "Python (pyproject.toml)")
    elif (repo / "requirements.txt").exists() or (repo / "setup.py").exists():
        parts.append("Python")

    pkgjson = repo / "package.json"
    if pkgjson.exists():
        try:
            data = json.loads(pkgjson.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            data = {}
        mod_type = data.get("type", "commonjs")
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        framework = ""
        for fw in ("next", "react", "vue", "svelte", "vite", "express"):
            if fw in deps:
                framework = fw
                break
        node_label = f"Node {'ESM' if mod_type == 'module' else 'CJS'}"
        if framework:
            node_label += f" + {framework}"
        parts.append(node_label + " (package.json)")

    if (repo / "go.mod").exists():
        parts.append("Go (go.mod)")
    if (repo / "Cargo.toml").exists():
        parts.append("Rust (Cargo.toml)")
    if (repo / ".claude-plugin" / "marketplace.json").exists() or (repo / "plugin" / ".claude-plugin").exists():
        parts.append("Claude Code plugin")

    return " + ".join(parts) if parts else "Unknown"


def _detect_entry_points(repo: Path) -> list[str]:
    eps: list[str] = []
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'^([\w_-]+)\s*=\s*"([^"]+)"', text, re.MULTILINE):
            key, val = m.group(1), m.group(2)
            if ":" in val and not key.startswith(("version", "name", "description")):
                eps.append(f"{key} ({val})")
    pkgjson = repo / "package.json"
    if pkgjson.exists():
        try:
            data = json.loads(pkgjson.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            data = {}
        bin_entry = data.get("bin")
        if isinstance(bin_entry, dict):
            eps.extend(f"{k} ({v})" for k, v in bin_entry.items())
        elif isinstance(bin_entry, str):
            eps.append(bin_entry)
        if data.get("main"):
            eps.append(data["main"])
    bin_dir = repo / "bin"
    if bin_dir.exists() and bin_dir.is_dir():
        for f in sorted(bin_dir.iterdir()):
            if f.is_file():
                eps.append(f"bin/{f.name}")
    for candidate in ("main.py", "main.go", "main.rs", "renmark/__main__.py"):
        if (repo / candidate).exists():
            eps.append(candidate)
    # Claude Code plugin commands
    cmds_dir = repo / "plugin" / "commands"
    if cmds_dir.exists():
        eps.append("plugin/commands/*.md")
    return eps[:8]  # cap


def _detect_top_dirs(repo: Path) -> list[tuple[str, str]]:
    """Return (dirname, one-line-purpose) for top-level non-noise dirs."""
    purpose_hints = {
        "src": "source code",
        "lib": "library code",
        "bin": "executable scripts / wrappers",
        "tests": "test suite",
        "test": "test suite",
        "docs": "documentation",
        "doc": "documentation",
        "examples": "example projects",
        "scripts": "utility scripts",
        "tools": "maintainer scripts",
        "plugin": "Claude Code plugin (commands, skills, templates)",
        "renmark": "Python runtime (CLI, dispatch, verifier, lifecycle)",
        "data": "data files",
        "assets": "static assets",
        "public": "public web assets",
        "static": "static web assets",
        "app": "application code",
        "pages": "page components",
        "components": "UI components",
        "api": "API handlers",
        "server": "server code",
        "client": "client code",
    }
    rows: list[tuple[str, str]] = []
    for entry in sorted(repo.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name in EXCLUDE_DIRS:
            continue
        if entry.name.endswith(".egg-info"):
            continue
        purpose = purpose_hints.get(entry.name, "")
        if not purpose:
            # Try to infer from a README inside the dir
            for readme_name in ("README.md", "readme.md", "README"):
                rfile = entry / readme_name
                if rfile.exists():
                    first_line = next(
                        (
                            ln.strip()
                            for ln in rfile.read_text(encoding="utf-8", errors="replace").splitlines()
                            if ln.strip() and not ln.strip().startswith("#")
                        ),
                        "",
                    )
                    if first_line:
                        purpose = first_line[:80]
                        break
            if not purpose:
                purpose = f"{entry.name}/"
        rows.append((entry.name, purpose))
    return rows[:LAYOUT_LINES_CAP]


def _detect_commands(repo: Path) -> list[tuple[str, str]]:
    """Pull Claude Code plugin commands from plugin/commands/*.md.

    Each command file has a frontmatter `description:` we use as the one-liner.
    """
    cmds_dir = repo / "plugin" / "commands"
    if not cmds_dir.exists():
        return []
    out: list[tuple[str, str]] = []
    plugin_name = "renmark"
    # Try to read plugin name from manifest
    manifest = repo / "plugin" / ".claude-plugin" / "plugin.json"
    if manifest.exists():
        with contextlib.suppress(json.JSONDecodeError, KeyError):
            plugin_name = json.loads(manifest.read_text(encoding="utf-8"))["name"]
    for cmd_file in sorted(cmds_dir.glob("*.md")):
        name = cmd_file.stem
        text = cmd_file.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        if m:
            # Take first sentence only
            desc = m.group(1).strip()
            desc = re.split(r"(?<=[.!?])\s", desc)[0]
            desc = desc[:120]
        else:
            desc = ""
        out.append((f"/{plugin_name}:{name}", desc))
    return out


# ── Symbol extraction ────────────────────────────────────────────────────────

_PY_SYM = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", re.MULTILINE)
_JS_SYM = re.compile(
    r"^export\s+(?:default\s+)?(?:async\s+)?"
    r"(?:function|class|const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
_GO_FUNC = re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Z]\w*)", re.MULTILINE)
_GO_TYPE = re.compile(r"^type\s+([A-Z]\w*)", re.MULTILINE)
_RS_SYM = re.compile(r"^pub\s+(?:async\s+)?(?:fn|struct|enum|trait|mod)\s+([A-Za-z_]\w*)", re.MULTILINE)
_RB_CLASS = re.compile(r"^\s*(?:class|module)\s+([A-Z]\w*)", re.MULTILINE)
_RB_DEF = re.compile(r"^\s*def\s+([a-z_]\w*)", re.MULTILINE)


def _extract_symbols(text: str, lang: str, include_private: bool) -> list[str]:
    found: list[str] = []
    if lang == "python":
        found = _PY_SYM.findall(text)
        if not include_private:
            found = [s for s in found if not s.startswith("_")]
    elif lang in ("javascript", "typescript"):
        found = _JS_SYM.findall(text)
    elif lang == "go":
        found = _GO_FUNC.findall(text) + _GO_TYPE.findall(text)
    elif lang == "rust":
        found = _RS_SYM.findall(text)
    elif lang == "ruby":
        found = _RB_CLASS.findall(text) + _RB_DEF.findall(text)
    # Dedupe preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for s in found:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq[:SYMBOLS_PER_FILE_CAP]


def _file_purpose(text: str, lang: str) -> str:
    """One-line purpose from the first docstring or comment of a file.

    For multi-line Python docstrings, all physical lines up to the first
    sentence-end (period, exclamation mark, or question mark) are joined so
    we never return a mid-sentence wrapped fragment.  If no sentence-end is
    found, the first non-empty line is returned on its own.
    """
    lines = text.splitlines()
    if lang == "python":
        # Look for module docstring
        for i, ln in enumerate(lines[:30]):
            s = ln.strip()
            if s.startswith('"""') or s.startswith("'''"):
                quote = s[:3]
                # Same-line docstring
                if s.endswith(quote) and len(s) > 6:
                    return s[3:-3].strip()[:80]
                # Multi-line — collect body lines, join, extract first sentence.
                body_lines: list[str] = []
                # Text after the opening triple-quote on the same line (may be empty)
                after_open = s[3:].strip()
                if after_open:
                    body_lines.append(after_open)
                for j in range(i + 1, min(i + 20, len(lines))):
                    inner = lines[j].strip()
                    if inner.startswith(quote):
                        break  # closing quotes
                    body_lines.append(inner)
                if not body_lines:
                    continue
                joined = " ".join(body_lines)
                # Find first sentence end: a period, ! or ? that is followed by
                # a space, end-of-string, or closing punctuation.  This avoids
                # stopping inside backtick paths (`path/to/file.py`), URL dots,
                # or mid-word abbreviations.
                for k, ch in enumerate(joined):
                    if ch in "!?":
                        return joined[: k + 1].strip()[:80]
                    if ch == "." and (k + 1 >= len(joined) or joined[k + 1] in (" ", "\t")):
                        return joined[: k + 1].strip()[:80]
                # No sentence-end found — return the first non-empty line
                for segment in body_lines:
                    if segment:
                        return segment[:80]
    # Generic: first non-shebang comment line
    for ln in lines[:15]:
        s = ln.strip()
        if not s or s.startswith("#!"):
            continue
        for prefix in ("# ", "// ", "/* ", "* "):
            if s.startswith(prefix):
                return s[len(prefix) :].rstrip(" */").strip()[:80]
    return ""


# ── Main scan ────────────────────────────────────────────────────────────────


def scan_repo(repo: Path, include_private: bool = False) -> RepoScan:
    files = _walk_source_files(repo)
    # Extract symbols from the top-N largest files
    top = sorted(files, key=lambda f: f.loc, reverse=True)[:TOP_FILES_FOR_SYMBOLS]
    top_paths = {f.rel for f in top}
    for fi in files:
        if fi.rel in top_paths:
            try:
                text = fi.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fi.symbols = _extract_symbols(text, fi.lang, include_private)

    lang_counts: dict[str, int] = {}
    for f in files:
        lang_counts[f.lang] = lang_counts.get(f.lang, 0) + 1

    return RepoScan(
        repo=repo,
        project_name=repo.resolve().name,
        stack=_detect_stack(repo),
        entry_points=_detect_entry_points(repo),
        top_dirs=_detect_top_dirs(repo),
        files=files,
        lang_counts=lang_counts,
        commands=_detect_commands(repo),
        git_sha=_git_short_sha(repo),
        today=date.today().isoformat(),
    )


# ── Rendering ────────────────────────────────────────────────────────────────


def _render_stub_body(scan: RepoScan) -> str:
    """The stub MINUS the timestamp header — what's compared for byte-equality."""
    lines = [
        "## Project at a glance",
        "",
        f"**Stack:** {scan.stack}",
    ]
    if scan.entry_points:
        eps = ", ".join(f"`{e}`" for e in scan.entry_points[:5])
        lines.append(f"**Entry points:** {eps}")
    lines.append("")
    lines.append("**Top-level layout:**")
    for name, purpose in scan.top_dirs:
        lines.append(f"- `{name}/` — {purpose}")
    lines.append("")
    # Dev gates line (only if standards detected with runnable commands)
    if scan.standards:
        gates_line = render_dev_gates_line(scan.standards)
        if gates_line:
            lines.append("")
            lines.append(gates_line)
            lines.append("**Standards detail** → `.renmark/memory/dev-standards.md` (read before non-trivial changes).")

    lines.append("")
    lines.append(
        "**Detailed map** (modules, symbols, full tree) → `.renmark/memory/project-map.md`. "
        "Read it when you need to find a specific module or symbol."
    )
    return "\n".join(lines)


def render_stub(scan: RepoScan) -> str:
    """The full stub including BEGIN/END markers and timestamp header."""
    body = _render_stub_body(scan)
    sha = scan.git_sha or "no-git"
    header = (
        f"<!-- Managed by /renmark:init. "
        f"Last refreshed: {scan.today} @ {sha}. "
        f"Edits inside this block will be overwritten. -->"
    )
    return f"{STUB_BEGIN}\n{header}\n\n{body}\n{STUB_END}"


def _render_tree(scan: RepoScan) -> str:
    """ASCII tree of top-level dirs only — keep it shallow and readable."""
    lines = [f"{scan.project_name}/"]
    dirs = scan.top_dirs
    for i, (name, purpose) in enumerate(dirs):
        last = i == len(dirs) - 1
        prefix = "└── " if last else "├── "
        lines.append(f"{prefix}{name}/   {purpose}")
    return "\n".join(lines)


def render_full_map(scan: RepoScan) -> str:
    sha = scan.git_sha or "no-git"
    out: list[str] = []
    out.append("<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->")
    out.append(f"<!-- Last refreshed: {scan.today} @ {sha} -->")
    out.append("")
    out.append(f"# Project map — {scan.project_name}")
    out.append("")
    out.append(f"**Stack:** {scan.stack}")
    if scan.entry_points:
        out.append("**Entry points:** " + ", ".join(f"`{e}`" for e in scan.entry_points))
    langs = ", ".join(f"{lang}={n}" for lang, n in sorted(scan.lang_counts.items(), key=lambda kv: -kv[1]))
    out.append(f"**Languages:** {langs or '—'}")
    out.append("")

    out.append("## Directory tree")
    out.append("")
    out.append("```")
    out.append(_render_tree(scan))
    out.append("```")
    out.append("")

    # Modules — group by directory, list files with symbols
    out.append("## Modules")
    out.append("")
    out.append("| Path | Purpose | Key symbols |")
    out.append("|---|---|---|")
    rows_emitted = 0
    # Sort: files with symbols first, then by LOC desc
    sorted_files = sorted(scan.files, key=lambda f: (-len(f.symbols), -f.loc))
    for f in sorted_files:
        if rows_emitted >= MODULES_CAP_FULL:
            remaining = len(sorted_files) - rows_emitted
            if remaining > 0:
                out.append(f"| _… {remaining} more files_ | | |")
            break
        if not f.symbols and rows_emitted > MODULES_CAP_FULL // 2:
            # Stop emitting symbol-less files once we have a decent core
            continue
        try:
            text = f.path.read_text(encoding="utf-8", errors="replace")
            purpose = _file_purpose(text, f.lang)
        except OSError:
            purpose = ""
        syms = ", ".join(f"`{s}`" for s in f.symbols) if f.symbols else "—"
        purpose_cell = purpose or "—"
        # Escape pipes
        purpose_cell = purpose_cell.replace("|", "\\|")
        out.append(f"| `{f.rel}` | {purpose_cell} | {syms} |")
        rows_emitted += 1

    if scan.commands:
        out.append("")
        out.append("## Commands (user-facing)")
        out.append("")
        out.append("| Command | Purpose |")
        out.append("|---|---|")
        for name, desc in scan.commands:
            cell = desc.replace("|", "\\|") if desc else "—"
            out.append(f"| `{name}` | {cell} |")

    out.append("")
    return "\n".join(out)


# ── Stub merge into CLAUDE.md / AGENTS.md ────────────────────────────────────


def _existing_stub_body(text: str) -> str | None:
    """Return the body inside the BEGIN/END markers, minus the timestamp header line."""
    begin_idx = text.find(STUB_BEGIN)
    if begin_idx < 0:
        return None
    end_idx = text.find(STUB_END, begin_idx)
    if end_idx < 0:
        return None
    inner = text[begin_idx + len(STUB_BEGIN) : end_idx]
    # Strip leading newlines and the first managed-comment line
    lines = inner.lstrip("\n").splitlines()
    # Skip the header comment line (starts with "<!-- Managed by")
    body_lines = [ln for ln in lines if not (ln.strip().startswith("<!-- Managed by") and ln.strip().endswith("-->"))]
    return "\n".join(body_lines).strip()


def _count_begin_markers(text: str) -> int:
    return text.count(STUB_BEGIN)


def merge_stub_into(file_path: Path, scan: RepoScan) -> str:
    """Returns 'created' (didn't exist), 'refreshed' (rewrote), 'unchanged', or 'skipped'.

    'skipped' means the file doesn't exist and we shouldn't create it (caller's
    decision — used by AGENTS.md merge).
    """
    if not file_path.exists():
        return "skipped"

    original = file_path.read_text(encoding="utf-8", errors="replace")
    n_begin = _count_begin_markers(original)
    if n_begin > 1:
        raise RuntimeError(
            f"{file_path}: found {n_begin} `{STUB_BEGIN}` markers — file corrupted. "
            f"Resolve manually before re-running init."
        )

    new_block = render_stub(scan)
    new_body = _render_stub_body(scan).strip()

    if n_begin == 1:
        existing_body = _existing_stub_body(original) or ""
        if existing_body == new_body:
            return "unchanged"
        # Replace the existing block
        end_idx = original.find(STUB_END)
        if end_idx < 0:
            raise RuntimeError(f"{file_path}: BEGIN marker without END — file corrupted.")
        begin_idx = original.find(STUB_BEGIN)
        new_text = original[:begin_idx] + new_block + original[end_idx + len(STUB_END) :]
        file_path.write_text(new_text, encoding="utf-8")
        return "refreshed"

    # No marker — append
    suffix = "" if original.endswith("\n") else "\n"
    file_path.write_text(original + suffix + "\n" + new_block + "\n", encoding="utf-8")
    return "refreshed"  # appended is functionally a refresh


# ── Full map write ───────────────────────────────────────────────────────────


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


def write_full_map(repo: Path, scan: RepoScan) -> str:
    """Write .renmark/memory/project-map.md. Returns 'created' / 'refreshed' / 'unchanged'."""
    mem_dir = repo / ".renmark" / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    target = mem_dir / "project-map.md"
    new_text = render_full_map(scan)

    if target.exists():
        existing = target.read_text(encoding="utf-8", errors="replace")
        if _strip_header_lines(existing) == _strip_header_lines(new_text):
            # Body unchanged. The freshness header (`Last refreshed @ <sha>`) must
            # STILL advance so the staleness check that reads it
            # (renmark.roadmap.program_map_is_stale) can clear after a
            # structure-neutral commit — otherwise the header sha freezes and
            # `/renmark:init` can never un-stale the map. Rewrite iff the full
            # text (header included) differs; still report "unchanged" so the
            # body-churn semantics + stdout line stay correct.
            if existing != new_text:
                target.write_text(new_text, encoding="utf-8")
            return "unchanged"
        target.write_text(new_text, encoding="utf-8")
        return "refreshed"

    target.write_text(new_text, encoding="utf-8")
    return "created"


# ── Dev standards & health ───────────────────────────────────────────────────


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


def evaluate_health(repo: Path, standards: list[Standard], files: list[FileInfo], deep: bool) -> list[Gap]:
    """Run the gap detectors and return a list of Gap objects, severity-sorted."""
    by_name = {s.name: s for s in standards}
    gaps: list[Gap] = []
    n_source_files = len(files)
    pkg = _package_json(repo)

    # 🚨 danger: .env committed
    env_committed = (repo / ".env").exists()
    if env_committed:
        # Check if .env is gitignored
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

    # 🚨 danger: multiple package managers
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

    # ⚠ warn: no linter at all
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

    # ⚠ warn: no type checker
    if "typecheck" not in by_name:
        # Only flag for typed-ish languages
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

    # ⚠ warn: no tests in a multi-file project
    n_tests = _count_test_files(repo, files)
    if n_source_files >= 10 and n_tests == 0:
        gaps.append(
            Gap(
                "warn",
                f"No tests detected ({n_source_files} source files, 0 test files)",
                "Multi-file project with zero test files. Every change is a bet.",
                "Add the first test before the next feature. Even one smoke test changes the trajectory.",
            )
        )

    # ⚠ warn: test framework in deps but zero test files
    if "test" in by_name and n_tests == 0 and n_source_files >= 3:
        gaps.append(
            Gap(
                "warn",
                "Test framework configured but no test files",
                f"`{by_name['test'].command}` is set up, but the test directory is empty.",
                "Either add tests, or remove the unused test framework so the README doesn't lie.",
            )
        )

    # ⚠ warn: linter exists but not wired to pre-commit or CI
    if "lint" in by_name and "precommit" not in by_name and "ci" not in by_name:
        gaps.append(
            Gap(
                "warn",
                "Linter not wired to pre-commit or CI",
                f"`{by_name['lint'].command}` is configured, but nothing enforces it before commit or in CI.",
                "Add a pre-commit hook (`.pre-commit-config.yaml`) or a CI workflow that runs it.",
            )
        )

    # ⚠ warn: multi-file project with no CI
    if n_source_files >= 10 and "ci" not in by_name:
        gaps.append(
            Gap(
                "warn",
                "No CI configured",
                f"{n_source_files} source files and no `.github/workflows/`, `.gitlab-ci.yml`, or CircleCI config.",
                "Add a minimal CI workflow that runs tests + lint on every PR.",
            )
        )

    # ⚠ warn: no pre-commit AND no CI
    if "precommit" not in by_name and "ci" not in by_name and n_source_files >= 5:
        gaps.append(
            Gap(
                "warn",
                "Nothing enforces quality (no pre-commit hooks AND no CI)",
                "Whatever you configure locally won't run automatically — both pre-commit and CI are missing.",
                "Pick one — pre-commit for fast local checks, CI for team-wide gates. Both is best.",
            )
        )

    # ⚠ warn: no lockfile when package.json exists
    if pkg is not None and not any((repo / lf).exists() for lf in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")):
        gaps.append(
            Gap(
                "warn",
                "Missing lockfile for `package.json`",
                "Dependencies are unpinned at the lockfile level — fresh `npm install` may resolve different versions.",
                "Run `npm install` (or yarn/pnpm) and commit the resulting lockfile.",
            )
        )

    # ℹ info: no .gitignore
    if not (repo / ".gitignore").exists() and n_source_files >= 3:
        gaps.append(
            Gap(
                "info",
                "No `.gitignore`",
                "Without `.gitignore`, build artifacts, caches, and secrets risk being committed.",
                "Add a stack-appropriate `.gitignore` (renmark's `/renmark:setup` will create one).",
            )
        )

    # ℹ info: no README
    if not (repo / "README.md").exists() and not (repo / "README").exists() and n_source_files >= 5:
        gaps.append(
            Gap(
                "info",
                "No README",
                "Anyone new to the repo has no entry point.",
                "Add a `README.md` with: what this is, how to run it locally, how to run tests.",
            )
        )

    # Deep-only: commit-message style sample
    if deep:
        try:
            out = subprocess.run(
                ["git", "-C", str(repo), "log", "-20", "--pretty=%s"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode == 0:
                subjects = [s for s in out.stdout.splitlines() if s]
                # Conventional commits detection
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

    # Severity sort: danger > warn > info
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


# ── Standards rendering ──────────────────────────────────────────────────────


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


# ── Scaffold-if-missing & rule-block back-fill ───────────────────────────────


class MarkerCorruptionError(RuntimeError):
    """A target file's managed markers are unbalanced/malformed.

    Raised by ``merge_rule_blocks`` BEFORE any write when a CLAUDE.md/AGENTS.md
    has orphan, duplicate, nested, or out-of-order ``BEGIN:``/``END:`` markers.
    The file is SKIPPED (never written to) so a corrupt file is never made
    worse. ``run()`` maps this to exit code 2 (user-fixable document
    corruption), distinct from a genuine scaffold/template failure (exit 1).

    ``files`` maps each corrupted filename to its list of marker problems.
    """

    def __init__(self, files: dict[str, list[str]]) -> None:
        self.files = files
        detail = "; ".join(f"{fname}: {', '.join(probs)}" for fname, probs in files.items())
        super().__init__(
            f"managed markers are unbalanced in {', '.join(files)} — resolve manually before re-running init ({detail})"
        )


def _scaffold_missing(repo: Path) -> None:
    """Create CLAUDE.md/AGENTS.md/.gitignore/.renmark/ and CHANGELOG.md if absent.

    Delegates to ``bootstrap(repo, init_git=False)`` for everything it covers
    (existence-skip = non-destructive) and then creates ``CHANGELOG.md`` from
    its template — bootstrap does not. Zero-LLM, idempotent.
    """
    from . import bootstrap as _bootstrap
    from . import memory

    _bootstrap.bootstrap(repo, init_git=False)

    changelog = repo / "CHANGELOG.md"
    if not changelog.exists():
        tdir = memory.template_dir()
        if tdir is not None:
            src = tdir.parent / "CHANGELOG.md.template"
            if src.is_file():
                today = date.today().isoformat()
                changelog.write_text(
                    src.read_text(encoding="utf-8").replace("{{DATE}}", today),
                    encoding="utf-8",
                )


def merge_rule_blocks(repo: Path, *, template_dir: Path | None = None) -> dict[str, int]:
    """Back-fill MISSING canonical ``BEGIN:<name>``…``END:<name>`` rule blocks.

    Manages the canonical rule blocks of any onboarding file that defines them
    via its template. In practice that is **CLAUDE.md** — ``CLAUDE.md.template``
    is the only template carrying managed ``<!-- BEGIN:name -->`` markers.
    ``AGENTS.md.template`` has no managed markers, so AGENTS.md (if present) is
    always reported as ``0`` blocks added: there is **no CLAUDE.md↔AGENTS.md
    rule-block back-fill or mirroring**. AGENTS.md is created from its own
    template by ``bootstrap``; rule-block parity between the two files is the
    human/``sync-note`` discipline, not an automated merge.

    For each managed file that exists, the canonical blocks defined by its own
    template are compared against the blocks already present. Any canonical
    block whose ``<name>`` is ABSENT is inserted BYTE-VERBATIM at the position
    implied by template order; present blocks are left untouched (idempotent +
    non-destructive — existing block content is never edited or reordered).

    **Pre-insert corruption gate (safety property):** before inserting anything
    into a file, its existing managed markers are validated for balance
    (``lint.validate_rule_markers``). If they are malformed — orphan ``END``,
    unclosed ``BEGIN``, duplicate or out-of-order markers — the file is SKIPPED
    (never written) and collected into a ``MarkerCorruptionError`` raised after
    all well-formed files are processed. This guarantees ``merge_rule_blocks``
    never produces a file with unbalanced markers: on malformed input it skips,
    it does not insert.

    A well-formed file with a missing block that happens to share a name with a
    present BEGIN is still safe — present names are never re-inserted.

    ``template_dir`` overrides the template lookup (mainly for tests); it must
    point at the directory holding ``CLAUDE.md.template`` / ``AGENTS.md.template``.

    Returns a dict mapping each touched filename to the count of blocks added,
    e.g. ``{"CLAUDE.md": 2, "AGENTS.md": 0}``. Files that don't exist are
    omitted. Raises ``MarkerCorruptionError`` if any present file's markers are
    malformed.
    """
    from . import memory
    from .lint import _BEGIN_RE, iter_rule_blocks, validate_rule_markers

    tdir = template_dir
    if tdir is None:
        mem_tdir = memory.template_dir()
        tdir = mem_tdir.parent if mem_tdir is not None else None
    if tdir is None:
        raise RuntimeError("renmark templates directory not found; cannot back-fill rule blocks.")

    result: dict[str, int] = {}
    corrupted: dict[str, list[str]] = {}
    for fname in ("CLAUDE.md", "AGENTS.md"):
        target = repo / fname
        if not target.exists():
            continue
        tmpl = tdir / f"{fname}.template"
        if not tmpl.is_file():
            result[fname] = 0
            continue

        original = target.read_text(encoding="utf-8")

        # SAFETY GATE: never insert into a file whose markers are already
        # malformed/unbalanced — that risks turning a recoverable file into an
        # unrecoverable one. Skip it and signal corruption to run() (→ exit 2).
        marker_issues = validate_rule_markers(original)
        if marker_issues:
            corrupted[fname] = marker_issues
            continue

        canonical = iter_rule_blocks(tmpl.read_text(encoding="utf-8"))
        present = {name for name, _ in iter_rule_blocks(original)}
        # Belt-and-suspenders: a name with any BEGIN marker is "present" so it
        # is never duplicated. (After the balance gate above, every BEGIN here
        # is part of a well-formed pair, but keep this for defensive clarity.)
        present |= {m.group(1) for m in _BEGIN_RE.finditer(original)}

        missing = [(name, block) for name, block in canonical if name not in present]
        if not missing:
            result[fname] = 0
            continue

        text = original
        for name, block in missing:
            text = _insert_block(text, name, block, canonical)
        target.write_text(text, encoding="utf-8")
        result[fname] = len(missing)

    if corrupted:
        raise MarkerCorruptionError(corrupted)

    return result


def _insert_block(text: str, name: str, block: str, canonical: list[tuple[str, str]]) -> str:
    """Insert ``block`` (verbatim) into ``text`` at the position implied by
    ``canonical`` template order.

    Strategy: find the nearest canonical block that PRECEDES ``name`` and is
    already present in ``text`` — insert right after it. If none precede,
    find the nearest canonical block that FOLLOWS ``name`` and is present —
    insert right before it. If neither anchor exists, append at EOF.
    """
    from .lint import _BEGIN_RE, _END_RE

    order = [n for n, _ in canonical]
    idx = order.index(name)

    def _begin_pos(n: str) -> int | None:
        for m in _BEGIN_RE.finditer(text):
            if m.group(1) == n:
                return text.rfind("\n", 0, m.start()) + 1
        return None

    def _end_line_end(n: str) -> int | None:
        for m in _END_RE.finditer(text):
            if m.group(1) == n:
                nl = text.find("\n", m.end())
                return len(text) if nl < 0 else nl + 1
        return None

    # Prefer inserting AFTER the closest preceding present block.
    for prev in reversed(order[:idx]):
        pos = _end_line_end(prev)
        if pos is not None:
            chunk = block if block.endswith("\n") else block + "\n"
            return text[:pos] + "\n" + chunk + text[pos:]

    # Else insert BEFORE the closest following present block.
    for nxt in order[idx + 1 :]:
        pos = _begin_pos(nxt)
        if pos is not None:
            chunk = block if block.endswith("\n") else block + "\n"
            return text[:pos] + chunk + "\n" + text[pos:]

    # No anchors — append at EOF.
    suffix = "" if text.endswith("\n") else "\n"
    chunk = block if block.endswith("\n") else block + "\n"
    return text + suffix + "\n" + chunk


# ── Top-level run ────────────────────────────────────────────────────────────


def run(repo: Path, include_private: bool = False, deep: bool = False) -> tuple[int, str]:
    """Returns (exit_code, summary_line)."""
    # Scaffold-if-missing FIRST: create CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/
    # from templates (existence-skip), so init initializes rather than dead-ends.
    try:
        _scaffold_missing(repo)
    except RuntimeError as exc:
        return 1, f"FAIL  {exc}"

    claude_md = repo / "CLAUDE.md"
    if not claude_md.exists():
        # Should never happen: scaffold ran above. Only fires if templates were
        # unavailable and bootstrap silently produced nothing.
        return 1, "FAIL  CLAUDE.md still absent after scaffold — renmark templates unavailable?"

    # Back-fill any missing canonical rule blocks (verbatim, idempotent).
    # Two distinct failure classes:
    #   - MarkerCorruptionError → user-fixable document corruption → exit 2
    #   - any other RuntimeError (e.g. templates unavailable)      → exit 1
    try:
        blocks_added = merge_rule_blocks(repo)
    except MarkerCorruptionError as exc:
        return 2, f"FAIL  {exc}"
    except RuntimeError as exc:
        return 1, f"FAIL  {exc}"
    n_blocks_added = sum(blocks_added.values())

    scan = scan_repo(repo, include_private=include_private)
    # Standards scan runs first so the stub can include the gates line
    scan.standards = scan_standards(repo, scan.files, deep=deep)

    try:
        stub_status = merge_stub_into(claude_md, scan)
        agents_md = repo / "AGENTS.md"
        agents_status = merge_stub_into(agents_md, scan) if agents_md.exists() else "skipped"
        map_status = write_full_map(repo, scan)
        standards_status = write_standards_md(repo, scan.project_name, scan.today, scan.git_sha, scan.standards)
    except RuntimeError as exc:
        return 2, f"FAIL  {exc}"

    sha = scan.git_sha or "no-git"
    langs_summary = ",".join(sorted(scan.lang_counts.keys())) or "—"
    n_gaps = len(scan.standards.gaps)
    mod_gaps = scan.standards.modularity_gaps
    n_mod = len(mod_gaps)
    blocks_field = str(n_blocks_added) if n_blocks_added else "unchanged"
    summary_lines = [
        f"OK  stub={stub_status} agents={agents_status} map={map_status} standards={standards_status} "
        f"blocks={blocks_field} modules={len(scan.files)} commands={len(scan.commands)} "
        f"langs={langs_summary} ref={scan.today}@{sha}"
    ]
    # Bounded HEALTH line: counts ONLY — never the per-gap detail. Modularity
    # can produce 100+ gaps; they live in dev-standards.md, not on stdout.
    if n_gaps > 0 or n_mod > 0:
        parts: list[str] = []
        if n_gaps > 0:
            counts = {"danger": 0, "warn": 0, "info": 0}
            for g in scan.standards.gaps:
                counts[g.severity] = counts.get(g.severity, 0) + 1
            sev_part = ", ".join(f"{n} {sev}" for sev, n in counts.items() if n)
            parts.append(f"{n_gaps} standards gap{'s' if n_gaps != 1 else ''} ({sev_part})")
        if n_mod > 0:
            n_major = sum(1 for g in mod_gaps if g.severity == "danger")
            n_warn = sum(1 for g in mod_gaps if g.severity == "warn")
            parts.append(f"{n_mod} modularity ({n_major} major/{n_warn} warn)")
        summary_lines.append(f"HEALTH: {', '.join(parts)} — see `.renmark/memory/dev-standards.md`")
    return 0, "\n".join(summary_lines)


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    include_private = False
    deep = False
    if "--full" in argv:
        include_private = True
        argv.remove("--full")
    if "--deep" in argv:
        deep = True
        argv.remove("--deep")

    # Allow a bare path as the first arg → implicit "refresh <path>"
    KNOWN_CMDS = {"refresh", ".", "scan", "help", "-h", "--help"}
    if argv and argv[0] not in KNOWN_CMDS:
        argv = ["refresh", *argv]

    cmd = argv[0] if argv else "refresh"

    if cmd in ("-h", "--help", "help"):
        sys.stdout.write(__doc__ or "")
        return 0

    if cmd == "scan":
        repo = Path(argv[1]) if len(argv) > 1 else Path(".")
        scan = scan_repo(repo, include_private=include_private)
        standards = scan_standards(repo, scan.files, deep=deep)
        sys.stdout.write(f"project:   {scan.project_name}\n")
        sys.stdout.write(f"stack:     {scan.stack}\n")
        sys.stdout.write(f"files:     {len(scan.files)}\n")
        sys.stdout.write(f"langs:     {dict(sorted(scan.lang_counts.items(), key=lambda kv: -kv[1]))}\n")
        sys.stdout.write(f"commands:  {len(scan.commands)}\n")
        sys.stdout.write(f"entries:   {scan.entry_points}\n")
        sys.stdout.write(f"top:       {[d for d, _ in scan.top_dirs]}\n")
        sys.stdout.write(f"standards: {[s.name for s in standards.standards]}\n")
        sys.stdout.write(
            f"gaps:      {len(standards.gaps)} ({', '.join(g.severity for g in standards.gaps) or 'none'})\n"
        )
        return 0

    if cmd in ("refresh", "."):
        repo = Path(argv[1]) if (len(argv) > 1 and not argv[1].startswith("-")) else Path(".")
        code, line = run(repo, include_private=include_private, deep=deep)
        if code == 0:
            sys.stdout.write(line + "\n")
        else:
            sys.stderr.write(line + "\n")
        return code

    sys.stderr.write(f"unknown command: {cmd}\n")
    sys.stderr.write("usage: python -m renmark.init [refresh|scan] [path] [--full] [--deep]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
