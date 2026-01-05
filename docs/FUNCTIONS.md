# AudioMason – Canonical Functions Reference

This document is the **single source of truth** for functional behavior in AudioMason.
If any other documentation conflicts with this file, **THIS FILE WINS**.

---

## Processing log (per-source)

**Identifier:** `processing_log`  
**Scope:** import / per-source lifecycle  
**Default:** disabled

AudioMason supports **optional per-source processing logs**, written to a dedicated `.log` file.

Each source has **its own log file**, covering the **entire lifecycle of that source**.

---

### Logged content

The processing log contains:

- all standard output (`stdout`)
- all error output (`stderr`)
- all interactive questions (prompts)
- all user answers
- all executed actions during source processing

Log writing is **streaming during runtime** (not written ex-post).

---

### Configuration

```yaml
processing_log:
  enabled: false
  path: null
```

#### Behavior

- `enabled: false`  
  → no log file is created

- `enabled: true`, `path: null`  
  → `processing.log` is created inside the stage directory of the source

- `enabled: true`, `path: <directory>`  
  → `<directory>/<slug(source_name)>.log`

- `enabled: true`, `path: <file>`  
  → log is written to the explicit file  
  → if the file has no `.log` suffix, it is appended automatically

---

### CLI

```bash
--processing-log
--processing-log-path <path>
```

#### Semantics

- `--processing-log`  
  → enables per-source logging to the stage directory

- `--processing-log-path <path>`  
  → enables per-source logging and writes logs to the given path

**CLI options override configuration values.**

---

### Runtime rules

- the log file is opened **at the beginning of source processing**
- log entries are written **line-by-line during execution**
- when `--dry-run` is active, **no log file is created**
- log files are **not cleaned up automatically**

---
