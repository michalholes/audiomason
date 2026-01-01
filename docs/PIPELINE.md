
# Pipeline steps

`pipeline_steps` allows overriding the default order.

Valid steps:
- Stage-level: unpack, convert, chapters, split
- Process-level: rename, tags, cover, publish

Notes:
- Unknown steps are rejected (fail fast).
- Some reorders are disallowed by design because stage-level steps must happen before process-level steps.
