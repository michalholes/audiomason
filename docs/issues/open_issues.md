# Open Issues

## #58 – Feat: add AM Remote API service (FastAPI) foundation
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:22Z
- Updated: 2026-01-03T08:55:22Z

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


---

## #59 – Feat: non-interactive import request (GUI-driven, fail-fast)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:23Z
- Updated: 2026-01-03T08:55:23Z

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


---

## #60 – Feat: run registry + status/report persistence for remote runs
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:24Z
- Updated: 2026-01-03T08:55:24Z

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


---

## #61 – Feat: remote run logs + progress endpoints (polling MVP)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:26Z
- Updated: 2026-01-03T08:55:26Z

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


---

## #62 – Security: Remote API auth (bearer token, opt-in, redacted logs)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:27Z
- Updated: 2026-01-03T08:55:27Z

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


---

## #63 – Feat: Web GUI MVP (runs list, run detail, start import)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:29Z
- Updated: 2026-01-03T08:55:29Z

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


---

## #64 – Ops: systemd service for AM Remote API
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T08:55:30Z
- Updated: 2026-01-03T08:55:30Z

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


---

## #68 – Feat: configurable default answers for binary preflight questions (y/n)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T09:19:55Z
- Updated: 2026-01-03T09:19:55Z

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


---

## #69 – Feat: configurable handling of non-binary preflight questions (deterministic)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-03T09:23:03Z
- Updated: 2026-01-03T09:23:03Z

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


---

## #77 – Feat: allow selecting multiple sources or books by index list (e.g. "1 4 15")
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-04T08:10:00Z
- Updated: 2026-01-04T08:10:00Z

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
- Extend selection prompts to support **explicit multi-selection** using index lists.

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


---

## #78 – Feat: preflight stage creation toggle per source (disable-able via config/CLI)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-04T13:14:36Z
- Updated: 2026-01-04T13:14:36Z

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


---

## #79 –  CLI enable + config-hide support for all Opts flags
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-04T23:00:23Z
- Updated: 2026-01-10T00:16:12Z

TRACKING (META) — split into sub-issues:
- # loudnorm determinism
- # cleanup_stage CLI control
- # clean_inbox config-hide validation bug
- # docs audit & alignment

Close #79 only when all sub-issues are closed.

---

## #87 – Feat: overlap staging copy with preflight prompts when selecting all sources
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-07T02:05:42Z
- Updated: 2026-01-07T02:05:42Z

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

---

## #97 – Sub-issue: loudnorm determinism (prompt + CLI symmetry + tests)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-10T00:19:35Z
- Updated: 2026-01-10T00:22:18Z

Child of #79.

Missing (per verification):
- preflight prompt
- --no-loudnorm
- tests

Scope:
- Add preflight prompt: "Apply loudnorm? [y/N]" (default No)
- Add CLI symmetry: --loudnorm and --no-loudnorm
- Allow config-hide/disable for the loudnorm prompt
- Deterministic resolution: CLI > config > default
- Tests: default, config-hide default, CLI override

Acceptance criteria:
- Deterministic behavior proven by tests
- No interactive leakage in non-interactive contexts


---

## #98 – Sub-issue: cleanup_stage must be CLI-controllable (remove hardcoded True)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-10T00:19:36Z
- Updated: 2026-01-10T00:22:19Z

Child of #79.

Missing (per verification):
- cleanup_stage is hardcoded True and not CLI-controllable

Scope:
- Remove hardcoded cleanup_stage=True
- Add explicit CLI enable/disable
- Preserve default behavior unless overridden
- Tests for CLI override + determinism

Acceptance criteria:
- CLI can explicitly control cleanup_stage
- Default behavior unchanged unless explicitly overridden
- Tests prove override


---

## #99 – Sub-issue: fix clean_inbox config-hide validation bug
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-10T00:19:37Z
- Updated: 2026-01-10T00:22:20Z

Child of #79.

Missing (per verification):
- clean_inbox prompt exists, but config-hide key is rejected by validation

Scope:
- Fix validation to accept intended config-hide key
- Ensure prompt hide works deterministically
- Regression tests

Acceptance criteria:
- Valid config key passes validation
- Hidden prompt applies deterministic behavior
- Regression tests cover the bug


---

## #100 – Sub-issue: docs audit & alignment for Opts CLI + config-hide behavior
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-10T00:19:38Z
- Updated: 2026-01-10T00:22:21Z

Child of #79.

Missing (per verification):
- docs do not reflect final behavior for the full Opts list

Scope:
- Audit full Opts list from #79
- Align docs with actual behavior:
  - CLI flags
  - config-hide/disable behavior
  - determinism rules (CLI > config > default)

Files (expected):
- README.md
- docs/CLI.md
- docs/CONFIGURATION.md

Acceptance criteria:
- Docs match actual behavior
- No contradictions
- Explicitly covers full Opts list from #79


---

## #107 – CI: avoid writing /etc/audiomason/config.yaml; use --config with repo config
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-10T11:14:52Z
- Updated: 2026-01-10T11:14:52Z

Decision: Variant A.

Problem:
- CI currently writes config to /etc/audiomason/config.yaml using sudo.
- This makes tests less isolated and hides config-loading brittleness.

Scope:
- Remove sudo copy into /etc from CI workflow.
- Use `--config <repo>/debian/config.yaml` (or equivalent) in CI invocations.

Acceptance criteria:
- CI completes without writing to /etc and without sudo copy of config.
- CI explicitly points CLI to a config via `--config`.
- At least one test/execution path runs in a clean env (no /etc config present) to prevent regressions.

---
