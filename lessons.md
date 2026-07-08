# Lessons

- Use small narrowing helpers like `_as_dict()` and `_as_str_list()` when reading JSON/YAML/config data under strict mypy.
- After fail-fast branches like `die()`, add `assert var is not None` so mypy narrows captured locals across later uses.
- For untyped external clients (for example `urllib.request.urlopen`), wrap the call in a tiny typed helper/Protocol instead of sprinkling casts across call sites.
- For AI fallback prompts, pass source/book context explicitly and use deterministic retry backoff on HTTP 429 before falling back.
- For user-facing defaults, prefer a cheap heuristic before AI: normalizing the prompt default is more reliable than post-prompt correction.
- For `mutagen.id3` under strict mypy, import frame classes from `mutagen.id3._frames` and `ID3NoHeaderError` from `mutagen.id3._util`; the public package does not explicitly export them.
- When debugging AI lookup behavior, persist the raw API response next to the current stage run so later inspection does not depend on logs or cache state.
- For audiobook series titles, infer the numbering style from the root audio or batch suggestion first, then normalize the rest of the series to that single style.
- For AI metadata hints, read existing ID3 tags read-only and pass them as small structured JSON samples instead of free-form prose.
- For mixed numbering in a series, prefer arabic numerals as the canonical style.
