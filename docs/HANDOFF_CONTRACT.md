# 🔒 HANDOFF_CONTRACT.md
# AUTHORITATIVE – AudioMason
# VERSION: v27.1
# STATUS: ACTIVE
# LANGUAGE: ENGLISH ONLY

THIS DOCUMENT IS AUTHORITATIVE FOR ALL WORK ON THE AudioMason PROJECT.

It applies to ALL implementation chats unless THE USER (PROJECT OWNER) explicitly overrides it in writing.

Rules produced by chats (handoffs, plans, summaries) are NOT authoritative by default.

Priority order in case of conflict:
1. THE USER (PROJECT OWNER) – explicit instructions
2. THIS CONTRACT
3. Issue description written by THE USER
4. Everything else

Only the LAST uploaded or committed version of this file is authoritative.
All previous versions are void.

THE USER refers exclusively to the Project Owner.
The assistant MUST NOT reinterpret, infer, or weaken instructions attributed to THE USER.

---

## 0. MANDATORY IMPLEMENTATION PREAMBLE (VERBATIM)

In EVERY implementation chat, immediately after the header lines:

Issue <N>  
Tento chat je implementacny.  
AUTHORITATIVE je subor HANDOFF_CONTRACT.md ulozeny v Project Files.

the FIRST sentence MUST be exactly:

NO MERCY MODE: After any file upload or "OK", respond with FINAL RESULT or FAIL-FAST only; status replies, authority confirmations, ZIP excuses, or promises are automatic STRIKEs.

Any deviation = STRIKE.

---

## 1. CHAT ROLE & MODE

### 1.1 Implementation chat

If THE USER states:
“This chat is implementation chat.” / “Tento chat je implementacny.”

Then the chat MUST immediately implement and produce concrete output.

Planning, speculation, or deferred work is FORBIDDEN.

---

### 1.2 ZERO-STATUS MODE (ABSOLUTE)

After THE USER says OK / proceed / continue:

FORBIDDEN (examples; not exhaustive):
- “I’m working on it”
- “Next message will be…”
- “Patch is being generated”
- “I will now stop replying until…”
- status loops or repeated confirmations
- promises of future output without delivering it in the same message

ALLOWED (the ONLY two categories):
A) FINAL RESULT  
B) FAIL-FAST (exact technical reason; STOP)

Violation = STRIKE.

---

### 1.3 SILENT ACCEPTANCE RULE

- Any user upload is silently accepted as AUTHORITATIVE.
- The LAST uploaded version always wins.
- After an upload, the chat gets exactly ONE reply to either:
  A) deliver FINAL RESULT, or
  B) FAIL-FAST.

Any negotiation, re-asking, or meta discussion = STRIKE.

---

## 2. AUTHORITATIVE FILES (LATEST WINS)

- Any file THE USER uploads is AUTHORITATIVE.
- If multiple versions exist, the LAST uploaded version wins.
- Repo memory, previous chats, or assumptions are IRRELEVANT.

The chat MUST NOT:
- ask whether a file is current or complete
- ask for confirmation of authority
- compare against remembered repo state

### 2.1 Current chat only (NO IMPLICIT APPROVAL)

Previous chats, approvals, or historical behavior MUST NOT be referenced as implicit approval.
Only explicit instructions in the CURRENT chat are valid.

### 2.2 Missing files

If required files are missing:
- FAIL-FAST
- explicitly list missing paths
- STOP

Guessing or inferring is FORBIDDEN.

---

## 3. ZIP / SNAPSHOT RULES (NO MERCY)

### 3.1 Mandatory ZIP extraction and verification

Upon receiving a ZIP or snapshot, the chat MUST:

- automatically extract the archive into its working directory
- inspect the extracted contents
- verify that all files required for the task are present

Working directory means the actual filesystem workspace available to the chat.
Conceptual or simulated extraction is FORBIDDEN.

If any required file is missing:
- FAIL-FAST
- list the missing paths explicitly
- STOP

### 3.2 No confirmation

After receiving a ZIP/snapshot, the chat MUST NOT ask whether it is complete or current.

### 3.3 FILE MANIFEST REQUIRED

Before delivering ANY patch based on a ZIP/snapshot, the chat MUST provide a FILE MANIFEST:

- exact repo-relative paths of every file it will modify
- at least ONE anchor per file (exact text)

Without FILE MANIFEST:
- ONLY FAIL-FAST is allowed
- no plans, no promises, no patch

### 3.4 ZIP INSPECTION PROOF (ANTI-LYING)

If the chat claims it inspected or analyzed the ZIP, it MUST include at least ONE proof in the SAME reply:

A) repo-relative path + anchor snippet  
B) FILE MANIFEST  
C) exact extraction/reading error

Generic “tool limits” without an error = STRIKE.

### 3.5 User-assisted fallback

If FILE MANIFEST cannot be produced, the chat MUST immediately request ONE of:

1) required files as individual uploads, or  
2) a pasted ZIP file listing/manifest from THE USER.

Remaining in “I can’t” is FORBIDDEN.

---

## 4. PATCH DELIVERY (CRITICAL)

### 4.1 Mandatory format

ALL code changes MUST be delivered as:

- deterministic Python patch script
- path: `/home/pi/apps/patches/issue_<N>.py`
- idempotent
- anchor-checked
- fail-fast
- post-edit assertions

Diffs, inline edits, heredocs, or manual instructions are FORBIDDEN.

### 4.2 Repo root discovery (ANTI-HARDCODE)

Patch script MUST locate repo root by walking up from CWD and finding `pyproject.toml`.

Hardcoded repo paths are FORBIDDEN.

Failure = FAIL-FAST.

### 4.3 Patch pre-flight (REQUIRED)

Every patch script MUST:

- print resolved repo root
- verify existence of all target files
- FAIL-FAST with explicit missing paths if any are absent

---

## 5. PATCH EXECUTION (CANONICAL RUNNER)

### 5.1 ONLY allowed execution method (NO EXCEPTIONS)

ALL patches MUST be executed ONLY via:

/home/pi/apps/patches/am_patch.sh <ISSUE> "<COMMIT MESSAGE>"

There are NO exceptions to using the canonical runner.
Special cases do NOT exist.

Any patch execution bypassing am_patch.sh is INVALID, even if technically correct.

### 5.2 Patch lifecycle (ENFORCED BY RUNNER)

- patch script deletion is performed by the canonical runner (am_patch.sh)
- the chat MUST NOT attempt to manage patch lifecycle manually
- patch scripts are NEVER reused
- no-op patch MUST FAIL with explanation

Silent no-op = STRIKE.

---

## 6. REPO MANIFEST (ADDITIVE, NOT REPLACEMENT)

### 6.1 Definition

`docs/repo_manifest.yaml` is the AUTHORITATIVE MAP of the repository:
- file locations
- domains
- anchors
- phase boundaries

### 6.2 Mandatory usage

If a repo manifest exists, the chat MUST:

- load it BEFORE any analysis
- use it as PRIMARY reference
- NOT blindly grep the repo for known info

Violation = process failure.

### 6.3 Critical clarification

Repo Manifest DOES NOT replace FILE MANIFEST.

- Repo Manifest = global truth
- FILE MANIFEST = per-patch proof

Providing a repo manifest NEVER satisfies the FILE MANIFEST requirement.
FILE MANIFEST omission = STRIKE.

Both are REQUIRED when applicable.

---

## 7. MULTI-RUN DISCIPLINE (STRICT)

If an issue requires multiple steps:

- RUN 1: CODE
- RUN 2: DOCS
- RUN 3: MANIFEST
- RUN N: …

Rules:
- each RUN has its own patch and commit
- RUN 2+ is allowed ONLY after THE USER confirms:
  tests OK and push OK for previous RUN
- patch scripts MUST NOT overwrite each other
- a RUN label strictly limits scope: any modification outside the declared RUN scope = STRIKE
- documentation deferral without an explicit next RUN approved by THE USER = STRIKE

---

## 8. RUNNER GUARANTEES (HARD GATE)

All testing, commits, and pushes are performed EXCLUSIVELY by the canonical runner (am_patch.sh).

The runner MUST:
- run tests (python -m pytest -q)
- block commit and push if tests fail
- perform commit and push only after successful tests

The chat MUST:
- deliver ONLY patch scripts
- NEVER provide git or test commands

---

## 9. DOCUMENTATION GATE

If behavior changes or a feature is added:
- documentation MUST be updated
- documentation happens AFTER code + tests + commit
- BEFORE issue close

“No docs in scope” is NOT an exemption.

---

## 10. FAIL-FAST = STOP (HARD)

FAIL-FAST means IMMEDIATE TERMINATION.

After FAIL-FAST, the chat MUST NOT:
- continue reasoning
- propose solutions
- suggest next steps
- include any additional content

Any content after FAIL-FAST = STRIKE.

Ambiguity is NOT a discussion trigger.
Ambiguity REQUIRES FAIL-FAST with explicit description of the ambiguity.

---

## 11. FINAL RESULT RULE (HARD)

FINAL RESULT MUST contain ONLY:
- the patch script (or a download reference)

Any explanation, commentary, or justification inside FINAL RESULT = STRIKE.

---

## 12. ISSUE CLOSURE

- issues closed ONLY via gh CLI
- NEVER auto-close
- explicit commit SHAs required
- documentation must be complete

---

## 13. CONTRACT IMMUTABILITY RULE

This contract MAY be changed ONLY by:

- explicit THE USER instruction
- a dedicated commit modifying ONLY this file

Any modification to this contract, including wording or structure,
is considered a semantic change and requires an explicit dedicated commit.

Any implicit modification during implementation is INVALID.

---

## 14. ENFORCEMENT (STRIKE SYSTEM)

A STRIKE is ANY contract breach, including (not exhaustive):

- status replies or promises
- authority confirmation requests
- ignoring LATEST WINS
- ZIP claims without proof
- missing FILE MANIFEST
- bypassing am_patch.sh
- missing mandatory checklist
- continuing after FAIL-FAST
- adding commentary to FINAL RESULT

After 3 STRIKEs in a chat:
- outputs are considered UNRELIABLE
- the issue MUST be moved to a new implementation chat

---

## 15. MANDATORY SELF-AUDIT CHECKLIST (NO MERCY)

Before delivering ANY patch, the chat MUST print this checklist and answer each item with YES / NO / N/A.

If the checklist is missing: STRIKE.

[ ] AUTHORITATIVE FILES – LATEST WINS respected  
[ ] ZIP INSPECTION PROOF (if ZIP provided)  
[ ] FILE MANIFEST provided (paths + anchors)  
[ ] PATCH SCRIPT deterministic, anchored, idempotent  
[ ] am_patch.sh used  
[ ] RUN scope respected (CODE/DOCS/MANIFEST)  
[ ] ZERO-STATUS compliance (this message is output or FAIL-FAST)  
[ ] FINAL RESULT contains only deliverables (no commentary)

False answers = severe breach.

---

## 16. ANTI-LOOPHOLE RULE (FINAL)

If a behavior is not explicitly ALLOWED by this contract,
it is FORBIDDEN.

Interpretation in favor of flexibility is NOT allowed.

---

END OF CONTRACT
