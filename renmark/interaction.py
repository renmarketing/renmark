"""Host-neutral choice menus for Claude Code and Codex.

The model-facing skills still invoke the host's selector tool. This module
owns the deterministic parts of that interaction: exactly one recommendation,
recommended-first ordering, host option limits, and a numbered fallback that
does not confuse a missing selector with a headless session.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

from .hosts import HostKind, capabilities_for, resolve_host

RECOMMENDED_SUFFIX = " (Recommended)"
MORE_CODE = "more"
BACK_CODE = "back"
CANCEL_CODE = "cancel"
_REFUSAL_CODES = frozenset({"cancel", "n", "no", "reject", "refuse"})
_REFUSAL_LABELS = frozenset({"cancel", "no", "nothing", "reject", "refuse", "stop"})


class ChoiceError(ValueError):
    """Raised when a choice set cannot satisfy the interaction contract."""


@dataclass(frozen=True)
class Choice:
    """One stable action shown in a host selector or numbered fallback."""

    code: str
    label: str
    description: str
    recommended: bool = False
    choice_id: str | None = None

    @property
    def display_label(self) -> str:
        """Return the visible label with one recommendation suffix at most."""
        base = self.label.removesuffix(RECOMMENDED_SUFFIX).strip()
        return f"{base}{RECOMMENDED_SUFFIX}" if self.recommended else base

    @property
    def semantic_id(self) -> str:
        """Return a stable semantic identifier for this choice."""
        return self.choice_id or self.code.casefold()


@dataclass(frozen=True)
class ChoiceSet:
    """A semantic decision plus its stable, normalized choice ordering."""

    decision_id: str
    question: str
    choices: tuple[Choice, ...]
    header: str = "Next step"
    allow_free_text: bool = False
    dangerous: bool = False


@dataclass(frozen=True)
class ContinuationResult:
    """Ephemeral result from resolving one rendered selector interaction."""

    kind: Literal["selected", "more", "back", "cancel", "free_text", "invalid"]
    choice: Choice | None = None
    text: str | None = None


@dataclass(frozen=True)
class _PageEntry:
    """One selectable entry on the current rendered page."""

    kind: Literal["choice", "more", "back"]
    code: str
    label: str
    description: str
    choice: Choice | None = None


@dataclass(frozen=True)
class _NativePage:
    """Ephemeral native-page layout for the current host capability."""

    index: int
    count: int
    entries: tuple[_PageEntry, ...]

    @property
    def has_back(self) -> bool:
        return any(entry.kind == "back" for entry in self.entries)

    @property
    def has_more(self) -> bool:
        return any(entry.kind == "more" for entry in self.entries)


def normalize_choices(choices: Iterable[Choice]) -> tuple[Choice, ...]:
    """Validate *choices* and move the sole recommendation to index zero."""
    items = tuple(choices)
    if not items:
        raise ChoiceError("at least one choice is required")
    if len({item.code.casefold() for item in items}) != len(items):
        raise ChoiceError("choice codes must be unique")
    recommended = [item for item in items if item.recommended]
    if len(recommended) != 1:
        raise ChoiceError("exactly one choice must be recommended")
    winner = recommended[0]
    return (winner, *(item for item in items if item is not winner))


def build_choice_set(
    question: str,
    choices: Iterable[Choice],
    *,
    decision_id: str = "renmark_choice",
    header: str = "Next step",
    allow_free_text: bool = False,
    dangerous: bool = False,
) -> ChoiceSet:
    """Return a stable semantic decision with normalized choices."""
    return ChoiceSet(
        decision_id=decision_id,
        question=question,
        choices=normalize_choices(choices),
        header=header,
        allow_free_text=allow_free_text,
        dangerous=dangerous,
    )


def render_numbered(choices: Iterable[Choice]) -> tuple[str, ...]:
    """Render the complete recommended-first fallback list."""
    normalized = normalize_choices(choices)
    return tuple(
        f"{index}. [{item.code}] {item.display_label} — {item.description}"
        for index, item in enumerate(normalized, start=1)
    )


def build_selector(
    question: str,
    choices: Iterable[Choice],
    *,
    header: str = "Next step",
    host: str | HostKind | None = None,
    tool_available: bool | None = None,
    decision_id: str = "renmark_choice",
    allow_free_text: bool = False,
    dangerous: bool = False,
    page: int = 0,
    render_surface: str | None = None,
) -> dict[str, Any]:
    """Build a host-native selector request plus a complete visible fallback.

    ``tool_available=False`` selects the numbered fallback, but deliberately
    says nothing about whether the session is headless. The caller must use
    :mod:`renmark.headless` for that separate decision.
    """
    decision = build_choice_set(
        question,
        choices,
        decision_id=decision_id,
        header=header,
        allow_free_text=allow_free_text,
        dangerous=dangerous,
    )
    selected_host = resolve_host(host)
    caps = capabilities_for(
        selected_host,
        render_surface=render_surface,
        selector_available=tool_available,
    )
    fallback = render_numbered(decision.choices)
    semantic = _semantic_payload(decision)

    if len(decision.choices) == 1:
        return _fallback_payload(
            decision,
            selected_host,
            fallback,
            semantic,
            reason="single_choice_requires_fallback",
        )
    if caps.selector_tool is None:
        return _fallback_payload(
            decision,
            selected_host,
            fallback,
            semantic,
            reason="selector_unavailable",
        )

    native_page = _native_page(decision.choices, caps.selector_max_options, caps.selector_min_options, page)
    if native_page is None:
        reason = (
            "selector_requires_multiple_options"
            if selected_host is HostKind.CODEX
            else "selector_capacity_unavailable"
        )
        return _fallback_payload(decision, selected_host, fallback, semantic, reason=reason)

    bindings = _page_bindings(native_page)
    visible_numbered = _render_visible_numbered(bindings)
    instructions = _instructions(decision, native_page)
    option_payload = [
        {"label": entry.label, "description": entry.description}
        for entry in native_page.entries
    ]
    if selected_host is HostKind.CODEX:
        arguments: dict[str, Any] = {
            "questions": [
                {
                    "header": decision.header[:12],
                    "id": decision.decision_id,
                    "question": decision.question,
                    "options": option_payload,
                }
            ]
        }
    else:
        arguments = {
            "questions": [
                {
                    "header": decision.header,
                    "question": decision.question,
                    "multiSelect": False,
                    "options": option_payload,
                }
            ]
        }

    return {
        "mode": "selector",
        "host": selected_host.value,
        "tool": caps.selector_tool,
        "arguments": arguments,
        "fallback": fallback,
        "overflow": native_page.count > 1,
        "instructions": instructions,
        "semantic": semantic,
        "page": {
            "index": native_page.index,
            "count": native_page.count,
            "visible_numbered": visible_numbered,
            "bindings": bindings,
        },
    }


def continue_selector(rendered: dict[str, Any], answer: str) -> ContinuationResult:
    """Resolve one rendered page without persisting any continuation state."""
    raw = answer.strip()
    if not raw:
        return ContinuationResult(kind="invalid")
    value = raw.casefold()
    semantic = rendered.get("semantic", {})
    allow_free_text = bool(semantic.get("allow_free_text"))
    bindings = tuple(rendered.get("page", {}).get("bindings", ()))
    options = tuple(rendered.get("options", ()))
    choices = tuple(_choices_from_semantic(semantic))

    if value == CANCEL_CODE:
        semantic_refusal = _refusal_choice(choices)
        if semantic_refusal is not None:
            return ContinuationResult(kind="cancel", choice=semantic_refusal)
        return ContinuationResult(kind="cancel")

    semantic_refusal = _refusal_choice(choices)
    if semantic_refusal is not None:
        refusal_value = value.removeprefix("[").removesuffix("]")
        if refusal_value in {
            semantic_refusal.code.casefold(),
            semantic_refusal.label.casefold(),
            semantic_refusal.display_label.casefold(),
        }:
            return ContinuationResult(kind="cancel", choice=semantic_refusal)

    if bindings:
        resolved = _resolve_binding(bindings, raw)
        if resolved is not None:
            return resolved
    elif options:
        resolved_choice = resolve_selection(choices, raw)
        if resolved_choice is not None:
            if _is_refusal_choice(resolved_choice):
                return ContinuationResult(kind="cancel", choice=resolved_choice)
            return ContinuationResult(kind="selected", choice=resolved_choice)

    if allow_free_text:
        return ContinuationResult(kind="free_text", text=raw)
    return ContinuationResult(kind="invalid")


def resolve_selection(choices: Iterable[Choice], answer: str) -> Choice | None:
    """Resolve a number, bracket code, or exact label; return ``None`` otherwise."""
    normalized = normalize_choices(choices)
    value = answer.strip().casefold()
    if value.isdigit():
        index = int(value) - 1
        return normalized[index] if 0 <= index < len(normalized) else None
    value = value.removeprefix("[").removesuffix("]")
    for item in normalized:
        if value in {item.code.casefold(), item.label.casefold(), item.display_label.casefold()}:
            return item
    return None


def with_recommendation(choices: Iterable[Choice], code: str) -> tuple[Choice, ...]:
    """Return a normalized copy with *code* as the sole recommendation."""
    wanted = code.casefold()
    items = tuple(replace(item, recommended=item.code.casefold() == wanted) for item in choices)
    if not any(item.recommended for item in items):
        raise ChoiceError(f"unknown recommended choice: {code}")
    return normalize_choices(items)


def _semantic_payload(decision: ChoiceSet) -> dict[str, Any]:
    """Return the stable semantic payload for one decision."""
    return {
        "decision_id": decision.decision_id,
        "question": decision.question,
        "header": decision.header,
        "allow_free_text": decision.allow_free_text,
        "dangerous": decision.dangerous,
        "choices": [
            {
                "choice_id": item.semantic_id,
                "code": item.code,
                "label": item.label,
                "description": item.description,
                "recommended": item.recommended,
            }
            for item in decision.choices
        ],
    }


def _fallback_payload(
    decision: ChoiceSet,
    host: HostKind,
    fallback: tuple[str, ...],
    semantic: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    """Return a complete fallback payload for the current decision."""
    return {
        "mode": "fallback",
        "host": host.value,
        "question": decision.question,
        "options": fallback,
        "reason": reason,
        "instructions": _fallback_instructions(decision.choices, decision.allow_free_text),
        "semantic": semantic,
        "page": {
            "index": 0,
            "count": 1,
            "visible_numbered": _render_fallback_bindings(decision.choices),
            "bindings": _fallback_bindings(decision.choices),
        },
    }


def _native_page(
    choices: Sequence[Choice],
    max_options: int,
    min_options: int,
    requested_page: int,
) -> _NativePage | None:
    """Return the requested native continuation page when it fits the host."""
    if max_options <= 0:
        return None
    if requested_page < 0:
        requested_page = 0

    pages: list[_NativePage] = []
    start = 0
    page_index = 0
    while start < len(choices):
        has_back = page_index > 0
        remaining = len(choices) - start
        semantic_count = min(remaining, max_options)
        page_entries: tuple[_PageEntry, ...] | None = None

        while semantic_count >= 1:
            end = start + semantic_count
            has_more = end < len(choices)
            extras = (1 if has_back else 0) + (1 if has_more else 0)
            total = semantic_count + extras
            if min_options <= total <= max_options:
                entries: list[_PageEntry] = [
                    _PageEntry(
                        kind="choice",
                        code=item.code,
                        label=item.display_label,
                        description=item.description,
                        choice=item,
                    )
                    for item in choices[start:end]
                ]
                if has_more:
                    entries.append(
                        _PageEntry(
                            kind="more",
                            code=MORE_CODE,
                            label="More",
                            description="show the remaining choices",
                        )
                    )
                if has_back:
                    entries.append(
                        _PageEntry(
                            kind="back",
                            code=BACK_CODE,
                            label="Back",
                            description="return to the previous choices",
                        )
                    )
                page_entries = tuple(entries)
                break
            semantic_count -= 1

        if page_entries is None:
            return None

        pages.append(_NativePage(index=page_index, count=0, entries=page_entries))
        start += sum(entry.kind == "choice" for entry in page_entries)
        page_index += 1

    if not pages:
        return None

    total_pages = len(pages)
    bounded_page = min(requested_page, total_pages - 1)
    selected = pages[bounded_page]
    return _NativePage(index=selected.index, count=total_pages, entries=selected.entries)


def _page_bindings(page: _NativePage) -> tuple[dict[str, Any], ...]:
    """Return the current page's bindings for continuation parsing."""
    bindings: list[dict[str, Any]] = []
    for entry in page.entries:
        binding = {
            "kind": entry.kind,
            "code": entry.code,
            "label": entry.label,
            "description": entry.description,
        }
        if entry.choice is not None:
            binding["choice_id"] = entry.choice.semantic_id
        bindings.append(binding)
    return tuple(bindings)


def _fallback_bindings(choices: Sequence[Choice]) -> tuple[dict[str, Any], ...]:
    """Return complete fallback bindings for every semantic choice."""
    return tuple(
        {
            "kind": "choice",
            "code": item.code,
            "label": item.display_label,
            "description": item.description,
            "choice_id": item.semantic_id,
        }
        for item in choices
    )


def _render_visible_numbered(bindings: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    """Render a local numbered view of the currently visible page entries."""
    return tuple(
        f"{index}. [{binding['code']}] {binding['label']} — {binding['description']}"
        for index, binding in enumerate(bindings, start=1)
    )


def _render_fallback_bindings(choices: Sequence[Choice]) -> tuple[str, ...]:
    """Render complete fallback numbering from the semantic choice order."""
    return render_numbered(choices)


def _instructions(decision: ChoiceSet, page: _NativePage) -> str:
    """Return one bounded instruction line for the current native page."""
    refusal = _refusal_choice(decision.choices)
    page_note = (
        f" Page {page.index + 1} of {page.count}."
        if page.count > 1
        else ""
    )
    if refusal is not None:
        cancel = f" Exact [{refusal.code}] or {refusal.label!r} refuses."
    else:
        cancel = " Exact [cancel] cancels without approval."
    free_text = " Unlisted text is kept as free text." if decision.allow_free_text else ""
    return f"Reply with the exact number, code, or label.{page_note}{cancel}{free_text}"


def _fallback_instructions(choices: Sequence[Choice], allow_free_text: bool) -> str:
    """Return one bounded instruction line for the complete fallback."""
    refusal = _refusal_choice(choices)
    if refusal is not None:
        cancel = f" Exact [{refusal.code}] or {refusal.label!r} refuses."
    else:
        cancel = " Exact [cancel] cancels without approval."
    free_text = " Unlisted text is kept as free text." if allow_free_text else ""
    return f"Reply with the exact number, code, or label.{cancel}{free_text}"


def _resolve_binding(bindings: Sequence[dict[str, Any]], answer: str) -> ContinuationResult | None:
    """Resolve the current page's number, code, or exact label."""
    value = answer.strip()
    lowered = value.casefold()
    if lowered.isdigit():
        index = int(lowered) - 1
        if 0 <= index < len(bindings):
            return _binding_result(bindings[index])
        return None

    token = lowered.removeprefix("[").removesuffix("]")
    for binding in bindings:
        exact_values = {str(binding["code"]).casefold(), str(binding["label"]).casefold()}
        if token in exact_values:
            return _binding_result(binding)
    return None


def _binding_result(binding: dict[str, Any]) -> ContinuationResult:
    """Translate one current-page binding into a continuation result."""
    kind = str(binding["kind"])
    if kind == "more":
        return ContinuationResult(kind="more")
    if kind == "back":
        return ContinuationResult(kind="back")
    choice = Choice(
        code=str(binding["code"]),
        label=str(binding["label"]).removesuffix(RECOMMENDED_SUFFIX),
        description=str(binding["description"]),
        recommended=str(binding["label"]).endswith(RECOMMENDED_SUFFIX),
        choice_id=str(binding.get("choice_id") or binding["code"]).casefold(),
    )
    if _is_refusal_choice(choice):
        return ContinuationResult(kind="cancel", choice=choice)
    return ContinuationResult(kind="selected", choice=choice)


def _choices_from_semantic(semantic: dict[str, Any]) -> tuple[Choice, ...]:
    """Rehydrate semantic choices from a rendered payload."""
    raw_choices = semantic.get("choices", ())
    choices: list[Choice] = []
    for raw in raw_choices:
        if not isinstance(raw, dict):
            continue
        choices.append(
            Choice(
                code=str(raw.get("code", "")),
                label=str(raw.get("label", "")),
                description=str(raw.get("description", "")),
                recommended=bool(raw.get("recommended", False)),
                choice_id=str(raw.get("choice_id") or raw.get("code") or "").casefold() or None,
            )
        )
    return tuple(choices)


def _refusal_choice(choices: Sequence[Choice]) -> Choice | None:
    """Return the semantic refusal choice when one exists."""
    for item in choices:
        if _is_refusal_choice(item):
            return item
    return None


def _is_refusal_choice(choice: Choice) -> bool:
    """Return whether *choice* is a safe refusal or rejection action."""
    return choice.code.casefold() in _REFUSAL_CODES or choice.label.casefold() in _REFUSAL_LABELS
