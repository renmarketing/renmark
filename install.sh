#!/usr/bin/env bash
# Renmark installer — idempotent, safe to re-run.
# Usage:
#   bash install.sh                  install plugin + CLI
#   bash install.sh --dev            also install .git/hooks/pre-commit guard
#   bash install.sh --uninstall      remove plugin + CLI (and dev hook)
set -euo pipefail

VERSION="$(cat "$(dirname "${BASH_SOURCE[0]}")/VERSION" | tr -d '[:space:]')"
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_PLUGINS_DIR="$HOME/.claude/plugins"
CODEX_PLUGIN_DIR="$HOME/plugins/renmark"
CODEX_MARKETPLACE_JSON="$HOME/.agents/plugins/marketplace.json"
LOCAL_BIN_DIR="$HOME/.local/bin"
DEV_HOOK_PATH="$INSTALL_DIR/.git/hooks/pre-commit"

DEV_MODE=0
for arg in "$@"; do
    case "$arg" in
        --dev) DEV_MODE=1 ;;
    esac
done

# ── uninstall ──────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$CLAUDE_PLUGINS_DIR/renmark"
    rm -f "$LOCAL_BIN_DIR/renmark-execute"
    rm -f "$LOCAL_BIN_DIR/renmark-browser"
    if command -v codex >/dev/null 2>&1; then
        codex plugin remove renmark@personal >/dev/null 2>&1 || true
    fi
    # Remove from settings.json + installed_plugins.json + cache symlink
    python3 - <<'PY' || echo "Settings cleanup: skipped (python3 not available or settings.json missing)"
import json, pathlib, shutil, sys

claude = pathlib.Path.home() / ".claude"
settings = claude / "settings.json"
installed = claude / "plugins" / "installed_plugins.json"
cache_root = claude / "plugins" / "cache" / "renmark-local"
codex_marketplace = pathlib.Path.home() / ".agents" / "plugins" / "marketplace.json"
codex_source = pathlib.Path.home() / "plugins" / "renmark"

if settings.exists():
    s = json.loads(settings.read_text())
    changed = False
    if "extraKnownMarketplaces" in s and "renmark-local" in s["extraKnownMarketplaces"]:
        del s["extraKnownMarketplaces"]["renmark-local"]
        changed = True
    if "enabledPlugins" in s and "renmark@renmark-local" in s["enabledPlugins"]:
        del s["enabledPlugins"]["renmark@renmark-local"]
        changed = True
    if changed:
        settings.write_text(json.dumps(s, indent=4))
        print("Settings: removed renmark entries from settings.json")

if installed.exists():
    d = json.loads(installed.read_text())
    if "renmark@renmark-local" in d.get("plugins", {}):
        del d["plugins"]["renmark@renmark-local"]
        installed.write_text(json.dumps(d, indent=2))
        print("Registry: removed renmark@renmark-local from installed_plugins.json")

if cache_root.exists():
    shutil.rmtree(cache_root)
    print(f"Cache:    removed {cache_root}")

if codex_marketplace.exists():
    m = json.loads(codex_marketplace.read_text())
    plugins = m.get("plugins", [])
    kept = [entry for entry in plugins if not isinstance(entry, dict) or entry.get("name") != "renmark"]
    if kept != plugins:
        m["plugins"] = kept
        codex_marketplace.write_text(json.dumps(m, indent=2) + "\n")
        print("Codex:    removed renmark from personal marketplace")

if codex_source.is_symlink():
    codex_source.unlink()
elif codex_source.is_dir():
    manifest = codex_source / ".codex-plugin" / "plugin.json"
    data = json.loads(manifest.read_text()) if manifest.exists() else {}
    if data.get("name") == "renmark":
        shutil.rmtree(codex_source)
        print(f"Codex:    removed {codex_source}")
PY
    if [[ -L "$DEV_HOOK_PATH" ]]; then
        rm -f "$DEV_HOOK_PATH"
        echo "Dev hook removed: $DEV_HOOK_PATH"
    fi
    echo "renmark uninstalled."
    echo "Run \`/reload-plugins\` in Claude Code to drop the slash commands from the menu."
    exit 0
fi

mkdir -p "$CLAUDE_PLUGINS_DIR" "$LOCAL_BIN_DIR"

# ── plugin symlink ─────────────────────────────────────────────────────────────
plugin_link="$CLAUDE_PLUGINS_DIR/renmark"
if [ -L "$plugin_link" ]; then
    rm "$plugin_link"
elif [ -e "$plugin_link" ]; then
    echo "ERROR: $plugin_link exists and is not a symlink. Move it aside and re-run." >&2
    exit 1
fi
ln -s "$INSTALL_DIR/plugin" "$plugin_link"
echo "Plugin:  $plugin_link → $INSTALL_DIR/plugin"

# ── CLI symlink ────────────────────────────────────────────────────────────────
cli_link="$LOCAL_BIN_DIR/renmark-execute"
if [ -L "$cli_link" ]; then
    rm "$cli_link"
elif [ -e "$cli_link" ]; then
    echo "ERROR: $cli_link exists and is not a symlink. Move it aside and re-run." >&2
    exit 1
fi
ln -s "$INSTALL_DIR/bin/renmark-execute" "$cli_link"
chmod +x "$INSTALL_DIR/bin/renmark-execute"
echo "CLI:     $cli_link → $INSTALL_DIR/bin/renmark-execute"

# ── browser CLI symlink (optional Playwright session-memory layer) ─────────────
browser_link="$LOCAL_BIN_DIR/renmark-browser"
if [ -L "$browser_link" ]; then
    rm "$browser_link"
elif [ -e "$browser_link" ]; then
    echo "ERROR: $browser_link exists and is not a symlink. Move it aside and re-run." >&2
    exit 1
fi
ln -s "$INSTALL_DIR/bin/renmark-browser" "$browser_link"
chmod +x "$INSTALL_DIR/bin/renmark-browser"
echo "CLI:     $browser_link → $INSTALL_DIR/bin/renmark-browser"

# ── Python package (editable) ─────────────────────────────────────────────────
if command -v pip3 >/dev/null 2>&1; then
    pip3 install -q -e "$INSTALL_DIR" 2>/dev/null && echo "Package: renmark editable install OK" \
        || echo "Package: pip install skipped (no setup.py/pyproject.toml or already installed)"
fi

# ── Codex CLI (optional) ──────────────────────────────────────────────────────
# Codex is the third-party CLI from OpenAI that renmark dispatches `executor: codex`
# tasks to. Without it, those tasks fall back to Sonnet automatically — renmark
# still works, just at higher token cost on bulk-emit tasks. We detect it and
# (interactively) offer to install. Non-interactive callers (CI, scripted
# installs) skip the prompt and just print guidance.
if command -v codex >/dev/null 2>&1; then
    echo "Codex:   $(codex --version 2>/dev/null | head -1) (already installed)"
else
    echo ""
    echo "Codex CLI is not installed."
    echo "  renmark uses Codex (OpenAI) as the cheap bulk-emission executor."
    echo "  Without it, codex-tagged tasks fall back to Sonnet (more expensive,"
    echo "  but works fine). Codex is OPTIONAL but recommended."
    echo ""
    if command -v npm >/dev/null 2>&1; then
        # Interactive only — if stdin isn't a terminal, skip the prompt
        if [[ -t 0 ]]; then
            read -r -p "Install Codex CLI now via npm? [Y/n] " codex_ans
            codex_ans="${codex_ans:-Y}"
            if [[ "$codex_ans" =~ ^[Yy] ]]; then
                echo "  Installing @openai/codex globally…"
                if npm install -g @openai/codex 2>&1 | tail -3; then
                    echo "Codex:   installed via npm"
                    echo "         (you'll need to authenticate with \`codex login\` once)"
                else
                    echo "Codex:   npm install failed — see https://github.com/openai/codex"
                fi
            else
                echo "Codex:   skipped (install later: npm install -g @openai/codex)"
            fi
        else
            echo "  Non-interactive install — skipping prompt."
            echo "  To enable Codex later:  npm install -g @openai/codex && codex login"
        fi
    else
        echo "  npm is not installed. To enable Codex:"
        echo "    1. Install Node.js (https://nodejs.org)"
        echo "    2. npm install -g @openai/codex"
        echo "    3. codex login"
    fi
fi

# ── Claude Code registry + settings.json (CRITICAL) ──────────────────────────
# A directory-marketplace plugin needs THREE registrations to surface its
# slash commands:
#   1. ~/.claude/plugins/installed_plugins.json  → entry under "renmark@renmark-local"
#   2. ~/.claude/settings.json → extraKnownMarketplaces.renmark-local
#   3. ~/.claude/settings.json → enabledPlugins["renmark@renmark-local"] = true
# The symlinks above are necessary but not sufficient. We delegate the
# registration to `python -m renmark.doctor --fix` since that's the same
# logic /renmark:doctor uses to repair installs — DRY, and the script
# writes backups of every config it touches.
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import renmark.doctor" 2>/dev/null; then
        echo ""
        echo "Registering with Claude Code and Codex:"
        # This registration pass runs before `codex plugin add`, so doctor may
        # still report the pending Codex install. The authoritative health
        # check runs after that install below.
        if doctor_output="$(
            PYTHONPATH="$INSTALL_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m renmark.doctor \
                --fix --refresh-codex 2>&1
        )"; then
            :
        fi
        printf '%s\n' "$doctor_output" \
            | grep -E "^(Applying|  •|\[)" \
            | head -24 || true
    else
        echo "Registry: skipped (renmark.doctor not importable yet — re-run install.sh after pip succeeds)"
    fi
fi

# The marketplace entry alone is not an install. When Codex is present, ask its
# native plugin manager to cache and enable the freshly cache-busted source.
if command -v codex >/dev/null 2>&1; then
    echo ""
    echo "Installing renmark@personal in Codex:"
    if codex plugin add renmark@personal --json >/dev/null; then
        echo "Codex:   renmark@personal installed and enabled"
    else
        echo "Codex:   plugin add failed; run: codex plugin add renmark@personal" >&2
    fi
fi

# Do not announce a successful installation until the registry and cache paths
# are healthy after every host-specific install step has finished.
if command -v python3 >/dev/null 2>&1 && python3 -c "import renmark.doctor" 2>/dev/null; then
    if ! doctor_output="$(
        PYTHONPATH="$INSTALL_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m renmark.doctor --fix 2>&1
    )"; then
        echo "ERROR: Claude Code registry/cache repair failed:" >&2
        printf '%s\n' "$doctor_output" >&2
        exit 1
    fi
fi

# ── Dev hook (--dev) ──────────────────────────────────────────────────────────
# Symlinks .git/hooks/pre-commit → tools/precommit.sh so every commit runs
# pytest + drift check + lint before allowing the commit to land.
if [[ "$DEV_MODE" == "1" ]]; then
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        mkdir -p "$INSTALL_DIR/.git/hooks"
        if [[ -L "$DEV_HOOK_PATH" ]]; then
            rm "$DEV_HOOK_PATH"
        elif [[ -e "$DEV_HOOK_PATH" ]]; then
            mv "$DEV_HOOK_PATH" "$DEV_HOOK_PATH.bak.$(date +%s)"
            echo "Dev:     existing pre-commit moved aside (.bak.timestamp)"
        fi
        ln -s "$INSTALL_DIR/tools/precommit.sh" "$DEV_HOOK_PATH"
        chmod +x "$INSTALL_DIR/tools/precommit.sh"
        echo "Dev:     $DEV_HOOK_PATH → $INSTALL_DIR/tools/precommit.sh"
    else
        echo "Dev:     skipped — not a git checkout"
    fi
fi

cat <<EOF

renmark v${VERSION} installed.

Hosts:
  Claude Code — reload plugins to pick up this version
  Codex       — start a new task to pick up this version

Skills:
  /renmark:start       — vibe coder entry: describe what you want, renmark builds the rest
  /renmark:setup       — prepare any project for renmark workflow
  /renmark:init        — scan repo: project map + dev-standards/health report
  /renmark:brainstorm  — design a feature into a spec
  /renmark:plan        — decompose spec into executor-tagged tasks
  /renmark:check-plan  — validate plan before spending tokens
  /renmark:orchestrate — execute plan (Haiku / Codex / Sonnet / Opus / Fable)
  /renmark:verify      — confirm feature goal was achieved
  /renmark:finish      — create PR or merge branch
  /renmark:feature     — full pipeline with branch isolation
  /renmark:debug       — systematic root-cause loop
  /renmark:codereview  — single-pass Codex diff review
  /renmark:roadmap     — project status and token usage report
  /renmark:doctor      — diagnose install health (run if /renmark:* not surfacing)
  /renmark:help        — list all skills

CLI:
  renmark-execute --help

New to renmark?  /renmark:start  (describe what you want to build)
Existing project: /renmark:setup  then  /renmark:start
EOF
