# Lessons

- Use small narrowing helpers like `_as_dict()` and `_as_str_list()` when reading JSON/YAML/config data under strict mypy.
- After fail-fast branches like `die()`, add `assert var is not None` so mypy narrows captured locals across later uses.
- For untyped external clients (for example `urllib.request.urlopen`), wrap the call in a tiny typed helper/Protocol instead of sprinkling casts across call sites.
- For `mutagen.id3` under strict mypy, import frame classes from `mutagen.id3._frames` and `ID3NoHeaderError` from `mutagen.id3._util`; the public package does not explicitly export them.
