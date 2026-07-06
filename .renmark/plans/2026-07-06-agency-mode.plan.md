---
artifact_type: plan
schema_version: 1
created_at: 2026-07-06T00:00:00Z
source_sha: 9c980b8
related_plan: self
generator: sonnet
stale_after: 2026-07-20T00:00:00Z
dependency_refs: []
completion_state: complete
confidence: high
validation_status: validated
---

# Plan — Agency Mode: behavior tests, CLI flags, lifecycle unit tests (BL-0002)

**Branch:** `feature/agency-mode`

Agency Mode core is already shipped (renmark/agency.py, agency-delivery.md, all 10 SKILL.md
sections, _with_agency_note in lifecycle.py, 6 state-persistence tests). This plan closes
the remaining AC11 gap and adds missing developer-facing surface:

- Behavior proof (AC11): no tests proving _with_agency_note changes skill_preamble output
- CLI gap: no --agency-status / --activate-agency / --deactivate-agency flags
- Pre-existing regression: mode.behavior.json fails on live repo with mode=orchestrator
- No _with_agency_note unit tests in test_lifecycle.py

DO NOT re-implement: renmark/agency.py, agency-delivery.md, lifecycle._with_agency_note,
plugin/skills/*/SKILL.md agency sections, tests/test_agency.py.

Wave 1 (parallel): Task 1, Task 3, Task 4
Wave 2 (parallel, after Task 1): Task 2, Task 5
Wave 3: Task 6

---

### Task 1: behavior.py — add fresh + agency_active dispatch adapters
- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 1
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** pytest -q tests/test_behavior.py
- **serves:** AC11
- **spec:**
  Read renmark/behavior.py first (especially _render_skill_preamble around line 433 and
  the _DISPATCH dict around line 490).

  DO NOT modify _render_skill_preamble or any existing adapter.

  Add two new adapter functions directly AFTER the existing `_render_skill_preamble`
  function (after line 438, before `_render_plan_lint`):

  ```python
  def _render_skill_preamble_fresh(repo: Path, case: Case) -> str:
      """Render skill_preamble in an isolated tmpdir (no mode, no agency set)."""
      import tempfile
      from . import lifecycle

      with tempfile.TemporaryDirectory() as d:
          hint = lifecycle.skill_preamble(Path(d), case.skill)
          return hint if hint is not None else ""


  def _render_skill_preamble_agency_active(repo: Path, case: Case) -> str:
      """Render skill_preamble in an isolated tmpdir with agency activated."""
      import tempfile
      from . import lifecycle, agency

      with tempfile.TemporaryDirectory() as d:
          tmp = Path(d)
          agency.activate(tmp)
          hint = lifecycle.skill_preamble(tmp, case.skill)
          return hint if hint is not None else ""
  ```

  Then update _DISPATCH to add both keys (keep existing keys unchanged):

  ```python
  _DISPATCH: dict[str, Callable[[Path, Case], str]] = {
      "lifecycle.next_steps": _render_next_steps,
      "lifecycle.skill_preamble": _render_skill_preamble,
      "lifecycle.skill_preamble_fresh": _render_skill_preamble_fresh,
      "lifecycle.skill_preamble_agency_active": _render_skill_preamble_agency_active,
      "plan_lint": _render_plan_lint,
  }
  ```

  Run: pytest -q tests/test_behavior.py — must stay green.

### Task 2: mode.behavior.json — use fresh dispatch key
- **mode:** B
- **target:** tests/behavioral/mode.behavior.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** renmark-execute --behavior
- **serves:** AC11
- **spec:**
  DEPENDS ON Task 1 (needs lifecycle.skill_preamble_fresh in _DISPATCH).

  Read tests/behavioral/mode.behavior.json. It currently has:
    "call": "lifecycle.skill_preamble"

  Change it to:
    "call": "lifecycle.skill_preamble_fresh"

  This makes the assertion "contains:Operating mode: not yet set" reliable by using
  a fresh tmpdir instead of the live repo (which has mode=orchestrator set).

  Do NOT change any other field. Run: renmark-execute --behavior — all cases must pass.

### Task 3: tests/test_lifecycle.py — _with_agency_note unit tests
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 1
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** pytest -q tests/test_lifecycle.py -k "agency_hint"
- **serves:** AC11
- **spec:**
  Read the END of tests/test_lifecycle.py to find the last function.
  The file is 859 lines. Read from line 840 to see the last test.

  APPEND four tests at the very end of the file (after the last existing function):

  ```python
  def test_agency_hint_inactive_is_passthrough(tmp_path):
      from renmark import lifecycle
      result = lifecycle._with_agency_note(tmp_path, "start", "some hint")
      assert result == "some hint"


  def test_agency_hint_inactive_none_is_passthrough(tmp_path):
      from renmark import lifecycle
      result = lifecycle._with_agency_note(tmp_path, "start", None)
      assert result is None


  def test_agency_hint_active_contains_marker(tmp_path):
      from renmark import lifecycle, agency
      agency.activate(tmp_path)
      result = lifecycle._with_agency_note(tmp_path, "start", None)
      assert result is not None
      assert lifecycle._AGENCY_HINT_MARKER in result


  def test_agency_hint_non_aware_skill_is_passthrough(tmp_path):
      from renmark import lifecycle, agency
      agency.activate(tmp_path)
      result = lifecycle._with_agency_note(tmp_path, "help", "original")
      assert result == "original"
  ```

  Do NOT modify any existing test. Run: pytest -q tests/test_lifecycle.py -k "agency_hint"
  — all 4 must pass.

### Task 4: renmark/cli/_engine.py — agency state CLI flags
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 1
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** renmark-execute --agency-status
- **serves:** BL-0002
- **spec:**
  Read renmark/cli/_engine.py. The argparse section is around line 1285-1310.
  The dispatch section is around line 1337+.

  STEP 1 — Add argparse flags after the `--get-compact-gate-tokens` block (after line 1291)
  and BEFORE the `# P4 file-handoff helpers` comment:

  ```python
      # Agency Mode state management
      ap.add_argument(
          "--agency-status",
          action="store_true",
          help="print current agency state (active/inactive, phase, milestone)",
      )
      ap.add_argument(
          "--activate-agency",
          action="store_true",
          help="activate Agency Mode in the current repo",
      )
      ap.add_argument(
          "--deactivate-agency",
          action="store_true",
          help="deactivate Agency Mode in the current repo",
      )
  ```

  STEP 2 — Add dispatch logic BEFORE the `if args.get_mode:` block (around line 1372).
  Find the exact line with `if args.get_mode:` and insert BEFORE it:

  ```python
      if args.agency_status:
          from renmark import agency as _agency
          state = _agency.read_agency(repo)
          status = "active" if state.active else "inactive"
          print(f"agency: {status}")
          if state.active:
              print(f"  phase: {state.current_phase or '(not set)'}")
              print(f"  milestone: {state.current_milestone or '(not set)'}")
              print(f"  signoff: {state.signoff_status or '(not set)'}")
          return 0

      if args.activate_agency:
          from renmark import agency as _agency
          _agency.activate(repo)
          print(f"renmark: Agency Mode activated ({repo}/.renmark/state/agency.json)")
          return 0

      if args.deactivate_agency:
          from renmark import agency as _agency
          _agency.deactivate(repo)
          print(f"renmark: Agency Mode deactivated ({repo}/.renmark/state/agency.json)")
          return 0
  ```

  Run: renmark-execute --agency-status — must exit 0 and print "agency: inactive".

### Task 5: tests/behavioral/agency.behavior.json — new behavior case
- **mode:** A
- **target:** tests/behavioral/agency.behavior.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** renmark-execute --behavior
- **serves:** AC11
- **spec:**
  DEPENDS ON Task 1 (needs lifecycle.skill_preamble_agency_active in _DISPATCH).

  CREATE tests/behavioral/agency.behavior.json with this exact content:

  ```json
  {
    "skill": "start",
    "deterministic": {
      "call": "lifecycle.skill_preamble_agency_active",
      "assertions": [
        "contains:Agency Mode active"
      ]
    },
    "eval": {
      "contract": "When Agency Mode is active, the start skill preamble includes an Agency Mode active hint.",
      "golden_ref": "agency.golden"
    }
  }
  ```

  "start" is in _AGENCY_AWARE_SKILLS so _with_agency_note will fire.
  The adapter activates agency in a tmpdir before calling skill_preamble.
  lifecycle._AGENCY_HINT_MARKER is "Agency Mode active" — the assertion matches.

  Run: renmark-execute --behavior — all cases including new agency case must pass.

### Task 6: CHANGELOG.md — Agency Mode CLI + test entry
- **mode:** B
- **target:** CHANGELOG.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 400
- **est_cost_usd:** 0.00
- **verifier:** head -30 CHANGELOG.md
- **serves:** BL-0002
- **spec:**
  Read the top of CHANGELOG.md (first 10 lines) to find the `# Changelog` header.
  Prepend a new entry IMMEDIATELY after the `# Changelog` header line:

  ```
  ## 2026-07-06 — Agency Mode: behavior tests + CLI flags

  **Request**: Close BL-0002 — add AC11 behavior proof, CLI agency state management,
  _with_agency_note unit tests, fix pre-existing mode.behavior.json regression.

  **Built**:
  - renmark/behavior.py: `lifecycle.skill_preamble_fresh` and
    `lifecycle.skill_preamble_agency_active` adapters registered in `_DISPATCH`
  - tests/behavioral/mode.behavior.json: switched to `lifecycle.skill_preamble_fresh` —
    fixes regression where live repo's mode=orchestrator broke the assertion
  - tests/behavioral/agency.behavior.json: new deterministic case asserting
    "Agency Mode active" fires in start-skill preamble when agency is active (AC11)
  - tests/test_lifecycle.py: 4 _with_agency_note unit tests (inactive passthrough x2,
    active-aware-skill marker, non-aware passthrough)
  - renmark/cli/_engine.py: --agency-status, --activate-agency, --deactivate-agency

  **Files changed**: renmark/behavior.py, tests/behavioral/mode.behavior.json,
  tests/behavioral/agency.behavior.json (new), tests/test_lifecycle.py,
  renmark/cli/_engine.py, CHANGELOG.md

  **Do not change**: renmark/agency.py state API, lifecycle._with_agency_note logic,
  plugin/skills/*/SKILL.md agency sections, tests/test_agency.py, agency-delivery.md
  ```
