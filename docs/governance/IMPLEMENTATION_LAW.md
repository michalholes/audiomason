# IMPLEMENTATION LAW – AudioMason

AUTHORITATIVE – AudioMason  
Status: active  

This document is an execution law subordinate to the Project Constitution
and defines all implementation mechanisms of the AudioMason project.

---

## 1. Purpose

This law defines:
- implementation procedures,
- technical mechanisms,
- execution workflows,
- obligations of the implementation chat.

---

## 2. Implementation chat

The implementation chat is used exclusively
to execute User-approved changes.

It is prohibited to:
- make decisions,
- perform planning,
- discuss governance,
- propose architecture,
- present alternative solutions.

---

## 3. Determinism and stopping

All implementation must be deterministic.

In case of ambiguity, missing input, or conflict:
- execution must stop immediately,
- a User decision must be requested.

---

## 4. Authoritative inputs

Only inputs explicitly provided by the User
in the current implementation chat are authoritative.

Working with assumptions or historical repository state
is prohibited.

---

## 5. Patch mechanism

All changes must be performed
using the official project patch mechanism.

Patching must:
- be deterministic,
- include validations,
- fail on no-op changes.

---

## 6. Runner and execution

Implementation must be performed exclusively
using the official project runner.

The official runner is located at:

/home/pi/apps/patches/am_patch.sh

The runner MUST be invoked exactly as follows:

/home/pi/apps/patches/am_patch.sh <ISSUE_NUMBER> "<COMMIT_MESSAGE>"

If the runner is unavailable or cannot be used,
the implementation chat must stop immediately
and request a User decision.

---

## 7. Testing

Running tests is mandatory.

If tests fail:
- the implementation is invalid.

---

## 8. Implementation output

The output of an implementation chat consists of:
- a successful execution,
- one or more commits in the repository,
- SHA identifiers of the commits.

---

## 9. Issue management

The implementation chat:
- must not close issues,
- must not modify issue state.

It must:
- provide commit SHAs,
- explicitly inform that the Project Manager
  must use those SHAs to close the issue.

---

## 10. Amendments to the Implementation Law

Amendments to this law:
- may be proposed by the Consultant or Project Manager,
- may be applied exclusively by the User.

---

## 11. Authority and supersession

This document is the sole authoritative source
of implementation rules for the AudioMason project.

---

END OF DOCUMENT
