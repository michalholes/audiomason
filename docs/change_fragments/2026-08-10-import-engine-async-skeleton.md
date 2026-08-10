Type: internal
Area: core
Summary: Add async skeletons for per-source lifecycle and import engine (no behavior change)
Details:
- New source_lifecycle_async.run_source_lifecycle_async() delegating to the sync lifecycle in a thread.
- New import_engine_async.run_import_async() delegating to run_import() in a thread.
- Serves as a stable async API surface for future native-async orchestration without touching the monolith.
