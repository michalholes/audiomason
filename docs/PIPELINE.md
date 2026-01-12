- Stage-level steps (happen during PREPARE/staging):
  - unpack
  - chapters
  - split

- Process-level steps (happen during PROCESS):
  - convert  (m4a/opus -> mp3)
  - rename
  - tags
  - cover
  - publish  (copy to final destination at end of PROCESS)

Typical full order:

- unpack
- chapters
- split
- convert
- rename
- tags
- cover
- publish

**Invariant (Issue #86):**
- conversion and publish are **PROCESS-only**; PREPARE/stage must not perform heavy audio operations.

If you disable or reorder, keep these invariants:
- tags should run before cover application if tag writer requires cover data at tag time
- cover must run after any ID3 wipe (wipe happens before PROCESS steps)
