#!/usr/bin/env bash
# Renmark installer. Idempotent — safe to re-run.
#
# Does three things:
#   1. Back up any existing /orchestrator skill to ~/.claude/skills/.orchestrator.bak/
#   2. Symlink plugin/ → ~/.claude/plugins/renmark/
#   3. Symlink bin/renmark-execute → ~/.local/bin/renmark-execute
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
CLAUDE_PLUGINS_DIR="$HOME/.claude/plugins"
LOCAL_BIN_DIR="$HOME/.local/bin"

mkdir -p "$CLAUDE_SKILLS_DIR" "$CLAUDE_PLUGINS_DIR" "$LOCAL_BIN_DIR"

# Step 1: back up /orchestrator if it exists and isn't already a symlink to us.
old_orch="$CLAUDE_SKILLS_DIR/orchestrator"
if [ -e "$old_orch" ] && [ ! -L "$old_orch" ]; then
    backup="$CLAUDE_SKILLS_DIR/.orchestrator.bak"
    if [ -e "$backup" ]; then
        echo "WARN: $backup already exists; not overwriting. Skipping orchestrator backup."
    else
        mv "$old_orch" "$backup"
        echo "Moved $old_orch → $backup"
    fi
elif [ -L "$old_orch" ]; then
    # Existing symlink (maybe from a prior run) — remove if it points outside our install
    target="$(readlink "$old_orch")"
    case "$target" in
        "$INSTALL_DIR"*) : ;;  # ours, leave alone
        *) rm "$old_orch"; echo "Removed unrelated symlink $old_orch -> $target" ;;
    esac
fi

# Step 2: symlink the plugin.
plugin_link="$CLAUDE_PLUGINS_DIR/renmark"
if [ -L "$plugin_link" ]; then
    rm "$plugin_link"
elif [ -e "$plugin_link" ]; then
    echo "ERROR: $plugin_link exists and is not a symlink. Move it aside and re-run." >&2
    exit 1
fi
ln -s "$INSTALL_DIR/plugin" "$plugin_link"
echo "Symlinked $plugin_link → $INSTALL_DIR/plugin"

# Step 3: symlink the CLI.
cli_link="$LOCAL_BIN_DIR/renmark-execute"
if [ -L "$cli_link" ]; then
    rm "$cli_link"
elif [ -e "$cli_link" ]; then
    echo "ERROR: $cli_link exists and is not a symlink. Move it aside and re-run." >&2
    exit 1
fi
ln -s "$INSTALL_DIR/bin/renmark-execute" "$cli_link"
chmod +x "$INSTALL_DIR/bin/renmark-execute"
echo "Symlinked $cli_link → $INSTALL_DIR/bin/renmark-execute"

cat <<EOF

renmark installed.
  Skills available:  /renmark:brainstorm /renmark:plan /renmark:orchestrate /renmark:debug /renmark:codereview
  CLI on PATH:       renmark-execute

The old /orchestrator skill is backed up at $CLAUDE_SKILLS_DIR/.orchestrator.bak
  (mv it back to "$old_orch" if you ever need to revert)

Next: start a Claude Code session in any project folder and try /renmark:brainstorm.
EOF
