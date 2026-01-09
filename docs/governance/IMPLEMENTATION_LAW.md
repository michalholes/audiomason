# IMPLEMENTATION LAW – AudioMason
AUTHORITATIVE – AudioMason
Status: active
Version: v2.5

This law governs implementation chats and execution behavior.

---

## Mandatory Governance Version Check

Any change that modifies governance documents
MUST include execution of the official
governance version verification tool:

    scripts/gov_versions.py

Implementation chats MUST:
- execute the verification tool,
- report its outcome,
- and provide commit SHA only if verification succeeds.

Failure to run or report the verification
constitutes a role violation.

---

## Deprecated Governance Artifacts

Implementation chats MUST NOT reference
deprecated governance artifacts,
including `HANDOFF_CONTRACT.md`.

Any such reference constitutes a role violation
and requires an immediate STOP
and escalation to the User.

---

END OF DOCUMENT
