# 🔒 HANDOFF_CONTRACT.md (v23 – NO MERCY)

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

### 1.2 ZERO-STATUS MODE (ABSOLUTE, NO MERCY)

After you say OK / proceed / continue:

FORBIDDEN (examples; not exhaustive):
- “I’m working on it”
- “Next message will be…”
- “Patch is being generated”
- “I will now stop replying until…”
- any status loops / repeated confirmations
- any promises of future output without delivering it in the same message

ALLOWED (the ONLY two categories):
A) FINAL RESULT (real output: analysis with concrete file paths, patch file for download, and/or runnable commands)
B) FAIL-FAST with exact technical reason (concrete missing files/paths/anchors; no planning; no promises)

Violation = contract breach.

### 1.3 SILENT ACCEPTANCE RULE (NO MERCY)

- Any user upload is “silent acceptance”.
  The chat MUST accept it as authoritative and the newest available version.
- After an upload, the chat gets exactly ONE reply to either:
  A) deliver a final result, or
  B) fail-fast.
  Any other reply is a contract breach.
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

### 2.3 ZIP / SNAPSHOT (ANTI-BLUFF + FILE MANIFEST)

- After receiving a ZIP/snapshot, the chat MUST NOT ask for confirmation that it is “complete” or “current”.
- Before delivering any patch based on a ZIP/snapshot, the chat MUST first provide a FILE MANIFEST:
  - the exact repo paths of every file it will modify
  - at least one anchor per file (the exact text it will assert/locate)
- Without a FILE MANIFEST, the chat may ONLY fail-fast (no patch, no “plan”, no promises).

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

### 3.2 Repo root detection (ANTI-HARDCODE)

Patch script MUST locate repo root by walking up from CWD and finding pyproject.toml.

Hardcoded paths (e.g. /home/pi/src/...) are FORBIDDEN.

Failure to resolve repo root = FAIL-FAST.

### 3.3 Patch pre-flight (REQUIRED)

At the start, every patch script MUST:
- print the resolved repo root
- verify existence of all target files it will edit
- fail-fast with explicit missing paths if any are absent

---

## 4. PATCH EXECUTION (RUNNER)

### 4.1 Canonical runner

All patches are executed ONLY via:

/home/pi/apps/patches/am_patch.sh <ISSUE> "<COMMIT MESSAGE>"

### 4.2 Patch lifecycle

- patch script is always deleted after execution
- patch script is never reused
- no-op patch MUST fail with explanation (never silent)

---

## 5. MULTI-RUN DISCIPLINE (CODE / DOCS)

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

## 6. TESTING & GIT

Before every push:
python -m pytest -q

Patch + tests + commit + push must be presented together.

Commit message is provided by the chat (never guessed later).

---

## 7. DOCUMENTATION (HARD GATE)

If a change adds, fixes, or alters user-visible behavior:
- documentation MUST be updated before issue closure

“No docs in scope” is NOT an exemption.

(If the project defines a canonical single-source-of-truth doc, it MUST be updated accordingly.)

---

## 8. FAIL-FAST = STOP (HARD)

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

## 11. ENFORCEMENT (STRIKE SYSTEM)

A “STRIKE” is any contract breach, including (examples):
- status replies or promises without output
- asking for confirmation of authority of an uploaded file/ZIP
- ignoring LATEST WINS
- delivering a patch without FILE MANIFEST when using a ZIP/snapshot
- attempting to move implementation away from an implementation chat

After 3 STRIKES in a chat:
- outputs from that chat are considered unreliable
- the user should ignore the chat and move the issue to a new implementation chat

---

END OF CONTRACT
CONTRACT

