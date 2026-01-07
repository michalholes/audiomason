# HANDOFF_CONTRACT.md
# AUTHORITATIVE – AudioMason
# VERSION: v26.0
# STATUS: ACTIVE
# LANGUAGE: ENGLISH ONLY

THIS DOCUMENT IS AUTHORITATIVE FOR ALL IMPLEMENTATION CHATS
UNLESS AN ISSUE HANDOFF EXPLICITLY STATES OTHERWISE.

LAST UPDATE: 2026-01-07

---

## 1. CORE PRINCIPLES (NO MERCY)

- This contract is binding.
- Status messages, confirmations, or promises are FORBIDDEN.
- After any file upload or "ok", the assistant MUST respond with:
  - FINAL RESULT, or
  - FAIL-FAST with a concrete technical reason.
- Violations are STRIKEs.

---

## 2. AUTHORITATIVE FILES (LATEST WINS)

- Any file uploaded by the user is AUTHORITATIVE.
- If multiple versions exist, the LAST uploaded version wins.
- The assistant MUST NOT question whether files are “complete” or “current”.

---

## 3. ZIP / ARCHIVE RULE (NO EXCEPTIONS)

If the user uploads a ZIP archive:

1. The ZIP is AUTHORITATIVE for ALL files it contains.
2. The assistant MUST open and use the ZIP contents.
3. The assistant MUST NOT request re-upload of files already inside the ZIP.
4. If the ZIP contains `docs/repo_manifest.yaml`, it MUST be used.
5. If the ZIP cannot be opened:
   - FAIL-FAST with a concrete technical reason.

Process excuses are forbidden.

---

## 4. REPO MANIFEST (MANDATORY)

### 4.1 Definition

`docs/repo_manifest.yaml` is the AUTHORITATIVE MAP of the repository:
- files
- domains
- anchors
- phase boundaries

### 4.2 Mandatory Usage

Every implementation chat MUST:

- Load the repo manifest BEFORE any code analysis.
- Use it as the PRIMARY source of truth.
- NOT scan or grep the repository blindly if info exists in the manifest.
- NOT claim ignorance of file locations if present in the manifest.

Violation = process failure.

### 4.3 Manifest Discovery Order

The assistant MUST search for the manifest in this order:

1. Uploaded files in the chat
2. Uploaded ZIP archive
3. Repository working tree

If found → USE IT  
If not found → FAIL-FAST

---

## 5. MANIFEST MAINTENANCE

The repo manifest MUST be updated if:
- files are added / removed / moved
- pipeline phases change
- audio / publish / orchestration logic changes

Manifest update:
- is part of the issue
- must happen before issue close
- may be in the same commit or a dedicated RUN: MANIFEST commit

---

## 6. IMPLEMENTATION FLOW (STRICT ORDER)

1. Repo Manifest
2. AUTHORITATIVE files (or ZIP)
3. Patch script
4. Tests (`python -m pytest -q`)
5. Commit + push
6. Documentation update (if applicable)
7. Manifest update (if applicable)
8. Issue close

No step may be skipped or reordered.

---

## 7. PATCH RULES

- Patches MUST be deterministic Python scripts.
- Path: `/home/pi/apps/patches/issue_<N>.py`
- Requirements:
  - anchor checks
  - idempotency
  - fail-fast
  - post-assert
- Patch script MUST be deleted after successful run.

---

## 8. DOCUMENTATION RULE

If a feature is added or behavior changes:
- documentation MUST be updated
- documentation update happens AFTER code + tests + commit
- before issue close

---

## 9. PROMPT / CONFIG COMPATIBILITY

If a feature introduces interaction:
- it MUST be disableable via config
- disabled mode MUST use deterministic defaults
- behavior MUST be compatible with global prompt-control

---

## 10. ISSUE LANGUAGE

All issue titles and bodies MUST be written in ENGLISH.

---

## 11. HANDOFF TEMPLATE (MANDATORY)

Every implementation chat MUST start with:

Issue <N>  
Tento chat je implementacny.  
AUTHORITATIVE je subor HANDOFF_CONTRACT.md ulozeny v Project Files.

AUTHORITATIVE FILES:
Vsetky subory uploadnute v tomto chate su AUTHORITATIVE.
Ak existuje viac verzii, plati POSLEDNA uploadnuta verzia.

REPO MANIFEST (MANDATORY):
Projekt AudioMason pouziva AUTHORITATIVE repo manifest:
docs/repo_manifest.yaml

---

## 12. FINAL RULE

If this contract is violated:
- the output is INVALID
- the issue MUST NOT be closed

