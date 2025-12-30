# AudioMason

AudioMason is a deterministic, ASCII-only CLI tool for importing, normalizing,
splitting, tagging, and organizing audiobooks on Linux systems.

It replaces a large monolithic import script with a maintainable, testable,
and CI-verified tool.

---

## Status

- Version: **1.0.0**
- Stability: **stable**
- CI: GitHub Actions (pytest)
- Python: 3.11+
- Execution model: CLI (no daemon)

---

## Design goals

- Safe by default (never overwrite existing books)
- Deterministic output (same input → same structure)
- ASCII-only filenames and tags
- Interactive by default, non-interactive when requested
- No background services, no watchers
- Explicit stages: inbox → stage → ready → optional publish

---

## Installation (development / local)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
