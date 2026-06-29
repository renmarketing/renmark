"""Tests for renmark.skillgen — the read-only SKILL.md consistency lint (P7).

`skillgen` carries NO generator: it is a pure lint over the registered SKILL.md
files. These tests drive `lint_skill` with *synthetic* `text` + `SkillMeta`
inputs (never mutating real skill files) to pin each violation category, then
exercise `lint_all('.')` and `main(['--check'])` against the live (clean) tree.

Violation categories under test:
  - missing / blank description
  - description not trigger-shaped (must open with "Use")
  - description names no trigger (no `/renmark:` and no quoted phrase)
  - `disable-model-invocation` mismatch vs skillmeta (both directions)
  - re-inlines a `_shared/<name>.md` canonical blockquote verbatim (doc-slimming)
"""

from __future__ import annotations

from renmark import skillgen
from renmark.skillmeta import SkillMeta

# ── synthetic-input helpers (never touch real SKILL.md files) ─────────────────


def _meta(*, disable_model_invocation: bool = False) -> SkillMeta:
    """A throwaway SkillMeta — only the fields the lint reads matter, but we
    fill all of them so the frozen dataclass constructs."""
    return SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=(),
        has_handoff=True,
        disable_model_invocation=disable_model_invocation,
    )


def _skill_md(
    *,
    description: str | None = "Use /renmark:example to do the thing.",
    disable_model_invocation: bool | None = None,
    body: str = "Some skill body that cites no shared block.\n",
) -> str:
    """Build a synthetic SKILL.md string with `---`-fenced frontmatter."""
    lines = ["---", "name: example"]
    if description is not None:
        lines.append(f"description: {description}")
    if disable_model_invocation is not None:
        lines.append(f"disable-model-invocation: {str(disable_model_invocation).lower()}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


# ── 1. clean skill → no violations ────────────────────────────────────────────


def test_clean_skill_has_no_violations() -> None:
    text = _skill_md()
    assert skillgen.lint_skill("example", text, _meta()) == []


def test_clean_skill_citing_pointer_only_is_clean() -> None:
    # Citing the _shared file BY POINTER (path mention) is the desired form and
    # must NOT be flagged as a re-inlined blockquote.
    body = (
        "Follow the reasoning contract → see "
        "${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md\n"
    )
    text = _skill_md(body=body)
    assert skillgen.lint_skill("example", text, _meta()) == []


# ── 2. missing / blank description ────────────────────────────────────────────


def test_missing_description_flagged() -> None:
    text = _skill_md(description=None)
    issues = skillgen.lint_skill("example", text, _meta())
    assert any("missing description" in i for i in issues)


def test_blank_description_flagged() -> None:
    text = _skill_md(description="   ")
    issues = skillgen.lint_skill("example", text, _meta())
    assert any("missing description" in i for i in issues)


# ── 3. description not opening with "Use" ─────────────────────────────────────


def test_description_not_trigger_shaped_flagged() -> None:
    # Names a trigger (so the "no trigger" check is satisfied) but does not
    # open with "Use" — isolates the trigger-shape violation.
    text = _skill_md(description="Run /renmark:example when you want the thing.")
    issues = skillgen.lint_skill("example", text, _meta())
    assert any("trigger-shaped" in i for i in issues)


# ── 4. description names no trigger ───────────────────────────────────────────


def test_description_names_no_trigger_flagged() -> None:
    # Opens with "Use" (so trigger-shape passes) but mentions no /renmark: and
    # no quoted phrase — isolates the no-trigger violation.
    text = _skill_md(description="Use this to do the thing whenever appropriate.")
    issues = skillgen.lint_skill("example", text, _meta())
    assert any("no trigger" in i for i in issues)


def test_quoted_phrase_counts_as_trigger() -> None:
    # A quoted natural-language trigger satisfies the trigger requirement.
    text = _skill_md(description='Use when the user says "do the thing".')
    assert skillgen.lint_skill("example", text, _meta()) == []


# ── 5. disable-model-invocation mismatch (both directions) ────────────────────


def test_disable_mismatch_declared_true_meta_false() -> None:
    text = _skill_md(disable_model_invocation=True)
    issues = skillgen.lint_skill("example", text, _meta(disable_model_invocation=False))
    assert any("disable-model-invocation=True but skillmeta expects False" in i for i in issues)


def test_disable_mismatch_declared_false_meta_true() -> None:
    # Frontmatter absent → declared False; meta expects True.
    text = _skill_md(disable_model_invocation=None)
    issues = skillgen.lint_skill("example", text, _meta(disable_model_invocation=True))
    assert any("disable-model-invocation=False but skillmeta expects True" in i for i in issues)


def test_disable_match_both_true_is_clean() -> None:
    text = _skill_md(disable_model_invocation=True)
    assert skillgen.lint_skill("example", text, _meta(disable_model_invocation=True)) == []


# ── 6. doc-slimming guard — re-inlined _shared blockquote ─────────────────────


def test_reinlined_shared_blockquote_flagged() -> None:
    # Pull the live signature so the test stays in sync with the _shared source.
    sig = skillgen._shared_signature("reasoning-contract")
    assert sig, "reasoning-contract signature should resolve against the live _shared file"
    # Re-inline it verbatim (as a blockquote, to also exercise quote-stripping).
    body = f"> {sig}\n"
    text = _skill_md(body=body)
    issues = skillgen.lint_skill("example", text, _meta())
    assert any(
        "re-inlines _shared/reasoning-contract.md blockquote verbatim" in i for i in issues
    )


def test_pointer_citation_is_not_a_reinline() -> None:
    # Citing only the pointer path must not trip the doc-slimming guard.
    body = "See ${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md for the stance.\n"
    text = _skill_md(body=body)
    issues = skillgen.lint_skill("example", text, _meta())
    assert not any("re-inlines" in i for i in issues)


# ── 7. lint_all + main over the live (clean) tree ─────────────────────────────


def test_lint_all_covers_every_skill_and_is_clean() -> None:
    results = skillgen.lint_all(".")
    assert results, "lint_all should find skills under plugin/skills/"
    # Every skill key present with an empty (clean) violation list on this tree.
    dirty = {skill: issues for skill, issues in results.items() if issues}
    assert not dirty, f"unexpected violations on the current tree: {dirty}"


def test_main_check_returns_zero_on_clean_tree() -> None:
    assert skillgen.main(["--check"]) == 0


def test_main_unknown_arg_returns_one() -> None:
    assert skillgen.main(["--bogus"]) == 1
