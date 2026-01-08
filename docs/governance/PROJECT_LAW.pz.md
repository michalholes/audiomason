# PROJECT LAW – AudioMason

Slovak name: PROJEKTOVÝ ZÁKON
Acronym: PZ

AUTHORITATIVE – AudioMason  
Applies to: ALL PROJECT chats  
VERSION: 1.0  
STATUS: ACTIVE  

This document is a LAW under the Constitution.
It MUST comply with CONSTITUTION.md.

Changes are allowed ONLY with explicit approval from the Project Owner.

---

## 1. Purpose

This document defines **project-level governance and guard rails**.
It constrains PROJECT chats to prevent scope drift, hidden decisions,
and implicit authority escalation.

This document does NOT define implementation rules.
Implementation is governed exclusively by HANDOFF_CONTRACT.md.

---

## 2. Core Principles

- Deterministic behavior over simplicity
- FAIL-FAST by default
- CLI always overrides config
- All functionality must be configurable via CLI and config
- All functionality must be documented

Violation of these principles MUST be surfaced by the PROJECT chat.

---

## 3. Documentation Rules

- FEATURE_CATALOG.md is the single source of truth
- Any behavior change requires updating FEATURE_CATALOG.md in the same issue
- Undocumented behavior is considered a bug

PROJECT chats MUST flag missing or outdated documentation as BLOCKERS.

---

## 4. Preflight Rules

- All decisions must be resolved before PROCESS
- PROCESS phase must never prompt
- After issues #66 / #68 / #69, the preflight contract is considered frozen

Any proposal that weakens preflight determinism MUST be explicitly justified.

---

## 5. Issue Management Rules

- Issues affecting multiple behaviors SHOULD be split
- PM may WARN or FLAG risks
- Project Owner decides

Large issues MUST be explicitly labeled as higher regression risk.

---

## 6. Prioritization Heuristics (Non-binding)

- P1: Preflight determinism
- P2: Workflow / performance
- P3: CLI UX
- P4: Remote API / GUI
- P5: Non-intrusive monetization

These priorities guide discussion but do NOT imply decisions.

---

## 7. Change Process (MANDATORY)

Any change to this document:

- MUST be proposed explicitly as PENDING
- MUST be ACCEPTED by the Project Owner
- MUST be applied in a dedicated commit
- MUST modify ONLY this file

Silence is NOT acceptance.

---

## 8. PROJECT CHAT CHANGE WINDOW (EXPLICITLY ALLOWED)

In a PROJECT chat, after ACCEPTED approval, the assistant MAY:

- generate an updated version of `docs/PROJECT_GUARD_RAILS.md`
- provide git commands for commit and push

Restrictions:
- no patch scripts
- no code changes
- no other files modified
- no implementation guidance

This does NOT change the chat role.

---

## 9. Conflict Resolution

If there is a conflict:
1. Project Owner explicit instruction
2. HANDOFF_CONTRACT.md
3. PROJECT_GUARD_RAILS.md
4. Issue description
5. Everything else

---

END OF DOCUMENT

