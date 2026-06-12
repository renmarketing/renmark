"""Renmark — vibe-coder development framework with multi-LLM orchestration.

13 Claude Code skills (/renmark:start, brainstorm, plan, check-plan,
orchestrate, verify, codereview, debug, finish, feature, setup, resume,
roadmap, help) backed by a CLI (renmark-execute) that dispatches tasks to
Haiku, Codex, Sonnet, Opus, Fable, or any registered provider.

Core innovation: AI workflows that survive context death. Workflow state
persists to `.renmark/state/lifecycle.json`; runtime state to
`pipeline.json`. After `/clear`, `/renmark:resume` recovers in one file
read.
"""

__version__ = "0.12.0"
