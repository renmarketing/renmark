"""renmark.doctor — diagnose Claude Code and Codex plugin install health.

Checks that renmark is properly registered with both supported hosts and surfaces
remediation commands for anything broken. Pure diagnostic by default;
``--fix`` mode applies the obvious safe fixes (add to settings.json,
register in installed_plugins.json, refresh cache symlink).

CLI:
    python -m renmark.doctor                    # check + report, exit 1 if any issue
    python -m renmark.doctor --fix              # apply safe registry/settings/cache fixes
    python -m renmark.doctor --refresh-codex     # stage a cache-busted local Codex source
    python -m renmark.doctor --install-routing  # opt-in: write the global routing rule
    python -m renmark.doctor --json             # machine-readable output

The global ``~/.claude/CLAUDE.md`` routing rule is ADVISORY in normal and
``--fix`` runs — doctor only DETECTS and reports its state; it never writes it.
The write is gated behind the explicit ``--install-routing`` flag, so routine
``--fix`` repairs never mutate the user's global CLAUDE.md.

Exit codes:
    0  all checks pass
    1  one or more checks failed, fixes still needed, or an explicitly
       requested --install-routing did not succeed
    2  bad usage

Why this exists: directory-marketplace Claude Code plugins need THREE
moving parts to surface their slash commands, and the canonical
``install.sh`` only addresses one of them. This module catches the
other two (and a few related drift modes) before the user discovers
the failure by typing ``/renmark:*`` and seeing nothing.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from . import global_routing

# ── Where renmark expects to live ─────────────────────────────────────────────

# Resolve the renmark source dir from this file's location.
# /home/renmark/projects/ai-system/renmark/doctor.py  →  /home/renmark/projects/ai-system
RENMARK_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SOURCE = RENMARK_ROOT / "plugin"
VERSION_FILE = RENMARK_ROOT / "VERSION"

CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_JSON = CLAUDE_DIR / "settings.json"
PLUGINS_DIR = CLAUDE_DIR / "plugins"
INSTALLED_PLUGINS_JSON = PLUGINS_DIR / "installed_plugins.json"
KNOWN_MARKETPLACES_JSON = PLUGINS_DIR / "known_marketplaces.json"
SYMLINK_PATH = PLUGINS_DIR / "renmark"

CODEX_MARKETPLACE_JSON = Path.home() / ".agents" / "plugins" / "marketplace.json"
CODEX_PLUGIN_SOURCE = Path.home() / "plugins" / "renmark"
CODEX_MARKETPLACE_NAME = "personal"
CODEX_MARKETPLACE_RELATIVE_SOURCE = "./plugins/renmark"

MARKETPLACE_NAME = "renmark-local"
PLUGIN_KEY = "renmark@renmark-local"  # `<plugin>@<marketplace>` per CC convention


@dataclass
class Check:
    """One diagnostic check result."""

    name: str
    status: str  # "pass", "fail", "warn"
    detail: str
    fix_cmd: str = ""  # shell command the user can run to remediate
    auto_fixable: bool = False  # whether --fix can resolve this
    fix_fn: Callable[[], str] | None = None  # callable that applies the fix (set by checker)


@dataclass
class DoctorReport:
    checks: list[Check] = field(default_factory=list)

    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.status == "fail"]

    def warned(self) -> list[Check]:
        return [c for c in self.checks if c.status == "warn"]

    def ok(self) -> bool:
        return not self.failed()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _current_version() -> str | None:
    if not VERSION_FILE.exists():
        return None
    return VERSION_FILE.read_text(encoding="utf-8").strip() or None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    # Guard against valid non-object JSON (lists, scalars, null) — downstream
    # callers use .get()/.setdefault() and would crash otherwise.
    if not isinstance(obj, dict):
        return {}
    return cast(dict[str, Any], obj)


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + f".doctor.bak.{int(_dt.datetime.now().timestamp())}")
    shutil.copy2(path, bak)
    return bak


# ── Individual checks ────────────────────────────────────────────────────────


def check_cli_on_path() -> Check:
    cli = shutil.which("renmark-execute")
    if cli:
        return Check("CLI on PATH", "pass", f"`renmark-execute` resolves to {cli}")
    return Check(
        "CLI on PATH",
        "warn",
        "`renmark-execute` is not on PATH. The plugin still works, but ad-hoc CLI usage won't.",
        fix_cmd=f"bash {RENMARK_ROOT}/install.sh",
    )


def check_python_package() -> Check:
    try:
        import renmark

        loc = Path(renmark.__file__).resolve()
        v = getattr(renmark, "__version__", "<no __version__>")
        return Check("Python package", "pass", f"`renmark` v{v} importable from {loc.parent}")
    except ImportError as exc:
        return Check(
            "Python package",
            "fail",
            f"`import renmark` failed: {exc}",
            fix_cmd=f"pip install -e {RENMARK_ROOT}",
            auto_fixable=False,  # involves package install — leave to user
        )


def check_version_file() -> Check:
    v = _current_version()
    if not v:
        return Check("VERSION file", "fail", f"{VERSION_FILE} missing or empty")
    return Check("VERSION file", "pass", f"v{v}")


def check_plugin_manifest() -> Check:
    src_v = _current_version()
    manifests = {
        "Claude Code": PLUGIN_SOURCE / ".claude-plugin" / "plugin.json",
        "Codex": PLUGIN_SOURCE / ".codex-plugin" / "plugin.json",
    }
    identities: dict[str, tuple[object, object]] = {}
    for host, manifest in manifests.items():
        if not manifest.exists():
            return Check("Cross-host plugin manifests", "fail", f"{host} manifest missing: {manifest}")
        data = _load_json(manifest)
        identities[host] = (data.get("name"), data.get("version"))

    names = {identity[0] for identity in identities.values()}
    if names != {"renmark"}:
        return Check(
            "Cross-host plugin manifests",
            "fail",
            f"manifest names must both be 'renmark': {identities}",
            fix_cmd="python -m renmark.release check",
        )
    versions = {identity[1] for identity in identities.values()}
    if len(versions) != 1 or (src_v and versions != {src_v}):
        return Check(
            "Cross-host plugin manifests",
            "fail",
            f"manifest versions must both match VERSION v{src_v}: {identities}",
            fix_cmd="python -m renmark.release check",
        )
    return Check("Cross-host plugin manifests", "pass", f"renmark v{src_v} for Claude Code and Codex")


def check_codex_marketplace() -> Check:
    """Codex's personal marketplace must point at the shared plugin root."""
    data = _load_json(CODEX_MARKETPLACE_JSON)
    entries = data.get("plugins", [])
    entry = next(
        (item for item in entries if isinstance(item, dict) and item.get("name") == "renmark"),
        None,
    )
    expected = {"source": "local", "path": CODEX_MARKETPLACE_RELATIVE_SOURCE}
    if not entry:
        return Check(
            "Codex marketplace",
            "fail",
            f"renmark missing from {CODEX_MARKETPLACE_JSON}",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_codex_marketplace,
        )
    if entry.get("source") != expected:
        return Check(
            "Codex marketplace",
            "fail",
            f"renmark source is {entry.get('source')!r}, expected {expected!r}",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_codex_marketplace,
        )
    return Check("Codex marketplace", "pass", f"{CODEX_MARKETPLACE_NAME} → {CODEX_PLUGIN_SOURCE}")


def check_codex_plugin_source() -> Check:
    """The Codex marketplace source must resolve to this checkout's plugin root."""
    if not CODEX_PLUGIN_SOURCE.exists():
        return Check(
            "Codex plugin source",
            "fail",
            f"{CODEX_PLUGIN_SOURCE} missing",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_codex_source_link,
        )
    if CODEX_PLUGIN_SOURCE.is_symlink() and CODEX_PLUGIN_SOURCE.resolve() != PLUGIN_SOURCE.resolve():
        return Check(
            "Codex plugin source",
            "fail",
            f"{CODEX_PLUGIN_SOURCE} points to {CODEX_PLUGIN_SOURCE.resolve()}, not {PLUGIN_SOURCE}",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_codex_source_link,
        )
    manifest = CODEX_PLUGIN_SOURCE / ".codex-plugin" / "plugin.json"
    if not manifest.exists():
        return Check("Codex plugin source", "fail", f"{manifest} missing")
    data = _load_json(manifest)
    source_version = data.get("version")
    current = _current_version()
    if (
        data.get("name") != "renmark"
        or not isinstance(source_version, str)
        or (current and source_version != current and not source_version.startswith(f"{current}+"))
    ):
        return Check(
            "Codex plugin source",
            "fail",
            f"{manifest} identity/version does not match renmark v{current}",
        )
    return Check("Codex plugin source", "pass", str(CODEX_PLUGIN_SOURCE))


def check_codex_installed() -> Check:
    """Use Codex's JSON registry view to verify installed and enabled state."""
    cli = shutil.which("codex")
    if not cli:
        return Check("Codex installed plugin", "warn", "Codex CLI is not on PATH; install state cannot be checked")
    try:
        result = subprocess.run(
            [cli, "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        payload = json.loads(result.stdout) if result.returncode == 0 else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return Check("Codex installed plugin", "fail", f"could not read Codex plugin registry: {exc}")
    installed = payload.get("installed", []) if isinstance(payload, dict) else []
    entry = next(
        (item for item in installed if isinstance(item, dict) and item.get("pluginId") == "renmark@personal"),
        None,
    )
    if not entry:
        return Check(
            "Codex installed plugin",
            "fail",
            "renmark@personal is available but not installed",
            fix_cmd="codex plugin add renmark@personal",
        )
    if not entry.get("installed") or not entry.get("enabled"):
        return Check(
            "Codex installed plugin",
            "fail",
            f"renmark@personal installed/enabled state is invalid: {entry}",
            fix_cmd="codex plugin add renmark@personal",
        )
    installed_version = entry.get("version")
    current = _current_version()
    if (
        current
        and isinstance(installed_version, str)
        and installed_version != current
        and not installed_version.startswith(f"{current}+")
    ):
        return Check(
            "Codex installed plugin",
            "fail",
            f"Codex has v{installed_version}, source is v{current}",
            fix_cmd="codex plugin add renmark@personal",
        )
    return Check("Codex installed plugin", "pass", f"renmark@personal v{installed_version} enabled")


def check_settings_marketplace() -> Check:
    settings = _load_json(SETTINGS_JSON)
    mkt = settings.get("extraKnownMarketplaces", {}).get(MARKETPLACE_NAME)
    if not mkt:
        return Check(
            "Marketplace registered (settings.json)",
            "fail",
            f"`extraKnownMarketplaces.{MARKETPLACE_NAME}` missing — Claude Code doesn't know where to find renmark.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_add_marketplace,
        )
    src = mkt.get("source", {})
    path = src.get("path")
    if path != str(RENMARK_ROOT):
        return Check(
            "Marketplace registered (settings.json)",
            "warn",
            f"marketplace registered but path is {path!r}, not {str(RENMARK_ROOT)!r}",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_add_marketplace,
        )
    return Check("Marketplace registered (settings.json)", "pass", f"`{MARKETPLACE_NAME}` → {path}")


def check_settings_enabled() -> Check:
    settings = _load_json(SETTINGS_JSON)
    enabled = settings.get("enabledPlugins", {}).get(PLUGIN_KEY)
    if not enabled:
        return Check(
            "Plugin enabled (settings.json)",
            "fail",
            f"`enabledPlugins[{PLUGIN_KEY!r}]` is not set to true — slash commands won't appear.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_enable_plugin,
        )
    return Check("Plugin enabled (settings.json)", "pass", f"`{PLUGIN_KEY}` = true")


def check_installed_plugins_registry() -> Check:
    data = _load_json(INSTALLED_PLUGINS_JSON)
    entries = data.get("plugins", {}).get(PLUGIN_KEY)
    if not entries:
        return Check(
            "Claude Code registry",
            "fail",
            f"`installed_plugins.json` has no entry for `{PLUGIN_KEY}`.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_register_plugin,
        )
    entry = entries[0] if isinstance(entries, list) else entries
    registered_v = entry.get("version")
    src_v = _current_version()
    if src_v and registered_v != src_v:
        return Check(
            "Claude Code registry",
            "fail",
            f"registry says v{registered_v} but source is v{src_v} — version drift will cause silent skip.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_register_plugin,
        )
    install_path = Path(entry.get("installPath", ""))
    if not install_path.exists():
        return Check(
            "Claude Code registry",
            "fail",
            f"registry installPath `{install_path}` does not exist on disk.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_register_plugin,
        )
    return Check("Claude Code registry", "pass", f"v{registered_v} at {install_path}")


def check_cache_install_path() -> Check:
    """The cache path that installed_plugins.json points to must resolve to the plugin dir."""
    src_v = _current_version()
    if not src_v:
        return Check("Cache install path", "warn", "VERSION missing — can't check cache")
    cache_path = PLUGINS_DIR / "cache" / MARKETPLACE_NAME / "renmark" / src_v
    if not cache_path.exists():
        return Check(
            "Cache install path",
            "fail",
            f"`{cache_path}` doesn't exist — Claude Code won't find the plugin source.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_cache_symlink,
        )
    if cache_path.is_symlink():
        target = cache_path.resolve()
        if target != PLUGIN_SOURCE.resolve():
            return Check(
                "Cache install path",
                "warn",
                f"`{cache_path}` is a symlink to {target}, not the current plugin source {PLUGIN_SOURCE}",
                fix_cmd="python -m renmark.doctor --fix",
                auto_fixable=True,
                fix_fn=_fix_cache_symlink,
            )
    # Either symlink to right place, or a real dir — both fine
    return Check("Cache install path", "pass", f"{cache_path}")


def check_plugin_symlink() -> Check:
    """The convenience symlink ~/.claude/plugins/renmark → source/plugin/."""
    if not SYMLINK_PATH.exists():
        return Check(
            "Convenience symlink",
            "warn",
            f"`{SYMLINK_PATH}` missing — not required for plugin load, but install.sh creates it.",
            fix_cmd=f"bash {RENMARK_ROOT}/install.sh",
        )
    if SYMLINK_PATH.is_symlink() and SYMLINK_PATH.resolve() != PLUGIN_SOURCE.resolve():
        return Check(
            "Convenience symlink",
            "warn",
            f"`{SYMLINK_PATH}` points to {SYMLINK_PATH.resolve()}, not {PLUGIN_SOURCE}",
            fix_cmd=f"bash {RENMARK_ROOT}/install.sh",
        )
    return Check("Convenience symlink", "pass", str(SYMLINK_PATH))


def check_global_routing_rule() -> Check:
    """ADVISORY-ONLY: report the optional global auto-routing rule state.

    The renmark routing rule in ``~/.claude/CLAUDE.md`` is opt-in, so this check
    never reports ``fail``/``warn`` — it uses the informational ``"info"`` tier,
    which is excluded from both the failure and warning tallies. It can never
    change doctor's overall pass/fail exit status, and it NEVER writes: this
    check only ever *detects*. The write is gated behind the explicit
    ``--install-routing`` flag (see ``main``), so plain ``--fix`` never mutates
    the global CLAUDE.md.
    """
    state = global_routing.detect_global_rule()
    path = global_routing.global_claude_path()
    if state == "present-with-rule":
        return Check("Global auto-routing rule", "info", f"global auto-routing rule present ({path})")
    if state == "present-malformed":
        return Check(
            "Global auto-routing rule",
            "warn",
            f"manual repair needed: multiple/unbalanced renmark-routing markers in {path}",
        )
    # "missing" or "present-without-rule": advisory pointer to the opt-in write.
    return Check(
        "Global auto-routing rule",
        "info",
        f"global auto-routing rule not set — run `python -m renmark.doctor --install-routing` "
        f"to add it (writes {path}, backed up)",
        fix_cmd="python -m renmark.doctor --install-routing",
    )


CHECKS = [
    check_cli_on_path,
    check_python_package,
    check_version_file,
    check_plugin_manifest,
    check_installed_plugins_registry,
    check_settings_marketplace,
    check_settings_enabled,
    check_cache_install_path,
    check_plugin_symlink,
    check_codex_marketplace,
    check_codex_plugin_source,
    check_codex_installed,
    check_global_routing_rule,
]


def run_checks() -> DoctorReport:
    return DoctorReport(checks=[c() for c in CHECKS])


# ── Fix functions (callable when --fix is passed) ────────────────────────────


def _fix_add_marketplace() -> str:
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(SETTINGS_JSON)
    s = _load_json(SETTINGS_JSON)
    s.setdefault("extraKnownMarketplaces", {})[MARKETPLACE_NAME] = {
        "source": {"source": "directory", "path": str(RENMARK_ROOT)}
    }
    SETTINGS_JSON.write_text(json.dumps(s, indent=4))
    return f"added {MARKETPLACE_NAME} → {RENMARK_ROOT} to extraKnownMarketplaces"


def _fix_enable_plugin() -> str:
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(SETTINGS_JSON)
    s = _load_json(SETTINGS_JSON)
    s.setdefault("enabledPlugins", {})[PLUGIN_KEY] = True
    SETTINGS_JSON.write_text(json.dumps(s, indent=4))
    return f"set enabledPlugins[{PLUGIN_KEY!r}] = true"


def _fix_register_plugin() -> str:
    INSTALLED_PLUGINS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(INSTALLED_PLUGINS_JSON)
    data = _load_json(INSTALLED_PLUGINS_JSON)
    data.setdefault("version", 2)
    data.setdefault("plugins", {})
    v = _current_version() or "0.0.0"
    cache_path = PLUGINS_DIR / "cache" / MARKETPLACE_NAME / "renmark" / v
    now = _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
    data["plugins"][PLUGIN_KEY] = [
        {
            "scope": "user",
            "installPath": str(cache_path),
            "version": v,
            "installedAt": now,
            "lastUpdated": now,
        }
    ]
    INSTALLED_PLUGINS_JSON.write_text(json.dumps(data, indent=2))
    # Also ensure the cache symlink exists
    _fix_cache_symlink()
    return f"registered {PLUGIN_KEY} v{v} at {cache_path}"


def _fix_cache_symlink() -> str:
    v = _current_version() or "0.0.0"
    cache_path = PLUGINS_DIR / "cache" / MARKETPLACE_NAME / "renmark" / v
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Clean up other versions
    for sibling in cache_path.parent.iterdir():
        if sibling != cache_path and (sibling.is_symlink() or sibling.is_dir()) and sibling.is_symlink():
            sibling.unlink()
            # Don't delete real dirs — could be user data
    if cache_path.exists() or cache_path.is_symlink():
        cache_path.unlink()
    cache_path.symlink_to(PLUGIN_SOURCE)
    return f"cache symlink {cache_path} → {PLUGIN_SOURCE}"


def _fix_codex_marketplace() -> str:
    CODEX_MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(CODEX_MARKETPLACE_JSON)
    data = _load_json(CODEX_MARKETPLACE_JSON)
    data.setdefault("name", CODEX_MARKETPLACE_NAME)
    data.setdefault("interface", {"displayName": "Personal"})
    plugins = data.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"{CODEX_MARKETPLACE_JSON}: plugins must be a list")
    entry = {
        "name": "renmark",
        "source": {"source": "local", "path": CODEX_MARKETPLACE_RELATIVE_SOURCE},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Engineering",
    }
    plugins[:] = [item for item in plugins if not isinstance(item, dict) or item.get("name") != "renmark"]
    plugins.append(entry)
    CODEX_MARKETPLACE_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"registered renmark in {CODEX_MARKETPLACE_JSON}"


def _fix_codex_source_link() -> str:
    CODEX_PLUGIN_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if CODEX_PLUGIN_SOURCE.is_symlink():
        CODEX_PLUGIN_SOURCE.unlink()
    elif CODEX_PLUGIN_SOURCE.exists():
        existing = _load_json(CODEX_PLUGIN_SOURCE / ".codex-plugin" / "plugin.json")
        if existing.get("name") != "renmark":
            raise FileExistsError(f"refusing to replace non-renmark directory {CODEX_PLUGIN_SOURCE}")
        shutil.rmtree(CODEX_PLUGIN_SOURCE)
    shutil.copytree(PLUGIN_SOURCE, CODEX_PLUGIN_SOURCE, symlinks=True)
    manifest = CODEX_PLUGIN_SOURCE / ".codex-plugin" / "plugin.json"
    data = _load_json(manifest)
    version = _current_version() or str(data.get("version") or "0.0.0")
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    data["version"] = f"{version}+codex.local.{stamp}"
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"staged cache-busted Codex source at {CODEX_PLUGIN_SOURCE}"


def install_routing_rule() -> tuple[bool, str]:
    """EXPLICIT opt-in: install the global routing rule (only on --install-routing).

    Returns ``(ok, message)``. ``ok`` is ``False`` when the install did not
    succeed — i.e. the rule needs manual repair — so ``main`` can flip the exit
    code on an explicitly-requested install that fails. (Exceptions propagate to
    the caller, which also treats them as a failed explicit install.)
    """
    result = global_routing.install_global_rule()
    action = result.get("action")
    path = result.get("path")
    backup = result.get("backup")
    if action == "needs-manual-repair":
        return (
            False,
            f"manual repair needed: multiple/unbalanced renmark-routing markers in {path}",
        )
    if action == "already-present":
        return True, f"global auto-routing rule already present ({path})"
    msg = f"global auto-routing rule {action} ({path})"
    if backup:
        msg += f"; prior file backed up to {backup}"
    return True, msg


def apply_fixes(report: DoctorReport) -> list[str]:
    """Run fix_fn for every check with auto_fixable=True. Returns list of applied descriptions."""
    applied: list[str] = []
    for c in report.checks:
        if c.status == "fail" and c.auto_fixable and c.fix_fn:
            try:
                desc = c.fix_fn()
                applied.append(f"[{c.name}] {desc}")
            except Exception as exc:
                applied.append(f"[{c.name}] FIX FAILED: {exc}")
    return applied


# ── Output rendering ─────────────────────────────────────────────────────────


_GLYPH = {"pass": "✓", "fail": "✗", "warn": "!", "info": "i"}


def render_human(report: DoctorReport) -> str:
    out: list[str] = []
    out.append("renmark doctor — diagnosis")
    out.append("")
    for c in report.checks:
        glyph = _GLYPH.get(c.status, "?")
        out.append(f"[{glyph}] {c.name}: {c.detail}")
        if c.status == "fail" and c.fix_cmd:
            out.append(f"     fix: {c.fix_cmd}")
    out.append("")

    n_fail = len(report.failed())
    n_warn = len(report.warned())
    if n_fail == 0 and n_warn == 0:
        out.append("✅ All checks pass. Renmark should be available in Claude Code and Codex.")
    else:
        bits = []
        if n_fail:
            bits.append(f"{n_fail} failure{'s' if n_fail != 1 else ''}")
        if n_warn:
            bits.append(f"{n_warn} warning{'s' if n_warn != 1 else ''}")
        out.append(f"{', '.join(bits)} detected.")
        auto = sum(1 for c in report.failed() if c.auto_fixable)
        if auto:
            out.append(f"{auto} can be auto-fixed: `python -m renmark.doctor --fix`")
    return "\n".join(out)


def render_json(report: DoctorReport) -> str:
    return json.dumps(
        {
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail, "fix_cmd": c.fix_cmd} for c in report.checks
            ],
            "ok": report.ok(),
        },
        indent=2,
    )


# ── CLI ──────────────────────────────────────────────────────────────────────


def _allow_unencodable_status_glyphs() -> None:
    """Keep human diagnostics printable on legacy Windows console encodings."""
    # Windows PowerShell may expose a cp1252 stdout stream. Doctor reports use
    # status glyphs, so degrade unsupported glyphs instead of crashing while
    # reporting the actual install failure.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        with contextlib.suppress(OSError, ValueError):
            reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    _allow_unencodable_status_glyphs()
    argv = list(sys.argv[1:] if argv is None else argv)
    fix = "--fix" in argv
    refresh_codex = "--refresh-codex" in argv
    install_routing = "--install-routing" in argv
    as_json = "--json" in argv
    if "-h" in argv or "--help" in argv or "help" in argv:
        sys.stdout.write(__doc__ or "")
        return 0

    # An explicitly-requested --install-routing that fails must flip the exit
    # code; the advisory detect in normal/--fix runs never does.
    explicit_install_failed = False

    if refresh_codex:
        try:
            refreshed = _fix_codex_source_link()
        except Exception as exc:
            if not as_json:
                sys.stderr.write(f"Codex source refresh FAILED: {exc}\n")
            return 1
        if not as_json:
            sys.stdout.write(f"Codex source refresh: {refreshed}\n\n")

    report = run_checks()
    if fix:
        # NOTE: --fix performs ONLY the registry/settings/cache repairs. It does
        # NOT write the global ~/.claude/CLAUDE.md routing rule — that write is
        # opt-in via --install-routing. The routing-rule check stays advisory.
        applied = apply_fixes(report)
        if applied and not as_json:
            sys.stdout.write("Applying fixes:\n")
            for line in applied:
                sys.stdout.write(f"  • {line}\n")
            sys.stdout.write("\nRe-checking…\n\n")
        # Re-run after fixes
        report = run_checks()

    if install_routing:
        # The ONLY path that writes the global routing rule. A failed explicit
        # install (exception OR needs-manual-repair) must yield a non-zero exit.
        try:
            ok, msg = install_routing_rule()
        except Exception as exc:
            ok, msg = False, f"FAILED: {exc}"
        if not ok:
            explicit_install_failed = True
        if not as_json:
            sys.stdout.write(f"Global auto-routing rule: {msg}\n\n")

    if as_json:
        sys.stdout.write(render_json(report) + "\n")
    else:
        sys.stdout.write(render_human(report) + "\n")

    if not report.ok():
        if fix:
            sys.stdout.write("\nSome checks still fail after auto-fix. Manual intervention required.\n")
            sys.stdout.write("After fixing, run `/reload-plugins` in Claude Code.\n")
        else:
            sys.stdout.write("\nAfter fixing, run `/reload-plugins` in Claude Code.\n")
        return 1

    if explicit_install_failed:
        sys.stdout.write("\nGlobal auto-routing rule install did not succeed — see message above.\n")
        return 1

    if fix or install_routing:
        sys.stdout.write("\nRun `/reload-plugins` in Claude Code to pick up the changes.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
