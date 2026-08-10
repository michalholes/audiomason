Type: internal
Area: core
Summary: Hook up async import driver using native-async per-source lifecycle
Details:
- import_engine_async.run_import_async now orchestrates sources and phases asynchronously.
- PROCESS phase for multiple sources uses run_parallel_async with existing limits.
- Per-source work uses source_lifecycle_async.run_source_lifecycle_async (PREPARE/PROCESS/FINALIZE), preserving behavior.
