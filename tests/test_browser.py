"""---
artifact_type: test_artifact
schema_version: 1
created_at: 2026-06-13T00:00:00Z
source_sha: 90237b4e4449e51f1ee64d3e42f50685096869d9
related_plan: null
generator: codex
stale_after: null
dependency_refs:
  - /home/renmark/projects/ai-system/renmark/browser.py
completion_state: complete
confidence: high
validation_status: pending
retry_count: 0
parser_success: true
schema_compliance: true
---

Browser-session unit tests for `renmark.browser` without a Playwright install.

Findings:
- Blocking: the task requires a runnable `pytest` module and renmark artifact
  metadata in the same file. The existing project convention already resolves
  that tension by storing YAML frontmatter in the module docstring.
- Deferrable: these tests do not exercise real Playwright or Chrome binaries;
  they pin only the guarded import path and filesystem/session behavior.

Assumptions:
- `resolve_channel("mcp")` is the intended explicit env/CLI value, even though
  the auto-fallback channel is `"chrome-devtools"`.
- Secret-bearing values may exist inside the storageState file itself, but must
  not leak through stdout/stderr or sidecar metadata.
- `repo_root` is the supported isolation seam for keeping writes out of the
  real `.renmark/` tree.

Edge cases considered:
- Import failure vs guarded success without a real browser binary.
- Fresh vs malformed/aged metadata for staleness checks.
- Activation should copy the profile verbatim only when the profile is fresh.

Recommendations:
- Keep session tests hermetic by passing `repo_root=tmp_path` rather than
  mutating process CWD.
- If the browser module later adds logging, preserve the no-secret assertions.

Evidence:
- Target inspected: `/home/renmark/projects/ai-system/renmark/browser.py`
- Style matched from: `/home/renmark/projects/ai-system/tests/test_capabilities.py`
- Verifier required by task: `python3 -m pytest -q tests/test_browser.py`

## Summary

- Covers guarded Playwright availability checks without importing Playwright.
- Pins channel precedence for explicit override, env override, auto, and error cases.
- Verifies storageState save/load behavior, metadata writing, and no-secret stdout leaks.
- Validates native vs foreign storage schemas and fresh vs stale session metadata.
- Confirms activation copies fresh profiles and rejects stale ones.
"""

from __future__ import annotations

import builtins
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from renmark import browser


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class _FakeContext:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[Path] = []

    def storage_state(self, path: str) -> None:
        dest = Path(path)
        self.calls.append(dest)
        dest.write_text(json.dumps(self.payload), encoding="utf-8")


class _FakeBrowser:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def new_context(self, storage_state: str) -> dict[str, str]:
        self.calls.append(storage_state)
        return {"storage_state": storage_state}


def test_is_playwright_available_returns_false_when_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "playwright.sync_api":
            raise ImportError("playwright not installed")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert browser.is_playwright_available() is False


def test_is_playwright_available_returns_true_with_fake_sync_playwright(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSyncPlaywright:
        def __enter__(self):
            return types.SimpleNamespace(
                chromium=types.SimpleNamespace(executable_path="/fake/chromium")
            )

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    playwright_module = types.ModuleType("playwright")
    sync_api_module = types.ModuleType("playwright.sync_api")
    sync_api_module.sync_playwright = lambda: FakeSyncPlaywright()
    playwright_module.sync_api = sync_api_module

    monkeypatch.setitem(sys.modules, "playwright", playwright_module)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_module)

    assert browser.is_playwright_available() is True


def test_resolve_channel_explicit_override_beats_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RENMARK_BROWSER", "mcp")
    monkeypatch.setattr(browser, "is_playwright_available", lambda: False)

    assert browser.resolve_channel("playwright") == "playwright"


def test_resolve_channel_env_override_beats_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # "mcp" is a back-compat alias → maps to "playwright", not "mcp"
    monkeypatch.setenv("RENMARK_BROWSER", "mcp")
    monkeypatch.setattr(browser, "is_playwright_available", lambda: True)

    assert browser.resolve_channel() == "playwright"


def test_resolve_channel_mcp_alias_maps_to_playwright(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RENMARK_BROWSER", raising=False)
    # Both explicit arg and env-var "mcp" must resolve to "playwright"
    assert browser.resolve_channel("mcp") == "playwright"

    monkeypatch.setenv("RENMARK_BROWSER", "mcp")
    assert browser.resolve_channel() == "playwright"


def test_resolve_channel_native_returns_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RENMARK_BROWSER", raising=False)
    assert browser.resolve_channel("native") == "native"

    monkeypatch.setenv("RENMARK_BROWSER", "native")
    assert browser.resolve_channel() == "native"


def test_resolve_channel_chrome_devtools_returns_chrome_devtools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RENMARK_BROWSER", raising=False)
    assert browser.resolve_channel("chrome-devtools") == "chrome-devtools"


@pytest.mark.parametrize(
    ("available", "expected"),
    [(True, "playwright"), (False, "chrome-devtools")],
)
def test_resolve_channel_auto_uses_playwright_availability(
    monkeypatch: pytest.MonkeyPatch,
    available: bool,
    expected: str,
) -> None:
    monkeypatch.delenv("RENMARK_BROWSER", raising=False)
    monkeypatch.setattr(browser, "is_playwright_available", lambda: available)

    assert browser.resolve_channel("auto") == expected
    assert browser.resolve_channel() == expected


def test_resolve_channel_rejects_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RENMARK_BROWSER", raising=False)

    with pytest.raises(ValueError, match="Unknown browser channel"):
        browser.resolve_channel("bogus")

    monkeypatch.setenv("RENMARK_BROWSER", "bogus")
    with pytest.raises(ValueError, match="Unknown browser channel"):
        browser.resolve_channel()


def test_save_and_load_storage_state_round_trip_stays_under_sessions_dir_and_hides_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "super-secret-token"
    context = _FakeContext(
        {
            "cookies": [{"name": "session", "value": secret}],
            "origins": [],
        }
    )

    saved = browser.save_storage_state("profile", context, repo_root=tmp_path)

    assert saved == browser.profile_path("profile", repo_root=tmp_path)
    assert saved.parent == tmp_path / browser.SESSIONS_DIR
    assert saved.is_file()
    assert context.calls == [saved]

    meta = browser.meta_path("profile", repo_root=tmp_path)
    meta_data = json.loads(meta.read_text(encoding="utf-8"))
    assert "saved_at" in meta_data
    assert secret not in meta.read_text(encoding="utf-8")

    fake_browser = _FakeBrowser()
    loaded = browser.load_context(fake_browser, "profile", repo_root=tmp_path)

    assert loaded == {"storage_state": str(saved)}
    assert fake_browser.calls == [str(saved)]

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err


def test_validate_storage_state_accepts_native_schema(tmp_path: Path) -> None:
    path = tmp_path / "native.json"
    _write_json(path, {"cookies": [], "origins": []})

    assert browser.validate_storage_state(path) is True


def test_validate_storage_state_rejects_foreign_schema(tmp_path: Path) -> None:
    path = tmp_path / "foreign.json"
    _write_json(path, {"profile": {"cookies": []}})

    with pytest.raises(ValueError, match="cookies"):
        browser.validate_storage_state(path)


def test_is_stale_distinguishes_fresh_and_aged_profiles(tmp_path: Path) -> None:
    fresh = browser.meta_path("fresh", repo_root=tmp_path)
    stale = browser.meta_path("stale", repo_root=tmp_path)

    _write_json(
        fresh,
        {"saved_at": datetime.now(timezone.utc).isoformat()},
    )
    _write_json(
        stale,
        {"saved_at": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()},
    )

    assert browser.is_stale("fresh", repo_root=tmp_path) is False
    assert browser.is_stale("stale", repo_root=tmp_path) is True


def test_activate_copies_fresh_profile_to_active_json(tmp_path: Path) -> None:
    src = browser.profile_path("fresh", repo_root=tmp_path)
    payload = {"cookies": [], "origins": [{"origin": "https://example.test"}]}
    _write_json(src, payload)
    _write_json(
        browser.meta_path("fresh", repo_root=tmp_path),
        {"saved_at": datetime.now(timezone.utc).isoformat()},
    )

    activated = browser.activate("fresh", repo_root=tmp_path)

    assert activated == browser.active_path(repo_root=tmp_path)
    assert activated.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_activate_rejects_stale_profile(tmp_path: Path) -> None:
    src = browser.profile_path("stale", repo_root=tmp_path)
    _write_json(src, {"cookies": [], "origins": []})
    _write_json(
        browser.meta_path("stale", repo_root=tmp_path),
        {"saved_at": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()},
    )

    with pytest.raises(ValueError, match="stale"):
        browser.activate("stale", repo_root=tmp_path)

    assert not browser.active_path(repo_root=tmp_path).exists()


# ── Traversal / path-injection guard tests ────────────────────────────────────


@pytest.mark.parametrize(
    "bad_name",
    ["../evil", "a/b", "..", "", "foo/../bar", "sub/path"],
)
def test_profile_path_rejects_traversal_names(
    tmp_path: Path, bad_name: str
) -> None:
    with pytest.raises(ValueError):
        browser.profile_path(bad_name, repo_root=tmp_path)


@pytest.mark.parametrize(
    "bad_name",
    ["../evil", "a/b", "..", "", "x\\y"],
)
def test_safe_profile_name_rejects_invalid_names(bad_name: str) -> None:
    with pytest.raises(ValueError):
        browser._safe_profile_name(bad_name)


# ── Malformed saved_at → is_stale returns True, never raises ──────────────────


@pytest.mark.parametrize(
    "meta_payload",
    [
        {"saved_at": 12345},             # non-string integer
        {"saved_at": "2026-06-01T12:00:00"},  # naive datetime (no tzinfo)
        {},                              # missing key entirely
        {"saved_at": None},             # explicit None
        {"saved_at": "not-a-date"},     # garbage string
    ],
)
def test_is_stale_malformed_saved_at_returns_true_without_raising(
    tmp_path: Path, meta_payload: dict
) -> None:
    _write_json(browser.meta_path("bad", repo_root=tmp_path), meta_payload)
    # Must return True and must NOT raise
    result = browser.is_stale("bad", repo_root=tmp_path)
    assert result is True


def test_is_stale_missing_meta_file_returns_true(tmp_path: Path) -> None:
    # No meta file written — is_stale should return True, not raise
    result = browser.is_stale("nonexistent", repo_root=tmp_path)
    assert result is True


# ── activate refuses fresh-but-foreign-schema JSON ────────────────────────────


def test_activate_rejects_foreign_schema_even_when_fresh(tmp_path: Path) -> None:
    src = browser.profile_path("foreign", repo_root=tmp_path)
    # Foreign schema: has no "cookies" or "origins" keys
    _write_json(src, {"profile": {"cookies": []}, "version": 1})
    _write_json(
        browser.meta_path("foreign", repo_root=tmp_path),
        {"saved_at": datetime.now(timezone.utc).isoformat()},
    )

    with pytest.raises(ValueError, match="cookies"):
        browser.activate("foreign", repo_root=tmp_path)

    # active.json must NOT have been written
    assert not browser.active_path(repo_root=tmp_path).exists()
