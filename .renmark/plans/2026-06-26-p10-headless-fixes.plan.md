---
artifact_type: plan
schema_version: 1
created_at: 2026-06-26T00:00:00Z
source_sha: b3953a6
related_plan: .renmark/plans/2026-06-26-p10-headless-contract.plan.md
generator: plan
dependency_refs:
  - .renmark/reviews/2026-06-26-315041a49a07456eac16b7e68bde5859d3c335be.review.md
---

# Plan — P10 review fixes + runtime gate-resolution helper

Addresses the codex review of the P10 contract: 2 Major + 1 Minor confirmed bugs,
plus the "under-built" spec verdict by adding the deterministic runtime core
(`renmark/headless.py`) that bridges the primitives to the skills. Per-skill
markdown adoption across all 28 skills is a tracked follow-up, not in this plan.

**Do-not-change guards honored:** detection precedence + dangerous-gate list
owner-locked; halt must RETURN `needs_input`, never raise; P3 skill_preamble
ordering load-bearing.

### Task 1: config.py — reject non-bool config value (review Major #1)
- **mode:** B
- **target:** renmark/config.py
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 350
- **est_cost_usd:** 0.03
- **verifier:** `python3 -c "import json,os; os.makedirs('.renmark',exist_ok=True); open('.renmark/config.json','w').write(json.dumps({'headless':'false'})); import importlib,renmark.config as c; importlib.reload(c); assert c.is_headless('.') is False, 'string false must NOT enable headless'; assert c.headless_source('.')=='default'; os.remove('.renmark/config.json')"`
- **serves:** review-fix
- **spec:**
  In `is_headless` and `headless_source`, the `.renmark/config.json` `"headless"`
  value must be honored ONLY when it is a real `bool`. A non-bool value (e.g. the
  string `"false"`, which `bool()` coerces to True) must NOT be coerced — fall
  through to the default (False) and `headless_source` must report `"default"`,
  not `"config"`. Remove the `return bool(val)` coercion; accept only
  `isinstance(val, bool)`. Keep env precedence and the never-raise contract intact.
  Update/extend the existing config tests if needed so the suite still passes.

### Task 2: lifecycle.py — halt is failure-safe + repo-relative path (review Major #2, Minor #3)
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.17
- **verifier:** `python3 -m pytest -q tests/test_lifecycle.py >/dev/null 2>&1 && python3 -c "from renmark import lifecycle; r=lifecycle.halt_for_human_review('.', 'merge', originating_skill='finish', what='x'); assert r['status']=='needs_input'; assert r['artifacts'][0].startswith('.renmark/'), r['artifacts']" && rm -rf .renmark/decisions`
- **serves:** review-fix
- **spec:**
  Two fixes to `halt_for_human_review`:
  (Major #2) The function must RETURN the `needs_input` envelope even if
  `write_lifecycle` raises (e.g. `LifecycleBloatError`). Arm the lifecycle gate in
  a way that cannot leave the function raising after the decision artifact is
  written: either call `write_lifecycle` (the gate-arming) BEFORE writing the
  artifact, or wrap the lifecycle write in try/except and still return the
  envelope (the halted state is the safe state — never propagate). Keep the gate
  fields (`human_review_required`, `human_review_for`) set on success.
  (Minor #3) The returned `artifacts[0]` must be the repo-RELATIVE path
  (`.renmark/decisions/<gate>-approval.json`), not absolute; keep the filesystem
  write path correct internally. Do NOT regress the P3 skill_preamble ordering.
  Existing tests must stay green.

### Task 3: renmark/headless.py — runtime gate-resolution helper (under-built fix)
- **mode:** A
- **target:** renmark/headless.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 1100
- **est_cost_usd:** 0.17
- **verifier:** `python3 -c "from renmark import headless; assert hasattr(headless,'resolve_gate') and hasattr(headless,'render_return')"`
- **serves:** under-built
- **spec:**
  New module: the deterministic runtime core skills call at any gate. stdlib-only;
  imports `renmark.config` (is_headless) and `renmark.lifecycle`
  (halt_for_human_review). Functions:
  - `resolve_gate(repo, gate, *, kind, recommended=None, tool_available=None, originating_skill=None, what=None) -> dict`
    where `kind ∈ {"safe","dangerous"}`. Logic:
      * Resolve headless: `config.is_headless(repo)`; if that is False AND
        `tool_available is False` (AskUserQuestion absent → layer-4), treat as
        headless. If still not headless → return `{"mode":"interactive"}` (skill
        renders its normal menu).
      * headless + kind=="safe" → return success envelope:
        `{"status":"success","mode":"headless","gate":gate,"decision":"auto_picked_recommended","human_review_required":False,"artifacts":[],"recommended":recommended}`.
      * headless + kind=="dangerous" (OR kind unknown / uncertain) → delegate to
        `lifecycle.halt_for_human_review(repo, gate, originating_skill=originating_skill or "", what=what or gate)` and return its envelope (fail-safe: uncertainty halts).
  - `render_return(envelope) -> str` → the one classifier-friendly prose line:
    `success`→`result: <decision/recommended>`; `needs_input`→`needs input: <gate> approval required; headless mode cannot approve <gate>`; `failed`→`failed: <reason>`; `interactive`→`""` (no prose, skill handles).
  Match the dangerous-gate list from headless-contract.md. Docstrings + type hints
  per house style. Never raise.

### Task 4: tests for headless.py + the two fixes
- **mode:** A
- **target:** tests/test_headless_runtime.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** `python3 -m pytest -q tests/test_headless_runtime.py`
- **serves:** under-built
- **spec:**
  New test file for `renmark.headless`. Cover: interactive mode when not headless
  and tool_available True/None → `{"mode":"interactive"}`; headless via
  `RENMARK_HEADLESS=1` + safe gate → success/auto_picked_recommended; headless +
  dangerous gate ("merge") → needs_input + decision artifact written + lifecycle
  armed; layer-4 fallback (`is_headless` False but `tool_available=False`) →
  treated headless; uncertain kind → halts (fail-safe); `render_return` prose for
  each status (success→`result:`, needs_input→`needs input:`, failed→`failed:`,
  interactive→empty). Use fresh `tmp_path` repos and monkeypatch env. Match the
  existing test style.

### Task 5: headless-contract.md — document the helper as the canonical gate call
- **mode:** B
- **target:** plugin/skills/_shared/headless-contract.md
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 350
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "resolve_gate" plugin/skills/_shared/headless-contract.md`
- **serves:** under-built
- **spec:**
  Add a "Runtime helper (how skills call this)" section: at any gate a skill calls
  `renmark.headless.resolve_gate(repo, gate, kind=..., recommended=..., tool_available=<AskUserQuestion present?>, ...)`; if it returns `mode==interactive` render the normal menu, otherwise emit the returned envelope as JSON + `render_return(envelope)` as the prose line instead of `AskUserQuestion`. Note that adopting this call across all 28 skill SKILL.md files is a tracked follow-up (the shared menu files already reference this contract). One section; do not rewrite existing sections.

---

## Cost preview

| Task | Executor | Tokens (+overhead) | Cost |
|---|---|---|---|
| 1 config.py fix | sonnet | 350 + 10k | $0.031 |
| 2 lifecycle.py fix | opus | 700 + 10k | $0.161 |
| 3 headless.py helper | opus | 1100 + 10k | $0.167 |
| 4 tests | sonnet | 800 + 10k | $0.032 |
| 5 contract doc | sonnet | 350 + 10k | $0.031 |

**Total: ~$0.42** — 5 tasks, 3 waves (1: tasks 1,2 · 2: task 3 · 3: tasks 4,5).
Executors: sonnet×3, opus×2.
