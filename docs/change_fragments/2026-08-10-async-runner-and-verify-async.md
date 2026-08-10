Type: internal
Area: core
Summary: Add async parallel runner and async verify entrypoint (no behavior change)
Details:
- Introduced async_runner.run_parallel_async() for native-async workers with bounded concurrency.
- Extracted verify_library_async() from the inner async block and refactored verify_library() to delegate to it via the existing bridge.
- No user-visible changes; CLI and outputs remain identical.
