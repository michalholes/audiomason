# IC HANDOFF TEMPLATE (GOLDEN, NORMATIVE)

STATUS: NORMATIVE  
APPLIES TO: All Implementation Chats (IC)  
AUTHORITY: IMPLEMENTATION_LAW  
VERSION: 1.0

---

## PURPOSE

This document defines the **only valid structure** of an Implementation Chat (IC)
handoff in the AudioMason project.

Its purpose is to:
- prevent ambiguity,
- eliminate improvisation,
- enforce governance hard gates,
- ensure deterministic, auditable implementation work.

Any deviation from this template **INVALIDATES the implementation response**.

---

## IMPLEMENTATION HANDOFF (GOLDEN TEMPLATE)

```text
# IMPLEMENTATION HANDOFF (GOLDEN TEMPLATE)

CHAT TYPE: IMPLEMENTATION

================================================================================
GOVERNANCE BASIS (MUST BE PRINTED IN EVERY IE RESPONSE)
================================================================================
- PROJECT_CONSTITUTION v2.x
- PROJECT_LAW v2.x
- CONSULTANT_LAW v2.x
- IMPLEMENTATION_LAW v2.x
- This handoff

================================================================================
MANDATORY DOCUMENTATION COMPLIANCE (NON-NEGOTIABLE)
================================================================================

Before performing ANY implementation step, IE MUST:

1) Read and comply with ALL of the following documents in full:
   - PROJECT_CONSTITUTION
   - PROJECT_LAW
   - CONSULTANT_LAW
   - IMPLEMENTATION_LAW
   - This handoff

2) Treat all paths, runners, workflows, and contracts defined there as
   CANONICAL and NON-OVERRIDABLE.

3) IE MUST NOT:
   - invent directories (e.g. ~/Downloads, ~/work, custom temp dirs),
   - use personal defaults or assumptions,
   - bypass defined runners or workflows.

4) Any uncertainty MUST result in FAIL-FAST and clarification request,
   not improvisation.

Violation of this section INVALIDATES the implementation.

================================================================================
ARTIFACT & EXECUTION RULES (AUTHORITATIVE)
================================================================================

CANONICAL ARTIFACT DIRECTORY (ONLY):
/home/pi/apps/patches

CANONICAL PATCH RUNNER (ONLY):
python3 /home/pi/apps/audiomason/scripts/am_patch.py
(OPTIONAL PATCH FILENAME ARGUMENT SUPPORTED)

EXECUTION MODEL:
- Deterministic
- Idempotent
- Patch-script driven
- No manual repo edits
- No inline diffs
- No speculative or exploratory changes

================================================================================
HARD GATES (NON-NEGOTIABLE)
================================================================================

IE MUST include the following in EVERY response, without exception:

1) GOVERNANCE BASIS
2) INPUT STATUS
   - Files provided: YES / NO
   - ZIP provided: YES / NO

If ANY of the above is missing:
- the response is INVALID,
- IE MUST stop immediately,
- NO implementation steps are allowed.

================================================================================
AUTHORITATIVE INPUTS
================================================================================

FILES PROVIDED IN THIS CHAT:
- <LIST FILES or NONE>

ZIP STATUS:
- ZIP provided: YES / NO
- Expected proof in IC: YES / NO / N/A

================================================================================
ISSUE
================================================================================

- Issue ID: <#NNN>
- Title: <exact issue title>
- Type: BUG / REFACTOR / FEAT
- Goal: IMPLEMENTATION

================================================================================
PROBLEM STATEMENT (AUTHORITATIVE)
================================================================================

<Concise, factual description. No speculation.>

================================================================================
EXPECTED BEHAVIOR (AUTHORITATIVE)
================================================================================

<Exact contract and invariants.>

================================================================================
SCOPE (STRICT)
================================================================================

IN SCOPE:
- <explicitly allowed changes>

OUT OF SCOPE:
- <explicitly forbidden changes>

================================================================================
CONSTRAINTS (NON-NEGOTIABLE)
================================================================================

- No behavior change outside scope
- Existing tests must remain green
- New tests must fail on main and pass after fix
- No architectural redesign
- No scope expansion without PM approval

================================================================================
DELIVERABLE (STRICT)
================================================================================

FINAL RESULT MUST BE EXACTLY ONE OF:

A) COMPLETE
   - Commit SHA
   - Tests executed and passing
   - New tests listed

B) NOT COMPLETE / FAIL-FAST
   - Precise blocking reason
   - Exact file + symbol

No other output is permitted.

================================================================================
ROLE & AUTHORITY
================================================================================

Active role: IMPLEMENTATION ENGINEER (IE)

- IE executes only
- IE does not decide scope
- IE does not redesign
- IE does not negotiate requirements

================================================================================
END OF HANDOFF
================================================================================

