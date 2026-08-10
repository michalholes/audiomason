Type: internal
Area: core
Summary: Switch CLI 'verify' to call async entrypoint (behavior unchanged)
Details:
- CLI now runs asyncio.run(verify_library_async(...)) for the 'verify' command.
- Functional behavior and outputs remain identical; this only aligns the CLI with the new async API.
