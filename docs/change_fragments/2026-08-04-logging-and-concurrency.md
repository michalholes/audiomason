Type: feature
Area: core
Summary: Introduced log bus with contextual prefixes and added concurrency flags and defaults (no behavior change yet).
Details:
- Added audiomason.log_bus for interleaved, prefixed console logs and optional per-source sink integration.
- Added logging_integration helpers (not yet wired in) to keep import_flow small during future async migration.
- util.out now routes through log bus (preserves quiet/debug semantics).
- Added config `concurrency` with defaults: sources=1, books=2, ffmpeg=2.
- Added CLI flags: `--max-parallel-sources`, `--max-parallel-books`, `--max-parallel-ffmpeg`, and `--serial`.
- Prefixed per-book PROCESS logs via log bus without changing import flow logic.
