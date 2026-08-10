Type: feature
Area: core
Summary: Parallel PROCESS orchestration for books and multi-source runs; ffmpeg concurrency gating.
Details:
- Added process_runner with thread pool orchestration:
  - run_books_process_parallel(items, worker, max_parallel_books, max_parallel_ffmpeg)
  - run_sources_process_parallel(sources, runner, max_parallel_sources)
- Added concurrency module with ffmpeg_slot() and set_ffmpeg_limit(), used by audio/covers to cap concurrent ffmpeg invocations.
- Wired import_flow to use parallel books processing and (for 'all' selections) parallel sources in PROCESS phase, controlled by new CLI/config limits.
- Kept preflight prompts sequential; no change to interactive UX.
