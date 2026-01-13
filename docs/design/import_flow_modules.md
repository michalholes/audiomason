# Import pipeline modules (developer notes)

This document is a **developer-facing contract map** for the import pipeline.
It complements the **behavior contracts** in `tests/test_import_flow_contract.py` (Issue #118) and is intended to
make refactors in Issue #117+ safer and faster.

Design doc is **non-normative** for user behavior (tests are normative), but it is **normative for intent**:
it explains *inputs*, *outputs*, and *allowed options* for each module seam.

---

## Module map

Primary façade / boundary:
- `audiomason.import_flow`

Extracted modules (may evolve, façade must stay stable while tests depend on it):
- `audiomason.import_discovery`
- `audiomason.import_preflight`
- `audiomason.import_stage`
- `audiomason.import_process`
- `audiomason.import_publish`
- `audiomason.import_logging` (optional helper layer)

---

## `audiomason.import_flow`

**Role:** Contract façade / orchestration boundary.  
**Why it exists:** provides stable names and seams for testing/refactors while allowing internal extraction.

### Inputs
- `cfg: dict`
  - Must be a loaded AudioMason config structure.
  - Must include `paths.inbox` (used to find sources).
  - May include prompt-disable / preflight-disable configuration (handled indirectly via seams).

### Outputs
- `run_import(cfg) -> None`
  - Performs import orchestration or raises `audiomason.util.AmExit` for user-facing failures.

### Contract-facing helpers (must remain importable while tests depend on them)
- `_pf_prompt(cfg, key, question, default) -> str`
  - Central prompt seam used by tests and by selection logic.
  - **Must not** raise on normal input; returns a string.
- `_pf_prompt_yes_no(cfg, key, question, *, default_no) -> bool`
  - Boolean prompt seam.
- `_list_sources(inbox: Path) -> list[Path]`
  - Returns candidates for import (directories or archives depending on implementation).
  - Expected properties (behavioral): deterministic ordering; stable filtering.
- `_choose_source(...)-> list[Path]`
  - Selects one or more sources.
  - **On invalid input:** must raise `audiomason.util.AmExit`.
  - Must support selecting a single source and selecting “all” when allowed by the caller.
- `run_import(cfg) -> None`
  - Entry point invoked by CLI/import flow.

### Allowed selection modes (conceptual)
- **single**: user selects one numbered source
- **all**: user selects all sources (often via `a`), when allowed by caller

---

## `audiomason.import_discovery`

**Role:** Source discovery + selection helpers.  
**Goal:** make discovery deterministic and testable without depending on interactive prompt text.

### Inputs
- `drop_root: Path` (aka inbox root)

### Outputs
- `list_sources(drop_root: Path) -> list[Path]`
  - Returns sources to be presented to the user or consumed by “import all”.
- `choose_sources_by_indices(sources: list[Path], indices: list[int]) -> list[Path]`
  - Pure helper mapping indices → source paths.

### Discovery rules (high-level)
- Must ignore non-source noise (implementation-defined).
- Must preserve deterministic order (e.g., name sort) for stable UX and stable tests.

---

## `audiomason.import_preflight`

**Role:** Preflight checks + configuration gating.

### Inputs
- `cfg: dict`
- `steps: Iterable[str] | None`
  - `None` means “use default preflight steps”.

### Outputs
- `run_preflight(*, cfg: dict, steps: Iterable[str] | None) -> tuple[bool, bool]`
  - Returns a minimal decision bundle for processing:
    - `publish: bool`
    - `wipe_id3: bool`

### Preflight concerns (examples)
- Prompt disable / headless mode decisions.
- Preflight step selection / validation.
- Any global “should we publish” decision.

---

## `audiomason.import_stage`

**Role:** Staging workspace management.

### Inputs
- `src: Path` source location
- `dst: Path` stage run directory

### Outputs
- `stage_tree(src: Path, dst: Path) -> None`
  - Materializes the source into staging (copy/extract/link depending on implementation).
- Helpers typically include:
  - `ensure_empty_dir(path: Path) -> None`

### Options / behaviors
- Must be safe to re-run (idempotent for the same stage run directory).

---

## `audiomason.import_process`

**Role:** Processing pipeline helpers.

### Inputs (conceptual)
- staged book/group data (paths + metadata)
- pipeline step selection
- output destination roots

### Outputs
- side effects on filesystem (processed output tree)
- may generate tags/cover/write metadata depending on step list

### Responsibilities
- Apply steps in a controlled order.
- Keep step logic separate from prompt/UI logic.

---

## `audiomason.import_publish`

**Role:** Final output/publish actions.

### Inputs
- `src: Path` processed output location
- `dest: Path` final destination
- `overwrite: bool`

### Outputs
- copies/moves final tree into destination
- raises `FileExistsError` (or `AmExit` at façade layer) when overwrite is disallowed

---

## `audiomason.import_logging` (optional)

**Role:** Output capture / tee helpers, used for deterministic logging.

### Inputs
- file-like stream for `stdout` / `stderr`

### Outputs
- context managers:
  - `tee_stdout(to)` / `tee_stderr(to)`
- used by orchestration to capture output while still emitting to console if desired

