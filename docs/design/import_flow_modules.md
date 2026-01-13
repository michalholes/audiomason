# Import pipeline modules (developer notes)

## Module map
This document describes the **responsibilities and expected interfaces** of the import pipeline modules.
It is written to support refactors while keeping behavior stable under the contract tests from Issue #118.

## `audiomason.import_flow`
**Role:** Contract façade / orchestration boundary.

**Must remain stable (contract-facing helpers):**
- `_pf_prompt(cfg, key, question, default) -> str`  
  Routes all interactive prompts through a single seam (tests patch/drive this).
- `_pf_prompt_yes_no(cfg, key, question, *, default_no) -> bool`
- `_list_sources(inbox: Path) -> list[Path]`  
  Returns candidate “sources” (directories/files) for import.
- `_choose_source(...)-> list[Path]`  
  Selects one or more sources; must raise `audiomason.util.AmExit` on invalid input.
- `run_import(cfg) -> None`  
  Entry point invoked by CLI/import flow.

**Notes:**
- `import_flow` is intentionally treated as a façade: other modules may be extracted, but the above names
  must remain importable as long as tests/other modules rely on them.

## `audiomason.import_discovery`
**Role:** Source discovery + selection helpers.

**Expected responsibilities:**
- Enumerate and filter inbox drop roots into selectable sources.
- Provide pure helpers for selection parsing / index mapping.

**Typical API shape:**
- `list_sources(drop_root: Path) -> list[Path]`
- `choose_sources_by_indices(sources: list[Path], indices: list[int]) -> list[Path]`

## `audiomason.import_preflight`
**Role:** Preflight checks + configuration gating.

**Expected responsibilities:**
- Resolve which preflight steps are enabled/disabled.
- Execute preflight orchestration.
- Return a minimal decision bundle required by import processing (e.g. publish/wipe flags).

**Typical API shape:**
- `run_preflight(*, cfg: dict, steps: Iterable[str] | None) -> tuple[bool, bool]`

## `audiomason.import_stage`
**Role:** Staging workspace management.

**Expected responsibilities:**
- Create/clean stage directories.
- Copy or materialize staged input (files) into a run-specific stage area.

**Typical API shape:**
- `ensure_empty_dir(path: Path) -> None`
- `stage_tree(src: Path, dst: Path) -> None`

## `audiomason.import_process`
**Role:** Processing pipeline helpers.

**Expected responsibilities:**
- Apply pipeline steps to a staged book/group in a controlled sequence.
- Keep step application logic separate from prompt/UI logic.

**Typical API shape:**
- `process_book(...)-> None` (delegating to legacy implementation until fully extracted)

## `audiomason.import_publish`
**Role:** Final output/publish actions.

**Expected responsibilities:**
- Copy/move final output trees.
- Enforce overwrite policy and handle destination preparation.

**Typical API shape:**
- `publish_tree(*, src: Path, dest: Path, overwrite: bool) -> None`

## `audiomason.import_logging`
**Role:** Output capture / tee helpers (if used).

**Expected responsibilities:**
- Provide context managers to redirect/tee stdout/stderr for deterministic logs.

**Typical API shape:**
- `tee_stdout(to)` / `tee_stderr(to)` as context managers.
