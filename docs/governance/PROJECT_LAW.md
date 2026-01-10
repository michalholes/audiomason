# PROJECT LAW – AudioMason
# AUTHORITATIVE – AudioMason
Version: v2.9
# Status: active

This document is a project governance law subordinate to the Project Constitution.
It governs project chats, issue management, and operational conventions.

---

## 1. Purpose

This law defines:
- project chat responsibilities,
- issue lifecycle management,
- planning and prioritization rules,
- mandatory operational conventions for project outputs.

---

## 2. Project chat scope

Project chats are used exclusively for:
- creating and managing issues,
- prioritization and planning,
- preparing implementation handoffs,
- governance updates coordination.

Project chats must not:
- implement code,
- execute patches,
- modify repository state directly.

---

## 3. Issue management

Project chats are responsible for:
- opening issues,
- refining scope and acceptance criteria,
- coordinating with implementation outputs.

Project chats must ensure that:
- issues are clearly scoped,
- large issues are split when appropriate.

---

## 4. Interaction with implementation

Implementation is governed exclusively by the Implementation Law.

Project chats:
- must not bypass implementation rules,
- must use commit SHAs provided by implementation chats
  when closing issues.

---

## 5. Change management

Changes to this law:
- may be proposed by the Consultant or Project Manager,
- may be applied only by the User.

---

## Governance Changes – Version Enforcement

Any change to governance documents
MUST be validated using the official
governance version verification procedure.

A governance change MUST NOT be considered complete
if the version verification fails.

Failure of the version verification
constitutes a hard stop.


---

## 6. Mandatory command and update delivery format

All operational instructions and updates provided in project, implementation,
or handoff contexts MUST be explicit, deterministic, and self-contained.

---

### 6.1 Mandatory working directory declaration

Every command sequence MUST begin with an explicit working directory change:

```
cd <absolute_path_to_repository_root>
```

Implicit assumptions about the current working directory are prohibited.

---

### 6.2 Absolute paths only

All file operations in command sequences MUST use absolute paths.

Relative paths are permitted only after an explicit `cd`
to the repository root.

---

### 6.3 Mandatory downloadable updates

All updates to governance documents, laws, or other authoritative project files
MUST be delivered as downloadable files.

Rules:
- the assistant MUST provide the updated file as a downloadable artifact,
- the User will store the file in `/home/pi/apps/patches`,
- inline-only or copy-paste–only updates are prohibited.

---

### 6.4 Mandatory post-download command sequence

Immediately after providing a downloadable update,
the assistant MUST provide the full command sequence required to:

1. move or rename the downloaded file into its canonical repository location,
2. stage the change,
3. commit it with an appropriate message,
4. push it to the remote repository.

The command sequence MUST:
- appear directly after the downloadable file reference,
- comply with all requirements of this law (explicit `cd`, absolute paths),
- be directly copy-pastable without interpretation.

Providing a downloadable file without the corresponding command sequence
is non-compliant.

---

### 6.5 Prohibited implicit context

The following are prohibited:

- command sequences without an explicit `cd`,
- reliance on the caller’s current directory,
- instructions such as “run this from the repo root” without an actual command,
- shortened or partial sequences omitting required setup steps.

---

### 6.6 Deterministic reproducibility requirement

Every command sequence must be:
- directly copy-pastable,
- executable without additional interpretation,
- reproducible in a clean shell session.

If a sequence cannot be executed verbatim, it is invalid.

---

### 6.7 Enforcement

Any update or command sequence that violates this section:
- is non-compliant with Project Law,
- must be rejected or corrected before use,
- must not be treated as authoritative.

---

## 7. Authority and supersession

This document is the sole authoritative law
governing project chats and project-level conventions
in the AudioMason project.

---

## Role Scope Boundaries

Project chats MUST NOT perform
implementation work or governance enforcement.

If a Project chat encounters:
- implementation-level tasks, or
- governance audit or enforcement,

it MUST:
- stop further discussion,
- and instruct the User to open
  the appropriate chat type.

Continuing outside Project scope
constitutes a role violation.


## Governance Version Synchronization (MANDATORY)

All governance documents located in `docs/governance/` constitute a single Governance Set.

### Rules

1. Any change to **any** governance document that introduces:
   - new mandatory workflows,
   - new enforcement mechanisms,
   - new authoritative tools,
   - or changes cross-document behavior,

   MUST be accompanied by a synchronized governance version update.

2. Governance version synchronization MUST be performed **exclusively** using the official tool:

   ```bash
   scripts/gov_versions.py --set-version <X.Y>
   ```

   Manual editing of version headers in governance documents is **strictly prohibited**.

3. Verification MUST be performed using:

   ```bash
   scripts/gov_versions.py --check
   ```

   A governance change is invalid unless verification succeeds.

4. Version updates MAY be alignment-only (no semantic change),
   but MUST represent a single governance epoch across:
   - PROJECT_CONSTITUTION.md
   - PROJECT_LAW.md
   - IMPLEMENTATION_LAW.md
   - CONSULTANT_LAW.md

5. Any governance change that bypasses the tool,
   or results in version drift,
   constitutes a governance violation.



## §X. Canonical Artifact Directory

The Project Manager MUST ensure that all execution artifacts
(patches, governance documents, scripts, and supporting files)
are consistently handled using the canonical artifact directory:

    /home/pi/apps/patches

This directory is the sole authoritative staging location
for artifacts referenced in consultant or implementation chats.

The Project Manager MUST:
- enforce this directory in all handoffs,
- reject handoffs that reference unspecified or alternative locations.

Failure to enforce the canonical artifact directory
constitutes a project management violation.

---


## §Y. Canonical Implementation Handoff Template (PM Mandatory)

When opening an implementation chat, the Project Manager MUST provide the handoff
using the **Canonical Implementation Handoff Template** below.

The Project Manager MUST:
- fill in all placeholders,
- list all authoritative inputs provided in the chat (exact filenames),
- include the canonical artifact directory,
- ensure the template is posted as the **first message** of the implementation chat.

Failure to use this template constitutes a project management violation.

---

### Canonical Implementation Handoff Template (copy/paste)

```text
# IMPLEMENTATION HANDOFF (CANONICAL)

CHAT TYPE: IMPLEMENTATION

GOVERNANCE BASIS (MUST PRINT IN EVERY IC RESPONSE):
- PROJECT_CONSTITUTION vX.Y
- PROJECT_LAW vX.Y
- CONSULTANT_LAW vX.Y
- IMPLEMENTATION_LAW vX.Y
- This handoff

ARTIFACT DIRECTORY (CANONICAL):
/home/pi/apps/patches

AUTHORITATIVE INPUTS (FILES PROVIDED IN THIS CHAT):
- <list exact filenames, or NONE>

ZIP STATUS:
- ZIP provided: YES/NO
- Expected proof in IC: FILE MANIFEST | anchor snippet | extraction error

ISSUE:
- #NN — <Title>
- Goal: IMPLEMENTATION | VERIFICATION-ONLY
- Scope: <exact scope>
- Non-goals: <explicit exclusions>
- Dependencies: <if any>

MANDATORY GATES (IC MUST ENFORCE):
- Hard Gates (GOVERNANCE BASIS + INPUT STATUS + ZIP proof)
- Docs + Repo Manifest gate (no “complete” without docs/manifest if applicable)
- Dual checklists:
  - GATE CHECKLIST (every response)
  - SELF-AUDIT CHECKLIST (FINAL RESULT only)

DELIVERABLE (STRICT):
- FINAL RESULT must be exactly one of:
  A) COMPLETE (with SHA + confirmation tests + docs + manifest)
  B) NOT COMPLETE / FAIL-FAST (explicit missing items, repo-relative paths)
```

END OF DOCUMENT
