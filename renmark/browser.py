"""Optional browser layer for renmark — session management and channel routing.

Playwright is an **optional** dependency. This module MUST import successfully
on a stdlib-only install. All playwright usage is guarded behind lazy imports
inside the functions that actually need it.

Channel resolution precedence:
  explicit ``--browser`` arg > ``RENMARK_BROWSER`` env > auto-detect.

Session layout (all relative to repo root):
  .renmark/state/browser-sessions/<name>.json   — Playwright storageState
  .renmark/state/browser-sessions/<name>.meta.json — sidecar metadata
  .renmark/state/browser-sessions/active.json   — copy of the active session
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Directory constant ─────────────────────────────────────────────────────────

SESSIONS_DIR = ".renmark/state/browser-sessions"

# Valid channel identifiers accepted by resolve_channel() (excluding "auto" and
# back-compat "mcp" alias which are resolved before returning).
_VALID_CHANNELS: frozenset[str] = frozenset(
    {"playwright", "chrome-devtools", "native", "auto", "mcp"}
)

# Profile name must be filesystem-safe: alphanumerics, dots, underscores, hyphens.
_PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# ── Safe name guard ────────────────────────────────────────────────────────────


def _safe_profile_name(name: str) -> str:
    """Validate *name* and return it unchanged when safe.

    Raises:
        ValueError: when *name* contains path separators, traversal sequences,
            or characters outside ``[A-Za-z0-9._-]``.
    """
    if not isinstance(name, str) or not name:
        raise ValueError(f"Profile name must be a non-empty string, got {name!r}")
    if name in (".", ".."):
        raise ValueError(f"Profile name must not be a bare dot sequence, got {name!r}")
    if not _PROFILE_NAME_RE.match(name):
        raise ValueError(
            f"Profile name {name!r} contains invalid characters. "
            "Only [A-Za-z0-9._-] are allowed."
        )
    return name


# ── Repo-root detection ────────────────────────────────────────────────────────


def _repo_root() -> Path:
    """Walk upward from cwd to the nearest dir containing ``.git`` or ``.renmark``.

    Falls back to ``Path.cwd()`` when no such directory is found.
    """
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / ".renmark").exists():
            return candidate
    return current


# ── Path helpers ───────────────────────────────────────────────────────────────


def _sessions_root(repo_root: str | Path | None = None) -> Path:
    """Return the absolute sessions directory, resolved against *repo_root*.

    Falls back to ``_repo_root()`` when *repo_root* is not supplied.
    """
    base = Path(repo_root) if repo_root is not None else _repo_root()
    return (base / SESSIONS_DIR).resolve()


def _check_under_sessions(path: Path, sessions: Path) -> Path:
    """Assert *path* stays under *sessions*; raise ValueError otherwise."""
    resolved = path.resolve()
    try:
        resolved.relative_to(sessions)
    except ValueError as exc:
        raise ValueError(
            f"Path {resolved!r} escapes the sessions directory {sessions!r}. "
            "Refusing to operate on it."
        ) from exc
    return resolved


def profile_path(name: str, repo_root: str | Path | None = None) -> Path:
    """Return the storageState JSON path for session *name*."""
    _safe_profile_name(name)
    sessions = _sessions_root(repo_root)
    candidate = sessions / f"{name}.json"
    _check_under_sessions(candidate, sessions)
    return candidate


def meta_path(name: str, repo_root: str | Path | None = None) -> Path:
    """Return the sidecar metadata JSON path for session *name*."""
    _safe_profile_name(name)
    sessions = _sessions_root(repo_root)
    candidate = sessions / f"{name}.meta.json"
    _check_under_sessions(candidate, sessions)
    return candidate


def active_path(repo_root: str | Path | None = None) -> Path:
    """Return the path for the currently-active session snapshot."""
    return _sessions_root(repo_root) / "active.json"


# ── Playwright availability ────────────────────────────────────────────────────


def is_playwright_available() -> bool:
    """Return True only when playwright is installed *and* Chromium is present.

    Never raises — all exceptions are caught and mapped to False.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            _ = pw.chromium.executable_path  # raises if binary missing
        return True
    except ImportError:
        return False
    except Exception:  # playwright "executable doesn't exist" or other runtime error
        return False


# ── Channel resolution ─────────────────────────────────────────────────────────


def resolve_channel(override: str | None = None) -> str:
    """Resolve the browser channel using the documented precedence order.

    Precedence:
      1. *override* (explicit ``--browser`` CLI arg)
      2. ``RENMARK_BROWSER`` environment variable
      3. ``auto`` — "playwright" if available, else "chrome-devtools"

    Accepted values:
      - ``playwright``      — use Playwright directly
      - ``chrome-devtools`` — use Chrome DevTools Protocol (MCP server)
      - ``native``          — explicit native channel; never chosen by auto
      - ``auto``            — resolved at runtime; never returned as-is
      - ``mcp``             — back-compat alias, maps to ``"playwright"``

    Raises:
        ValueError: when *override* (or the env var) is not a recognised value.

    Returns:
        One of ``"playwright"``, ``"chrome-devtools"``, or ``"native"``.
    """
    raw: str | None = override or os.environ.get("RENMARK_BROWSER")

    if raw is not None:
        normalised = raw.strip().lower()
        if normalised not in _VALID_CHANNELS:
            raise ValueError(
                f"Unknown browser channel {raw!r}. "
                f"Valid values: {sorted(_VALID_CHANNELS)}"
            )
        if normalised == "mcp":
            # Back-compat alias: "mcp" → playwright (@playwright/mcp channel).
            return "playwright"
        if normalised == "auto":
            return "playwright" if is_playwright_available() else "chrome-devtools"
        # "playwright", "chrome-devtools", "native" returned as-is.
        return normalised

    # No explicit override and no env var → auto-detect.
    return "playwright" if is_playwright_available() else "chrome-devtools"


# ── Session storage helpers ────────────────────────────────────────────────────


def save_storage_state(
    name: str,
    context: Any,
    repo_root: str | Path | None = None,
) -> Path:
    """Persist Playwright *context* storage state and write sidecar metadata.

    Args:
        name: Logical session name (used as filename stem).
        context: A live Playwright ``BrowserContext`` instance.
        repo_root: Optional repo root for path resolution.

    Returns:
        The path to the saved storageState JSON file.

    Note:
        Cookie and token *values* are never logged.  The path is safe to log.
    """
    dest = profile_path(name, repo_root)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Playwright writes the file; we only keep the path.
    context.storage_state(path=str(dest))

    _write_meta(name, mode="storageState", repo_root=repo_root)
    return dest


def load_context(
    browser: Any,
    name: str,
    repo_root: str | Path | None = None,
) -> Any:
    """Create a new Playwright ``BrowserContext`` from a saved session.

    Args:
        browser: A live Playwright ``Browser`` instance.
        name: Logical session name whose storageState will be loaded.
        repo_root: Optional repo root for path resolution.

    Returns:
        A new ``BrowserContext`` with the saved authentication.

    Raises:
        FileNotFoundError: when the session file does not exist.
        ValueError: when the session file fails schema validation.
    """
    src = profile_path(name, repo_root)
    if not src.exists():
        raise FileNotFoundError(f"Session not found: {src}")

    validate_storage_state(src)
    return browser.new_context(storage_state=str(src))


# ── Sidecar metadata ───────────────────────────────────────────────────────────


def _write_meta(
    name: str,
    mode: str = "storageState",
    repo_root: str | Path | None = None,
) -> Path:
    """Write sidecar metadata JSON next to the session file.

    The metadata schema is intentionally minimal — it carries only what is
    needed for staleness checks and diagnostics.  It NEVER contains cookie or
    token values.
    """
    dest = meta_path(name, repo_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, str] = {
        "saved_at": datetime.now(tz=timezone.utc).isoformat(),
        "browser": "chromium",
        "mode": mode,
    }
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def is_stale(
    name: str,
    max_age_hours: float = 24,
    repo_root: str | Path | None = None,
) -> bool:
    """Return True if session *name* is older than *max_age_hours*.

    Returns True (stale) when the metadata file is missing, malformed, or
    contains a non-string / naive / invalid ``saved_at`` value.
    """
    mp = meta_path(name, repo_root)
    if not mp.exists():
        return True
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
        saved_at_raw = data["saved_at"]
        if not isinstance(saved_at_raw, str):
            return True
        saved_at = datetime.fromisoformat(saved_at_raw)
        # Require timezone-aware datetime; naive values are treated as stale.
        if saved_at.tzinfo is None:
            return True
        age = datetime.now(tz=timezone.utc) - saved_at
        return age.total_seconds() > max_age_hours * 3600
    except (KeyError, ValueError, OSError, TypeError):
        return True


# ── Schema validation ──────────────────────────────────────────────────────────


def validate_storage_state(path: str | Path) -> bool:
    """Validate that *path* contains a Playwright-native storageState.

    Playwright storageState must have a ``cookies`` list and an ``origins``
    list at the top level.  Foreign schemas (e.g. Chrome user-data dirs,
    Selenium pickles) are rejected with a clear error.

    Returns:
        True when the schema is valid.

    Raises:
        ValueError: when the file does not match the expected schema.
        FileNotFoundError: when *path* does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Storage state file not found: {p}")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Storage state is not valid JSON: {p}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Storage state must be a JSON object, got {type(data).__name__}: {p}"
        )
    if not isinstance(data.get("cookies"), list):
        raise ValueError(
            f"Storage state missing 'cookies' list (foreign schema?): {p}"
        )
    if not isinstance(data.get("origins"), list):
        raise ValueError(
            f"Storage state missing 'origins' list (foreign schema?): {p}"
        )
    return True


# ── Activation ────────────────────────────────────────────────────────────────


def activate(
    name: str,
    repo_root: str | Path | None = None,
) -> Path:
    """Copy session *name* → active.json so the static MCP server starts auth'd.

    The MCP server reads ``active.json`` at startup; this call makes the named
    session current without requiring a re-login.

    Args:
        name: Logical session name to activate.
        repo_root: Optional repo root for path resolution.

    Returns:
        The ``active_path()`` that was written.

    Raises:
        FileNotFoundError: when the session profile does not exist.
        ValueError: when the session is stale (caller must re-login) or when
            the session file fails schema validation.
    """
    src = profile_path(name, repo_root)
    if not src.exists():
        raise FileNotFoundError(
            f"Cannot activate session {name!r}: profile not found at {src}"
        )
    if is_stale(name, repo_root=repo_root):
        raise ValueError(
            f"Session {name!r} is stale. Re-login before activating."
        )

    # Validate schema before copying — refuse foreign/malformed JSON.
    validate_storage_state(src)

    dest = active_path(repo_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest
