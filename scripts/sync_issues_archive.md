# sync_issues_archive.py

Standalone helper tool for deterministic synchronization of GitHub issues
into repository archives.

This tool is **NOT** part of the AudioMason runtime or CLI.
It is an auxiliary maintenance script intended to be run manually
or as a follow-up step after GitHub issue operations.

---

## Purpose

The repository maintains canonical issue archives:

- `docs/issues/open_issues.md`
- `docs/issues/closed_issues.md`
- `docs/issues/all_issues.yaml`

These files must reflect the **exact state of GitHub issues**, without manual editing.

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

## Output Files

Only these files may be modified:

- `docs/issues/open_issues.md`
- `docs/issues/closed_issues.md`
- `docs/issues/all_issues.yaml`

No timestamps such as “generated at” are ever included.

### all_issues.yaml

Deterministic YAML (YAML 1.2 JSON-subset) export of **all issues** (open + closed),
including:
- core issue data,
- full comments,
- full timeline events (including `closed`, `reopened`, `referenced`, etc.),
- commit SHA + URL references where present in timeline events.

Stable ordering:
- issues: by issue number ascending
- comments: by `created_at` ascending, tie-break by `id`
- timeline: by `created_at` ascending, tie-break by (`event`, `id`)

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

## Explicit Non-Goals

- No AudioMason imports
- No runtime or CLI integration
- No interactive prompts
- No issue mutation
- No UI

---

END OF DOCUMENT
