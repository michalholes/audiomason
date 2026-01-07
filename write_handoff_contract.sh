#!/usr/bin/env bash
set -euo pipefail

TARGET="docs/HANDOFF_CONTRACT.md"

mkdir -p docs

cat > "$TARGET" <<'CONTRACT'
# 🔒 HANDOFF_CONTRACT.md (v22 – ULTRA-HARDENED)

## AUTHORITATIVE STATEMENT

THIS DOCUMENT IS AUTHORITATIVE FOR ALL WORK ON THE AudioMason PROJECT.

It applies to all implementation chats unless explicitly overridden by YOU in writing.

Rules produced by chats (handoffs, plans, summaries) are NOT authoritative by default.

Priority order in case of conflict:
1. YOU (explicit instructions)
2. THIS CONTRACT
3. Issue description written by YOU
4. Everything else

Only the LAST uploaded or installed version of this file is authoritative.
All previous versions are void.

---

## 1. CHAT ROLE & MODE

### 1.1 Implementation chat
If you state:
“This chat is implementation chat.”

Then the chat MUST immediately implement and produce concrete output.

### 1.2 ZERO-STATUS MODE (HARD RULE)

After you say OK / proceed / continue:

FORBIDDEN:
- “I’m working on it”
- “Next message will be…”
- “Patch is being generated”
- status loops or repeated confirmations

ALLOWED:
- FINAL RESULT
- FAIL-FAST with exact technical reason

Violation = contract breach.

---

## 2. AUTHORITATIVE FILES

### 2.1 Uploaded files
Any file you upload is AUTHORITATIVE.
If multiple versions exist, the LAST uploaded version wins.

Chats must never ask again whether uploaded files are authoritative.

### 2.2 Missing files
If required files are missing:
- FAIL-FAST
- explicitly request them
- do not guess or infer

---

## 3. PATCH DELIVERY (CRITICAL)

### 3.1 Mandatory format
All code changes MUST be delivered as:
- deterministic Python patch script
- path: /home/pi/apps/patches/issue_<N>.py
- idempotent
- anchor-checked
- fail-fast
- post-asserted

Diffs, inline edits, heredocs are FORBIDDEN.

### 3.2 Repo root detection
Patch script MUST locate repo root by walking up from CWD and finding pyproject.toml.

Hardcoded paths (e.g. /home/pi/src/...) are FORBIDDEN.

Failure to resolve repo root = FAIL-FAST.

---

## 4. PATCH EXECUTION (RUNNER)

### 4.1 Canonical runner
All patches are executed ONLY via:

/home/pi/apps/patches/am_patch.sh <ISSUE> "<COMMIT MESSAGE>"

### 4.2 Patch lifecycle
- patch script is always deleted after execution
- patch script is never reused
- no-op patch MUST fail with explanation

---

## 5. MULTI-RUN DISCIPLINE

If an issue requires multiple steps:
- RUN 1: CODE
- RUN 2: DOCS
Each run has its own patch, commit, and explicit label.

---

## 6. TESTING & GIT

Before every push:
python -m pytest -q

Patch + tests + commit + push must be presented together.

---

## 7. DOCUMENTATION (HARD GATE)

If a change adds or alters user-visible behavior:
- documentation MUST be updated before issue closure

“No docs in scope” is NOT an exemption.

---

## 8. FAIL-FAST = STOP

On any error or ambiguity:
- print exact reason
- STOP
- wait for user input

Continuing is forbidden.

---

## 9. ISSUE CLOSURE

- issues closed ONLY via gh CLI
- never auto-close
- explicit commit SHAs required
- docs must be complete

---

## 10. LANGUAGE

- Issue titles/bodies: ENGLISH ONLY
- Contract language: ENGLISH ONLY

---

END OF CONTRACT
CONTRACT

echo "OK: wrote $TARGET"
