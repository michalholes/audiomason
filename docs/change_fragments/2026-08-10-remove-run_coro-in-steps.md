Type: internal
Area: core
Summary: Remove run_coro usage in sync apply_book_steps (tags/cover)
Details:
- Simplified import_flow._apply_book_steps to call write_tags/write_cover directly in sync path.
- Async path already handled in source_lifecycle_async; behavior unchanged.
