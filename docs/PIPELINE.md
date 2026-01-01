# Pipeline

AudioMason supports an optional configuration key pipeline_steps to control the order of steps.

If pipeline_steps is not set or is null:
- the internal default order is used

## Valid step names

- Stage-level steps (happen before PREPARE in this codebase):
  - unpack
  - convert
  - chapters
  - split

- Process-level steps (happen during PROCESS):
  - rename
  - tags
  - cover
  - publish

Unknown step names are rejected (fail fast).

## Ordering rules

- Stage-level steps must occur before process-level steps
- PROCESS only applies process-level steps; stage-level steps are handled earlier
- Reordering process-level steps is supported to the extent allowed by validation

## Practical examples

Typical full order:

- unpack
- convert
- chapters
- split
- rename
- tags
- cover
- publish

If you disable or reorder, keep these invariants:
- tags should run before cover application if tag writer requires cover data at tag time
- cover must run after any ID3 wipe (wipe happens before PROCESS steps)
