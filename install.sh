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
    if [[ -L "$DEV_HOOK_PATH" ]]; then
        rm -f "$DEV_HOOK_PATH"
        echo "Dev hook removed: $DEV_HOOK_PATH"
    fi
    echo "renmark uninstalled."
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

# ── Python package (editable) ─────────────────────────────────────────────────
if command -v pip3 >/dev/null 2>&1; then
    pip3 install -q -e "$INSTALL_DIR" 2>/dev/null && echo "Package: renmark editable install OK" \
        || echo "Package: pip install skipped (no setup.py/pyproject.toml or already installed)"
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

Skills:
  /renmark:start       — vibe coder entry: describe what you want, renmark builds the rest
  /renmark:setup       — prepare any project for renmark workflow
  /renmark:brainstorm  — design a feature into a spec
  /renmark:plan        — decompose spec into executor-tagged tasks
  /renmark:check-plan  — validate plan before spending tokens
  /renmark:orchestrate — execute plan (Haiku / Codex / Sonnet / Opus)
  /renmark:verify      — confirm feature goal was achieved
  /renmark:finish      — create PR or merge branch
  /renmark:feature     — full pipeline with branch isolation
  /renmark:debug       — systematic root-cause loop
  /renmark:codereview  — single-pass Codex diff review
  /renmark:roadmap     — project status and token usage report
  /renmark:help        — list all skills

CLI:
  renmark-execute --help

New to renmark?  /renmark:start  (describe what you want to build)
Existing project: /renmark:setup  then  /renmark:start
EOF
