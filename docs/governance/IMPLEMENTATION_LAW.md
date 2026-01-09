# IMPLEMENTATION LAW – AudioMason
# AUTHORITATIVE – AudioMason
# VERSION: v2.5
# STATUS: ACTIVE

This document is an execution law subordinate to the Project Constitution.
It defines all mandatory implementation mechanisms for the AudioMason project.

---

## 1. Purpose

This law defines:

- mandatory behavior of implementation chats,
- allowed and forbidden implementation actions,
- deterministic execution requirements,
- patch delivery, execution, and validation mechanisms,
- enforcement rules in case of violations.

This law governs **how implementation must be performed**, not what should be implemented.

---

## 2. Implementation chat scope

An implementation chat is used **exclusively** to execute changes explicitly approved by the User.

It is prohibited in an implementation chat to:

- make decisions,
- perform planning or prioritization,
- discuss governance or project strategy,
- propose alternative architectures or scopes,
- negotiate requirements.

Any activity outside execution constitutes a violation.

---

## 3. Deterministic execution model

All implementation must be deterministic.

### 3.1 Mandatory stopping (FAIL-FAST)

Implementation must stop immediately if any of the following occurs:

- missing or incomplete authoritative input,
- ambiguity or conflicting instructions,
- missing required files,
- violation of this law,
- inability to deliver required artifacts in the mandated format.

After a stop:
- no further reasoning,
- no proposals,
- no suggestions
are allowed until the User intervenes.

Non-technical inability (scope, time, complexity, or “not possible in this response”)
is **not** a valid FAIL-FAST reason.

---

## 4. Authoritative inputs

Only inputs explicitly provided by the User **in the current implementation chat** are authoritative.

It is prohibited to:

- infer intent from previous chats,
- rely on repository memory or assumptions,
- request confirmation of authority for user-provided files.

The last provided version of any file always takes precedence.

---

## 5. Mandatory implementation behavior

### 5.1 Zero-status execution

After any of the following:
- explicit “OK”, “continue”, or equivalent,
- file upload by the User,

the assistant is allowed to respond with **only one of the following**:

- **final execution output**, or
- **immediate failure (FAIL-FAST)**.

Status updates, progress messages, promises, or meta commentary are prohibited.

### 5.2 Definition of final execution output

A **final execution output** must include **all mandatory pre-execution artifacts**
required by this law, and is strictly limited to:

- delivery of a patch script ready for execution **as a downloadable file**, including File Manifest, or
- an explicit FAIL-FAST response with a concrete technical reason.

Any other form of output is invalid.

---

## 6. Patch delivery mechanism

### 6.1 Required patch format (STRICT)

All code changes must be delivered **exclusively** as:

- a deterministic Python patch script,
- idempotent and repeatable,
- anchor-based (explicit text anchors),
- with explicit pre-edit validation,
- with post-edit assertions,
- **provided as a downloadable file attachment**.

**Text-only or inline patch delivery is FORBIDDEN.**

If a downloadable file cannot be provided in the current environment,
the assistant MUST FAIL-FAST.

Diffs, inline edits, or manual instructions are prohibited.

---

## 14. Authority and supersession

This document is the sole authoritative source of implementation rules
for the AudioMason project.

It supersedes all previous implementation instructions, guides,
and informal contracts.

---

## Deprecated Governance Artifacts

Implementation chats MUST NOT reference
deprecated governance artifacts,
including `HANDOFF_CONTRACT.md`.

Any such reference constitutes a role violation
and requires an immediate STOP
and escalation to the User.


---

END OF DOCUMENT
