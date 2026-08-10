Title: Remove remaining run_coro usages in sync paths

- import_flow: use sync conversions and sync metadata lookup; use asyncio.run for run_parallel
- source_lifecycle: switch to sync metadata lookup; use asyncio.run for run_parallel
- stage_detect_runtime: drop async bridge FS ops; use shutil directly
- verify: call asyncio.run for verify_library_async instead of async_bridge
