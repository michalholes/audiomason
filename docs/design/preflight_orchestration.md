# Preflight Orchestration

## 1. Purpose
Preflight orchestration provides a **deterministic and configurable mechanism**
to control the order and scope of all preflight decisions **before any data
processing occurs**.

Its goals are:
- deterministic execution,
- explicit ordering control,
- fail-fast validation,
- full backward compatibility when no configuration is provided.

---

## 2. What is a preflight step
A *preflight step* represents **one logical decision** taken before processing.

Rules:
- each decision is represented by exactly one `step_key`,
- every preflight prompt must belong to a registered step,
- no preflight prompt may execute outside the step registry.

There are no hidden side-effects.

---

## 3. Fixed vs movable steps

### Non-movable steps (always first)
The following steps are **not reorderable** and are executed first:

- `select_source`
- `select_books`

They establish execution context and are intentionally excluded from ordering.

### Movable steps
All other preflight decisions are movable and ordered via `preflight_steps`.

---

## 4. Ordering model
Preflight uses a **single global ordering list**:

```
preflight_steps:
  - reuse_stage
  - clean_stage
  - publish
```

Characteristics:
- ordering is linear and deterministic,
- there are no run/source/book sections in configuration,
- unknown, duplicate, or invalid steps cause FAIL-FAST errors.

---

## 5. Default ordering
If `preflight_steps` is not provided, AudioMason uses the **default ordering**
defined in the **step registry within the code**.

The default ordering:
- exactly preserves current behavior,
- serves as the canonical baseline,
- is documented here for reference only.

Documentation mirrors code but is **not authoritative**.

---

## 6. Context and pending decisions
Some steps require execution context (selected source or books).

If a step is encountered **before its required context exists**:
- it is recorded as a *pending decision*,
- it is materialized automatically once the context becomes available.

This guarantees:
- full ordering freedom,
- no heuristics,
- deterministic behavior.

---

## 7. Scope and overrides
Each decision applies at a certain scope:
- run,
- source,
- book.

Override rules:
1. more specific scope overrides less specific (`book > source > run`),
2. at equal scope, the later decision wins.

This allows early defaults with later, more specific overrides.

---

## 8. Canonical step keys (overview)

Movable steps:
- `clean_inbox`
- `reuse_stage`
- `clean_stage`
- `use_manifest_answers`
- `skip_processed_books`
- `normalize_author`
- `normalize_title`
- `apply_suggested_author`
- `apply_suggested_title`
- `tags`
- `chapters`
- `loudnorm`
- `publish`
- `wipe_id3`

Exact eligibility and defaults are defined in code.

---

## 9. Backward compatibility guarantees
- No configuration means no behavior change.
- Existing flows continue to work unchanged.
- Reordering is always explicit and opt-in.

---

## 10. Relation to issues
- Introduced in Issue #66
- Design finalized in Issue #92
- Implemented in Issue #93
