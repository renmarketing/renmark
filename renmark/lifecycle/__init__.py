"""renmark lifecycle package.

Split from a single 1747-line module (`renmark/lifecycle.py`) into a package.
Stage/state primitives live in `stage.py` and next-step routing in
`next_steps.py`; later steps split out `preamble.py` and `reconciliation.py`
per `.renmark/rethink/renmark-architecture/target-blueprint.md` §1.2.

This package re-exports the prior surface so `from renmark.lifecycle import X`
and `from renmark import lifecycle; lifecycle.X` keep working unchanged.

Attribute writes (`monkeypatch.setattr(lifecycle, "read_lifecycle", ...)`) are
forwarded to the module that actually owns the name, so patching the package
stays visible to callers inside the implementation module -- preserving the
pre-split single-module attribute semantics exactly.
"""

from __future__ import annotations

import sys as _sys
from types import ModuleType as _ModuleType

from . import next_steps as _next_steps_mod
from . import stage as _stage
from .next_steps import *  # noqa: F403
from .next_steps import (  # noqa: F401
    NextSteps,
    _gates_not_run,
    _resolve_next,
    next_recommended,
    next_steps,
)
from .stage import *  # noqa: F403
from .stage import (  # noqa: F401
    _AGENCY_AWARE_SKILLS,
    _AGENCY_HINT_MARKER,
    _AGENCY_SPINE_SKILLS,
    _CONTEXT_BYPASS_SKILLS,
    _INDEPENDENT_REVIEW_GENERATORS,
    _LIFECYCLE_FIELD_TYPES,
    _LIFECYCLE_MILESTONE_BY_STAGE,
    _MODE_DEFAULT_SKILLS,
    _MODE_DIRECTIVE,
    _MODE_POLICY_BY_TOKEN,
    _MODE_PROMPT_SKILLS,
    _agency_milestone,
    _choose_mode_hint,
    _current_head_sha,
    _current_program_stage,
    _evidence_has_failure,
    _has_fresh_milestone_evidence,
    _legacy_delivery_run_id,
    _lifecycle_host,
    _lifecycle_milestone,
    _lifecycle_path,
    _normalize_mode_note,
    _now,
    _program_milestone,
    _project_workflow_delivery,
    _read_raw_mode_token,
    _safe_read_program,
    _signoff_milestone_id,
    _state_dir,
    _validate_one_artifact,
    _with_agency_note,
    _with_headless_note,
    _with_mode_note,
    _work_package_summaries_for_stage,
    _workflow_drift_notes,
)

#: Implementation modules that own the re-exported names, in resolution order.
#: Extended as `stage.py` is split into the blueprint's four modules.
_IMPL_MODULES: tuple[_ModuleType, ...] = (_stage, _next_steps_mod)


class _LifecyclePackage(_ModuleType):
    """Package module type that mirrors attribute writes onto the impl module.

    Before the split, `lifecycle.py` was one module: setting `lifecycle.foo`
    rebound the same global that functions in the module read.  After the
    split, the package and the implementation module have separate namespaces,
    so a plain re-export would silently break every `monkeypatch.setattr`
    call site.  Forwarding writes (and deletes) restores the old semantics.
    """

    def __setattr__(self, name: str, value: object) -> None:
        for module in _IMPL_MODULES:
            if hasattr(module, name):
                setattr(module, name, value)
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        for module in _IMPL_MODULES:
            if hasattr(module, name):
                delattr(module, name)
        super().__delattr__(name)

    def __getattr__(self, name: str) -> object:
        for module in _IMPL_MODULES:
            try:
                return getattr(module, name)
            except AttributeError:
                continue
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_sys.modules[__name__].__class__ = _LifecyclePackage
