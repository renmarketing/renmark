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
PROJECT_DELIVERY_MARKER = "project-delivery-contract"
PROJECT_DELIVERY_BEGIN = f"<!-- BEGIN:{PROJECT_DELIVERY_MARKER} -->"
PROJECT_DELIVERY_END = f"<!-- END:{PROJECT_DELIVERY_MARKER} -->"

# Cap how many symbols to list per file (most-significant first)
SYMBOLS_PER_FILE_CAP = 6
# Cap rows in the module table
MODULES_CAP_FULL = 40
# Cap top-level layout lines in the stub
LAYOUT_LINES_CAP = 7
# How many files to extract symbols from (largest first)
TOP_FILES_FOR_SYMBOLS = 20

# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class FileInfo:
    path: Path
    rel: str
    lang: str
    loc: int
    symbols: list[str] = field(default_factory=list)


# Re-exports for backward compatibility — symbols moved to renmark.health
from .health import (
    Gap as Gap,
)
from .health import (
    Standard as Standard,
)
from .health import (
    StandardsScan as StandardsScan,
)
from .health import (
    _strip_header_lines,
)
from .health import (
    evaluate_health as evaluate_health,
)
from .health import (
    render_dev_gates_line as render_dev_gates_line,
)
from .health import (
    render_standards_md as render_standards_md,
)
from .health import (
    scan_standards as scan_standards,
)
from .health import (
    write_standards_md as write_standards_md,
)


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


def _first_sentence(joined: str) -> str:
    """Return the first sentence from a joined docstring body (≤80 chars), or ''."""
    for k, ch in enumerate(joined):
        if ch in "!?":
            return joined[: k + 1].strip()[:80]
        if ch == "." and (k + 1 >= len(joined) or joined[k + 1] in (" ", "\t")):
            return joined[: k + 1].strip()[:80]
    return ""


def _collect_docstring_body(lines: list[str], i: int, quote: str, first_part: str) -> str:
    """Collect a multi-line docstring body and return its first sentence (≤80 chars)."""
    body_lines: list[str] = []
    if first_part:
        body_lines.append(first_part)
    for j in range(i + 1, min(i + 20, len(lines))):
        inner = lines[j].strip()
        if inner.startswith(quote):
            break
        body_lines.append(inner)
    if not body_lines:
        return ""
    result = _first_sentence(" ".join(body_lines))
    if result:
        return result
    for segment in body_lines:
        if segment:
            return segment[:80]
    return ""


def _extract_python_docstring(lines: list[str]) -> str:
    """Return the first sentence of a Python module docstring, or ''."""
    for i, ln in enumerate(lines[:30]):
        s = ln.strip()
        if not (s.startswith('"""') or s.startswith("'''")):
            continue
        quote = s[:3]
        if s.endswith(quote) and len(s) > 6:
            return s[3:-3].strip()[:80]
        result = _collect_docstring_body(lines, i, quote, s[3:].strip())
        if result:
            return result
    return ""


def _extract_generic_comment(lines: list[str]) -> str:
    """Return the first non-shebang comment line across common comment styles."""
    for ln in lines[:15]:
        s = ln.strip()
        if not s or s.startswith("#!"):
            continue
        for prefix in ("# ", "// ", "/* ", "* "):
            if s.startswith(prefix):
                return s[len(prefix) :].rstrip(" */").strip()[:80]
    return ""


def _file_purpose(text: str, lang: str) -> str:
    """One-line purpose from the first docstring or comment of a file.

    For multi-line Python docstrings, all physical lines up to the first
    sentence-end (period, exclamation mark, or question mark) are joined so
    we never return a mid-sentence wrapped fragment.  If no sentence-end is
    found, the first non-empty line is returned on its own.
    """
    lines = text.splitlines()
    if lang == "python":
        result = _extract_python_docstring(lines)
        if result:
            return result
    return _extract_generic_comment(lines)


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


class MarkerNotFoundError(LookupError):
    """A requested ``BEGIN:<name>``…``END:<name>`` block is absent from the text.

    Raised by :func:`merge_marked_block` when the named block does not exist.
    Distinct from :class:`MarkerCorruptionError` (which signals malformed/
    unbalanced markers). The caller decides whether absence means "insert" or
    "error out" — the primitive itself never inserts a missing block.
    """


def count_begin_markers(text: str, marker_name: str | None = None) -> int:
    """Count managed ``<!-- BEGIN:<name> -->`` markers in ``text``.

    With ``marker_name`` ``None`` (default), counts every BEGIN marker that
    matches the canonical convention (``renmark.lint._BEGIN_RE`` — optional
    surrounding whitespace, ``name`` of ``[A-Za-z][A-Za-z0-9_-]*``). With a
    ``marker_name``, counts only BEGIN markers for that exact name.

    This is the public, reusable counterpart of the marker convention used by
    :func:`merge_marked_block` and the rule-block merge; other modules (e.g. the
    skill-template generator) import it instead of re-deriving the regex.
    """
    from .lint import _BEGIN_RE

    if marker_name is None:
        return sum(1 for _ in _BEGIN_RE.finditer(text))
    return sum(1 for m in _BEGIN_RE.finditer(text) if m.group(1) == marker_name)


def _marker_validation_text(text: str) -> str:
    """Return the LF view used solely for managed-marker validation/detection.

    The marker regexes are intentionally LF-anchored.  Keep writes and all
    non-marker content on the original text, but make CRLF guidance files obey
    the same corruption contract before any merge decides a block is absent.
    """
    return text.replace("\r\n", "\n")


def _count_begin_markers(text: str) -> int:
    """Stub-specific corruption counter — substring count of ``STUB_BEGIN``.

    Deliberately a raw ``str.count`` (not the regex-based
    :func:`count_begin_markers`): the stub corruption check must catch a
    ``STUB_BEGIN`` substring anywhere — inline, mid-line, or duplicated — not
    only canonical own-line markers. Routing this through the regex primitive
    silently changed malformed-marker behavior, so it stays a substring count.
    """
    return text.count(STUB_BEGIN)


def merge_marked_block(text: str, marker_name: str, new_body: str, *, newline: str = "\n") -> str:
    """Replace the content between ``BEGIN:<marker_name>`` and ``END:<marker_name>``.

    General, reusable marker-merge primitive: returns a copy of ``text`` in
    which the span from the start of the ``<!-- BEGIN:<marker_name> -->`` line
    through the end of the ``<!-- END:<marker_name> -->`` line is rewritten as::

        <!-- BEGIN:<marker_name> -->{new_body}<!-- END:<marker_name> -->

    The markers themselves are preserved (regenerated in canonical form);
    ``new_body`` is the verbatim inner content placed between them, including any
    leading/trailing newlines the caller wants. Text outside the block is left
    byte-for-byte unchanged.

    Guard semantics match the rule-block merge: ``text`` is first validated with
    ``renmark.lint.validate_rule_markers`` and any malformed markers — orphan
    ``END``, unclosed ``BEGIN``, duplicate, or out-of-order — raise
    :class:`MarkerCorruptionError` (nothing is written). If the named block is
    absent (well-formed text, no such ``BEGIN``/``END`` pair), raises
    :class:`MarkerNotFoundError` — the caller decides whether to insert.

    Byte-equality / idempotence is the caller's concern; this just returns the
    merged text.
    """
    from .lint import validate_rule_markers

    # The lint regexes intentionally match LF-terminated Markdown. Normalize
    # only for validation; all subsequent slicing uses the original text so
    # bytes outside the managed block remain untouched.
    issues = validate_rule_markers(_marker_validation_text(text))
    if issues:
        raise MarkerCorruptionError({"<text>": issues})

    begin_re = re.compile(rf"^<!-- BEGIN:{re.escape(marker_name)} -->\r?$", re.MULTILINE)
    end_re = re.compile(rf"^<!-- END:{re.escape(marker_name)} -->\r?$", re.MULTILINE)
    begin = begin_re.search(text)
    end = end_re.search(text)
    if begin is None or end is None:
        raise MarkerNotFoundError(
            f"no `BEGIN:{marker_name}`…`END:{marker_name}` block found in text"
        )

    # Expand to whole-line boundaries: start of the BEGIN line through the end
    # of the END line (validate_rule_markers already guaranteed BEGIN<END).
    line_start = text.rfind("\n", 0, begin.start()) + 1
    nl = text.find("\n", end.end())
    line_end = len(text) if nl < 0 else nl + 1
    trailing = "" if nl < 0 else newline

    rebuilt = f"<!-- BEGIN:{marker_name} -->{new_body}<!-- END:{marker_name} -->{trailing}"
    return text[:line_start] + rebuilt + text[line_end:]


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
        # Replace the existing block. Stub merge intentionally uses substring
        # find/index splicing (NOT the regex ``merge_marked_block`` primitive):
        # the corruption contract here is substring-based and must stay so.
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


def project_delivery_contract_path() -> Path:
    """Return the shipped canonical managed project-delivery contract."""
    return Path(__file__).resolve().parents[1] / "plugin" / "skills" / ".shared" / "project-delivery-contract.md"


def project_delivery_contract_freshness_marker(repo: Path | None = None) -> str:
    """Return the deterministic source revision recorded in contract refreshes."""
    sha = _git_short_sha(repo) if repo is not None else None
    return sha or "no-git"


def render_project_delivery_contract(repo: Path | None = None) -> str:
    """Render the canonical contract body used by both root guidance files.

    The source revision is a deterministic freshness marker. It changes after
    a repository commit even when the contract prose itself is unchanged.
    """
    source = project_delivery_contract_path()
    if not source.is_file():
        raise RuntimeError(f"canonical project-delivery contract not found: {source}")
    marker = project_delivery_contract_freshness_marker(repo)
    return "\n" + f"<!-- Last refreshed: @ {marker} -->" + "\n" + source.read_text(encoding="utf-8").strip() + "\n"


def _marked_block_body(text: str, marker_name: str) -> str | None:
    """Return a well-formed managed block's body, or ``None`` if it is absent."""
    begin_re = re.compile(rf"^<!-- BEGIN:{re.escape(marker_name)} -->\r?$", re.MULTILINE)
    end_re = re.compile(rf"^<!-- END:{re.escape(marker_name)} -->\r?$", re.MULTILINE)
    begin = begin_re.search(text)
    end = end_re.search(text)
    if begin is None or end is None:
        return None
    return text[begin.end() : end.start()]


def _semantic_markdown(text: str) -> str:
    """Stable, deliberately small semantic comparison for managed prose."""
    return " ".join(text.casefold().split())


def project_delivery_contract_is_fresh(text: str, repo: Path | None = None) -> bool:
    """Whether ``text`` contains the current canonical contract body exactly."""
    # Marker regexes use LF line anchors, so normalize solely for this
    # read-only freshness comparison.  Writers retain original file bytes.
    body = _marked_block_body(text.replace("\r\n", "\n"), PROJECT_DELIVERY_MARKER)
    # The managed block may live in a CRLF guidance file even though the
    # canonical renderer uses LF.  Freshness concerns the block's content, not
    # its on-disk newline convention; writers still preserve that convention.
    return body is not None and body == render_project_delivery_contract(repo)


def project_delivery_contracts_are_semantically_equal(claude_text: str, agents_text: str) -> bool:
    """Whether the two managed contract blocks express the same contract."""
    claude_body = _marked_block_body(claude_text, PROJECT_DELIVERY_MARKER)
    agents_body = _marked_block_body(agents_text, PROJECT_DELIVERY_MARKER)
    return claude_body is not None and agents_body is not None and _semantic_markdown(claude_body) == _semantic_markdown(agents_body)


# Short aliases keep deterministic callers from reimplementing freshness/parity.
contract_is_fresh = project_delivery_contract_is_fresh
contracts_are_semantically_equal = project_delivery_contracts_are_semantically_equal


def merge_project_delivery_contract(repo: Path) -> dict[str, str]:
    """Merge the canonical contract into root guidance via the one safe writer.

    Only the named managed block is changed. Existing prose and unrelated
    managed blocks remain byte-for-byte intact; malformed files are not written.
    """
    from .lint import validate_rule_markers

    body = render_project_delivery_contract(repo)
    originals: dict[str, str] = {}
    corrupted: dict[str, list[str]] = {}
    for fname in ("CLAUDE.md", "AGENTS.md"):
        target = repo / fname
        if not target.exists():
            continue
        original = target.read_bytes().decode("utf-8")
        originals[fname] = original
        issues = validate_rule_markers(_marker_validation_text(original))
        if issues:
            corrupted[fname] = issues
    if corrupted:
        raise MarkerCorruptionError(corrupted)

    result: dict[str, str] = {}
    for fname, original in originals.items():
        target = repo / fname
        if project_delivery_contract_is_fresh(original, repo):
            result[fname] = "unchanged"
            continue
        try:
            newline = "\r\n" if "\r\n" in original else "\n"
            merged = merge_marked_block(
                original,
                PROJECT_DELIVERY_MARKER,
                body.replace("\n", newline),
                newline=newline,
            )
        except MarkerNotFoundError:
            newline = "\r\n" if "\r\n" in original else "\n"
            suffix = "" if original.endswith(("\n", "\r")) else newline
            merged = (
                original
                + suffix
                + newline
                + PROJECT_DELIVERY_BEGIN
                + body.replace("\n", newline)
                + PROJECT_DELIVERY_END
                + newline
            )
        if merged != original:
            target.write_bytes(merged.encode("utf-8"))
            result[fname] = "refreshed"
        else:
            result[fname] = "unchanged"
    return result


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
        marker_view = _marker_validation_text(original)
        marker_issues = validate_rule_markers(marker_view)
        if marker_issues:
            corrupted[fname] = marker_issues
            continue

        canonical = iter_rule_blocks(tmpl.read_text(encoding="utf-8"))
        present = {name for name, _ in iter_rule_blocks(marker_view)}
        # Belt-and-suspenders: a name with any BEGIN marker is "present" so it
        # is never duplicated. (After the balance gate above, every BEGIN here
        # is part of a well-formed pair, but keep this for defensive clarity.)
        present |= {m.group(1) for m in _BEGIN_RE.finditer(marker_view)}

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

    # The delivery contract is deliberately merged only here, through the same
    # guarded marker primitive used for all managed root guidance. Start and
    # Feature may inspect freshness, but must never become competing writers.
    try:
        contract_status = merge_project_delivery_contract(repo)
    except MarkerCorruptionError as exc:
        return 2, f"FAIL  {exc}"
    except RuntimeError as exc:
        return 1, f"FAIL  {exc}"

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
    contract_field = (
        "unchanged"
        if contract_status and all(status == "unchanged" for status in contract_status.values())
        else "refreshed"
    )
    summary_lines = [
        f"OK  stub={stub_status} agents={agents_status} map={map_status} standards={standards_status} "
        f"blocks={blocks_field} contract={contract_field} modules={len(scan.files)} commands={len(scan.commands)} "
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
