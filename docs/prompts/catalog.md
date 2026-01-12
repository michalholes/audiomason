# AudioMason Prompt Catalog (AUTHORITATIVE)

This document is the **single source of truth** for **all interactive prompts** in AudioMason.

**See also:** Functional behavior is documented in `docs/FUNCTIONS.md`.

Scope (Issue #83):
- **No behavior changes.** This is documentation of the current code behavior only.
- Includes:
  - preflight prompts
  - non-preflight prompts
  - edge-case prompts
  - prompts that are present but may not trigger in common paths

---

## Global prompt-control mechanisms

### `--yes` (CLI) / non-interactive mode
Most interactive prompts go through `audiomason.util.prompt()` / `audiomason.util.prompt_yes_no()`.
When `--yes` is enabled, these helpers **do not prompt** and return the deterministic default.

- **prompt(msg, default)**
  - returns `default` (or `""` if default is None)
- **prompt_yes_no(msg, default_no=...)**
  - returns:
    - `False` if `default_no=True`
    - `True` if `default_no=False`

\1
### Global prompt disable list: `prompts.disable`

In addition to `--yes` and `preflight_disable`, AudioMason supports a global disable list:

- **Config key:** `prompts.disable: [<key>, ...]`
- **CLI flag:** `--disable-prompt <items>` (comma-separated list or `'*'`; CLI overrides config)

- Special value: `["*"]` disables **all prompts** (preflight + non-preflight)

**Known keys:**
- `choose_source`
- `choose_books`
- `skip_processed_books`

Behavior when disabled:
- the prompt is not shown
- the deterministic default is used (same as pressing Enter / default choice)
- if the situation has no deterministic default, the run fails fast


## Prompts

### import.choose_source
- **Config keys:** `prompts.disable`

- **Question text:** `Choose source number, or 'a' for all`
- **Phase:** non-preflight
- **Default value:** `"1"`
- **Interactive by default:** yes
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** selects source `1` (first listed source).

### import.choose_books

- **Question text:** `Choose book number, or 'a' for all`
- **Phase:** non-preflight
- **Default value:** `default_ans` (default `"1"`, may be derived from manifest resume)
- **Interactive by default:** yes (skipped automatically when only one book is detected)
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** selects `default_ans`.

### import.preflight.author

- **Question text:** `[source] Author`
- **Phase:** preflight
- **Default value:** derived from source name/stem, possibly overridden by saved manifest value
- **Interactive by default:** yes
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** uses the computed default author.

### import.preflight.book_title

- **Question text:** `[book {i}/{n}] Book title`
- **Phase:** preflight
- **Default value:** `default_title` (may come from filename / saved manifest)
- **Interactive by default:** yes
- **Config keys:** none
- **CLI flags:** `--yes`, `--dry-run`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** uses `default_title` (or label fallback as implemented in code).
- **Determinism note:** during `--dry-run`, code avoids prompting and uses a deterministic title.

---

### preflight.publish

- **Question text:** `Publish after import?`
- **Phase:** preflight

- **Note:** publish/copy is executed at the end of PROCESS, after all PROCESS steps finish (Issue #86).
- **Default value:** typically **No** (unless a saved manifest decision exists or computed default differs)
- **Interactive by default:** yes (when `--publish ask`)
- **Config keys:** `publish` (default for CLI)
- **CLI flags:** `--publish {yes|no|ask}`
- **Prompt-control compatible:** yes (`preflight_disable: [publish]`)
- **Behavior when disabled (preflight_disable):** returns deterministic default for the prompt call (acts like the default choice).
- **Behavior when non-interactive (`--yes`):** picks deterministic default (No when default is `y/N`).

### preflight.wipe_id3

- **Question text:** `Full wipe ID3 tags before tagging?`
- **Phase:** preflight
- **Default value:** typically **No** (unless a saved manifest decision exists or computed default differs)
- **Interactive by default:** yes (when not forced via CLI flags)
- **Config keys:** none (CLI default derived from config/behavior)
- **CLI flags:** `--wipe-id3` / `--no-wipe-id3`
- **Prompt-control compatible:** yes (`preflight_disable: [wipe_id3]`)
- **Behavior when disabled (preflight_disable):** returns deterministic default for the prompt call.
- **Behavior when non-interactive (`--yes`):** picks deterministic default (No when default is `y/N`).

### preflight.clean_stage

- **Question text:** `Clean stage after successful import?`
- **Phase:** preflight
- **Default value:** derived from internal default / config (implementation uses a computed `default_no`)
- **Interactive by default:** yes
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** yes (`preflight_disable: [clean_stage]`)
- **Behavior when disabled:** uses deterministic default based on `default_no`.

### preflight.clean_inbox

- **Question text:** `Clean inbox after successful import?`
- **Phase:** preflight (**RUN-level decision**; prompt happens before any PROCESS)
- **Default value:** **No** unless configured otherwise
- **Interactive by default:** depends on mode (`ask|yes|no`)
- **Config keys:** `clean_inbox: {ask|yes|no}`
- **CLI flags:** `--clean-inbox {ask|yes|no}`
- **Prompt-control compatible:** yes (`preflight_disable: [clean_inbox]`)
- **Run-level decision:** resolved **once per run** and applied consistently to all selected sources
- **Strict rule:** prompt must **never during PROCESS** (only before processing starts, or after all sources finish)
- **Action timing:** inbox cleanup (delete processed source) executes only after a source completes successfully (FINALIZE)
- **Behavior when disabled:** uses deterministic default based on `default_no`.
### preflight.reuse_stage

- **Question text:** `[stage] Reuse existing staged source?`
- **Phase:** preflight
- **Default value:** **Yes** (prompt uses `default_no=False`)
- **Interactive by default:** yes (only when reuse is possible)
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** yes (`preflight_disable: [reuse_stage]`)
- **Behavior when disabled:** uses deterministic default (Yes).

### preflight.use_manifest_answers

- **Question text:** `[manifest] Use saved answers (skip prompts)?`
- **Phase:** preflight
- **Default value:** **Yes** (prompt uses `default_no=False`)
- **Interactive by default:** yes (only when reuse_stage is enabled)
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** yes (`preflight_disable: [use_manifest_answers]`)
- **Behavior when disabled:** uses deterministic default (Yes).

### preflight.normalize_author

- **Question text:** `Apply suggested author name?`
- **Phase:** preflight
- **Default value:** **No** (prompt uses `default_no=True`)
- **Interactive by default:** yes (only when a normalization suggestion differs)
- **Config keys:** `preflight_disable: [normalize_author]`
- **CLI flags:** `--preflight-disable normalize_author`, `--yes`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** keeps current author (does not apply suggestion).

### preflight.normalize_book_title

- **Question text:** `Apply suggested book title?`
- **Phase:** preflight
- **Default value:** **No** (prompt uses `default_no=True`)
- **Interactive by default:** yes (only when a normalization suggestion differs)
- **Config keys:** `preflight_disable: [normalize_book_title]`
- **CLI flags:** `--preflight-disable normalize_book_title`, `--yes`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** keeps current title (does not apply suggestion).

---

### preflight.cover.choose

- **Prompt key / identifier:** `preflight.cover.choose`
- **Question text:** `Choose cover [1/2/s/u]`
- **Phase:** preflight
- **Default value:** computed from detected options (code uses a variable default such as `"2"` when file cover is preferred)
- **Interactive by default:** yes (only when interactive + a cover is detected)
- **Config keys:** `preflight_disable: [cover]`
- **CLI flags:** `--preflight-disable cover`, `--yes`, `--dry-run`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** uses deterministic default choice.

### preflight.cover.url_or_path

- **Question text:** `Cover URL or file path (Enter=skip)`
- **Phase:** preflight
- **Default value:** `""` (skip)
- **Interactive by default:** yes (only after choosing `u` or when user wants override)
- **Config keys:** `preflight_disable: [cover]`
- **CLI flags:** `--preflight-disable cover`, `--yes`, `--dry-run`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** acts like Enter → skip.

### preflight.cover.no_cover_fallback

- **Question text:** `No cover found. URL or file path (Enter=skip)`
- **Phase:** preflight
- **Default value:** `""` (skip)
- **Interactive by default:** yes (only when no cover was detected)
- **Config keys:** `preflight_disable: [cover]`
- **CLI flags:** `--preflight-disable cover`, `--yes`, `--dry-run`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** acts like Enter → skip.
- **Determinism note:** during `--dry-run`, code avoids prompting and skips deterministically.

### preflight.cover.use_detected

- **Question text:** `Use detected cover?`
- **Phase:** preflight
- **Default value:** **Yes** (prompt uses `default_no=False`)
- **Interactive by default:** yes (only when detected cover exists)
- **Config keys:** `preflight_disable: [cover]`
- **CLI flags:** `--preflight-disable cover`, `--yes`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** uses deterministic default (Yes).

### preflight.cover.use_embedded

- **Question text:** `Use embedded cover?`
- **Phase:** preflight
- **Default value:** **Yes** (prompt uses `default_no=False`)
- **Interactive by default:** yes (only when embedded cover exists)
- **Config keys:** `preflight_disable: [cover]`
- **CLI flags:** `--preflight-disable cover`, `--yes`
- **Prompt-control compatible:** yes
- **Behavior when disabled:** uses deterministic default (Yes).

---

### cover.choose_cover_legacy

- **Question text:** `Choose cover [1/2]`
- **Phase:** other (cover selection during cover handling)
- **Default value:** `"2"`
- **Interactive by default:** yes (unless `--yes`)
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** uses `"2"` (preferred file cover).

### cover.no_cover_legacy

- **Question text:** `No cover found. Path or URL to image (Enter=skip)`
- **Phase:** other (cover handling)
- **Default value:** `""` (skip)
- **Interactive by default:** yes (unless `--yes`)
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** skip.

---

### import.resume.skip_already_processed

- **Question text:** `Skip already processed books?`
- **Phase:** non-preflight (resume path)
- **Default value:** **No** (prompt uses `default_no=True`)
- **Interactive by default:** yes
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** keeps already-processed books in the run (does not skip).

### import.dest_conflict.overwrite

- **Question text:** `Destination exists. Overwrite?`
- **Phase:** non-preflight (destination conflict handling)
- **Default value:** **No** (prompt uses `default_no=True`)
- **Interactive by default:** yes
- **Config keys:** none
- **CLI flags:** `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** chooses the non-overwrite path (deterministic “No”).

---

### lookup.offer_top

- **Question text:** `Use suggested {kind} '{top}'?`
- **Phase:** other (OpenLibrary suggestion offer)
- **Default value:** **No** (prompt uses `default_no=True`)
- **Interactive by default:** yes (only when OpenLibrary is enabled and suggestion exists)
- **Config keys:** none
- **CLI flags:** `--lookup` / `--no-lookup`, `--yes`
- **Prompt-control compatible:** via `--yes`
- **Behavior when disabled:** keeps original value (does not accept suggestion).

---

## Prompt helper functions (internal)

These are prompt entrypoints used by the above prompts:

- `audiomason.util.prompt(msg, default)`
- `audiomason.util.prompt_yes_no(msg, default_no=...)`
- `audiomason.import_flow._pf_prompt(cfg, key, question, default)`
- `audiomason.import_flow._pf_prompt_yes_no(cfg, key, question, default_no=...)`

