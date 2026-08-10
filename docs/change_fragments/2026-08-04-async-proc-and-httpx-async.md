Type: feature
Area: core
Summary: Added async subprocess runner and async HTTP client variants for metadata.
Details:
- New async_proc.run_cmd_async() provides asyncio-based subprocess execution with streamed logging via log bus.
- OpenLibrary client migrated to httpx (sync) and now also exposes validate_author_async/validate_book_async.
- Google Books client migrated to httpx (sync) and now also exposes suggest_title_async.
- No behavior change in pipeline yet; async APIs are prepared for future use.
