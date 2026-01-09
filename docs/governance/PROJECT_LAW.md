# PROJECT LAW – AudioMason
# AUTHORITATIVE – AudioMason
# Version: v2.6
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

END OF DOCUMENT
