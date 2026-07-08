# Lessons

- Use small narrowing helpers like `_as_dict()` and `_as_str_list()` when reading JSON/YAML/config data under strict mypy.
- After fail-fast branches like `die()`, add `assert var is not None` so mypy narrows captured locals across later uses.
