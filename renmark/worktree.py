"""deterministic-first — git commands only, no model calls (REQ-21).

Worktree lifecycle helpers: enumerate worktrees, check cleanliness, compute
divergence, and identify merged/stale branches ready for cleanup.  Every
function is pure and deterministic — subprocess calls to git, graceful
degradation on failure (return typed empties / False / None instead of raising).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Internal helpers (private — not for cross-module import)
# ---------------------------------------------------------------------------

def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in *repo* and return the completed process.

    ``shell=False``, list args, text mode — matches the style in
    ``renmark/providers/codex.py``.  Callers are responsible for checking
    ``returncode``.
    """
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )


def _default_branch(repo: Path) -> str:
    """Return the default branch name (main/master/…) for *repo*.

    Tries ``origin/HEAD`` first; falls back to ``main``.
    """
    proc = _run_git(repo, "rev-parse", "--abbrev-ref", "origin/HEAD")
    if proc.returncode == 0:
        ref = proc.stdout.strip()
        # "origin/main" → "main"
        return ref.split("/", 1)[-1] if "/" in ref else ref
    # Fallback: check local branch names
    for candidate in ("main", "master"):
        check = _run_git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}")
        if check.returncode == 0:
            return candidate
    return "main"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def current_branch(repo: Path) -> str | None:
    """Return the currently checked-out branch name, or *None* on failure.

    Uses ``git rev-parse --abbrev-ref HEAD``.  Returns ``None`` if git
    reports an error (e.g. empty repo, detached HEAD yields ``"HEAD"`` which
    is returned as-is so callers can detect the detached state).
    """
    proc = _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if proc.returncode != 0:
        return None
    branch = proc.stdout.strip()
    return branch if branch else None


def list_worktrees(repo: Path) -> list[dict[str, object]]:
    """Return a list of dicts describing every git worktree for *repo*.

    Parses ``git worktree list --porcelain``.  Each dict contains:
    - ``path`` (str) — absolute filesystem path of the worktree
    - ``head`` (str) — current HEAD SHA
    - ``branch`` (str | None) — branch ref (e.g. ``refs/heads/main``), or
      ``None`` for a detached worktree
    - ``is_bare`` (bool) — True when the worktree is bare
    - ``is_detached`` (bool) — True when HEAD is detached

    Returns ``[]`` on any git error.
    """
    proc = _run_git(repo, "worktree", "list", "--porcelain")
    if proc.returncode != 0:
        return []

    worktrees: list[dict[str, object]] = []
    current: dict[str, object] = {}

    for raw_line in proc.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            # blank line separates worktree blocks
            if current:
                worktrees.append(current)
            current = {}
        elif line.startswith("worktree "):
            current["path"] = line[len("worktree "):]
            current.setdefault("head", "")
            current.setdefault("branch", None)
            current.setdefault("is_bare", False)
            current.setdefault("is_detached", False)
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):]
        elif line == "bare":
            current["is_bare"] = True
        elif line == "detached":
            current["is_detached"] = True

    if current:
        worktrees.append(current)

    return worktrees


def is_clean_tree(repo: Path) -> bool:
    """Return *True* when the working tree has no staged or unstaged changes.

    Uses ``git status --porcelain``; an empty output means clean.
    Returns *False* on git error (conservative: treat unknown as dirty).
    """
    proc = _run_git(repo, "status", "--porcelain")
    if proc.returncode != 0:
        return False
    return proc.stdout.strip() == ""


def diff_stat(repo: Path, base: str | None = None) -> dict[str, int]:
    """Return a summary of changes vs. *base* (or the working tree if None).

    Uses ``git diff --numstat [base]`` to count modified files, inserted
    lines, and deleted lines.

    Returns a dict ``{files_changed, insertions, deletions}`` — all zero on
    error or when there are no changes.
    """
    args = ["diff", "--numstat"]
    if base is not None:
        args.append(base)

    proc = _run_git(repo, *args)
    if proc.returncode != 0:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}

    files_changed = 0
    insertions = 0
    deletions = 0

    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            ins = int(parts[0]) if parts[0] != "-" else 0
            dels = int(parts[1]) if parts[1] != "-" else 0
        except ValueError:
            continue
        insertions += ins
        deletions += dels
        files_changed += 1

    return {
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def divergence(repo: Path, base: str, head: str = "HEAD") -> dict[str, int]:
    """Return how many commits *head* is ahead of / behind *base*.

    Uses ``git rev-list --left-right --count base...head`` (three-dot /
    symmetric-difference range).  Returns ``{ahead, behind}``; both zero on
    error.

    ``ahead``  = commits reachable from *head* but not *base*.
    ``behind`` = commits reachable from *base* but not *head*.
    """
    proc = _run_git(repo, "rev-list", "--left-right", "--count", f"{base}...{head}")
    if proc.returncode != 0:
        return {"ahead": 0, "behind": 0}

    parts = proc.stdout.strip().split()
    if len(parts) != 2:
        return {"ahead": 0, "behind": 0}

    try:
        # left-right: left = behind (reachable from base), right = ahead
        behind = int(parts[0])
        ahead = int(parts[1])
    except ValueError:
        return {"ahead": 0, "behind": 0}

    return {"ahead": ahead, "behind": behind}


def is_merged(repo: Path, branch: str, into: str = "HEAD") -> bool:
    """Return *True* when *branch*'s tip is an ancestor of *into*.

    Uses ``git merge-base --is-ancestor <branch> <into>`` — exit code 0
    means ancestor (merged), non-zero means not merged or error.

    This is the exact gate used before removing a stale worktree: if the
    branch is an ancestor of the default branch it is safe to delete.
    """
    proc = _run_git(repo, "merge-base", "--is-ancestor", branch, into)
    return proc.returncode == 0


def stale_worktrees(repo: Path, *, clean_only: bool = True) -> list[dict[str, object]]:
    """Return worktrees whose branch has already been merged into the default branch.

    These are candidates for cleanup.  When *clean_only* is True (default),
    only worktrees with a clean working tree are included — dirty worktrees
    are never reported as stale even if merged.

    Composes :func:`list_worktrees`, :func:`is_merged`, and
    :func:`is_clean_tree`.  Each returned dict is the raw worktree dict from
    :func:`list_worktrees`.
    """
    default = _default_branch(repo)
    worktrees = list_worktrees(repo)
    stale: list[dict[str, object]] = []

    for wt in worktrees:
        branch_ref = wt.get("branch")
        wt_path = wt.get("path")

        # Skip bare or detached worktrees — no meaningful branch to merge-check
        if wt.get("is_bare") or wt.get("is_detached") or not branch_ref:
            continue

        # Resolve the short branch name from the full ref (refs/heads/foo → foo)
        branch_name = str(branch_ref)
        if branch_name.startswith("refs/heads/"):
            branch_name = branch_name[len("refs/heads/"):]

        # Skip the default branch itself
        if branch_name == default:
            continue

        # The merge check is run from the repo root — branch ref is authoritative
        if not is_merged(repo, branch_name, into=default):
            continue

        # Optionally skip dirty worktrees
        if clean_only and wt_path and not is_clean_tree(Path(str(wt_path))):
            continue

        stale.append(wt)

    return stale
