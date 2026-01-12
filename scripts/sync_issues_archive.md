# sync_issues_archive.py

Standalone helper tool for deterministic synchronization of GitHub issues
into repository markdown archives.

This tool is **NOT** part of the AudioMason runtime or CLI.
It is an auxiliary maintenance script intended to be run manually
or as a follow-up step after GitHub issue operations.

---

## Purpose

The repository maintains canonical issue archives:

- `docs/issues/open_issues.md`
- `docs/issues/closed_issues.md`

These files must reflect the **exact state of GitHub issues**,
including **full issue bodies**, without manual editing.

This tool ensures:
- zero drift between GitHub and repo archives
- deterministic rendering
- idempotent execution

---

## Source of Truth

- **GitHub Issues** (via `gh` CLI)

The tool **only reads** from GitHub.
It never mutates issues (open/close/edit).

---

## What the Tool Does

1. Fetches **OPEN + CLOSED** issues from GitHub
2. Splits them into open / closed sets
3. Sorts deterministically:
   - Open issues: ascending by issue number
   - Closed issues: descending by closed timestamp
4. Renders stable markdown output
5. Updates archive files **only if content changed**
6. Commits and pushes changes (unless disabled)

---

## Output Files

Only these files may be modified:

- `docs/issues/open_issues.md`
- `docs/issues/closed_issues.md`

No timestamps such as “generated at” are ever included.

---

## Determinism & Idempotence

- Running the tool twice with no GitHub changes produces **no diff**
- Byte-identical output is guaranteed
- Rendering order and formatting are stable

---

## Requirements

- Python 3.9+
- `gh` CLI authenticated
- Clean git working tree (default)

---

## Usage

Canonical invocation:

```bash
python3 scripts/sync_issues_archive.py
```

### Dry run

Detects changes without writing files or committing:

```bash
python3 scripts/sync_issues_archive.py --dry-run
```

### Override dirty working tree

```bash
python3 scripts/sync_issues_archive.py --allow-dirty
```

---

## CLI Flags

| Flag | Description |
|-----|------------|
| `--repo owner/name` | Explicit repository (auto-detect by default) |
| `--dry-run` | Detect changes only |
| `--no-commit` | Write files but do not commit |
| `--no-push` | Commit but do not push |
| `--allow-dirty` | Skip dirty working tree check |

---

## Git Behavior

- Dirty working tree → **FAIL-FAST**
- No diff → **no commit**
- Diff → write → commit → push

Commit message (fixed):

```
Docs: sync GitHub issues archive (open/closed)
```

---

## Typical Workflow

```bash
gh issue open ...
python3 scripts/sync_issues_archive.py
```

```bash
gh issue close <id>
python3 scripts/sync_issues_archive.py
```

---

## Explicit Non-Goals

- No AudioMason imports
- No runtime or CLI integration
- No interactive prompts
- No issue mutation
- No UI

---

## Status

Production-ready.  
Covered by unit tests in `tests/test_sync_issues_archive.py`.

END OF DOCUMENT
