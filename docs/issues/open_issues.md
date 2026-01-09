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
- Updated: 2026-01-04T23:37:58Z

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

Not only loudnorm: the same capability is required for *all* current Opts fields.

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

## #90 – Feat: add Buy Me a Coffee support (non-intrusive monetization)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-08T00:06:57Z
- Updated: 2026-01-08T00:06:57Z

## Goal

Enable optional, non-intrusive financial support for AudioMason via Buy Me a Coffee,
without introducing paywalls, prompts, or behavior changes.

AudioMason remains 100% open-source and fully functional without support.

---

## Scope

This issue introduces *visibility only*:
- no feature gating
- no interactive prompts
- no conditional behavior

---

## Tasks

### 1. README.md
- Add a short **Support AudioMason** section
- Include a single Buy Me a Coffee link
- Tone: technical, respectful, no guilt-tripping

Example copy (may be adjusted):

AudioMason is free and open-source.
If it saves you time or frustration, consider supporting development:
https://buymeacoffee.com/audiomason

---

### 2. CLI output (non-interactive)
- Print **one informational line** per run
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

---

## #91 – Enhancement: preflight_steps does not fully control all preflight prompts
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-08T20:51:51Z
- Updated: 2026-01-08T20:54:47Z

Issue #66 introduced preflight_steps with deterministic ordering and fail-fast validation.
During implementation, several architectural limitations were identified.

Issue #66 is correctly implemented and closed.
This issue tracks known design gaps discovered during that work.

## Problem statement

preflight_steps currently does not fully control all preflight prompts.

Key gaps:
- Not all preflight prompts are modeled as steps (run-level, inline prompts)
- Some step_keys are evaluated as blocks, not individually ordered
- Side-effect driven prompts weaken ordering guarantees
- State-dependent steps may never trigger
- Normalizations and suggestion prompts are not first-class steps

## Goal

Define and implement a fully preflight-driven orchestration model with:
- canonical step registry,
- explicit run/source/book execution levels,
- precise ordering guarantees,
- complete and truthful preflight_steps control surface.

## Non-goals

- No changes to Issue #66 behavior
- No breaking changes without explicit migration
- No UI / API work

## Acceptance criteria

- All preflight prompts are either canonical steps or explicitly documented exceptions
- Clear execution-level separation
- Deterministic model is documented
- Tests cover ordering and conditional execution

## References

- Issue #66
- dd7b455 (code + tests)
- 1cd69c7 (docs + repo_manifest)

---

## #92 – Design: canonical preflight orchestration (step registry + run/source/book levels) (Follow-up to #91)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-08T20:53:50Z
- Updated: 2026-01-08T21:47:19Z

Parent: #91

## Goal
Define the target architecture for fully preflight-driven orchestration:
- canonical step registry (all prompts as steps or explicitly documented exceptions)
- explicit execution levels: run / source / book
- deterministic ordering guarantees and how they are enforced
- rules for conditional (state-dependent) steps
- rules for sub-prompts (normalizations/suggestions) as first-class steps vs. nested prompts

## Deliverables
- Design doc (in-repo) describing:
  - step registry API (data model, keys, metadata: level, dependencies, default order)
  - orchestration algorithm (how steps are executed and skipped)
  - migration plan from current flow to registry-driven flow
  - what remains intentionally outside steps (if anything) + rationale
- Test strategy for ordering and conditional execution

## Acceptance criteria
- Design doc merged
- Clear, implementable plan for refactor and cleanup work (scoped into follow-up issues)

---

## #96 – Tooling: sync GitHub issues to open_issues.md + closed_issues.md (full bodies)
- State: **OPEN**
- Labels: —
- Assignees: —
- Milestone: —
- Created: 2026-01-09T13:48:41Z
- Updated: 2026-01-09T13:59:44Z

## Problem
We maintain two authoritative archive files in the repository:

- `docs/contracts/projects/open_issues.md`
- `docs/contracts/projects/closed_issues.md`

These files must reflect the **current state of GitHub issues**, including their **full bodies**.
Today, this synchronization is manual and error-prone, which leads to drift.

## Goal
Create a **standalone helper tool** that:

1. Fetches issues from GitHub (open + closed)
2. Renders them into a deterministic markdown archive format
3. Updates `open_issues.md` and `closed_issues.md`
4. Commits and pushes changes **only if a real diff exists**

This tool is intended to be run **immediately after** `gh issue open` or `gh issue close`
as the next command in the workflow.

## Non-goals
- This tool is **NOT** part of AudioMason runtime or CLI.
- No UI, no daemon, no long-running service.
- No issue creation, editing, or closing.
- No GitHub project or milestone management.

## Requirements (must)

### 1. Tool nature
- Must be a **standalone helper script**, e.g. under `scripts/`
- Must NOT import or depend on AudioMason code
- Must be safe to run repeatedly (idempotent)

### 2. Data source
- GitHub is the **only source of truth**
- Must fetch **full issue bodies**, not just titles
- For each issue, archive must include:
  - Issue number + title
  - State (OPEN / CLOSED)
  - Labels (if any)
  - Assignees (if any)
  - Milestone (if any)
  - Created timestamp
  - Updated timestamp
  - Closed timestamp (for closed issues)
  - Full issue body (verbatim, markdown preserved)

### 3. Output files
Only these two files may be modified:
- `docs/contracts/projects/open_issues.md`
- `docs/contracts/projects/closed_issues.md`

Ordering rules:
- Open issues: ascending by issue number
- Closed issues: descending by closed date, tie-break by issue number

Rendering rules:
- Stable headings and delimiters per issue
- No “generated at now” timestamps
- Output must be byte-stable across runs if issues did not change

### 4. Execution & safety
- Non-interactive by default (no prompts)
- Must FAIL-FAST with clear error if:
  - GitHub auth is missing or invalid
  - Rate limit prevents fetching
  - Target files are missing
  - Working tree is dirty (unless explicitly overridden)

### 5. Git behavior
- Must not commit if there is no diff
- Deterministic commit message:
  - `Docs: sync GitHub issues archive (open/closed)`
- Default behavior:
  - write files
  - commit if diff exists
  - push to default remote branch
- Flags must allow:
  - `--dry-run`
  - `--no-commit`
  - `--no-push`
  - optional override for dirty working tree

### 6. CLI
Canonical invocation:
```bash
python3 scripts/sync_issues_archive.py
```

Required flags:
- `--repo <owner/name>` (default: auto-detect from git remote if possible)
- `--dry-run`
- `--no-commit`
- `--no-push`

### 7. Workflow intent (explicit)
This tool is designed to be used as a **natural follow-up command**:

```bash
gh issue open …
python3 scripts/sync_issues_archive.py
```

```bash
gh issue close …
python3 scripts/sync_issues_archive.py
```

The tool itself must not require chaining or interaction.

## Acceptance criteria
- Archives fully match GitHub issues (including full bodies)
- Ordering and rendering are deterministic
- Re-running with no issue changes produces no diff and no commit
- With changes present, files are updated, committed, and pushed
- Unit tests cover:
  - ordering rules
  - rendering stability
  - no-diff → no commit behavior
  - correct open/closed split
- `docs/repo_manifest.yaml` is updated if new scripts or tests are added

## Notes
- This is a project/tooling issue.
- Implementation must follow Implementation Law for patch delivery and execution.


---
