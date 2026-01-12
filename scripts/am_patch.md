# am_patch.sh — Canonical Patch Runner

This document describes the **canonical patch runner** used in the AudioMason project.

The runner is designed to execute implementation patches in a **deterministic,
auditable, and failure‑friendly** way, while keeping final control in the hands
of the human operator.

---

## Location

**Canonical runner path (repo‑backed):**
```
/home/pi/apps/audiomason/scripts/am_patch.sh
```

**Canonical patch staging directory:**
```
/home/pi/apps/patches/
```

---

## Purpose

The runner exists to:

- provide a **single, versioned execution entrypoint** for all IC‑produced patches
- ensure patches are:
  - executed consistently
  - tested in a controlled environment
  - either committed cleanly or left for manual inspection
- preserve **forensic visibility** on failures (no hidden cleanup)

---

## Invocation

```bash
/home/pi/apps/audiomason/scripts/am_patch.sh <ISSUE> "<COMMIT MESSAGE>" [<PATCH_FILENAME>]
```

### Parameters

| Parameter | Required | Description |
|---------|----------|-------------|
| `<ISSUE>` | yes | Issue number (used for naming, logging, audit) |
| `<COMMIT MESSAGE>` | yes | Commit message used **only if tests pass** |
| `<PATCH_FILENAME>` | no | Patch script filename located in `/home/pi/apps/patches/` |

### Patch filename rules

- If `<PATCH_FILENAME>` is omitted, the runner expects:
  ```
  issue_<ISSUE>.py
  ```
- If provided:
  - it **must be a filename only** (no paths, no `..`)
  - it **must exist** under `/home/pi/apps/patches/`

Examples:
```bash
am_patch.sh 79 "Fix: preflight ordering"
am_patch.sh 79 "Fix: preflight ordering" issue_79_run3_fix2.py
```

---

## Options

### Verify-only mode

Run patch/finalize + tests, but **do not** commit or push:

```bash
/home/pi/apps/audiomason/scripts/am_patch.sh <ISSUE> "<COMMIT MESSAGE>" [<PATCH_FILENAME>] --verify-only
```

### Finalize mode (dirty tree)

When you have made manual edits (dirty working tree) and want tests + commit/push:

```bash
/home/pi/apps/audiomason/scripts/am_patch.py -f "<COMMIT MESSAGE>"
```

### Test policy switches

Default is strict:

- `--tests all` (ruff + pytest + mypy)

You can opt out:

- `--tests pytest` (pytest only)
- `--no-ruff` (skip ruff; only relevant with `--tests all`)
- `--no-mypy` (skip mypy; only relevant with `--tests all`)

## Execution model

### High‑level flow

1. Acquire exclusive lock (no concurrent runs)
2. Truncate and start a **single rotating log**
3. Discover repository root
4. Execute patch script
5. Always delete patch script
6. On failure:
   - print forensic information
   - explain next steps
7. On success:
   - run tests in venv
   - commit & push only if tests pass

---

## Logging

Logs are stored under a dedicated directory:

```
/home/pi/apps/patches/logs/
```

Each run creates a new per-run log file:

```
am_patch_<ISSUE|finalize>_<YYYYmmdd_HHMMSS>.log
```

A stable symlink always points to the latest run log:

```
/home/pi/apps/patches/am_patch.log
```

### Retention (automatic)

The runner automatically keeps the most recent **20** log files and prunes older logs at the start of each run.
Only files matching the expected log filename pattern are ever deleted.

## Failure handling (forensic‑only)

The runner **never performs automatic cleanup or rollback**.

### Patch failure

If the patch script exits non‑zero:

The runner will:
- print a **best‑effort filesystem diff**
- show `git status --porcelain` (if applicable)
- print **explicit NEXT STEPS**, including:
  - which files to upload to IC
  - optional commands to discard only the affected paths

The repository state is left unchanged for the user to decide.

---

### Test failure

If tests fail:
- modified files are listed
- the log file path is printed
- **no cleanup advice** is given (by design)

The user decides whether to:
- upload files + log to IC
- discard changes manually

---

## Commit rules

A commit + push happens **only if all tests pass**.

The runner will refuse to:
- create empty commits
- commit outside a git repository

---

## Design principles

- **Determinism over automation**
- **Forensics over rollback**
- **Human decision at failure points**
- **One canonical tool, one canonical path**

---

## Non‑goals

The runner intentionally does **not**:
- auto‑rollback changes
- guess developer intent
- manage multiple patch states
- clean up after failures

All such decisions are left to the operator.

---

## Typical workflow

```text
IC produces patch
↓
User runs am_patch.sh
↓
Patch fails → forensics + guidance
OR
Tests fail → upload files + log
OR
Success → commit + push
```

---

## Summary

`am_patch.sh` is a **controlled execution boundary** between
human decision‑making and automated patch application.

It enforces consistency while preserving transparency and control.
