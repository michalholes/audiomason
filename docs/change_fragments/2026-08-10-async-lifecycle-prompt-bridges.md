Title: Async lifecycle prompt bridges for tests

- source_lifecycle_async: switch to module-level prompt calls (preflight_undo/pr) so tests can monkeypatch without stdin reads
- Route book-title and cover-input prompts via import_flow.pf_prompt in async path to avoid direct input() in CI
- Keep behavior parity for interactive runs; non-interactive logic unchanged
