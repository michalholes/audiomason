# PROJECT LAW – AudioMason
# AUTHORITATIVE – AudioMason
# VERSION: v1.2
# Status: active

This document is an execution law subordinate to the Project Constitution.
It governs project chats and issue management.

---

## 1. Purpose

This law defines:
- project chat responsibilities,
- issue lifecycle management,
- planning and prioritization rules.

---

## 2. Project chat scope

Project chats are used exclusively for:
- creating and managing issues,
- prioritization and planning,
- preparing implementation handoffs.

Project chats must not:
- implement code,
- execute patches,
- modify governance documents.

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

## 6. Mandatory command sequence format

All command sequences provided in project, implementation, or handoff contexts  
MUST be explicit, deterministic, and self-contained.

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

Canonical example:

```
cd /home/pi/apps/audiomason
mv /home/pi/apps/patches/IMPLEMENTATION_LAW_v2.2.md /home/pi/apps/audiomason/docs/governance/IMPLEMENTATION_LAW.md
git add docs/governance/IMPLEMENTATION_LAW.md
git commit -m "Governance: Implementation Law v2.2 (ban scope-based FAIL-FAST, mandatory File Manifest, ZIP inspection proof)"
git push
```

---

### 6.3 Prohibited implicit context

The following are prohibited:

- command sequences without an explicit `cd`,
- reliance on the caller’s current directory,
- instructions such as “run this from the repo root” without an actual command,
- shortened or partial sequences omitting required setup steps.

---

### 6.4 Deterministic reproducibility requirement

Every command sequence must be:

- directly copy-pastable,
- executable without additional interpretation,
- reproducible in a clean shell session.

If a sequence cannot be executed verbatim, it is invalid.

---

### 6.5 Mandatory delivery format for updates

All updates to governance documents, laws, or authoritative project files
MUST be delivered as **downloadable files**.

Rules:
- the assistant MUST provide the updated document as a downloadable file,
- the User will store the file in `/home/pi/apps/patches`,
- inline-only updates or copy-paste–only changes are prohibited.

Any update not delivered as a downloadable file is non-compliant.

---

### 6.6 Enforcement

Any command sequence or update that violates this section:

- is non-compliant with Project Law,
- must be rejected or corrected before use,
- must not be treated as authoritative.

---

## 7. Authority and supersession

This document is the sole authoritative law
governing project chats in the AudioMason project.

---

END OF DOCUMENT
