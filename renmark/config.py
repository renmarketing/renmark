"""Persisted project-level configuration for renmark (P11 — proactivity toggle).

State lives in ``.renmark/config.json`` (committed, not gitignored — it is a
durable user preference, not runtime state).  Absence of the file or absence
of a key is always treated as the default value so that the repo behaves
identically before and after the first ``--set-proactive`` call.

Design constraints:
- stdlib json only (no third-party deps).
- All public functions are pure I/O wrappers that never raise — any OS or
  parse error degrades silently to the documented default.
- ``is_proactive`` default is ``True`` (= current behaviour; no-config == on).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG_REL = ".renmark/config.json"

_ENV_HEADLESS = "RENMARK_HEADLESS"
_ENV_EVAL_RUNNER_CMD = "RENMARK_EVAL_RUNNER_CMD"
_ENV_TRUE = {"1", "true", "yes", "on"}
_ENV_FALSE = {"0", "false", "no", "off"}


def _config_path(repo: str | Path) -> Path:
    return Path(repo) / _CONFIG_REL


def _read_raw(repo: str | Path) -> dict[str, object]:
    """Return the parsed config dict, or {} on any error (missing / corrupt)."""
    try:
        text = _config_path(repo).read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_raw(repo: str | Path, data: dict[str, object]) -> None:
    """Write the config dict atomically (best-effort — never raises)."""
    try:
        p = _config_path(repo)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


# ── Public API ────────────────────────────────────────────────────────────────


def is_proactive(repo: str | Path) -> bool:
    """Return the persisted proactivity flag for the project at *repo*.

    ``True`` (auto-route plain-English build/dev tasks through renmark) unless
    the user has explicitly turned it off via ``--set-proactive false``.

    Never raises — a missing or corrupt config file returns ``True`` so that
    the repository behaves exactly as it did before this feature shipped.
    """
    data = _read_raw(repo)
    val = data.get("proactive", True)
    # Coerce to bool; treat any non-bool truthy/falsy value sensibly.
    if isinstance(val, bool):
        return val
    return bool(val)


def set_proactive(repo: str | Path, value: bool) -> None:
    """Persist the proactivity flag for the project at *repo*.

    Reads the existing config, updates only the ``proactive`` key, and writes
    it back so unrelated keys are preserved.  Never raises.
    """
    data = _read_raw(repo)
    data["proactive"] = value
    _write_raw(repo, data)


def _env_headless() -> bool | None:
    """Parse ``RENMARK_HEADLESS`` (case-insensitive) into a tri-state.

    Returns ``True``/``False`` for a recognised value, or ``None`` when the
    variable is unset or holds any other value (so the caller falls through to
    the config file).  Never raises.
    """
    raw = os.environ.get(_ENV_HEADLESS)
    if raw is None:
        return None
    norm = raw.strip().lower()
    if norm in _ENV_TRUE:
        return True
    if norm in _ENV_FALSE:
        return False
    return None


def is_headless(repo: str | Path) -> bool:
    """Return whether renmark should run in headless (non-interactive) mode.

    Precedence:
    1. env ``RENMARK_HEADLESS`` (``1/true/yes/on`` → ``True``,
       ``0/false/no/off`` → ``False``; an explicit OFF overrides config);
    2. else the ``.renmark/config.json`` key ``"headless"`` if present **and a
       real ``bool``** (a non-bool value is ignored, not coerced — headless is
       fail-dangerous, so anything but a true bool falls through);
    3. else ``False``.

    Never raises — any OS or parse error degrades to ``False``.
    """
    env = _env_headless()
    if env is not None:
        return env
    val = _read_raw(repo).get("headless")
    if isinstance(val, bool):
        return val
    return False


def set_headless(repo: str | Path, value: bool) -> None:
    """Persist the headless flag for the project at *repo*.

    Reads the existing config, updates only the ``headless`` key, and writes
    it back so unrelated keys are preserved.  Never raises.
    """
    data = _read_raw(repo)
    data["headless"] = value
    _write_raw(repo, data)


def headless_source(repo: str | Path) -> str:
    """Return which layer decided :func:`is_headless` for *repo*.

    ``"env"`` if ``RENMARK_HEADLESS`` resolved the value, ``"config"`` if the
    config file's ``"headless"`` key did (i.e. it is a real ``bool``), else
    ``"default"``.  Uses the same precedence as :func:`is_headless` so the two
    never disagree — a non-bool config value reports ``"default"``.  Never
    raises.
    """
    if _env_headless() is not None:
        return "env"
    if isinstance(_read_raw(repo).get("headless"), bool):
        return "config"
    return "default"


def _env_eval_runner_cmd() -> str | None:
    """Parse ``RENMARK_EVAL_RUNNER_CMD`` into an optional command string.

    Returns the stripped value when the variable is set and non-blank, or
    ``None`` when it is unset or holds only whitespace (so the caller falls
    through to the config file).  Never raises.
    """
    raw = os.environ.get(_ENV_EVAL_RUNNER_CMD)
    if raw is None:
        return None
    norm = raw.strip()
    if norm:
        return norm
    return None


def _config_eval_runner_cmd(repo: str | Path) -> str | None:
    """Return the ``.renmark/config.json`` ``eval_runner_cmd`` value, normalized.

    Mirrors :func:`_env_eval_runner_cmd`: returns the stripped value only when
    the key is present, a real ``str``, and non-blank; a non-str or
    whitespace-only value is treated as unset (``None``) so the caller degrades
    to ``LiveRunnerUnavailable`` rather than a spurious empty-command error.
    Never raises.
    """
    val = _read_raw(repo).get("eval_runner_cmd")
    if isinstance(val, str):
        norm = val.strip()
        if norm:
            return norm
    return None


def eval_runner_cmd(repo: str | Path) -> str | None:
    """Return the command used to launch the eval-tier runner for *repo*.

    Precedence:
    1. env ``RENMARK_EVAL_RUNNER_CMD`` if set and non-blank (whitespace is
       stripped; a blank value is treated as unset and falls through);
    2. else the ``.renmark/config.json`` key ``"eval_runner_cmd"`` if present,
       a real ``str``, **and non-blank** (whitespace is stripped; a non-str or
       blank value is ignored, not coerced);
    3. else ``None``.

    Never raises — any OS or parse error degrades to ``None``.
    """
    env = _env_eval_runner_cmd()
    if env is not None:
        return env
    return _config_eval_runner_cmd(repo)


def set_eval_runner_cmd(repo: str | Path, value: str) -> None:
    """Persist the eval-runner command for the project at *repo*.

    Reads the existing config, updates only the ``eval_runner_cmd`` key, and
    writes it back so unrelated keys are preserved.  Never raises.
    """
    data = _read_raw(repo)
    data["eval_runner_cmd"] = value
    _write_raw(repo, data)


def eval_runner_source(repo: str | Path) -> str:
    """Return which layer decided :func:`eval_runner_cmd` for *repo*.

    ``"env"`` if ``RENMARK_EVAL_RUNNER_CMD`` resolved the value, ``"config"``
    if the config file's ``"eval_runner_cmd"`` key did (i.e. it is a real
    ``str``), else ``"default"``.  Uses the same precedence as
    :func:`eval_runner_cmd` so the two never disagree — a non-str config value
    reports ``"default"``.  Never raises.
    """
    if _env_eval_runner_cmd() is not None:
        return "env"
    if _config_eval_runner_cmd(repo) is not None:
        return "config"
    return "default"
