---
description: "Use to run a deterministic plugin/registry health audit — composes the lint, modularity, and version-drift checkers and adds registry-sync, shim-thinness, and description-drift passes. Read-only: writes artifacts only under .renmark/audits/, never advances lifecycle.json."
argument-hint: '[--quick | --inventory-only]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/audit/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the audit skill's flow.
