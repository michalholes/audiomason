# OPEN ISSUES – AudioMason (AUTHORITATIVE PROJECT SNAPSHOT)

Applies to: PROJECT / PLAN chats  
Maintained by: PROJECT chat (PM + Project Owner)  
Source of truth for execution: GitHub Issues  
This file is the planning/audit snapshot (full bodies + PM status/priority).

Last updated: 2026-01-08 (Europe/Bratislava)

---

## Index (OPEN)


- #91 – Enhancement: preflight_steps does not fully control all preflight prompts
- #92 – Design: canonical preflight orchestration
- #93 – Refactor: preflight step registry enforcement
- #94 – Cleanup: docs + repo_manifest + legacy preflight paths
- #68 – Feat: configurable default answers for binary preflight questions (y/n)
- #69 – Feat: configurable handling of non-binary preflight questions (deterministic)
- #78 – Feat: preflight stage creation toggle per source (disable-able via config/CLI)
- #87 – Feat: overlap staging copy with preflight prompts when selecting all sources
- #77 – Feat: allow selecting multiple sources or books by index list (e.g. "1 4 15")
- #79 – CLI enable + config-hide support for all Opts flags
- #58 – Feat: add AM Remote API service (FastAPI) foundation
- #60 – Feat: run registry + status/report persistence for remote runs
- #61 – Feat: remote run logs + progress endpoints (polling MVP)
- #62 – Security: Remote API auth (bearer token, opt-in, redacted logs)
- #59 – Feat: non-interactive import request (GUI-driven, fail-fast)
- #63 – Feat: Web GUI MVP (runs list, run detail, start import)
- #64 – Ops: systemd service for AM Remote API
- #90 – Feat: add Buy Me a Coffee support (non-intrusive monetization)

---

## Canonical priority buckets (non-binding, from PROJECT_GUARD_RAILS)

- P1 (Preflight determinism): #66, #68, #69
- P2 (Workflow / performance): #78, #87
- P3 (CLI UX): #77, #79
- P4 (Remote API / GUI): #58, #60, #61, #62, #59, #63, #64
- P5 (Non-intrusive monetization): #90

---

================================================================================
ISSUE #66 – Feat: configurable preflight question order (deterministic, validated)
PM Status: OPEN
Priority: P1
Decision points: none
================================================================================

Feat: Configurable preflight question order

Goal
- Allow deterministic configuration of the order in which preflight questions are asked.

Problem
- Preflight currently asks questions in a fixed, code-defined order.
- For CLI power users and future GUI integration, the order must be:
  - configurable
  - deterministic
  - validated fail-fast

Scope
- Introduce a configurable list (e.g. `preflight_steps`) defining question order.
- Each step represents one logical preflight decision (source, book, id3 wipe, cover, publish, cleanup, etc.).
- Validate configuration at startup:
  - unknown step -> error
  - missing required step -> error
  - duplicate steps -> error
- CLI behavior must strictly follow configured order.
- Default configuration preserves current behavior exactly.

Acceptance criteria
- User can define preflight question order via config (and optionally CLI override if appropriate).
- Order is enforced deterministically.
- Invalid configuration fails fast with a clear error.
- Fully covered by tests.
- No change to default behavior unless explicitly configured.

Notes
- This is a prerequisite for GUI-driven and non-interactive preflight flows.

================================================================================
ISSUE #68 – Feat: configurable default answers for binary preflight questions (y/n)
PM Status: OPEN
Priority: P1
Decision points: none
================================================================================

Feat: Configurable default answers for binary (y/n) preflight questions

Goal
- Allow deterministic configuration of default answers for binary (yes/no) preflight questions.

Problem
- Binary preflight questions (y/N, Y/n) currently have hardcoded interactive defaults.
- For automation, power users, and future GUI/Remote API usage, defaults must be:
  - configurable
  - explicit
  - deterministic
- Relying on implicit interactive defaults is not acceptable in non-interactive contexts.

Scope
- Introduce configuration for default answers to binary preflight questions
  (e.g. `preflight_defaults` mapping: question_key -> yes|no).
- Defaults apply when:
  - question is asked interactively and user just presses Enter
  - question is disabled but needs deterministic resolution
- Validation rules:
  - unknown question key -> error
  - non-binary question referenced -> error
  - invalid value -> error
- CLI-provided answers always override configured defaults.
- Default configuration preserves current behavior exactly.

Acceptance criteria
- User can configure default answers for y/n preflight questions.
- Configured defaults override interactive hardcoded defaults.
- CLI flags take precedence over config defaults.
- Missing deterministic value in non-interactive context -> fail fast.
- Fully covered by tests.
- No behavior change unless explicitly configured.

Notes
- This is complementary to:
  - configurable preflight order
  - disabling preflight questions
- Required for GUI-driven and Remote API workflows.

================================================================================
ISSUE #69 – Feat: configurable handling of non-binary preflight questions (deterministic)
PM Status: OPEN
Priority: P1
Decision points: none
================================================================================

Feat: Configurable handling of non-binary preflight questions

Goal
- Allow deterministic configuration of how non-binary preflight questions are handled.

Problem
- Non-binary preflight questions (free text, selections, lists, numeric input, etc.)
  currently rely on interactive prompting.
- For automation, power users, and future GUI / Remote API usage, their behavior must be:
  - configurable
  - explicit
  - deterministic
- Implicit interactive behavior is not acceptable in non-interactive contexts.

Scope
- Introduce a configuration model for non-binary preflight questions, allowing:
  - predefined default values
  - required explicit values (no default allowed)
  - optional questions that may be skipped
- Define per-question policy, e.g.:
  - required | optional
  - default value (if allowed)
- Resolution order:
  1) CLI-provided value
  2) Configured value
  3) Interactive prompt (only if allowed)
- Fail-fast rules:
  - Missing required value in non-interactive mode -> error
  - Unknown question key -> error
  - Invalid value (type/format/enum) -> error

Acceptance criteria
- User can configure handling rules for non-binary preflight questions.
- Non-interactive runs either resolve deterministically or fail fast.
- Interactive runs respect configured defaults and requirements.
- CLI values always override config values.
- Default configuration preserves current behavior exactly.
- Covered by tests.

Notes
- Complements:
  - configurable preflight order
  - disabling preflight questions
  - configurable defaults for binary questions
- Required for full GUI-driven and Remote API-based workflows.

================================================================================
ISSUE #78 – Feat: preflight stage creation toggle per source (disable-able via config/CLI)
PM Status: OPEN
Priority: P2
Decision points: none
================================================================================

Feat: preflight question to control stage creation per source (disable-able via config/CLI)

Problem
- AudioMason currently always creates a stage after source selection and works on copied data.
- There is no way to decide to work directly on files and directories in the inbox without creating a stage.

Goal
- Introduce a preflight question immediately after source selection that controls whether a stage should be created or not.

Preflight question
- Question (indicative wording):
  "Create stage for this source? [Y/n]"
- Default answer: Yes (preserves current behavior)

Behavior
- If answer = Yes:
  - stage is created using the existing deterministic stage naming and layout (unchanged)
  - subsequent processing works on stage data
- If answer = No:
  - stage is NOT created
  - AudioMason works directly with files and directories in the inbox
  - no data copying occurs

Rules / constraints
- Decision is per source.
- Default behavior without any configuration must remain unchanged.
- The answer must be persisted deterministically (for resume / repeated runs).

Critical requirement – prompt control
- This question (and all future questions introduced in AudioMason) MUST be disable-able deterministically via:
  - configuration file
  - command-line options
- When the prompt is disabled:
  - the prompt must not be shown
  - the default answer must be applied deterministically
- This requirement must integrate with the existing / planned global prompt control mechanism
  (e.g. global prompt disable or per-prompt disable via config/CLI).

Scope
- Changes limited to:
  - preflight logic
  - stage creation flow
  - validation and tests
- No changes to:
  - discovery logic
  - export logic
  - documentation (unless explicitly required by the issue)

Acceptance criteria
- After source selection, a stage creation question is shown.
- Yes -> behavior identical to current implementation.
- No -> no stage is created, processing happens directly in inbox.
- Default answer is Yes.
- When the prompt is disabled:
  - no interactive prompt is shown
  - default Yes is applied deterministically.
- Covered by tests:
  - stage enabled
  - stage disabled
  - prompt disabled -> default Yes

Notes
- This feature enables faster workflows without unnecessary data duplication.

================================================================================
ISSUE #87 – Feat: overlap staging copy with preflight prompts when selecting all sources
PM Status: OPEN
Priority: P2
Decision points:
- Confirm the opt-in mechanism (CLI flag, config key, or both).
- Confirm how progress/output is kept readable (no garbled output).
================================================================================

Problem
When selecting all sources (input 'a'), AudioMason currently stages (copies) data first and only then asks preflight questions.
This creates idle time where the user waits for I/O-heavy staging to finish before answering prompts.

Goal
Allow the user to answer preflight questions while staging copy is still running.
This should work per source, and especially for batch runs when selecting all sources.

Proposed behavior
- For each selected source, start staging copy in the background.
- While staging is running, ask preflight prompts in the foreground (interactive).
- Start PROCESS for that source only after BOTH:
  (1) staging copy completed successfully
  (2) preflight decisions are completed.

Constraints (strict)
- Must remain deterministic.
- Must not break non-interactive / prompt-disable modes.
- No changes to default behavior unless the feature is enabled.
- Interactive I/O must remain stable (no garbled output).

Configuration / CLI
- Feature should be opt-in via CLI and/or config.
- If enabled, it applies when multiple sources are selected (e.g. 'a').

Acceptance criteria
- User can answer preflight questions while staging copy runs.
- No PROCESS begins before staging is finished.
- Errors in staging are handled cleanly and fail-fast.
- Existing tests pass; add a regression test if feasible.

================================================================================
ISSUE #77 – Feat: allow selecting multiple sources or books by index list (e.g. "1 4 15")
PM Status: OPEN
Priority: P3
Decision points: none
================================================================================

Feat: allow selecting multiple sources or books by explicit index list (e.g. "1 4 15")

Problem
- Today, selection prompts only support:
  - a single index (e.g. "1")
  - or "a" for all
- There is no way to select an explicit subset (e.g. authors 1, 4, and 15),
  which makes batch processing of specific items unnecessarily slow and repetitive.

Affected prompts (examples)
- Source selection:
  "Choose source number, or a for all"
- Book selection:
  "Choose book number, or a for all"

Goal (authoritative)
- Extend selection prompts to support explicit multi-selection using index lists.

Desired UX
- User can enter:
  - space-separated list: "1 4 15"
  - (optionally later) comma-separated list: "1,4,15" (not required for MVP)
- Result:
  - Only the selected sources / books are processed
  - In the order specified by the user (or normalized deterministically)

Rules / behavior
- Supported inputs:
  - single number (existing behavior)
  - "a" (existing behavior: all)
  - multi-number list (new behavior)
- Validation (fail-fast):
  - non-numeric token (except "a") -> error
  - index out of range -> error
  - duplicates -> error
  - mixing "a" with numbers -> error
- Default behavior with empty input stays unchanged.

Scope
- Implement only for:
  - source selection
  - book selection
- No changes to preflight logic itself.
- No changes to discovery logic.
- No documentation changes in this issue.

Implementation notes (guidance, not mandate)
- Centralize parsing logic:
  - helper like `_parse_index_selection(input: str, max_n: int) -> list[int]`
- Reuse helper for both source and book selection.
- Deterministic ordering must be guaranteed.

Acceptance criteria
- User can select multiple sources via e.g. "1 4 15"
- User can select multiple books via e.g. "2 3 5"
- Existing behaviors (single index, "a") remain unchanged.
- Invalid input fails fast with a clear error message.
- Covered by tests:
  - valid multi-select
  - invalid token
  - duplicate index
  - out-of-range index
  - mixing "a" with numbers

Notes
- This feature complements (but does not replace):
  - "a" (select all)
  - future global prompt disable / non-interactive modes.

================================================================================
ISSUE #79 – CLI enable + config-hide support for all Opts flags
PM Status: OPEN
Priority: P3
Decision points:
- Recommend split: (A) loudnorm preflight + wiring; (B) "all Opts flags" consistency sweep.
================================================================================

Feat/Bug: expose loudnorm in preflight (default No) with CLI control and disable-able prompt

Problem
- `loudnorm` exists in the codebase (and may already be wired as an option internally), but it is not discoverable in the interactive dialogs.
- Users cannot enable/disable loudnorm via a dedicated preflight prompt.
- This leads to inconsistent UX: a feature exists but cannot be reached from the normal interactive workflow.

Goal (authoritative)
- Add a preflight question for loudnorm so it becomes a first-class user-facing option.

Required behavior
1) Preflight prompt
- Add a preflight question (indicative wording):
  "Apply loudnorm? [y/N]"
- Default answer: No (preserves current behavior unless explicitly enabled).

2) CLI control
- Provide a CLI option to enable loudnorm without prompting (exact flag name may already exist; if so, ensure it works and is documented by behavior/tests).
- CLI must override config/preflight defaults.

3) Prompt disable (config)
- It must be possible to disable this new loudnorm prompt via config (consistent with the global/per-prompt prompt-control mechanism used for other preflight prompts).
- When the prompt is disabled, the default (No) must be applied deterministically unless overridden by CLI.

Scope
- Add/route loudnorm into preflight decision flow.
- Ensure the chosen value is carried into processing where loudnorm is applied.
- Add validation and tests.
- No unrelated refactors or documentation changes in this issue.

Acceptance criteria
- Interactive mode shows a loudnorm question in preflight.
- Default is No.
- CLI can enable loudnorm (no prompt required).
- Config can disable the loudnorm question deterministically.
- Regression tests cover:
  - default No behavior
  - prompt disabled -> default No
  - CLI enabling loudnorm overrides defaults

Notes
- If loudnorm is currently only partially implemented or unused, this issue includes wiring it end-to-end so the preflight choice actually affects processing.

---

Additional requirement: CLI enable + config-hide support for all Opts flags

Not only loudnorm: the same capability is required for all current Opts fields.

Requirement
- For every Opts field listed below:
  - it must be possible to explicitly enable/disable it via CLI (when applicable)
  - and it must be possible to hide/disable the corresponding interactive question via config (prompt control)
- When a prompt is hidden/disabled:
  - behavior must remain deterministic (use default unless CLI overrides)
- CLI overrides config/defaults.

Opts fields (current)
- yes
- dry_run
- config
- quiet
- publish
- wipe_id3
- loudnorm
- q_a
- verify
- verify_root
- lookup
- cleanup_stage
- clean_inbox_mode
- split_chapters
- ff_loglevel
- cpu_cores
- debug
- json

Notes
- Some fields may already have CLI flags; for those, the requirement is to ensure consistency and test coverage.
- Fields that are not interactive prompts today should still follow the rule: if a prompt exists or is introduced, it must be suppressible via config and controllable via CLI.

================================================================================
ISSUE #58 – Feat: add AM Remote API service (FastAPI) foundation
PM Status: OPEN
Priority: P4
Decision points:
- Remote API/GUI direction is explicitly deferred (keep foundation minimal).
================================================================================

Build: AM Remote API service (FastAPI) as stable server-side wrapper

Goal
- Introduce a new HTTP service that wraps AudioMason functionality for remote control (GUI client).

Scope
- New package/module: src/audiomason/remote_api/ (or similar)
- Provide a minimal FastAPI app with health/version endpoint
- Provide a consistent run-id concept for server-triggered executions

Acceptance criteria
- `GET /health` returns ok + version
- Service can be started locally (dev) and returns responses deterministically
- No interactive prompts over HTTP (this issue only lays foundation)

Notes
- Assume access over Tailscale (no public exposure) for MVP.

================================================================================
ISSUE #60 – Feat: run registry + status/report persistence for remote runs
PM Status: OPEN
Priority: P4
Decision points: none
================================================================================

Feat: Runs registry (run-id, status, JSON report persistence)

Goal
- Track each server-triggered run so the GUI can list runs and open details.

Scope
- Introduce a runs registry under an app-controlled state directory (deterministic structure)
- Store:
  - run metadata (request, timestamps)
  - current status (queued/running/succeeded/failed/canceled)
  - final JSON report (reuse existing JSON report mode if available)
  - path to log file for the run

Acceptance criteria
- `GET /runs` lists recent runs with status
- `GET /runs/{id}` returns run details + links/paths to artifacts (log/report)
- Data survives service restart

================================================================================
ISSUE #61 – Feat: remote run logs + progress endpoints (polling MVP)
PM Status: OPEN
Priority: P4
Decision points: none
================================================================================

Feat: Log and progress streaming endpoints (polling-first MVP)

Goal
- Allow GUI to show live logs and a basic progress indicator.

Scope
- Add endpoints:
  - `GET /runs/{id}/log` (tail with offset/limit; polling-friendly)
  - optional: `GET /runs/{id}/events` (SSE) if easy; otherwise stick to polling MVP
- Ensure deterministic log formatting where possible (no random ordering)

Acceptance criteria
- GUI can poll log tail without re-downloading whole file
- Offset-based log reads are correct and stable
- Clear handling when run is finished (EOF)

================================================================================
ISSUE #62 – Security: Remote API auth (bearer token, opt-in, redacted logs)
PM Status: OPEN
Priority: P4
Decision points: none
================================================================================

Security: Authentication for Remote API (Tailscale-first, token-based)

Goal
- Prevent accidental access even on trusted networks.

Scope
- Implement a simple bearer token auth (env var or config entry)
- Deny by default if token not configured (explicit opt-in)
- Add request logging with redaction (no token leakage)

Acceptance criteria
- All non-health endpoints require valid token
- Invalid/missing token -> 401
- Token never appears in logs

================================================================================
ISSUE #59 – Feat: non-interactive import request (GUI-driven, fail-fast)
PM Status: OPEN
Priority: P4
Decision points: none
================================================================================

Feat: Non-interactive import request model (no prompts)

Goal
- Make server-triggered imports fully non-interactive so the GUI can drive them.

Scope
- Define a strict JSON request schema for an import job (source selection, config overrides, decisions)
- Add a codepath that runs import using provided answers (fail-fast if required answers missing)
- Keep output deterministic for same request

Acceptance criteria
- API can start an import run without any stdin prompts
- Missing required decision -> 4xx error with machine-readable list of missing fields
- Existing CLI behavior stays unchanged

================================================================================
ISSUE #63 – Feat: Web GUI MVP (runs list, run detail, start import)
PM Status: OPEN
Priority: P4
Decision points: none
================================================================================

Feat: Minimal Web GUI (MVP) for iPhone Safari

Goal
- Provide a tiny web UI to drive imports and monitor runs from iPhone (Safari).

Scope
- Web pages:
  - Runs list
  - Run detail (status + log tail + link to JSON report)
  - Start import form (very small; uses non-interactive request schema)
- Prefer server-rendered HTML or minimal JS (keep dependencies low)

Acceptance criteria
- Works in iPhone Safari
- Can start an import and follow logs to completion
- No complex styling; function > form

================================================================================
ISSUE #64 – Ops: systemd service for AM Remote API
PM Status: OPEN
Priority: P4
Decision points: none
================================================================================

Ops: Systemd service for AM Remote API (deployable on Debian/Ubuntu)

Goal
- Make the Remote API run as a managed service on the server.

Scope
- Add systemd unit file (and install path decisions aligned with .deb packaging)
- Define environment/config loading for token + bind address/port
- Ensure log location is deterministic and writable

Acceptance criteria
- `systemctl start audiomason-remote` works
- Service restarts cleanly
- Runs registry/logs persist across restarts

================================================================================
ISSUE #90 – Feat: add Buy Me a Coffee support (non-intrusive monetization)
PM Status: OPEN
Priority: P5
Decision points: none
================================================================================

## Goal

Enable optional, non-intrusive financial support for AudioMason via Buy Me a Coffee,
without introducing paywalls, prompts, or behavior changes.

AudioMason remains 100% open-source and fully functional without support.

---

## Scope

This issue introduces visibility only:
- no feature gating
- no interactive prompts
- no conditional behavior

---

## Tasks

### 1. README.md
- Add a short Support AudioMason section
- Include a single Buy Me a Coffee link
- Tone: technical, respectful, no guilt-tripping

Example copy (may be adjusted):

AudioMason is free and open-source.
If it saves you time or frustration, consider supporting development:
https://buymeacoffee.com/audiomason

---

### 2. CLI output (non-interactive)
- Print one informational line per run
- No prompts, no input required
- Must respect unattended / non-interactive runs

Example:

☕ Enjoying AudioMason?
Support development: https://buymeacoffee.com/audiomason

Placement:
- startup or final summary
- printed exactly once per invocation

---

### 3. Documentation
- Add a short support note at the end of user-facing docs
- Explain that support helps maintenance and long-term quality
- No mention of money needs or personal finance

---

## Non-goals (explicitly out of scope)

- No paywalled features
- No supporter-only functionality
- No ads or banners
- No additional prompts
- No behavior changes based on support status

---

## Acceptance criteria

- AudioMason behavior remains unchanged
- CLI remains fully non-interactive
- Support link is visible but unobtrusive
- Documentation updated accordingly

---

## Notes

Buy Me a Coffee page already exists:
https://buymeacoffee.com/audiomason

