Type: feature
Area: core
Summary: Introduced asyncio-based parallel runner for PROCESS phase (books and multi-source) with minimal import_flow changes.
Details:
- Added async_runner.run_parallel() to schedule work with asyncio.Semaphore, cancel on first error.
- import_flow now uses asyncio runner for books and multi-source PROCESS; preflight remains sequential.
- Keeps ffmpeg gating via concurrency.ffmpeg_slot in audio/covers.
