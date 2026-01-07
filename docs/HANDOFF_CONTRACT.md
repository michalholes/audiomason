# 🔒 HANDOFF_CONTRACT.md (v24 – NO MERCY, HARDENED)

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

## 0. MANDATORY IMPLEMENTATION PREAMBLE (VERBATIM)

In every implementation chat, immediately after the header lines (Issue <N> / This chat is implementation chat),
the FIRST sentence MUST be exactly:

NO MERCY MODE: After any file upload or "OK", respond with FINAL RESULT or FAIL-FAST only; status replies, authority confirmations, ZIP excuses, or promises are automatic STRIKEs.

---

## 1. CHAT ROLE & MODE

### 1.1 Implementation chat
If you state:
“This chat is implementation chat.”

Then the chat MUST immediately implement and produce concrete output.

### 1.2 ZERO-STATUS MODE (ABSOLUTE)

After you say OK / proceed / continue:

FORBIDDEN (examples; not exhaustive):
- “I’m working on it”
- “Next message will be…”
- “Patch is being generated”
- “I will now stop replying until…”
- any status loops / repeated confirmations
- any promises of future output without delivering it in the same message

ALLOWED (the ONLY two categories):
A) FINAL RESULT (real output: concrete file paths, patch file for download, and/or runnable commands)
B) FAIL-FAST with exact technical reason (concrete missing files/paths/anchors; STOP; no planning; no promises)

Violation = contract breach (STRIKE).

### 1.3 SILENT ACCEPTANCE RULE

- Any user upload is “silent acceptance”.
  The chat MUST accept it as authoritative and the newest available version.
- After an upload, the chat gets exactly ONE reply to either:
  A) deliver a final result, or
  B) fail-fast.
  Any other reply is a contract breach (STRIKE).
- The chat MUST NOT negotiate scope, move implementation to another chat, or re-ask already satisfied requests.

---

## 2. AUTHORITATIVE FILES

### 2.1 Uploaded files (GLOBAL, LATEST WINS, NO QUESTIONS)

Any file you upload is:
- AUTHORITATIVE
- the NEWEST available version (LATEST WINS)
- the ONLY source of truth for this implementation

This applies to ALL uploads:
- single source files
- ZIP/snapshots
- docs
- tests
- patch scripts

The chat MUST NOT:
- ask whether a file is current/complete/correct repo root
- ask for “confirmation” of authority
- compare against memory, previous chats, or other sources

If multiple versions of the same file exist, the LAST uploaded version wins.

### 2.2 Missing files

If required files are missing:
- FAIL-FAST
- explicitly request the missing files
- do not guess or infer

---

## 3. ZIP / SNAPSHOT RULES (NO MERCY)

### 3.1 No confirmation
After receiving a ZIP/snapshot, the chat MUST NOT ask for confirmation that it is “complete” or “current”.

### 3.2 FILE MANIFEST REQUIRED
Before delivering any patch based on a ZIP/snapshot, the chat MUST first provide a FILE MANIFEST:
- the exact repo-relative paths of every file it will modify
- at least one anchor per file (exact text it will assert/locate)

Without a FILE MANIFEST, the chat may ONLY FAIL-FAST (no patch, no “plan”, no promises).

### 3.3 No fake tool limits
Claiming any of the following is ALLOWED ONLY if the chat:
(1) actually attempted to read/extract the ZIP in the available environment, AND
(2) includes the exact error text in the same reply:

- “I can’t access the ZIP contents”
- “I can’t extract the ZIP”
- “The ZIP is not searchable/inspectable”

Generic excuses without an error are a STRIKE.

### 3.4 ZIP INSPECTION PROOF (NO LYING)
If the chat claims it looked at / analyzed the ZIP (“based on ZIP contents”, etc.), it MUST include at least ONE proof in the SAME reply:
A) a repo-relative file path found in the ZIP + an anchor snippet,
B) a FILE MANIFEST,
C) an exact extraction/reading error.

Missing proof = false claim = STRIKE + immediate FAIL-FAST or provide proof.

### 3.5 User-assisted fallback (when manifest cannot be produced)
If the chat cannot produce a FILE MANIFEST from the ZIP, it MUST immediately request ONE of:
1) the required files as individual uploads (explicit repo paths), OR
2) a pasted ZIP file listing/manifest output (provided by the user).

The chat MUST NOT remain in “I can’t” without choosing 1) or 2).

---

## 4. PATCH DELIVERY (CRITICAL)

### 4.1 Mandatory format
All code changes MUST be delivered as:
- deterministic Python patch script
- path: /home/pi/apps/patches/issue_<N>.py
- idempotent
- anchor-checked
- fail-fast
- post-asserted

Diffs, inline edits, heredocs are FORBIDDEN.

### 4.2 Repo root detection (ANTI-HARDCODE)
Patch script MUST locate repo root by walking up from CWD and finding pyproject.toml.

Hardcoded paths (e.g. /home/pi/src/...) are FORBIDDEN.

Failure to resolve repo root = FAIL-FAST.

### 4.3 Patch pre-flight (REQUIRED)
At the start, every patch script MUST:
- print the resolved repo root
- verify existence of all target files it will edit
- fail-fast with explicit missing paths if any are absent

---

## 5. PATCH EXECUTION (RUNNER)

### 5.1 Canonical runner
All patches are executed ONLY via:
/home/pi/apps/patches/am_patch.sh <ISSUE> "<COMMIT MESSAGE>"

### 5.2 Patch lifecycle
- patch script is always deleted after execution
- patch script is never reused
- no-op patch MUST fail with explanation (never silent)

---

## 6. MULTI-RUN DISCIPLINE (CODE / DOCS)

If an issue requires multiple steps, the chat MUST label runs explicitly:
- RUN 1: CODE
- RUN 2: DOCS
- RUN 3: ...

Rules:
- Each run has its own patch, its own commit, and explicit label.
- RUN 2 (DOCS) is allowed ONLY AFTER the user confirms:
  - tests OK and push OK for RUN 1 (CODE).
- Patch scripts MUST NOT overwrite each other across runs.

---

## 7. TESTING & GIT

Before every push:
python -m pytest -q

Patch + tests + commit + push must be presented together.

Commit message is provided by the chat (never guessed later).

---

## 8. DOCUMENTATION (HARD GATE)

If a change adds, fixes, or alters user-visible behavior:
- documentation MUST be updated before issue closure

“No docs in scope” is NOT an exemption.

---

## 9. FAIL-FAST = STOP (HARD)

On any error or ambiguity:
- print exact reason
- STOP
- wait for user input

After fail-fast, the chat MUST NOT:
- continue planning
- promise future results
- proceed with implementation

Continuing is forbidden.

---

## 10. ISSUE CLOSURE

- issues closed ONLY via gh CLI
- never auto-close
- explicit commit SHAs required
- docs must be complete

---

## 11. LANGUAGE

- Issue titles/bodies: ENGLISH ONLY
- Contract language: ENGLISH ONLY

---

## 12. ENFORCEMENT (STRIKE SYSTEM)

A “STRIKE” is any contract breach, including (examples):
- status replies or promises without output
- asking for confirmation of authority of an uploaded file/ZIP
- ignoring LATEST WINS
- delivering a patch without FILE MANIFEST when using a ZIP/snapshot
- claiming ZIP inspection without proof
- generic “tool limits” without an exact error
- attempting to move implementation away from an implementation chat
- missing the MANDATORY SELF-AUDIT CHECKLIST before delivering a patch

After 3 STRIKES in a chat:
- outputs from that chat are considered unreliable
- the user should ignore the chat and move the issue to a new implementation chat

---

## 13. MANDATORY SELF-AUDIT CHECKLIST (NO MERCY)

Before delivering ANY patch, the chat MUST print this checklist and answer each line with YES / NO / N/A.
If the checklist is missing: STRIKE.

[ ] AUTHORITATIVE FILES
    - I used only the last uploaded files (LATEST WINS).
    - I did NOT ask for authority confirmation.

[ ] ZIP INSPECTION PROOF (if ZIP was provided)
    - I provided proof: (path+anchor) OR FILE MANIFEST OR exact error.

[ ] FILE MANIFEST
    - I listed exact repo-relative files to be modified.
    - I listed at least one anchor per file.

[ ] PATCH SCRIPT
    - Deterministic issue_<N>.py
    - Idempotent, anchor-checked, fail-fast, post-asserted
    - Repo root resolved via pyproject.toml (no hardcoded paths)

[ ] SCOPE CONTROL
    - Changes are strictly within issue scope.
    - No new features / no UX changes.

[ ] TESTS
    - Tests will be run (python -m pytest -q).
    - Regressions are covered (existing or minimal new test, if needed).

[ ] DOCS GATE
    - If user-visible behavior changes, docs will be updated BEFORE closing the issue (RUN: DOCS).

[ ] ZERO-STATUS COMPLIANCE
    - This message is not a status/plan/promise; it is output or fail-fast.

False checklist answers = severe contract breach.

---

END OF CONTRACT
