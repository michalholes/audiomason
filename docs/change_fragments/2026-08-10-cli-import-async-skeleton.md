Type: internal
Area: core
Summary: Switch CLI 'import' to async engine skeleton (no behavior change)
Details:
- CLI now calls asyncio.run(run_import_async(...)) which delegates to existing run_import() in a thread.
- Preserves behavior; prepares for native-async import orchestration later.
