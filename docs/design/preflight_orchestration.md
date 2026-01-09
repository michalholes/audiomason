# Preflight Orchestration

This document describes the preflight orchestration model introduced in Issue #93.

The goal is to make all preflight prompts deterministic, reorderable, and centrally
governed by a single ordering mechanism.

---

## 1. Motivation

Historically, preflight prompts were partially hard-coded and partially ordered
implicitly by control flow.

This made it impossible to:
- reason about ordering deterministically,
- safely reorder prompts,
- defer decisions until sufficient context existed.

Issue #93 introduces a unified orchestration model that fixes these problems.

---

## 2. One-list model

Preflight ordering is defined by one linear list:

```
preflight_steps: [step_key, step_key, ...]
```

There are no user-visible levels (run/source/book).

All ordering semantics are internal.

---

## 3. Non-movable selection steps

Some steps are structural and must never be reordered:

- choose_source
- choose_books

Properties:
- they are part of the one-list,
- they are validated, but
- they are never offered as movable options.

This guarantees structural integrity while preserving a single ordering model.

---

## 4. Ordering model

The ordering system enforces:

- unknown keys: fail-fast
- duplicate keys: fail-fast
- missing required keys: fail-fast
- required relative ordering constraints: fail-fast

Default ordering is defined in code and represents the canonical baseline.

If preflight_steps is not configured, behavior is identical to historical behavior.

---

## 5. Context eligibility

Each step declares a minimum required context:

- none
- source_selected
- books_selected

If a step appears before its context exists, it is not executed immediately.

---

## 6. Pending decisions

Steps that appear too early are handled via pending decisions:

- the step is recorded as pending,
- once sufficient context exists, it is materialized deterministically,
- no heuristics or reordering occur.

Materialization always respects the original list order.

---

## 7. Determinism guarantees

The orchestration system guarantees:

- same inputs lead to same ordering,
- same context progression leads to same execution points,
- no hidden prompts,
- no implicit control-flow ordering.

---

## Implementation guardrails (Issue #94)

- Preflight steps are registered in the preflight registry.
- Execution is performed by the orchestrator/dispatcher.
- `import_flow.py` must route all preflight questions through the preflight wrappers
  (no direct `prompt()` / `prompt_yes_no()` for preflight decisions).

Issue #94 adds a guard test to make this hard to regress accidentally.


## 8. Summary
Issue #93 establishes a foundation for:

- fully deterministic preflight execution,
- safe reordering,
- future non-interactive and GUI frontends.

All future preflight behavior must go through the registry and orchestrator.
