# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Governance

Two authority files govern all work in this repository:

- **`governance/governance_local.jsonl`** — cross-repo rules (anti-monolith, docs-gate, specification discipline, code quality, bug discipline). Read this before making any changes.
- **`governance/specification.jsonl`** — authoritative specification of what this repo does, must do, and must not do. The single source of truth for this codebase.

## What to read before making changes

**Step 1 — always, for every task:** read `governance_local.jsonl` in full (24 rules, ~3 KB). These are the cross-repo constraints that apply unconditionally.

**Step 2 — before touching any file:** query the relevant subset of `governance/specification.jsonl` using `spec_navigator.py`. Do not read the full spec — it has 521 rules.

```bash
# See available domain tags
python3 governance/spec_navigator.py governance/specification.jsonl --list-tags

# Query by the domain tags that match your task
python3 governance/spec_navigator.py governance/specification.jsonl --tags PLUGIN REGISTRY
python3 governance/spec_navigator.py governance/specification.jsonl --tags FILE_IO
python3 governance/spec_navigator.py governance/specification.jsonl --tags ARCH
```

**Which tags to use:** look at what the file you are changing imports and does, then pick the matching tags:
- Code in `plugins/` or using `PluginRegistry`/`PluginLoader` → `PLUGIN`, `REGISTRY`
- Code touching file system or using file_io plugin → `FILE_IO`
- Core architectural changes → `ARCH`
- Configuration → `CONFIG`
- Web/API endpoints → `ENDPOINT`

Available tags: `ARCH`, `ARTIFACT`, `CONFIG`, `CORE`, `ENDPOINT`, `ERROR`, `FILE_IO`, `LAYOUT`, `PLUGIN`, `REGISTRY`, `UI`

## Key rules to internalize from `governance_local.jsonl`:
- Any change to `src/`, `plugins/`, or `docs/` requires a new file under `docs/change_fragments/`
- Files ≥ 1300 LOC must not grow at all; files ≥ 900 LOC have restricted growth
- No catchall filenames (`utils.py`, `helpers.py`, etc.) or directories
- A single change must not touch 3+ ownership areas (`src`, `plugins`, `badguys`, `scripts`, `tests`, `docs`)
- Specification changes must be committed before implementation changes

## After every change

When the implementation is complete, run Amp to validate all gates (ruff, mypy, pytest, compile, docs, monolith) and commit:

```bash
python3 /home/pi/gitrepos/patchhub/scripts/am_patch.py -s "your commit message"
```

Amp detects the repo root from cwd, runs all gates, commits and pushes on success. If a gate fails, fix it and rerun. Task is not done until Amp passes.

## Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/path/to/test_file.py

# Run a single test
pytest tests/path/to/test_file.py::test_name

# Lint
ruff check src/ plugins/ badguys/ tests/

# Type check
mypy src/

# Run Amp (patch runner) — from /home/pi/gitrepos/patchhub
python3 scripts/am_patch.py ISSUE_ID "commit message" patches/issue_<ISSUE>_v<N>.zip --target-repo-name audiomason2
```

## Architecture

AudioMason2 is a plugin-based audiobook processing pipeline.

**`src/audiomason/core/`** — framework kernel:
- `pipeline.py` / `orchestration.py` — pipeline execution and phase orchestration
- `plugin_registry.py` / `loader.py` — plugin discovery and loading
- `interfaces.py` — base interfaces all plugins implement
- `process_contract_authority.py` / `process_contract_runtime.py` — process job contract enforcement
- `events.py` / `log_bus.py` — event and log routing between core and plugins

**`src/audiomason/api/`** — public API surface (config, plugin queries)

**`plugins/<name>/`** — each plugin is self-contained: `plugin.py` (logic), `plugin.yaml` (manifest). Plugins must not import from other plugins. Each plugin owns its area exclusively.

**`badguys/`** — integration test suite runner. Executes recipe-based test suites against the live system.

**`docs/change_fragments/`** — one file per change that touches `src/`, `plugins/`, or `docs/`. Never edit `docs/changes.md` directly.

## Ownership areas

| Area | Path |
|---|---|
| `src` | `src/` |
| `plugins` | `plugins/` |
| `badguys` | `badguys/` |
| `scripts` | `scripts/` |
| `tests` | `tests/` |
| `docs` | `docs/` |

A single change must not span 3+ of these areas.
