# Architecture

How the parts fit together. Updated as the system evolves.

## Components

(One section per significant module / service. Example below.)

### example_component

**Purpose:** What it does in one sentence.
**Location:** `path/to/code/`
**Depends on:** other components / external services
**Public interface:** functions/classes/endpoints exposed to the rest of the system
**Notes:** non-obvious constraints or invariants

## Data flow

(A short prose or ASCII diagram showing how a request/event moves through the system.)

```
(example)
user → http_handler → router → business_logic → db
                                       ↓
                                    cache
```

## Module boundaries

What's allowed to import what. Rules that prevent cross-cutting concerns from creeping in.

- (example) `routes/*` may not import from `db/*` directly — must go through `services/*`

## Key invariants

Things that must always be true. Violating these is a bug.

- (example) Every public API response includes a `request_id` for correlation.
