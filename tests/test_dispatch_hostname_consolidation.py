"""Guard test for dispatch HostName consolidation.

Pure file-content checks: `renmark/dispatch.py` must expose `HostName`, but it
must not define `HostName = Literal[` locally. We do NOT import or run the
module.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_uses_hostkind_without_local_hostname_literal() -> None:
    text = (REPO_ROOT / "renmark/dispatch.py").read_text(encoding="utf-8")

    assert "HostName" in text, "dispatch.py must still expose HostName"
    assert "HostName = Literal[" not in text, "HostName must not be defined locally"
    assert "from .hosts import HostKind" in text, "dispatch.py must import HostKind from hosts"
