"""Renmark — pipeline-first development framework with multi-LLM orchestration.

The user works through seven pipelines — /renmark:init (adopt a repo),
/renmark:start (new build), /renmark:rethink (reassess/transform an existing
app), /renmark:feature (add/change), /renmark:debug (fix), /renmark:roadmap
(gaps / what's next), /renmark:finish (ship) — backed by 31 Claude Code
commands and a CLI (renmark-execute) that dispatches tasks to Haiku, Codex,
Sonnet, Opus, Fable, or any registered provider.

Core innovation: AI workflows that survive context death. Workflow state
persists to `.renmark/state/lifecycle.json`; runtime state to
`pipeline.json`. After `/clear`, `/renmark:resume` recovers in one file
read.
"""

__version__ = "0.43.1"
