# PROJECT GUARD RAILS – AudioMason

AUTHORITATIVE – AudioMason
Applies to: ALL PROJECT chats
VERSION: 1.5
STATUS: ACTIVE

Changes are allowed ONLY with explicit approval from the Project Owner.

---

## 1. Purpose

This document defines project-level governance and guard rails.
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

## 4. Project Owner Expectations (BINDING)

The following expectations are explicitly defined by the Project Owner
and are considered binding project-level guard rails.

### 4.1 Stability and Quality
- Stability is prioritized over development speed.
- Regressions are considered critical failures.
- A feature is considered complete only if:
  - it is fully tested,
  - fully documented,
  - configurable via CLI and config,
  - and behaves deterministically (fail-fast by default).

### 4.2 Determinism and Defaults
- FAIL-FAST is the default behavior when required information is missing.
- Intelligent defaults are allowed but must always be explicitly documented.
- Undocumented behavior is considered a bug.

### 4.3 CLI, Config, and UX
- CLI must always override config.
- All functionality must be controllable via both CLI and config.
- CLI must be usable by humans and machines, never at the cost of determinism.

### 4.4 Errors and Output
- Human-readable error messages are always required.
- Machine-readable errors must be available when JSON output is enabled.
- Default output verbosity must be high-level pipeline stages
  (DISCOVER / PREFLIGHT / STAGE / PROCESS / FINALIZE).

### 4.5 Outputs and Reproducibility
- Final outputs must be correct and deterministic.
- Logs and timestamps are not required to be bitwise identical.

### 4.6 Documentation
- Documentation is a first-class requirement.
- FEATURE_CATALOG.md is the single source of truth for all functionality.
- Any behavior change requires documentation updates in the same issue.

### 4.7 Long-term Vision
- AudioMason aims to be a best-in-class tool for managing audiobook libraries.
- Reliability and predictability are valued over clever automation.

---

## 5. Preflight Rules

- All decisions must be resolved before PROCESS
- PROCESS phase must never prompt
- After issues #66 / #68 / #69, the preflight contract is considered frozen

Any proposal that weakens preflight determinism MUST be explicitly justified.

---

## 6. Issue Management Rules

- Issues affecting multiple behaviors SHOULD be split
- PM may WARN or FLAG risks
- Project Owner decides

Large issues MUST be explicitly labeled as higher regression risk.

---

## 7. Prioritization Heuristics (Non-binding)

- P1: Preflight determinism
- P2: Workflow / performance
- P3: CLI UX
- P4: Remote API / GUI
- P5: Non-intrusive monetization

These priorities guide discussion but do NOT imply decisions.

---

## 8. Issue State Snapshots (PROJECT CHAT RESPONSIBILITY)

PROJECT chats are responsible for maintaining authoritative issue state
snapshots in the repository.

The following documents are considered authoritative planning/audit references:

- docs/open_issues.md
  - contains all currently OPEN issues with full bodies
  - reflects the current project planning state (status/priority/decision points)
  - MUST be actively kept up-to-date

- docs/closed_issues.md
  - contains all CLOSED issues with full bodies
  - serves as immutable project history
  - only appended to, never rewritten

GitHub Issues remain the execution system of record,
but these documents are the planning and audit reference.

### Mandatory PROJECT chat startup requirement

Every new PROJECT chat MUST explicitly request authoritative issue snapshots
using one of the following methods:

- direct upload of:
  - docs/open_issues.md
  - docs/closed_issues.md
- OR a single ZIP archive containing both files.

If a ZIP archive is provided, the PROJECT chat MUST:
- explicitly unpack the archive,
- verify that both required files are present,
- fail-fast if any file is missing or malformed.

Until both documents are verified:
- the PROJECT chat MUST NOT perform prioritization,
  scope decisions, or planning,
- the chat MUST remain in a BLOCKED state
  due to missing authoritative inputs.

---

## 9. Change Process (MANDATORY)

Any change to this document:

- MUST be proposed explicitly as PENDING
- MUST be ACCEPTED by the Project Owner
- MUST be applied in a dedicated commit
- MUST modify ONLY this file

Silence is NOT acceptance.

---

## 10. PROJECT CHAT CHANGE WINDOW (EXPLICITLY ALLOWED)

In a PROJECT chat, after ACCEPTED approval, the assistant MAY:

- generate an updated version of `docs/PROJECT_GUARD_RAILS.md`
  as a downloadable file that can be directly committed,
- provide explicit git commands to commit and push
  the updated guard rails.

Mandatory delivery requirements:
- the updated guard rails MUST be provided as a complete,
  ready-to-commit document,
- the document MUST be downloadable (not only displayed inline),
- partial diffs or descriptive-only changes are NOT allowed.

Restrictions:
- no patch scripts
- no code changes
- no other files modified
- no implementation guidance

This does NOT change the chat role.

---

## 11. Conflict Resolution

If there is a conflict:
1. Project Owner explicit instruction
2. HANDOFF_CONTRACT.md
3. PROJECT_GUARD_RAILS.md
4. Issue description
5. Everything else

---

END OF DOCUMENT
