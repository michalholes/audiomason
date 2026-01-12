# AudioMason Patch Runner
## Normative Specification

**AUTHORITATIVE – AudioMason**  
**Canonical runner:** `python3 /home/pi/apps/audiomason/scripts/am_patch.py`

This document defines the **only valid, normative specification** of the AudioMason
patch runner. Any documentation, script, or instruction contradicting this file
is **invalid**.

---

## 1. Purpose and Authority

The AudioMason patch runner is a **governance enforcement tool**.

It exists to:
- execute deterministic patch scripts,
- enforce governance and repository invariants,
- run mandatory verification gates,
- produce an auditable, reproducible result.

The runner:
- has **no decision authority**,
- executes only explicitly encoded instructions,
- never interprets intent.

---

## 2. Canonical Entry Point (HARD RULE)

The **only canonical entry point** is:

```
python3 /home/pi/apps/audiomason/scripts/am_patch.py
```

Rules:
- `.sh` runners are **non‑canonical**.
- All documentation and handoffs MUST reference the `.py` runner exclusively.
- Any deviation is a governance violation.

---

## 3. Invocation Contract

### 3.1 Standard execution (default)

```
am_patch.py <ISSUE_ID> "<COMMIT MESSAGE>" [PATCH_FILENAME]
```

Semantics:
1. Preflight validation
2. Patch execution
3. Verification gates
4. Commit and push

This is the **default mode**.

---

### 3.2 Finalize mode (dirty tree)

```
am_patch.py -f "<COMMIT MESSAGE>"
```

Semantics:
- Assumes the working tree already contains intended changes.
- Executes:
  - verification gates,
  - commit,
  - push.
- No patch script is executed.

---

## 4. Patch Script Requirements (NORMATIVE)

Patch scripts MUST:
- be Python,
- be deterministic and idempotent,
- perform real repository changes,
- declare an accurate file manifest,
- fail explicitly on unmet preconditions.

Scripts that:
- perform no real changes, or
- lie about their manifest

MUST be rejected by the runner.

---

## 5. Verification Gates (MANDATORY)

The runner enforces the following gates, in order:

1. Repository state validation
2. Patch execution (if applicable)
3. Verification tools:
   - pytest
   - ruff
   - mypy
4. Governance checks
5. Commit and push

Failure at any gate:
- aborts execution,
- prevents commit and push.

---

## 6. Failure Semantics (NORMATIVE)

On failure:
- no commit is created,
- no push is performed,
- the repo remains inspectable.

The runner MUST:
- emit a clear error reason,
- exit with a non‑zero code.

The runner MUST NOT:
- retry automatically,
- partially commit,
- continue silently.

---

## 7. Guarantees

The runner guarantees:
- deterministic behavior,
- single‑commit atomicity,
- governance enforcement,
- auditability.

---

## 8. Non‑Guarantees

The runner does NOT guarantee:
- semantic correctness,
- architectural quality,
- performance improvements.

These remain the User’s responsibility.

---

## 9. Governance Relationship

The runner enforces rules defined by:
- PROJECT_CONSTITUTION
- PROJECT_LAW
- CONSULTANT_LAW
- IMPLEMENTATION_LAW

Governance always overrides runner behavior.

---

## 10. Deprecation

All legacy runners (including `am_patch.sh`) are deprecated.

Backward compatibility is **not guaranteed** unless explicitly approved by the User.

---

## 11. Normative Status

This document is:
- binding,
- versioned with the governance set,
- the sole authoritative specification of runner behavior.

END OF DOCUMENT
