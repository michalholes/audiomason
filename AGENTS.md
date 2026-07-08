# AGENTS.md

## Project

AudioMason — Python CLI for importing, normalizing, tagging, and publishing audiobooks.
Deterministic output, ASCII-safe paths, fail-fast. Python 3.11+, setuptools build.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test,dev]"
```

## Commands

| Task | Command |
|------|---------|
| Run app (dev) | `./am` or `audiomason` |
| Tests | `pytest` |
| Single test file | `pytest tests/test_foo.py` |
| Single test | `pytest tests/test_foo.py::test_bar` |
| Lint | `ruff check .` |
| Format check | `ruff format --check .` |
| Type check | `mypy src/audiomason` |

CI only runs `pytest` (no lint/typecheck in CI).

## Structure

- `src/audiomason/` — package source (entry: `cli.py:main`)
- `tests/` — pytest suite (flat, no subdirs)
- `am` — shell launcher script (finds repo root, uses `.venv/bin/python`)
- `configuration.yaml` — example config (not the installed one)
- `docs/` — documentation and APT repo assets
- `debian/` — Debian packaging files

## Key conventions

- Config loaded lazily: only for commands that need it (Issue #105).
- Argument parsing is pure — no config access during parse.
- Global state in `state.py` (`OPTS`, `DEBUG`, `VERBOSE`).
- Tests disable all external network access by default (OpenLibrary, urllib).
  Set `AM_TEST_ALLOW_NET=1` to allow network in tests.
- `conftest.py` patches OpenLibrary callsites; tests never hit real APIs.
- Line length 120, target Python 3.11.

## Config

Runtime config: `~/.config/audiomason1/config.yaml`.
Override with `--config <path>`. CLI flags override config values.

## Gotchas

- `mypy` currently has `ignore_errors = true` in pyproject.toml — it won't fail.
- `ruff` lint `select = []` is empty in pyproject.toml — effectively no rules enforced.
- `pyproject.toml.ruff.mypy` exists as a reference for stricter settings but is NOT active.
- `requirements.txt` is legacy; use `pip install -e .` instead.
- Version comes from `importlib.metadata`, not a hardcoded string.
