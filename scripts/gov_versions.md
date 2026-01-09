# Governance Version Sync Script

This document describes the **helper script**:

```
scripts/gov_versions.py
```

---

## Status

This is a **helper / maintenance tool**.

It is **NOT** part of AudioMason runtime behavior, CLI commands, or import pipeline.
Running or not running this script has **no effect** on AudioMason functionality
unless governance documents themselves are modified.

---

## Scope

The script operates **only** on governance documents located in:

```
docs/governance/*.md
```

No other files or directories are touched.

---

## Supported version formats

The script detects versions in a **case-insensitive** manner and supports both formats:

```
Version: vX.Y
# VERSION: vX.Y
```

When updating versions, the script **preserves the original format**:
- keeps or omits `#` as originally present,
- keeps original key casing,
- updates **only the version value**.

---

## Capabilities

### `--list`

Print a table of governance files and their detected versions.

Missing versions are shown as `MISSING`.

```
python3 scripts/gov_versions.py --list
```

---

### `--check`

Validate governance documents.

Default mode: **lockstep**

- all governance documents must define a version,
- all versions must be identical.

```
python3 scripts/gov_versions.py --check
```

---

### `--check --mode independent`

- all governance documents must define a version,
- versions may differ.

```
python3 scripts/gov_versions.py --check --mode independent
```

---

### `--set-version X.Y`

**Write mode.**

Update the existing version line in all governance documents.

Rules:
- only existing version lines are modified,
- the rest of each file remains unchanged,
- fails if any file has a missing or ambiguous version.

```
python3 scripts/gov_versions.py --set-version v3.0
```

---

### `--dry-run`

Valid only together with `--set-version`.

Shows planned changes without writing files.

```
python3 scripts/gov_versions.py --set-version v3.0 --dry-run
```

---

### `--repo-root PATH`

Explicitly specify repository root.
If omitted, the script auto-detects the repository root
by locating `pyproject.toml`.

---

## Determinism & safety

- deterministic ordering (sorted file paths),
- fail-fast on ambiguity or missing data,
- local filesystem only,
- no network access,
- no side effects unless `--set-version` is used.

---

## Exit codes

| Code | Meaning |
|-----:|--------|
| 0 | success |
| 2 | validation or usage error |
| 3 | filesystem / I/O error |

---

## Intended workflow

Typical usage:

```
python3 scripts/gov_versions.py --list
python3 scripts/gov_versions.py --check --mode independent
python3 scripts/gov_versions.py --set-version v3.0 --dry-run
```

Actual writes should be performed **only after explicit governance approval**.

---

## Governance note

This script is a **tool**, not a **rule**.

Whether it must be executed, and when, is defined by governance documents
(Project Constitution / Laws), not by this script.
