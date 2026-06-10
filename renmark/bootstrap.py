"""Empty-folder bootstrap helper.

Used by `/renmark:brainstorm` when invoked in a fresh project (no CLAUDE.md,
no AGENTS.md, no `.renmark/`). Copies templates from the plugin, substitutes
project name + date, and creates the directory structure.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import memory


@dataclass
class BootstrapResult:
    created: list[str]  # absolute paths created
    git_initialized: bool  # True if we ran git init


def is_empty_project(repo: str | Path) -> bool:
    """Heuristic: no CLAUDE.md, no AGENTS.md, no .renmark/, no source files."""
    p = Path(repo)
    if (p / "CLAUDE.md").exists():
        return False
    if (p / "AGENTS.md").exists():
        return False
    return not (p / ".renmark").exists()


def _substitute(text: str, project_name: str, date: str) -> str:
    return text.replace("{{PROJECT_NAME}}", project_name).replace("{{DATE}}", date)


def bootstrap(
    repo: str | Path,
    *,
    project_name: str | None = None,
    init_git: bool = True,
) -> BootstrapResult:
    """Scaffold CLAUDE.md, AGENTS.md, .renmark/, and .gitignore from templates.

    Idempotent: existing files are left alone.
    """
    repo_p = Path(repo).resolve()
    repo_p.mkdir(parents=True, exist_ok=True)
    if project_name is None:
        project_name = repo_p.name
    today = dt.date.today().isoformat()

    tdir = memory.template_dir()
    if tdir is None:
        raise RuntimeError("renmark templates directory not found; install.sh symlink missing?")
    plugin_tdir = tdir.parent  # plugin/templates/

    created: list[str] = []

    # CLAUDE.md
    target = repo_p / "CLAUDE.md"
    src = plugin_tdir / "CLAUDE.md.template"
    if not target.exists() and src.is_file():
        target.write_text(
            _substitute(src.read_text(encoding="utf-8"), project_name, today),
            encoding="utf-8",
        )
        created.append(str(target))

    # AGENTS.md
    target = repo_p / "AGENTS.md"
    src = plugin_tdir / "AGENTS.md.template"
    if not target.exists() and src.is_file():
        target.write_text(
            _substitute(src.read_text(encoding="utf-8"), project_name, today),
            encoding="utf-8",
        )
        created.append(str(target))

    # .gitignore — append if missing or doesn't have .renmark/state/
    gi = repo_p / ".gitignore"
    needed_lines = (".renmark/state/", ".renmark/debug/", ".renmark/logs/")
    if gi.exists():
        text = gi.read_text(encoding="utf-8")
        missing = [ln for ln in needed_lines if ln not in text]
        if missing:
            gi.write_text(text.rstrip() + "\n\n# renmark\n" + "\n".join(missing) + "\n", encoding="utf-8")
            created.append(str(gi) + " (appended)")
    else:
        gi.write_text(
            "__pycache__/\n*.pyc\n.venv/\nvenv/\nnode_modules/\n"
            ".pytest_cache/\n.env\n.env.local\n\n# renmark\n"
            ".renmark/state/\n.renmark/debug/\n.renmark/logs/\n",
            encoding="utf-8",
        )
        created.append(str(gi))

    # .renmark/ memory files via memory.ensure_memory
    memory.ensure_memory(repo_p)
    for name in memory.MEMORY_FILES:
        created.append(str(repo_p / ".renmark" / "memory" / name))

    # .renmark/README.md from template
    rm = repo_p / ".renmark" / "README.md"
    src = plugin_tdir / "renmark-readme.md"
    if not rm.exists() and src.is_file():
        rm.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(str(rm))

    # Create empty specs/, plans/, reviews/ dirs.
    for sub in ("specs", "plans", "reviews"):
        d = repo_p / ".renmark" / sub
        d.mkdir(parents=True, exist_ok=True)
        gk = d / ".gitkeep"
        if not gk.exists():
            gk.touch()
            created.append(str(gk))

    git_initialized = False
    if init_git and not (repo_p / ".git").is_dir():
        try:
            subprocess.run(
                ["git", "init", "-q", "-b", "main"],
                cwd=str(repo_p),
                check=True,
                capture_output=True,
            )
            # Identity defaults if not configured.
            res = subprocess.run(
                ["git", "-C", str(repo_p), "config", "user.email"],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0 or not res.stdout.strip():
                subprocess.run(
                    ["git", "-C", str(repo_p), "config", "user.email", "renmark@local"],
                    check=True,
                    capture_output=True,
                )
            res = subprocess.run(
                ["git", "-C", str(repo_p), "config", "user.name"],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0 or not res.stdout.strip():
                subprocess.run(
                    ["git", "-C", str(repo_p), "config", "user.name", "renmark"],
                    check=True,
                    capture_output=True,
                )
            # Safety: only stage the files bootstrap itself created.
            # If the project is not empty (pre-existing user files present),
            # `git add -A` would silently commit every pre-existing file —
            # restrict the add to only the scaffolded paths instead.
            if is_empty_project.__doc__ and not created:
                # Nothing to stage — shouldn't happen, but guard defensively.
                pass
            else:
                # Stage only the files bootstrap created, not -A (traversal
                # guard: a non-empty project's pre-existing files must NOT be
                # committed as part of the scaffold commit).
                for path_str in created:
                    # Strip the " (appended)" annotation we sometimes add
                    clean = path_str.removesuffix(" (appended)")
                    with contextlib.suppress(subprocess.CalledProcessError):
                        subprocess.run(
                            ["git", "-C", str(repo_p), "add", "--", clean],
                            check=True,
                            capture_output=True,
                        )
            subprocess.run(
                ["git", "-C", str(repo_p), "commit", "-q", "-m", "chore: renmark scaffold"],
                check=True,
                capture_output=True,
            )
            git_initialized = True
        except subprocess.CalledProcessError:
            pass

    return BootstrapResult(created=created, git_initialized=git_initialized)
