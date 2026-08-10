Type: internal
Area: core
Summary: Extract per-source lifecycle from import_flow to source_lifecycle module (no behavior change)
Details:
- Added src/audiomason/source_lifecycle.py implementing run_source_lifecycle_sync().
- import_flow._process_one_source now delegates to the new module (legacy body kept unreachable for now to minimize risk; follow-up will remove it).
- No changes in behavior or outputs; tests relying on _SOURCE_PREFIX preserved.
