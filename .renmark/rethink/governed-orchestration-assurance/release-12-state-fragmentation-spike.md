---
artifact_type: spike-finding
schema_version: 1
created_at: 2026-08-05T00:00:00Z
source_sha: fa6409ead1d75955bf9e9fa73beea72ba182f413
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-12.plan.md
generator: sonnet
dependency_refs:
  - CLAUDE.md
  - AGENTS.md
  - renmark/hygiene.py
---

# Release 12 spike: state-fragmentation in the canonical-homes list

## 1. What CLAUDE.md currently documents

`CLAUDE.md` § "All renmark output stays inside the project" (lines 141-147)
lists exactly 9 canonical-home bullets in one comma-separated sentence:

- specs → `.renmark/specs/`
- plans → `.renmark/plans/`
- reviews/verification → `.renmark/reviews/`
- research → `.renmark/research/`
- runtime → `.renmark/state/`
- memory → `.renmark/memory/`
- logs → `.renmark/logs/`
- debug → `.renmark/debug/<session-id>/`
- audits → `.renmark/audits/`

`AGENTS.md` line 49 carries the identical sentence, word for word (the two
files are required to mirror this rule — see `CLAUDE.md`'s "Mirror all rule
changes in AGENTS.md in the same commit").

## 2. Cross-check against `renmark/hygiene.py` and a fresh `ls -la .renmark/`

`renmark/hygiene.py`'s `ARTIFACT_REGISTRY` (lines 61-101+) declares these
top-level artifact-type names (registry `name` field, several of which
share a top-level directory, e.g. `state-live`/`state-scratch` both live
under `state/`, and `version-unpacked`/`version-zip` both live under
`version/`):

`audits, plans, reviews, state-live, state-scratch, memory, ledger,
reports, rethink, roadmap, specs, debug, version-unpacked, version-zip`

A fresh `ls -la .renmark/` (run at HEAD, sha `fa6409e`) shows these
top-level directories:

`analytics, audits, debug, ledger, logs, memory, plans, reports, research,
rethink, reviews, roadmap, specs, state, version`

(plus `config.json` and `README.md`, which are not artifact-type
directories).

Comparing the CLAUDE.md 9-bullet list against the union of the registry
names and the live directory listing, the following top-level categories
exist in the codebase/filesystem but have **no bullet** in CLAUDE.md's
canonical-homes sentence:

1. `analytics` — live directory `.renmark/analytics/`, not in
   `ARTIFACT_REGISTRY` either (used by `/renmark:analytics`); no bullet.
2. `ledger` — `ARTIFACT_REGISTRY` entry `"ledger"` → `ledger/events.jsonl`
   (line 86); live directory `.renmark/ledger/`; no bullet.
3. `reports` — `ARTIFACT_REGISTRY` entry `"reports"` →
   `reports/features/*/*` (line 87); live directory `.renmark/reports/`;
   no bullet.
4. `rethink` — `ARTIFACT_REGISTRY` entry `"rethink"` → `rethink/*/*.md`
   (line 88, this very artifact's home); live directory
   `.renmark/rethink/`; no bullet.
5. `roadmap` — `ARTIFACT_REGISTRY` entry `"roadmap"` → `roadmap/*.md`
   (line 89); live directory `.renmark/roadmap/`; no bullet.
6. `version` — `ARTIFACT_REGISTRY` entries `"version-unpacked"` and
   `"version-zip"` (lines 100-101) → `version/v*/**` and `version/*.zip`;
   live directory `.renmark/version/`; no bullet.

That is exactly **6 missing categories**, confirming the plan's expected
count: `analytics`, `ledger`, `reports`, `rethink`, `roadmap`, `version`.

## 3. `.renmark/memory/failure_rules.jsonl` (Release 10) — already covered

`renmark/recurrence.py` defines the failure-rules store path as:

```
Path(repo) / ".renmark" / "memory" / "failure_rules.jsonl"
```

(`renmark/recurrence.py:731`, exercised by `load_failure_rules` at line
814 and referenced throughout the Release 10 plan,
`.renmark/plans/2026-08-05-governed-orchestration-assurance-release-10.plan.md`).
This file lives directly under `.renmark/memory/`, which is exactly the
directory CLAUDE.md's existing `memory→.renmark/memory/` bullet already
names. **No new bullet is needed for `failure_rules.jsonl` specifically**
— it is a file inside an already-documented canonical home, not a new
top-level category. It is called out here only to confirm the spike
checked it and found no gap.

## 4. Conclusion

CLAUDE.md's canonical-homes list **is stale**. It documents 9 of the 15
top-level `.renmark/` categories that renmark's own tooling
(`renmark/hygiene.py::ARTIFACT_REGISTRY`) and the live `.renmark/`
directory tree actually use, leaving exactly 6 categories undocumented:
`analytics`, `ledger`, `reports`, `rethink`, `roadmap`, `version`.

The fix is **small and mechanical**: append 6 short `category→path`
clauses to the existing comma-separated sentence in CLAUDE.md line 144
(and mirror the same 6 clauses into AGENTS.md line 49, per the existing
"mirror in AGENTS.md" rule) — this is not a rewrite of the section, not a
restructuring of the sentence, and not a change to any `.py` file or to
`ARTIFACT_REGISTRY` itself (the registry is already correct; only the
prose describing it is behind).

**This task performed no edit.** The fix — appending the 6 missing
canonical-home clauses to CLAUDE.md and mirroring them into AGENTS.md —
is Task 2 of
`.renmark/plans/2026-08-05-governed-orchestration-assurance-release-12.plan.md`.

## Assumptions and edge cases considered

- Assumed "canonical-home bullet" means the comma-separated
  `category→path` clauses inside the one sentence on CLAUDE.md line 144,
  not the surrounding "Never write outside the project" guidance (which
  needs no change).
- Considered whether `state-live` / `state-scratch` (both under
  `state/`) or `version-unpacked` / `version-zip` (both under `version/`)
  should count as separate missing bullets — they do not: CLAUDE.md's
  existing style documents one top-level directory per bullet
  (`runtime→.renmark/state/` already covers both state sub-registries),
  so only one new `version→.renmark/version/` bullet is warranted, not
  two.
- Considered whether `config.json` and `README.md` at `.renmark/`'s top
  level need bullets — they are not artifact-type directories governed by
  `ARTIFACT_REGISTRY` and are out of scope for this sentence.
- No missing information: the registry, the live directory listing, and
  the CLAUDE.md/AGENTS.md text were all read directly at the current
  HEAD sha; no gaps to flag.
