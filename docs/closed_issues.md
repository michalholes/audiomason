
================================================================================
ISSUE #89 – Feat: CLI flag for global prompt disable (--disable-prompt)
CLOSED AT: 2026-01-08T08:14:26Z
================================================================================

Follow-up to Issue #76.

Add CLI support for global prompt disable so users can override config at runtime.

Requirements:
- --disable-prompt '*' disables all prompts
- --disable-prompt choose_books,choose_source supports selective disable
- CLI overrides config
- Same validation rules as config (unknown key, duplicates, '*' exclusivity)
- Deterministic behavior only (fail-fast if no default)

Scope:
- CLI parsing
- Wiring into existing prompts.disable mechanism
- Tests only (no docs in this issue)


================================================================================
ISSUE #88 – Bug: clean_inbox prompt appears during PROCESS when selecting all sources
CLOSED AT: 2026-01-07T21:20:38Z
================================================================================

Problem
When selecting all sources ('a'), AudioMason asks the prompt:
Clean inbox after successful import? [y/N]
while already iterating and processing sources, i.e. during the PROCESS phase.

Evidence
Example log excerpt:
[ignore] added: Komensky.JanAmos
[inbox] cleaned: /mnt/warez/abooksinbox/Komensky.JanAmos
[stage] cleaned: /mnt/warez/_am_stage/Komensky.JanAmos
[source] 4/14: Lipton.BruceH
Clean inbox after successful import? [y/N]

Key observations:
- All sources were selected
- Source iteration is already in progress (4/14)
- PROCESS phase is active
- clean_inbox prompt appears mid-run

Why this is wrong
The clean_inbox decision is a global / batch-level concern.
Asking it during PROCESS:
- breaks phase separation
- breaks determinism
- creates confusing UX

Expected behavior
- clean_inbox decision must be resolved once per run
- it must be resolved either:
  - before any PROCESS starts, or
  - after all sources finish processing
- the prompt must never appear mid-PROCESS

Actual behavior
- clean_inbox prompt is evaluated inside the per-source loop
- it can appear after some sources are already processed

Scope (STRICT)
- Move clean_inbox decision to a clear phase boundary
- Ensure it is resolved once per batch
- Preserve existing defaults and config behavior
- No new features, only phase-correctness


================================================================================
ISSUE #86 – BUG: audio conversion and publish run in the wrong phase/order (opus + m4a)
CLOSED AT: 2026-01-07T09:56:56Z
================================================================================

BUG: audio conversion and publish run in the wrong phase/order (opus + m4a)

Summary
AudioMason performs heavy audio work too early and/or in the wrong order:
- conversion (confirmed for .opus and .m4a) runs during PREPARE/stage instead of PROCESS
- output publish/copy to the final library happens at the start of PROCESS, before finalization steps

Observed
- With .opus sources, ffmpeg conversion logs appear immediately after staging (before PROCESS).
- The same behavior is confirmed for .m4a.
- In debug logs, PROCESS begins with copying files from stage/src into the final output directory.

Expected
- PREPARE must remain lightweight (prompts/validation/manifest/stage setup) and must not run heavy conversions.
- All audio transformations must happen inside PROCESS (convert/rename/wipe_id3/tags/chapters/split/loudnorm/etc.).
- Publish/copy to the final output directory must happen only after all finalization steps complete.

Scope (strict)
- Fix phase ordering only.
- No UX changes.
- No new features.
- Preserve existing behavior except for moving work to the correct phase/order.

Acceptance criteria
- No .opus or .m4a conversion runs during PREPARE/stage.
- Conversions run only in PROCESS.
- Final output publish/copy happens after all processing/finalization steps.
- Existing tests pass; add a regression test if feasible.



================================================================================
ISSUE #85 – Docs: cross-link canonical FUNCTIONS and prompt catalog (avoid duplication)
CLOSED AT: 2026-01-07T07:46:41Z
================================================================================

## Problem

There are two canonical documentation files that describe different but related aspects
of AudioMason behavior:

- `docs/FUNCTIONS.md` — canonical source of truth for functional behavior
- `docs/prompts/catalog.md` — canonical source of truth for interactive prompts

While they are intentionally separate, the relationship between them is not explicit,
which can lead to confusion or accidental duplication.

## Goal

Keep the documents strictly separated (no merge), but make the relationship explicit
and self-documenting.

## Requirements (STRICT)

1. Do NOT merge the documents.
2. Add a short cross-reference in the introduction of both files:
   - `docs/FUNCTIONS.md` must point to `docs/prompts/catalog.md` for interactive prompts.
   - `docs/prompts/catalog.md` must point to `docs/FUNCTIONS.md` for functional behavior.
3. Do NOT duplicate content between the two documents.
4. Documentation-only change (no functional or behavioral changes).

## Acceptance criteria

- Both documents contain a clear and visible cross-link.
- Each document keeps its original responsibility and scope.
- No duplicated descriptions of prompts or functions exist.
- All tests pass.



================================================================================
ISSUE #84 – Feat: support .opus audiobooks (convert to .mp3)
CLOSED AT: 2026-01-07T07:57:49Z
================================================================================

Feat: support .opus audiobooks (convert to .mp3 and process normally)

Problem
AudioMason currently does not support audiobooks stored as .opus files.
Such sources are either ignored or fail during processing, even though .opus
is a common and efficient audiobook format.

Goal
Add first-class support for .opus audiobook files by converting them to .mp3
and then processing them through the standard AudioMason pipeline.

Expected behavior
- .opus files found in source directories are detected as valid audio inputs
- Each .opus file is converted to .mp3 using the existing audio toolchain
- After conversion, processing continues exactly as for native .mp3 sources
- Folder and book structure semantics remain unchanged

Scope (STRICT)
- Only add support for .opus input files
- Conversion target format: .mp3
- No changes to existing .mp3/.m4a behavior

Configuration / CLI
- Conversion must be controllable via CLI and config
- No new prompts by default
- Any new prompt MUST be disable-able via config/CLI

Acceptance criteria
- .opus-only audiobooks are fully processed end-to-end
- Mixed folders (.opus + .mp3/.m4a) behave deterministically
- All existing tests pass
- New tests cover .opus detection and conversion



================================================================================
ISSUE #83 – Chore: authoritative catalog of all AudioMason prompts (defaults, config, CLI)
CLOSED AT: 2026-01-06T07:12:35Z
================================================================================

Chore/Docs: authoritative catalog of all AudioMason prompts (defaults, config, CLI)

Goal
Create a single authoritative document that enumerates ALL prompts used by AudioMason.

This catalog will serve as:
- the definitive reference for users
- the authoritative source for future feature work
- a living document updated by future chats/issues

Scope of the catalog
The document MUST list every prompt, including:
- preflight prompts
- non-preflight prompts
- prompts that are currently hidden or only reachable in edge cases
- prompts that may no longer be shown by default but still exist in code

For EACH prompt, the catalog must include:
- unique prompt key / identifier
- human-readable question text
- phase (preflight / non-preflight / other)
- default value
- whether it is interactive by default
- config key(s) that control it (if any)
- CLI flag(s) that control it (if any)
- whether it can be disabled via prompt-control mechanisms
- deterministic behavior when disabled

File requirements
- The catalog must live in a dedicated file in the repository (exact path to be decided in the issue).
- The file is AUTHORITATIVE.
- Future chats and issues will rely on this file and update it incrementally.

Non-goals
- This issue does NOT change behavior.
- This issue does NOT add new prompts.
- This issue does NOT refactor code.

Acceptance criteria
- A single file exists that documents all AudioMason prompts.
- No known prompt is undocumented.
- Defaults, config options, and CLI mappings are explicit.
- The file can be safely referenced by future feature and bugfix issues.



================================================================================
ISSUE #82 – Feat: disable OpenLibrary suggestions via config and CLI
CLOSED AT: 2026-01-06T21:45:49Z
================================================================================

Disable OpenLibrary suggestions via config and CLI

Problem
AudioMason shows OpenLibrary suggestion prompts (author/book normalization) even when related preflight prompts are disabled.

Root cause
OpenLibrary prompts are implemented using prompt_yes_no(...) instead of preflight-aware helpers, so they ignore preflight_disable and non-interactive workflows.

Required solution
- Allow disabling OpenLibrary via config (e.g. openlibrary.enabled: false or lookup: false).
- Allow disabling OpenLibrary via CLI (e.g. --no-openlibrary / --no-lookup).
- CLI overrides config.

Acceptance criteria
- No OpenLibrary prompts or network calls when disabled.
- Existing behavior unchanged when enabled.

Scope
- Only add the ability to disable OpenLibrary.
- No normalization or UX changes when enabled.



================================================================================
ISSUE #81 – BUG: missing explicit per-source processing boundary blocks cross-cutting features
CLOSED AT: 2026-01-05T12:01:14Z
================================================================================

BUG: missing explicit per-source processing boundary in import_flow.py blocks cross-cutting features

Problem
The current `import_flow.py` does not define a clear, explicit boundary for "per-source processing".

The function `_run_one_source()` mixes:
- preparation
- user prompts
- processing logic
- error exits
- cleanup

into a single, branching control-flow with multiple early returns.

Because of this, it is not possible to safely:
- wrap the entire per-source execution in a single context
- introduce per-source features such as complete processing logs
- guarantee that such features cover the full lifecycle of a source

This limitation was discovered while implementing Issue #74
("save processing log to per-source file").

Why this is a blocker
Any attempt to add per-source cross-cutting features (logging, metrics,
timing, tracing, cancellation scopes) requires:
- a single, well-defined entry point
- a single, well-defined exit point

Without that boundary, implementations would be:
- partial
- heuristic
- or misleading to users

This refactor is therefore a design prerequisite, not a cosmetic change.

Scope (STRICT)
This issue must:
- Introduce an explicit per-source processing boundary, e.g.:
  - a dedicated helper such as `_process_one_source(...)`, or
  - an equivalent clearly defined wrapper
- Preserve existing behavior exactly
- Make no functional or UX changes
- Add no new features by itself

This issue must NOT:
- Change pipeline semantics
- Change prompts or CLI behavior
- Add logging or other cross-cutting features directly

Acceptance criteria
- There is a single, explicit function or block that represents
  "the full per-source processing lifecycle"
- `_run_one_source()` delegates actual processing to this boundary
- All existing tests pass without modification
- No user-visible behavior changes

Follow-up
Once this refactor is completed, Issue #74
("optional per-source processing log file")
can be implemented cleanly and deterministically.



================================================================================
ISSUE #80 – Fix: util.py has syntax error (unexpected indent)
CLOSED AT: 2026-01-06T05:36:28Z
================================================================================

Fix: util.py has syntax error (unexpected indent)

Summary
- `src/audiomason/util.py` is syntactically invalid Python and blocks:
  - importing `audiomason.util`
  - running tests
  - running patch scripts
  - any further development

Error
- Fails with:
  `IndentationError: unexpected indent` (around line ~62)

Root cause
- `util.py` contains top-level code with invalid indentation, e.g. an indented block like:
  - optional per-source log sink globals
  - helper functions
  - contextmanager `out_to_file(...)`
- This code is not inside any function/class/conditional, yet is indented, which is invalid at module top-level.

Important notes
- This is not a patch runner/test issue.
- This is not a regression caused by Issue #74.
- The bug exists in the authoritative repo state.
- Until fixed, no other issues can be worked on safely.

Scope of fix
- Fix indentation / placement in `src/audiomason/util.py` so the module parses/imports again.
- No behavior changes.
- No refactors.
- No new features.

Acceptance criteria
- `python -c "import audiomason.util"` succeeds.
- `python -m pytest -q` succeeds.



================================================================================
ISSUE #76 – Feat: global prompt disable (non-preflight + preflight)
CLOSED AT: 2026-01-07T23:24:31Z
================================================================================

Feat: global prompt disable (non-preflight + preflight)

Problem
- Dnes vieme deterministicky vypínať iba preflight otázky cez `preflight_disable` (Issue #67).
- Stále však existujú non-preflight interaktívne prompty, ktoré volajú priamo:
  - `prompt(...)`
  - `prompt_yes_no(...)`
  Príklady:
  - "Choose source number, or a for all"
  - "Choose book number, or a for all"
  - "Skip already processed books? [y/N]"
  - prípadne ďalšie prompty v import flow

Goal (authoritative)
- Zaviesť globálnu konfiguráciu, ktorá umožní vypnúť VŠETKY otázky (preflight + non-preflight) deterministicky.

Navrhovaný config
- Nový kľúč:
  prompts:
    disable:
      - "*"
- Význam:
  - ["*"] = vypne všetky interaktívne otázky počas celého behu
  - voliteľne: disable: [choose_source, choose_books, skip_processed_books, ...] pre selektívne vypnutie mimo preflightu

Required behavior
1) Config kľúč
- Zaviesť `prompts.disable` (list)
- Povoliť `*` pre disable-all

2) Determinizmus
- Ak je prompt vypnutý, musí sa vyriešiť deterministicky:
  - použiť existujúci default (rovnaký ako dnes), alebo
  - použiť uložené odpovede (manifest), ak je to relevantné, alebo
  - fail-fast, ak prompt nemá deterministické riešenie bez otázky

3) Fail-fast validácia (pred FS zmenami)
- `prompts.disable` musí byť list
- neznámy key -> chyba
- duplicity -> chyba
- `*` nesmie byť kombinované s ďalšími key (buď ["*"] alebo konkrétny zoznam)

4) Default správanie
- Ak `prompts.disable` nie je nastavené:
  - správanie musí zostať presne ako dnes

5) CLI vs config
- Ak existuje CLI ekvivalent (napr. `--prompts-disable`), CLI má prednosť pred configom.
- Ak CLI ešte neexistuje, minimálny scope môže byť iba config (deterministicky).

Scope (strict)
- Zmeny iba na:
  - globálne prompt disable mechanizmy
  - wrappery pre non-preflight prompty
  - validácia + testy
- Bez refaktorov mimo nutného, bez docs zmien, bez ďalších preflight features (order/disable/defaults/non-binary sú samostatné issues).

Minimal non-preflight prompt keys (initial proposal)
- choose_source -> "Choose source number, or a for all"
- choose_books -> "Choose book number, or a for all"
- skip_processed_books -> "Skip already processed books? [y/N]"
- plus všetky ďalšie prompty mimo preflightu po audite (`rg -n "\bprompt\(" src/audiomason` + `rg -n "\bprompt_yes_no\(" src/audiomason`)

Implementation strategy (authoritative)
- Zaviesť helpery (napr. v import_flow.py alebo v util module podľa existujúceho patternu):
  - `_resolved_prompt_disable(cfg) -> set[str]`
  - `_prompt_disabled_all(cfg) -> bool`
  - `_q_prompt(cfg, key, text, default) -> str`
  - `_q_prompt_yes_no(cfg, key, text, default_no) -> bool`
- Presmerovať non-preflight prompty na wrappery (posúvať `cfg` do výberových funkcií a call-sites).
- Zaviesť fail-fast validáciu na začiatku import flow (pred FS prácou).
- Pri `--debug` logovať preskočenie promptu:
  [TRACE] [prompt] disabled: <key> -> default: <value>

Acceptance criteria
- `prompts.disable: ["*"]` -> nespustí sa žiadna otázka (preflight ani non-preflight)
- `prompts.disable: [choose_source]` -> preskočí iba výber source (deterministicky default "1")
- `skip_processed_books` prompt sa dá vypnúť rovnako
- invalid config -> fail-fast s jasnou chybou
- default bez configu -> nezmenené správanie
- testy pokrývajú:
  - disable-all zamedzí volaniu prompt/prompt_yes_no
  - unknown key / duplicate / invalid type -> chyba



================================================================================
ISSUE #75 – BUG: nested sources collapse multiple books into one (should preserve folder structure)
CLOSED AT: 2026-01-04T21:58:16Z
================================================================================

BUG: Nested folder sources collapse multiple books into one (should treat each audio folder as separate book and preserve structure)

Repro A (nested source)
- Source is a directory with nested subdirectories, where the actual MP3/M4A folders are deeper:
  source/
    level1/
      level2/
        Book A/
          01.mp3 ...
        Book B/
          01.mp3 ...
- AudioMason currently treats all discovered audio files as a single book and exports them into one output folder.

Repro B (selecting all sources)
- When selecting a (all sources) from the inbox menu, similar collapsing happens: nested audio folders under selected sources may be treated as a single book.

Observed
- All MP3/M4A files found under a source are grouped as one book.
- Export output structure collapses into a single folder.

Expected
- AudioMason must treat **each directory that contains MP3/M4A** as a separate book root.
- For each such book root, process independently (preflight/book prompts per book as needed).
- Output must preserve the **relative directory structure** from the source:
  - If audio folder is nested 38 levels deep, the same relative nesting is preserved under the destination (deterministic, filesystem-safe).
- This must work both for:
  - a single selected source
  - selecting a (all sources)

Rules / constraints
- Deterministic discovery order (stable ordering).
- No cross-contamination of state between books.
- Filesystem-safe path mapping (no path traversal; normalized).

Acceptance criteria
- Given a nested source containing N distinct folders with MP3/M4A, AM processes N books (not 1).
- Destination mirrors the source’s relative path structure for each book folder.
- Works for both single source selection and a (all sources).
- Covered by tests:
  - discovery identifies multiple book roots under nested trees
  - export preserves relative directory structure
  - regression for a selection path (if relevant)

Notes
- This is required for large nested archives and batch imports.



================================================================================
ISSUE #74 – Feat: optional per-source processing log saved to file (CLI + config)
CLOSED AT: 2026-01-05T22:25:20Z
================================================================================

Feat: Optional per-source processing log saved to file

Goal
- Allow optional saving of processing logs to a file named after the processed source.

Behavior
- Feature is **disabled by default**.
- When enabled, AudioMason saves a log file for each processed source.
- Log filename is derived deterministically from the source name.

Configuration
- Feature must be configurable via:
  - CLI option
  - config file
- In both cases, user may specify:
  - only enable logging
  - enable logging + explicit output directory

Defaults
- If logging is enabled **without specifying a directory**:
  - log file is saved into the **stage directory**.
- If an explicit directory is provided:
  - log file is saved there.

CLI (example, final naming up to implementation)
- --log-to-file
- --log-to-file-dir <path>

Config (example, final naming up to implementation)
- log_to_file: true|false
- log_to_file_dir: <path>

Rules
- CLI options override config.
- Logging never changes stdout/stderr behavior (logs are additive).
- Each source gets its own log file (no shared logs).
- Log writing must be deterministic and append-safe.

Acceptance criteria
- Feature is off by default.
- Enabling logging creates one log file per source.
- File is named after the source in a deterministic, filesystem-safe way.
- Default location is stage directory if no path is provided.
- CLI overrides config.
- Covered by tests.

Notes
- Intended for later debugging, audits, and GUI/API integrations.



================================================================================
ISSUE #73 – Feat: support user-space config alongside /etc/audiomason/config.yaml
CLOSED AT: 2026-01-03T18:35:45Z
================================================================================

Problem
-------
AudioMason currently loads configuration only from a single system-wide path:
  /etc/audiomason/config.yaml

This causes friction for:
- non-root usage
- per-user customization
- development and testing

Example:
User has a valid config in user space:

  ~/.config/audiomason/config.yaml

with content like:
  clean_inbox: ask
  publish: ask
  wipe_id3: ask
  lookup: yes

but AudioMason ignores it unless --config is explicitly provided.

Goal
----
Allow AudioMason to load configuration from both system-wide and user-space locations,
with deterministic precedence and no ambiguity.

Proposed behavior (authoritative)
---------------------------------
1. Config discovery order (deterministic):
   1) --config <path>          (explicit override, highest priority)
   2) ~/.config/audiomason/config.yaml
   3) /etc/audiomason/config.yaml

2. Merge semantics:
   - Later configs override earlier ones
   - All merges must be shallow and deterministic
   - No implicit defaults beyond existing config defaults

3. Debug visibility:
   - When --debug is enabled, AudioMason must print:
       [config] loaded_from=[list of paths in order]
   - Must clearly show which values came from which file (if feasible without refactor)

4. Backward compatibility:
   - Existing installations relying on /etc/audiomason/config.yaml must keep working
   - No behavior change unless user-space config exists

Non-goals
---------
- No environment-variable-based config paths
- No interactive config editing
- No refactors unrelated to config loading

Constraints
-----------
- Deterministic behavior only
- Fail-fast on invalid YAML
- Covered by tests
- Must follow mandatory patch-script rule:
    tools/patches/issue_<N>.py
    idempotent, fail-fast, post-assert
- Issue must NOT be auto-closed

Status
------
Feature request.



================================================================================
ISSUE #72 – Feat: always display AudioMason version (CLI + config)
CLOSED AT: 2026-01-03T19:27:03Z
================================================================================

Problem
-------
AudioMason currently does not reliably display its version unless explicitly invoked with --version.
In practice:
- `am` starts interactive mode without showing version
- `am --debug` shows config/path info, but version visibility is inconsistent
- There is no config-level control for version visibility

Goal
----
Make AudioMason version visibility explicit, deterministic, and configurable.

Requirements
------------
1. CLI behavior
   - On startup, AudioMason should be able to display its version banner
   - Version display must be deterministic and not depend on accidental flags

2. Config support
   - New config option, e.g.:
       show_version: always | never | debug
   - Default must preserve current behavior (no breaking change)

3. Interaction rules
   - show_version: always
       - version is printed on every run (before any prompts)
   - show_version: debug
       - version is printed only when --debug is active
   - show_version: never
       - version is never printed automatically

4. Output rules
   - Version output must be single-line, stable, machine-readable friendly
   - Example:
       AudioMason 1.2.0b2

Non-goals
---------
- No changes to packaging versioning
- No changes to semantic version format
- No unrelated CLI refactors

Constraints
-----------
- Deterministic behavior only
- Config + CLI override rules must be explicit
- Covered by tests
- Must follow patch-script rule:
    tools/patches/issue_<N>.py
    idempotent, fail-fast, post-assert

Status
------
Feature request. Issue must NOT be auto-closed.



================================================================================
ISSUE #71 – Chore: document mandatory deterministic patch-script workflow
CLOSED AT: 2026-01-05T22:29:58Z
================================================================================

Chore: Document mandatory deterministic patch-script workflow for development

Goal
- Formally document the mandatory patching workflow using deterministic Python edit scripts.

Background
- Diff-based patches frequently fail due to context drift.
- The project now mandates a single, robust patching method based on Python edit scripts
  with anchor checks, idempotency, and fail-fast behavior.

Scope
- Update developer documentation to define:
  - Mandatory use of Python edit scripts for all code changes
  - Standard location: tools/patches/issue_XX.py
  - Required properties:
    - anchor checks
    - idempotency
    - fail-fast behavior
    - post-edit assertions
  - Forbidden practices:
    - diff patches
    - manual edits
    - heredoc-based scripts
- Document the required end-to-end workflow:
  edit → pytest → git add → commit → push
- Explicitly state that patches must be written only against authoritative files
  provided by the user.

Acceptance criteria
- Developer documentation clearly describes the required patch workflow.
- Rules are unambiguous and enforceable.
- No behavioral or runtime code changes.

Notes
- This documents an already-adopted rule set; it does not introduce new functionality.



================================================================================
ISSUE #70 – BUG: selecting 'a' (all sources) treats multiple sources as one author
CLOSED AT: 2026-01-05T02:02:20Z
================================================================================

BUG: Choosing a (all sources) in inbox menu is treated as a single author

Repro
1) Run: am
2) At inbox menu, enter: a
3) AudioMason then proceeds as if all selected sources belong to one author (single author flow).

Observed
- After selecting a, AM behaves as if it has one combined author/source, instead of processing each source independently.

Expected
- Selecting a should process sources one-by-one, in a deterministic order:
  - For each selected source, ask author name (and other per-source/book questions) separately.
  - No cross-contamination of author/title answers between sources.

Scope / likely area
- Inbox source selection handling and the loop that dispatches per-source import runs.

Acceptance criteria
- a expands to a list of sources and triggers the same per-source flow as selecting them individually.
- Prompts are repeated per source (author name, etc.) rather than once for the whole batch.
- Order is deterministic (e.g., menu order).
- Covered by tests:
  - Selecting a results in N independent source processing iterations.
  - Each source gets its own author prompt / state.

Notes
- This is required for correct multi-source imports and future GUI/Remote API batching.

---

Additional bug: incorrect phase ordering when selecting all sources

Observed behavior
- When selecting all sources using input "a" / "A", AudioMason executes:
  (preflight for source 1) -> (process source 1) -> (preflight for source 2) -> (process source 2) -> ...

Expected behavior
- When selecting all sources, AudioMason must:
  - run preflight for all selected sources first (one by one, collecting decisions)
  - only after all preflights complete, start processing for all sources

Rationale
- Ensures deterministic batch decisions before any processing starts
- Prevents partial processing when later sources would lead to different preflight outcomes
- Aligns with phase separation principles already present in the pipeline

Acceptance criteria
- With "a" / "A" selection:
  - no processing occurs until preflight has completed for all sources
  - processing starts only after the last preflight finishes



================================================================================
ISSUE #67 – Feat: disable selected preflight questions (deterministic skip + fail-fast)
CLOSED AT: 2026-01-05T22:36:19Z
================================================================================

Feat: Disable selected preflight questions (skip prompts deterministically)

Goal
- Allow users to disable (skip) specific preflight questions/prompts in a deterministic, configurable way.

Problem
- Preflight currently prompts for multiple decisions.
- For automation, power users, and future GUI/Remote API, some questions must be suppressible:
  - either because defaults are desired
  - or because the decision is provided elsewhere (CLI/config/request)

Scope
- Add configuration to disable a set of preflight questions (e.g. `preflight_disable` list).
- Disabled questions must:
  - not be prompted
  - resolve deterministically via defaults / config / CLI options
- Fail-fast rules:
  - If a disabled question has no deterministic resolution (no default / config / CLI), error out before any filesystem changes.
  - Unknown question keys -> error.
- Defaults:
  - Nothing disabled by default (preserve current behavior).

Acceptance criteria
- User can disable one or more preflight questions via config.
- Disabled questions are not prompted.
- Runs remain deterministic.
- Missing required deterministic value for a disabled prompt -> fail fast with clear error.
- Covered by tests.



================================================================================
ISSUE #65 – Feat: inbox cleanup control (prompt + CLI option, deterministic)
CLOSED AT: 2026-01-03T17:56:31Z
================================================================================

Feat: Inbox cleanup option (prompt + CLI configurable)

Goal
- Allow controlled cleanup of the inbox directory after a successful import.

Problem
- Today, inbox cleanup behavior is implicit or inconsistent.
- User wants:
  - an explicit question (interactive mode)
  - a deterministic CLI option (non-interactive / automation / GUI)

Scope
- Introduce a clear inbox cleanup decision with three modes:
  - ask      -> prompt user after successful import
  - yes      -> always clean inbox after successful import
  - no       -> never clean inbox
- Expose this via:
  - CLI flag (e.g. --clean-inbox={ask,yes,no})
  - config default (if CLI flag not provided)
- Ensure behavior is:
  - fail-safe (never deletes on failed import)
  - deterministic
  - testable

Acceptance criteria
- Interactive CLI:
  - user is explicitly asked whether to clean inbox (only on success)
- Non-interactive CLI:
  - --clean-inbox=yes cleans inbox automatically after success
  - --clean-inbox=no skips cleanup
- Missing decision in non-interactive mode -> fail fast with clear error
- Behavior covered by tests
- No change to existing defaults unless explicitly configured

Notes
- Required for future GUI / Remote API integration.



================================================================================
ISSUE #57 – CI: tests fail without /etc/audiomason/config.yaml in editable install
CLOSED AT: 2026-01-02T16:39:32Z
================================================================================

Problem:
- GitHub Actions runs tests after an editable install (pip install -e .)
- CLI arg parsing loads config, and load_config() requires /etc/audiomason/config.yaml
- CI environment does not have this file, so pytest fails early

Fix:
- CI now ensures /etc/audiomason/config.yaml exists before running pytest (uses debian/config.yaml)

Result:
- CI green again

Commits:
- 169fa0e CI: ensure /etc/audiomason/config.yaml exists for pytest


================================================================================
ISSUE #56 – BUG: clean install tries to mkdir under /etc/audiomason (PermissionError)
CLOSED AT: 2026-01-02T15:42:05Z
================================================================================

On a clean .deb install, running `audiomason` could attempt to create inbox/stage/output under `/etc/audiomason/*`, causing:

PermissionError: [Errno 13] Permission denied: '/etc/audiomason/abooksinbox'

Expected:
- Clean install must use user-safe defaults under ~/.local/share/audiomason unless configured paths are provided.

Fix:
- Accept *_root aliases in paths resolvers.
- Make default data base user-safe and align tests to AUDIOMASON_DATA_ROOT.

Verification:
- `audiomason --debug` shows mkdir under ~/.local/share/audiomason and inbox empty (no PermissionError).



================================================================================
ISSUE #55 – BUG: existing MP3 embedded cover lost after wipe (not preserved to cover.jpg)
CLOSED AT: 2026-01-01T22:47:19Z
================================================================================

Problem
When input MP3 files already contain embedded cover art, AudioMason performs ID3 wipe before preserving the cover. As a result, cover art is lost and the output MP3s end up without a cover.

Observed
- Input MP3s had cover art embedded
- AudioMason wiped ID3 tags
- AudioMason did NOT first persist the embedded cover to cover.jpg (or otherwise preserve it)
- Output MP3s do not include cover art

Rule / Expected behavior
- If MP3 already has an embedded cover, AudioMason MUST preserve it across wipe.
- It does NOT need to extract it to cover.jpg before wipe (optional), but it must not lose it.
- Minimal acceptable fix: if embedded cover is detected, keep/apply it after wipe automatically.

Acceptance
- Given MP3s with embedded cover and wipe enabled:
  - output MP3s still contain cover art
  - no requirement for cover.jpg to be created unless needed by pipeline

Notes
- This is separate from preflight cover selection; this is about preservation of existing embedded art when wiping tags.
- Likely fix location: processing step order around wipe_id3 vs cover selection/application.

Environment
- AudioMason main branch
- Python 3.11
- Run inside venv



================================================================================
ISSUE #54 – BUG: NameError in validate_author after OL suggestion sanitize (undefined variable t)
CLOSED AT: 2026-01-01T22:40:23Z
================================================================================

Problem
AudioMason crashes with NameError during author validation after the OpenLibrary suggestion sanitize change (#53).

Observed crash:
NameError: name 't' is not defined

Traceback (abridged):
File "src/audiomason/openlibrary.py", line 123, in validate_author
    top = _sanitize_title_suggestion(t, top)
NameError: name 't' is not defined

Repro
- Run am
- Proceed through import
- At author prompt, enter an author name
- Validation crashes immediately

Observed
- Application terminates with NameError
- Happens in validate_author(), where variable 't' does not exist

Expected
- Author validation must not reference undefined variables
- OpenLibrary sanitize logic should only apply where correct context (book title vs author) exists
- No crash during author validation

Notes
- Regression introduced by Issue #53 fix (OpenLibrary title suggestion sanitization)
- validate_author() should not use book-title variables
- Likely fix: remove or adjust sanitize call in validate_author()

Environment
- AudioMason main branch
- Python 3.11
- Run inside venv



================================================================================
ISSUE #53 – BUG: OpenLibrary title suggestions must be de-diacritized before prompting
CLOSED AT: 2026-01-01T22:30:29Z
================================================================================

Problem
AudioMason currently offers OpenLibrary book title suggestions that contain diacritics, even though the project explicitly rejects diacritics in titles.

Example:
[ol] book title suggestion: 'Vychovavame deti a rosteme s nimi' -> 'Vychováváme děti a rosteme s nimi'
Prompt:
Use suggested book title 'Vychováváme děti a rosteme s nimi'?

Observed
- Suggested title contains diacritics
- User is prompted to accept a title that violates AudioMason naming rules

Expected
- Any OpenLibrary-suggested title must be normalized to ASCII (no diacritics) *before* being presented to the user
- Example expected suggestion:
  'Vychovavame deti a rosteme s nimi'
- Prompt must never offer a diacritics-containing string

Notes
- This applies to OpenLibrary title suggestions only
- De-diacritization should be deterministic and consistent with existing AM normalization rules
- No change to matching/scoring logic required; only the presented suggestion

Environment
- AudioMason main branch
- Python 3.11
- Run inside venv



================================================================================
ISSUE #52 – BUG: stage copy starts without informing user (no [stage]/[copy] progress)
CLOSED AT: 2026-01-01T22:11:37Z
================================================================================

Problem
After selecting a source, AudioMason begins copying data into the stage directory (when the stage does not already exist), but it does not inform the user that copying has started. This is confusing on slow hardware (Raspberry Pi 4B), as the CLI appears idle.

Repro
- Run am
- Select a source
- When no existing stage is present for that source, AudioMason copies source data into stage
- User sees no explicit log line indicating the copy phase/progress started

Observed
- Copy happens silently (no clear "[stage] copy ..." or similar)
- On large sources this looks like a hang

Expected
- Before copying begins, print a clear message, e.g.:
  - "[stage] copying source into stage..."
  - include src path and stage path
- Ideally, provide minimal progress info (file count or per-dir messages), but at minimum one explicit start line is required
- Must respect --quiet / --dry-run behavior as appropriate

Notes
- This is about user feedback/visibility; copy behavior itself is correct
- Particularly important on CPU/I/O constrained systems

Environment
- AudioMason main branch
- Raspberry Pi 4B
- Python 3.11
- Run inside venv



================================================================================
ISSUE #51 – BUG: processed book directories not added to ignore; reappear in next run
CLOSED AT: 2026-01-01T22:02:24Z
================================================================================

Problem
After a successful book import, AudioMason does not add the processed book directory to the ignore list. As a result, the same directories are shown again as candidates in subsequent runs.

Repro
- Run am import
- Successfully process one or more books
- Stage cleanup may occur correctly
- Run am again on the same inbox root

Observed
- Already processed book directories are listed again as selectable sources/books

Expected
- After successful processing, AudioMason should mark processed content as ignored
- Minimal acceptable behavior: add the MAIN processed directory (book root) to ignore
- Ignored directories must not be listed in subsequent runs

Notes
- This is not about stage cleanup (already fixed in #50)
- Applies after successful import only
- Deterministic behavior required (no silent reprocessing)
- Likely related to ignore handling after FINALIZE

Environment
- AudioMason main branch
- Python 3.11
- Run inside venv
- Real data



================================================================================
ISSUE #50 – BUG: stage not cleaned after successful import despite confirmation
CLOSED AT: 2026-01-01T21:53:31Z
================================================================================

Problem
Stage directory is not cleaned after a successful import, even when the user confirms cleanup.

Repro (interactive run):
- Choose source with existing stage
- Reuse existing staged source? -> Y
- Use saved answers? -> N
- Clean stage after successful import? -> (Yes / default)
- Import completes successfully (PROCESS + FINALIZE)

Observed
- Stage directory remains on disk
- No error or warning is shown
- FINALIZE phase completes, but stage is not removed

Expected
- If user confirms "Clean stage after successful import?", the stage directory must be deleted after FINALIZE
- Behavior should be deterministic and explicit

Notes
- This is NOT a dry-run
- Import finished successfully
- Likely regression or missing hook in FINALIZE phase
- Related to stage reuse / crash-resume logic

Full log excerpt (abridged):
[stage] Reuse existing staged source? [Y/n] y
[manifest] Use saved answers (skip prompts)? [Y/n] n
...
Clean stage after successful import? [Y/n]
...
[phase] FINALIZE
(stage still exists)

Environment
- AudioMason main branch
- Python 3.11
- Run inside venv
- Real data (Asimov.Isaac, multiple books)



================================================================================
ISSUE #49 – BUG: crash when downloading cover URL (duplicate check=True in run_cmd)
CLOSED AT: 2026-01-01T20:29:37Z
================================================================================

Repro:
- Interactive run with cover prompt
- Select URL cover
- App crashes with:
  TypeError: subprocess.run() got multiple values for keyword argument 'check'

Traceback ends at:
- audiomason/covers.py: download_url()
- run_cmd([...], check=True)
- util.run_cmd() already passes check=True internally

Root cause:
- check=True is passed twice to subprocess.run()

Expected:
- URL cover downloads without crash

Scope:
- src/audiomason/covers.py
- Remove explicit check=True from run_cmd() call

Notes:
- Found while testing Issue #48 (cover prompt behavior)
- Issue #48 remains OPEN



================================================================================
ISSUE #48 – BUG: Cover silently skipped due to sticky manifest cover_mode and skip default
CLOSED AT: 2026-01-01T20:32:02Z
================================================================================

Cover handling has a UX/behavior bug independent of pipeline_steps.

Observed:
- Stage manifest can contain book_meta.__ROOT_AUDIO__.cover_mode = "skip"
- Even when selecting "Use saved answers? n", cover remains silently skipped.
- If cover_mode key is deleted from manifest, behavior still defaults to skip (no prompt) when prompts are enabled.
- Result: cover step executes but does not prompt and logs "[cover] skipped".

Expected:
- Selecting "Use saved answers? n" should clear cover_mode decisions (or at least cover decisions).
- When prompts are enabled, missing cover_mode should default to asking (not silent skip).
- Provide an explicit mechanism to reset/override cover decision (config flag or CLI switch).

Notes:
- Discovered during validation of issue #20.
- Intentionally split out to keep pipeline_steps issue clean and closed.



================================================================================
ISSUE #47 – Packaging: provide .deb package for system-wide install
CLOSED AT: 2026-01-02T01:54:42Z
================================================================================

Problem
- AudioMason is currently installed via editable pip / venv only.
- There is no system-native package for easy installation, upgrade, or removal.

Goal
- Provide an optional .deb package for Debian-based systems (Debian, Ubuntu, Raspberry Pi OS).
- This is low priority (P2) and not required for core functionality.

Requirements
- Build a .deb package that:
  - installs audiomason CLI system-wide (read-only)
  - does NOT assume writable system paths at runtime
  - respects existing config model (AUDIOMASON_ROOT / configuration.yaml)
- No daemon, no systemd service.
- Packaging only; runtime behavior unchanged.

Notes / constraints
- Likely approaches:
  - setuptools + debhelper
  - fpm-based packaging
  - or simple dpkg-deb wrapper
- Must not break venv-based development workflow.

Acceptance
- .deb can be built reproducibly.
- Installing the package provides the 'audiomason' command.
- Uninstall cleanly removes files.



================================================================================
ISSUE #46 – Covers: add cache GC / cleanup for disk cover cache
CLOSED AT: 2026-01-01T21:16:50Z
================================================================================

Problem
- Disk cover cache can grow unbounded over time.
- There is no built-in way to prune old/unused entries.

Requirements (pick one or combine)
- Add a GC/cleanup mechanism for disk cache, with deterministic and safe defaults.
- Options:
  A) Command: am cache gc [--days N] [--max-mb M] [--dry-run]
  B) Config-based policy: cover.cache_gc (days/max_mb/off)
- Must respect:
  - --dry-run (report only)
  - --debug (log what would be removed / why)
- Safety:
  - never delete outside the configured cache dir
  - only delete known cache files

Acceptance
- User can reduce cache size deterministically.
- Dry-run shows exactly what would be removed.



================================================================================
ISSUE #45 – Covers: detect MIME and store cached covers with correct extension (.jpg/.png/.webp)
CLOSED AT: 2026-01-01T17:37:49Z
================================================================================

Problem
- Disk cover cache currently stores downloads as .img, losing the original content-type/extension.
- This makes cache harder to inspect/debug and can break downstream tooling that expects correct extensions.

Requirements
- Detect MIME type of downloaded cover bytes (or via HTTP headers where available).
- Store cache files with correct extension:
  - image/jpeg -> .jpg
  - image/png  -> .png
  - image/webp -> .webp
  - fallback -> .img
- Deterministic mapping:
  - same URL + same bytes => same cached filename (stable).
- Respect:
  - --dry-run (no writes)
  - --debug (log detected MIME + chosen extension)

Acceptance
- Existing behavior unchanged unless cache=disk is enabled.
- Disk cache files become human-friendly and correctly typed.



================================================================================
ISSUE #44 – Config: allow --config / CWD configuration.yaml and show loaded_from under --debug
CLOSED AT: 2026-01-01T15:18:12Z
================================================================================

Problem
- It is currently not possible to reliably test AudioMason with a throwaway configuration in a temporary working directory.
- Running from a temp dir containing configuration.yaml still loads the "real" config/defaults (e.g. inbox stays /mnt/warez/abooksinbox).
- load_config() does not expose which file was loaded ("loaded_from" is unknown), so this is hard to verify/debug.

Repro
1) Create a temp config and run am from that temp dir:

TMP=$(mktemp -d)
cat >"$TMP/configuration.yaml" <<'YAML'
publish: no
split_chapters: true
paths:
  inbox:  /tmp/am_inbox
  stage:  /tmp/am_stage
  output: /tmp/am_output
  archive:/tmp/am_archive
  cache:  /tmp/am_cache
ffmpeg:
  loglevel: error
  loudnorm: false
  q_a: "4"
YAML
mkdir -p /tmp/am_inbox /tmp/am_stage /tmp/am_output /tmp/am_archive /tmp/am_cache
cd "$TMP"
am --dry-run

Expected
- Config discovery should be deterministic and test-friendly:
  - Either respect configuration.yaml in the current working directory, OR
  - Provide a --config /path/to/configuration.yaml flag to force a specific file.
- Under --debug (or equivalent), print which config file was loaded, e.g.:
  [config] loaded_from=/path/to/configuration.yaml

Actual
- am --dry-run still reads sources from the real inbox (e.g. /mnt/warez/abooksinbox).
- load_config() provides no reliable "loaded_from" info (shows unknown), so the active config source cannot be verified.

Scope / acceptance criteria
- Add a deterministic way to select config:
  - Option A: search order includes CWD/configuration.yaml (documented), OR
  - Option B: implement --config PATH that overrides discovery.
- Add "loaded_from" visibility:
  - Print loaded_from under --debug, and/or
  - Store loaded_from in cfg (or a module-level var) for programmatic inspection.
- Update README with the discovery/override behavior.

Notes
- This blocks reliable isolated testing and makes troubleshooting configuration issues harder.



================================================================================
ISSUE #43 – FEATURE: choose/add cover during preflight (no cover prompts in processing)
CLOSED AT: 2026-01-01T21:04:40Z
================================================================================

### Problem

Cover selection currently happens in the processing phase via `choose_cover(...)`. This clashes with the project rule that processing should not prompt (see the existing preflight/processing separation). In practice, when no embedded/file cover is detected in preflight, `cover_mode` becomes `"skip"` and processing prints `[cover] skipped`, even though the user could supply a URL/path at that time.

Example observed flow:
- preflight sets `cover_mode = "skip"` when no cover is detected
- processing phase calls `choose_cover(..., mode="skip")` and never asks for a URL/path
- result: `[cover] skipped`

### Goal

Move **all cover decisions and user interaction** into **preflight** so that:
- processing phase never prompts
- cover never gets silently skipped when the user could provide one
- crash-resume can reuse the selected cover deterministically

### Requirements

1) Preflight must determine a final cover input for each book:
- `embedded` (from audio) OR
- `file` (existing cover file) OR
- `url` (download + cached file) OR
- `path` (user-supplied local file path) OR
- explicit `skip`

2) Preflight prompts:
- If a cover is detected (embedded/file), allow confirm/override/skip.
- If no cover is detected, prompt the user for:
  - URL (http/https) OR
  - local file path OR
  - skip

3) Processing phase:
- Must only apply the preflight decision (no prompts).
- Must not call interactive cover selection.
- Must print a single concise line indicating which cover was used (embedded/file/url/path/skip).

4) Persistence / resume:
- Store the chosen cover decision in stage/manifest so crash-resume reuses it without prompting.
- If cover is URL, store the cached file path (or the URL + cache key) so it is deterministic.

5) Config integration:
- URL cover downloads must use the configured cache root (`paths.cache`) if set.

### Acceptance Criteria

- Running `am import` with a book that has no cover:
  - preflight asks once for cover URL/path/skip
  - processing never prompts and does not output `[cover] skipped` unless the user chose skip
- Re-running after crash or stage reuse:
  - no cover prompt repeats if manifest already contains the decision
- Tests added/updated for:
  - preflight cover decision persistence
  - processing uses preflight decision
  - URL cover uses configured cache root

### Notes

This change is meant to align cover handling with the preflight/processing contract and improve deterministic resume behavior.



================================================================================
ISSUE #42 – CLI: replace expected tracebacks with human-readable exits
CLOSED AT: 2026-01-01T13:47:39Z
================================================================================

### Problem\n\nCurrently, AudioMason prints Python tracebacks for many *expected* termination scenarios (invalid configuration, missing external tools, validation failures, user abort via Ctrl+C). This is noisy, user-unfriendly, and not aligned with a CLI tool intended to run on constrained systems (e.g. Raspberry Pi) or by non-developers.\n\nTracebacks should be reserved **only** for genuine programmer bugs (unexpected exceptions).\n\n---\n\n### Goal\n\nDefine and enforce a strict CLI contract:\n\n- **No tracebacks for expected exits**\n- Always show a **single, human-readable message** explaining *why* the program exited\n- Deterministic exit codes\n- Centralized handling in CLI entrypoint\n\n---\n\n### Proposed Design\n\n#### 1. Controlled exit exception hierarchy\n\nIntroduce a small set of explicit exit exceptions:\n\n\n\n- No printing inside exceptions\n- Message only\n\n---\n\n#### 2. Single catch point in cli.main()\n\n\n\n- No other broad excepts elsewhere\n\n---\n\n#### 3. KeyboardInterrupt handling\n\n\n\n---\n\n#### 4. Replace raw RuntimeError usage\n\nAll expected failures must raise an appropriate  subclass instead of raw RuntimeError / ValueError:\n\n- config load / validation\n- paths contract enforcement\n- verify failures\n- missing external tools (ffmpeg, unzip, 7z, unrar)\n\n---\n\n### User-visible behavior\n\n**Invalid config**\n\n\n**Missing external tool**\n\n\n**Ctrl+C**\n\n\n**Real bug**\n\n\n---\n\n### Acceptance Criteria\n\n- No Python tracebacks for expected termination paths\n- All expected exits go through AmExit hierarchy\n- Single catch point in CLI\n- Tracebacks remain for unexpected bugs only\n- Covered by tests where applicable\n\n---\n\n### Notes\n\nThis is a CLI UX contract change and should be treated as a foundational behavior guarantee.


================================================================================
ISSUE #41 – CLI: replace expected tracebacks with human-readable exits
CLOSED AT: 2026-01-01T18:39:55Z
================================================================================

### Problem

Currently, AudioMason prints Python tracebacks for many expected termination scenarios (invalid configuration, missing external tools, validation failures, user abort via Ctrl+C). This is noisy and user-unfriendly. Tracebacks should be reserved only for genuine programmer bugs (unexpected exceptions).

---

### Goal

Define and enforce a strict CLI contract:

- No tracebacks for expected exits
- Always show a single, human-readable message explaining why the program exited
- Deterministic exit codes
- Centralized handling in CLI entrypoint

---

### Proposed Design

#### 1) Controlled exit exception hierarchy

Introduce explicit exit exceptions:

Example:

class AmExit(RuntimeError):
    exit_code = 1

class AmConfigError(AmExit):
    pass

class AmValidationError(AmExit):
    pass

class AmExternalToolError(AmExit):
    pass

class AmAbort(AmExit):
    exit_code = 130  # Ctrl+C

Notes:
- No printing inside exceptions
- Message only

---

#### 2) Single catch point in cli.main()

Example:

try:
    ...
except AmAbort as e:
    out(f"[abort] {e}")
    return e.exit_code
except AmExit as e:
    out(f"[error] {e}")
    return e.exit_code

- No other broad excepts elsewhere

---

#### 3) KeyboardInterrupt handling

Example:

except KeyboardInterrupt:
    raise AmAbort("cancelled by user")

---

#### 4) Replace raw RuntimeError usage

All expected failures must raise an appropriate AmExit subclass instead of raw RuntimeError / ValueError:

- config load / validation
- paths contract enforcement
- verify failures
- missing external tools (ffmpeg, unzip, 7z, unrar)

---

### User-visible behavior

Invalid config:
[error] Invalid configuration: paths must be a mapping

Missing external tool:
[error] Missing external tool: ffmpeg (install ffmpeg)

Ctrl+C:
[abort] cancelled by user

Real bug:
Traceback (most recent call last):
  ...

---

### Acceptance Criteria

- No Python tracebacks for expected termination paths
- All expected exits go through AmExit hierarchy
- Single catch point in CLI
- Tracebacks remain for unexpected bugs only
- Covered by tests where applicable

---

### Notes

This is a CLI UX contract change and should be treated as a foundational behavior guarantee.



================================================================================
ISSUE #40 – Docs: README configuration section out of sync with current contract
CLOSED AT: 2026-01-01T13:32:05Z
================================================================================

Audit finding: README still references legacy config discovery (/etc, ~/.config) and outdated key layout.\n\nAcceptance:\n- document AUDIOMASON_ROOT resolution\n- only /configuration.yaml\n- examples match real schema


================================================================================
ISSUE #39 – BUG: paths._get swallows exceptions and hides config errors
CLOSED AT: 2026-01-01T13:45:50Z
================================================================================

Audit finding: src/audiomason/paths.py has 'except Exception: pass' when reading cfg.\n\nThis violates fail-fast contract.\n\nAcceptance:\n- remove broad exception swallowing\n- raise clear RuntimeError with context\n- tests for malformed config


================================================================================
ISSUE #38 – BUG: mixed print/input bypasses quiet/debug UX contract
CLOSED AT: 2026-01-01T14:00:48Z
================================================================================

Audit finding: import_flow.py and covers.py mix raw print/input with audiomason.util out/prompt.\n\nImpact:\n- --quiet / --debug not consistently respected\n\nAcceptance:\n- all interaction via util wrappers\n- uniform UX behavior


================================================================================
ISSUE #37 – BUG: missing external archive tools cause raw FileNotFoundError
CLOSED AT: 2026-01-01T14:06:08Z
================================================================================

Audit finding: src/audiomason/archives.py raises FileNotFoundError when unzip/7z/unrar is missing.\n\nExpected:\n- fail-fast with clear error message\n- name missing tool + hint\n\nAcceptance:\n- explicit detection\n- readable RuntimeError


================================================================================
ISSUE #36 – BUG: cover cache path ignores configuration.yaml (CACHE_ROOT constant used)
CLOSED AT: 2026-01-01T14:45:47Z
================================================================================

Audit finding: src/audiomason/covers.py uses CACHE_ROOT constant instead of resolving cache root from cfg.\n\nImpact:\n- paths.cache is ignored\n\nAcceptance:\n- cache root resolved from cfg\n- test verifies configured cache path


================================================================================
ISSUE #35 – BUG: configuration key mismatch across config, CLI, and README
CLOSED AT: 2026-01-01T15:08:10Z
================================================================================

Audit finding: config keys differ between src/audiomason/config.py defaults, cli lookups, and README examples (publish, ffmpeg, audio).\n\nImpact:\n- configuration.yaml values may be ignored\n\nAcceptance:\n- single canonical schema\n- CLI + defaults + docs aligned\n- tests cover config parsing


================================================================================
ISSUE #34 – BUG: verify checks wrong directory level (author dirs treated as books)
CLOSED AT: 2026-01-01T16:45:00Z
================================================================================

Audit finding: src/audiomason/verify.py iterates immediate subdirs of root as books, but canonical layout is Author/Book.\n\nImpact:\n- false verify failures\n- real books may be skipped\n\nAcceptance:\n- verify walks Author -> Book\n- tests updated


================================================================================
ISSUE #33 – Hardcoded filesystem paths audit & cleanup
CLOSED AT: 2026-01-01T13:19:23Z
================================================================================

Audit and cleanup of hardcoded filesystem paths across AudioMason.

Scope:
- Removed absolute hardcoded paths (/mnt, /etc, cwd fallbacks)
- Introduced strict path resolution via configuration.yaml
- Separated app root (AUDIOMASON_ROOT) from data roots
- Updated tests and legacy code

Result:
- No hardcoded filesystem paths remain in active code
- Verified via ripgrep audit

This issue documents the cleanup and is closed after verification.


================================================================================
ISSUE #32 – BUG: explicit 'am import <PATH>' must bypass ignore list
CLOSED AT: 2026-01-01T10:57:36Z
================================================================================

When a concrete source PATH is provided on CLI (am import <PATH>), the import must process it regardless of ignore rules. Ignore list should apply only to interactive DROP_ROOT listings.


================================================================================
ISSUE #31 – FEATURE: Google Books fallback for localized (CZ/SK) title suggestions
CLOSED AT: 2026-01-01T10:02:11Z
================================================================================

Goal:\n- When OpenLibrary returns only EN titles or no localized editions, query Google Books Volumes API for localized (CZ/SK) title suggestions.\n\nRules:\n- Deterministic behavior only.\n- Prompt-only (no silent overwrites).\n- Safe-by-default (threshold + gap).\n- Must respect --no-lookup.\n- Must not write any cache in --dry-run.\n\nAcceptance:\n- CZ/SK typo title can trigger CZ/SK suggestion when strong match exists.\n- Weak/ambiguous matches produce no suggestion.\n- Correct author+title stays silent.


================================================================================
ISSUE #30 – FEATURE: Google Books fallback for localized (CZ/SK) title suggestions
CLOSED AT: 2026-01-01T10:31:43Z
================================================================================

Goal:\n- When user-entered title looks CZ/SK but OpenLibrary suggests only EN (or no localized editions), query Google Books Volumes API for candidate titles.\n- Deterministic, prompt-only, safe-by-default threshold+gap.\n- Respect --no-lookup.\n- No network/cache writes in --dry-run.\n\nAcceptance:\n- CZ typo title can trigger CZ suggestion when strong match exists.\n- Weak/ambiguous => no suggestion.\n- Correct author+title stays silent.


================================================================================
ISSUE #29 – FEATURE: prefer CZ/SK edition titles for OpenLibrary book suggestions
CLOSED AT: 2026-01-01T10:00:27Z
================================================================================

Problem: /search.json returns work-level 'title' (often English) even when using language:cze/slo filters. We want suggestions in Czech/Slovak when available.\n\nGoal:\n- When offering a guarded book title suggestion, prefer edition titles in CZ/SK.\n- Strategy: after selecting best matching work candidate, fetch editions for that work and pick an edition title where language includes 'cze' or 'slo' (prefer cze then slo, or configurable later).\n- Still deterministic, prompt-only (no silent overwrites), safe-by-default.\n- Must respect --no-lookup.\n- Must not write OL cache in --dry-run.\n\nAcceptance:\n- For Douglas Adams query, suggestion offered as Czech title when Czech edition exists.\n- If only English exists, fall back to current behavior.\n- If ambiguous/low confidence, offer nothing.


================================================================================
ISSUE #28 – BUG: import should accept source path as CLI argument
CLOSED AT: 2026-01-01T10:39:16Z
================================================================================

am import currently rejects a positional source path with 'unrecognized arguments'. Expected: allow 'am import /path/to/source' while keeping current interactive behavior when no path is provided. Must respect --dry-run and --lookup/--no-lookup. Needed for scripting and testing.


================================================================================
ISSUE #27 – FEATURE: guarded fuzzy suggestions for book titles (OpenLibrary)
CLOSED AT: 2026-01-01T11:04:49Z
================================================================================

Goal:
- When lookup is enabled and validate_book(author,title) returns not_found with no top suggestion, offer a guarded closest-title suggestion.

Rules (non-negotiable):
- Deterministic behavior only.
- No silent overwrites: always prompt to accept suggestion.
- Safe-by-default: if confidence is low, offer nothing.
- Must respect --no-lookup.
- Must not write OpenLibrary cache in --dry-run.

Proposed approach:
- On book not_found: secondary OpenLibrary search constrained by author.
- Score candidate titles vs entered title (e.g. SequenceMatcher).
- Suggest only if score >= conservative threshold.

Acceptance criteria:
- Typo title triggers suggestion prompt when strong match exists.
- Weak/ambiguous matches produce no suggestion.
- Correct author+title stays silent.
- --no-lookup disables everything.


================================================================================
ISSUE #26 – FEATURE: preflight prompt to clean stage at end
CLOSED AT: 2025-12-31T18:41:23Z
================================================================================

Request:
- During preflight, ask whether stage should be cleaned at the end of the run.

Expected behavior:
- New preflight question (once per run): "Clean stage after successful import?" [y/N]
- Decision must be persisted in stage manifest for resume/reuse consistency.
- Behavior:
  - If Yes: after successful completion of the run, remove the stage_run directory (or a deterministic subset), without touching input/output.
  - If No: keep stage as-is (current behavior).

Constraints:
- Deterministic, safe-by-default.
- Must not clean stage on abort/CTRL-C unless explicitly decided (default: do not).


================================================================================
ISSUE #25 – BUG: abooks_ready written to inconsistent / incorrect locations
CLOSED AT: 2025-12-31T17:56:18Z
================================================================================

Observed behavior:
- abooks_ready (OUTPUT_ROOT when publish=no) is written to different and inconsistent filesystem locations.
- In some runs, output ends up under unexpected paths (e.g. relative to repo / cwd), not under AUDIOMASON_ROOT-derived OUTPUT_ROOT.

Expected behavior:
- OUTPUT_ROOT must be derived exclusively from AUDIOMASON_ROOT.
- publish=no MUST ALWAYS write to: <AUDIOMASON_ROOT>/abooks_ready
- No fallback to CWD, repo root, or implicit paths.

Impact:
- High risk of data scattering and accidental overwrites.
- Breaks filesystem contract.

Notes:
- Likely path resolution leak between env override, defaults, and call sites.
- Must be deterministic and test-covered.


================================================================================
ISSUE #24 – P0 FEATURE: persist preflight answers in stage and reuse stage data for crash-resume (no re-copy)
CLOSED AT: 2025-12-31T16:15:53Z
================================================================================

[goal]
Make imports resumable and deterministic after crashes/interrupts.

[proposal]
Write a run manifest into the stage directory that stores ALL decisions already asked (preflight + per-book metadata), and reuse it on the next run if the same staged source is present.

[required behavior]
1) During preflight, persist decisions immediately to stage (atomic writes):
   - publish yes/no
   - wipe_id3 yes/no
   - author (per source)
   - per-book titles + any per-book selections
   - cover choice / cover URL / cover path (if provided)
2) On restart after crash/CTRL-C:
   - detect existing stage for the selected source
   - load manifest and continue WITHOUT re-asking answered prompts
   - continue at the next unfinished book/step deterministically
3) Stage reuse:
   - do NOT re-copy / re-unpack source into stage if stage already contains the staged src for that source
   - only restage if explicitly forced OR if a mismatch is detected (e.g. different source chosen / stage missing / manifest indicates incomplete staging)

[acceptance]
- A crash during staging/processing does not lose answers.
- Re-running the same source continues where it left off.
- If stage already has the source data, am does not copy/unpack again.
- Deterministic and safe-by-default (no silent overwrite).

[notes]
User observation: data is copied into stage every run; this is wasteful. Reuse existing stage when valid.


================================================================================
ISSUE #23 – BUG: cover prompt does not identify which book is requesting a cover
CLOSED AT: 2025-12-31T16:28:06Z
================================================================================

[repro]
1) Run import with multiple books (ALL)
2) Reach cover selection phase

[observed]
Prompt shows:
"No cover found. Path or URL to image (Enter=skip):"
without indicating author/book.

[expected]
Cover prompt must clearly identify the current book (author + title or [book i/n]: label) so the user knows which book the cover applies to.

[impact]
High UX risk during multi-book imports; easy to attach wrong cover to wrong book.

[example]
[id3] wiped 35.mp3
[id3] wiped 36.mp3
No cover found. Path or URL to image (Enter=skip):

Should be:
[cover] [book 2/5] Stoparuv pruvodce galaxii 2
No cover found. Path or URL to image (Enter=skip):


================================================================================
ISSUE #22 – P0 BUG: publish=no should write to abooks_ready (OUTPUT_ROOT), but conflicts with archive output
CLOSED AT: 2025-12-31T13:25:59Z
================================================================================

[repro]
1) Run: AUDIOMASON_ROOT=/mnt/warez am
2) Choose a source + books
3) Answer: Publish after import? -> n
4) Continue import

[expected]
When publish=no, output must be written under OUTPUT_ROOT (abooks_ready), as defined by config/paths contract. No conflict with archive paths should occur.

[actual]
Import crashes with conflict error saying files already exist in archive (abooks). This indicates the pipeline still targets ARCHIVE_ROOT when publish is disabled.

[impact]
Blocks non-publish workflow; makes safe-by-default staging/output unusable.

[notes]
Config contract: inbox->stage->output (abooks_ready) -> optional publish to archive.
Current behavior violates contract.


================================================================================
ISSUE #21 – Cover cache configuration (memory / disk / off)
CLOSED AT: 2026-01-01T17:04:23Z
================================================================================

Add configurable cover cache behavior.

Current state:
- cover_cache is implicit, in-memory only
- lives for a single run
- not configurable

Requirements:
- Configurable cache mode:
  - memory (current behavior, default)
  - disk (persistent between runs)
  - off (always ask)
- Optional config keys:
  cover:
    cache: memory|disk|off
    cache_dir: <path>   # used when cache=disk
- Must respect:
  - --dry-run (no writes)
  - --debug (log cache hits/misses)
- Deterministic behavior:
  - same input + same cache state => same result

Acceptance:
- Default behavior unchanged.
- disk cache persists covers across runs.
- off disables caching completely.
- Clear logging when cache is used or bypassed.


================================================================================
ISSUE #20 – Config: allow customizing pipeline step order
CLOSED AT: 2026-01-01T20:05:59Z
================================================================================

Add ability to configure the order of pipeline steps via config.

Requirements:
- Config key (example):
  pipeline_steps:
    - unpack
    - convert
    - chapters
    - split
    - rename
    - tags
    - cover
    - publish
- Default order = current behavior (no behavior change without config).
- Validate config:
  - unknown step => error (fail fast)
  - duplicate step => error
  - missing required steps => error (define required set)
- Deterministic execution:
  - same input + same config => same order and result
- Works with --dry-run (summary must reflect configured order)
- Works with --debug logs (must print resolved order)

Acceptance:
- Setting pipeline_steps changes execution order.
- Invalid pipeline_steps aborts before touching filesystem.
- Existing runs without pipeline_steps behave exactly as today.


================================================================================
ISSUE #19 – Public DB validation cache (OpenLibrary) [P3]
CLOSED AT: 2026-01-01T02:29:26Z
================================================================================

Cache results of public DB validation.

Requirements:
- Cache author/book lookups
- Offline-friendly behavior
- Optional / feature-gated

Acceptance:
- No repeated external lookups for same metadata
- Offline runs still work


================================================================================
ISSUE #18 – Machine-readable output mode (--json) [P2]
CLOSED AT: 2026-01-01T18:20:13Z
================================================================================

Add optional machine-readable output.

Requirements:
- --json prints structured output:
  - sources
  - books
  - decisions
  - results
- No change to default human output

Acceptance:
- JSON output is deterministic and parseable


================================================================================
ISSUE #17 – Strict path contract enforcement (AUDIOMASON_ROOT) [P1]
CLOSED AT: 2026-01-01T18:03:55Z
================================================================================

Enforce filesystem path contract strictly.

Rules:
- All roots derive from AUDIOMASON_ROOT
- Fail fast if contract is violated
- Covered by tests

Acceptance:
- Invalid path layout aborts early with clear error


================================================================================
ISSUE #16 – Explicit performance profiles (--rpi4, --low-cpu, --fast) [P1]
CLOSED AT: 2025-12-31T20:11:25Z
================================================================================

Add explicit performance profiles.

Examples:
- --rpi4
- --low-cpu
- --fast

Profiles control:
- ffmpeg threads
- seek behavior
- encoder presets

Acceptance:
- Same input + same profile => same performance behavior
- Default profile remains current behavior


================================================================================
ISSUE #15 – One book = one unit of work (clear phase boundaries) [P1]
CLOSED AT: 2026-01-01T18:01:50Z
================================================================================

Make 'book' the atomic unit of work.

Phases:
- PREPARE (all questions)
- PROCESS (CPU/IO)
- FINALIZE (publish, cleanup)

Benefits:
- Simpler resume
- Cleaner logs
- Deterministic behavior

Acceptance:
- Each book is processed independently with clear phase transitions


================================================================================
ISSUE #14 – Root-audio handling as first-class book [P1]
CLOSED AT: 2026-01-01T11:11:34Z
================================================================================

Treat audio files in archive root as a normal book.

Requirements:
- Root-level audio becomes its own logical book (__ROOT_AUDIO__)
- Same prompts, logging, and processing as directory-based books

Acceptance:
- Root audio appears as a selectable book
- Processing is identical to subdir-based books


================================================================================
ISSUE #13 – Stage reuse (deterministic resume) [P1]
CLOSED AT: 2025-12-31T20:21:08Z
================================================================================

Reuse existing stage safely and deterministically.

Requirements:
- If stage already exists:
  - do not unpack again
  - do not overwrite files
- Enables resume after interruption

Acceptance:
- Re-run after interruption continues without re-unpack
- Stage contents are never silently overwritten


================================================================================
ISSUE #12 – Unified preflight decision block [P0]
CLOSED AT: 2025-12-31T20:19:17Z
================================================================================

Ask ALL user decisions before any filesystem or ffmpeg work starts.

Includes:
- author
- book(s)
- covers
- publish yes/no
- ID3 wipe yes/no

Rules:
- No prompts during processing phase
- One deterministic preflight block

Acceptance:
- After preflight, processing runs without interaction
- --yes skips the entire preflight deterministically


================================================================================
ISSUE #11 – Single-pass chapter split (1 ffmpeg per book) [P0]
CLOSED AT: 2025-12-31T20:16:07Z
================================================================================

Replace N× ffmpeg chapter splitting with single-pass split per book.

Requirements:
- One ffmpeg process per book
- Deterministic output
- Significantly reduced CPU usage and runtime (RPi-friendly)

Acceptance:
- Exactly one ffmpeg invocation per book
- Output tracks identical to current behavior


================================================================================
ISSUE #10 – Multi-book archive processing (root + subdirs) [P0]
CLOSED AT: 2025-12-31T12:27:57Z
================================================================================

Fix archive iteration so ALL books are processed.

Requirements:
- Detect __ROOT_AUDIO__ + every top-level directory as a separate book
- When selecting 'all':
  - prompt for metadata for EACH book
  - clearly print which folder/book is being asked about
- Process root audio AND subdirectories independently

Acceptance:
- No book in archive is silently skipped
- Logs show correct [book] i/n for all books


================================================================================
ISSUE #9 – Logging: add DEBUG level (print every action) [HIGH]
CLOSED AT: 2025-12-31T17:11:39Z
================================================================================

Add a DEBUG logging level that prints *everything* the tool does.

Requirements:
- New flag: --debug (or --log-level debug)
- DEBUG outputs:
  - every filesystem operation (mkdir/copy/move/remove)
  - every external command (ffmpeg/unpack) including full argv
  - all resolved paths (drop/stage/output/archive) + env overrides
  - every decision (reuse stage, skip, conflict, dry-run plan)
  - per-book and per-source state transitions

Priority: HIGH

Acceptance:
- With --debug, user can reconstruct the full pipeline deterministically from logs.
- Default behavior unchanged.
- --quiet still suppresses non-errors (debug must not override quiet unless explicitly chosen).


================================================================================
ISSUE #8 – Public database validation (OpenLibrary) (DEFERRED)
CLOSED AT: 2025-12-31T21:23:58Z
================================================================================

After meta is collected (author + book), validate against public DB (OpenLibrary).

If not found:
- warn user
- prompt:
  1) Continue as-is
  2) Search similar titles

If 2) suggest max 5 similar titles.

Acceptance:
- Works without breaking offline runs (feature-gated / optional).
- Never auto-changes metadata without confirmation.


================================================================================
ISSUE #7 – Logging levels (--quiet/--verbose)
CLOSED AT: 2026-01-01T08:53:05Z
================================================================================

--quiet => only errors
--verbose => include ffmpeg + unpack details
default = current behavior

Acceptance:
- quiet suppresses progress logs.
- verbose shows underlying commands and detailed steps.


================================================================================
ISSUE #6 – Normalized author/book naming helper (confirm before apply)
CLOSED AT: 2025-12-31T21:36:44Z
================================================================================

Optional helper suggests cleaned names by removing common noise:
- (2021)(CZ)
- (audiokniha)
- bitrate/narrator info

User must confirm suggested normalized names.

Acceptance:
- Helper never changes output unless user confirms.
- Default remains current behavior.


================================================================================
ISSUE #5 – am inspect <source> (read-only analysis)
CLOSED AT: 2025-12-31T20:28:56Z
================================================================================

New command: am inspect <source>

Must be read-only:
- no staging, no copying, no unpack, no writes

Prints:
- number of books
- root audio present?
- chapters count (if m4a present)

Acceptance:
- Running inspect produces no filesystem changes.


================================================================================
ISSUE #4 – Resume after Ctrl-C (keep stage, continue next run)
CLOSED AT: 2025-12-31T13:31:56Z
================================================================================

Ctrl-C should stop cleanly:
- finish/terminate current ffmpeg step
- do not delete or corrupt stage

Next run reuses stage deterministically and continues.

Acceptance:
- Interrupt during split leaves stage intact.
- Re-run continues without re-unpack and without overwriting stage.


================================================================================
ISSUE #3 – Consistent source/book labels in logs
CLOSED AT: 2025-12-31T12:03:11Z
================================================================================

All logs must use:
[source] <n>/<total>: <src>
[book]   <i>/<count>: <book>

Applies to preflight prompts, processing, conflicts, skips, publish.

Acceptance:
- Grep for "[source]" and "[book]" shows only the canonical format.


================================================================================
ISSUE #2 – Dry-run summary (no filesystem changes)
CLOSED AT: 2025-12-31T19:44:11Z
================================================================================

--dry-run prints:
- which books will be processed (source + book labels)
- destination paths (author/book)
- publish yes/no
- ID3 wipe yes/no

No unpack, no convert, no cover writes, no tag writes, no mkdir, no move.

Acceptance:
- Running with --dry-run causes zero filesystem modifications.
- Output includes a deterministic summary block per selected source.


================================================================================
ISSUE #1 – Conflict detection in output (no overwrite)
CLOSED AT: 2025-12-31T18:27:18Z
================================================================================

If destination directory already exists, stop processing that book.

- Print:
  [conflict] Author / Book already exists
- Must never silently overwrite.
- Applies to both: stage->output move and publish step.

Acceptance:
- Existing target dir => book is skipped/aborted with [conflict] message.
- Exit code non-zero if any conflicts encountered (unless --yes defines otherwise).


================================================================================
ISSUE #66 – Feat: configurable preflight question order (deterministic, validated)
CLOSED AT: 2026-01-08

Commits:
- dd7b455 – implementation (code + tests)
- 1cd69c7 – documentation + repo_manifest

Verdict:
Scope fulfilled. Follow-up design/refactor tracked in #91–#94.
================================================================================
