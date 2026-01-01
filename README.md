# AudioMason

AudioMason is a **deterministic audiobook import and tagging tool** with a fully staged, resumable workflow.
It is designed to be safe for repeated runs, partial failures, and large libraries.

---

## What AudioMason does

- Imports audiobooks from directories or archives
- Produces clean, consistently named MP3 outputs
- Applies tags and covers deterministically
- Separates **decision-making** from **processing**
- Allows safe resume after interruption or crash

AudioMason is not a media player or library server.
It focuses exclusively on **import, normalization, and preparation** of audiobooks.

---

## Key features (v1.3.0)

### Deterministic workflow
- Explicit phases: **STAGE → PREPARE → PROCESS → FINALIZE**
- PROCESS phase is **strictly non-interactive**
- All user decisions are persisted in a manifest

### Resumable imports
- Stage reuse when source fingerprint matches
- Ability to skip already processed books
- Safe to rerun after crash or interruption

### Cover handling
- Covers selected in PREPARE (never during processing)
- Supported sources:
  - cover image files
  - embedded MP3 covers
  - embedded M4A covers
  - URL or local path overrides
- Embedded MP3 covers are **preserved across full ID3 wipe**

### Flexible pipeline
- Configurable pipeline order via `pipeline_steps`
- Validation and fail-fast checks on invalid ordering
- Clear separation of stage-level vs process-level steps

### Safety and consistency
- Deterministic file naming and ordering
- Robust destination conflict handling
- Processed sources are automatically ignored
- Optional stage cleanup after successful import

### Metadata assistance
- Author and title normalization
- Optional OpenLibrary validation and suggestions
- Diacritics-safe comparisons

### Reporting and dry-run
- Dry-run mode with per-book summary
- Optional machine-readable JSON report

---

## Quick start

```bash
git clone https://github.com/michalholes/audiomason.git
cd audiomason
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

cp configuration.minimal.yaml configuration.yaml
export AUDIOMASON_DATA_ROOT="$HOME/audiomason_data"

audiomason
```

---

## Installation

Multiple installation methods are supported:

- pipx (recommended, isolated)
- pip --user
- system pip
- Debian package (layout prepared)

See: docs/INSTALL.md

---

## Documentation

- Workflow: docs/WORKFLOW.md
- Covers: docs/COVERS.md
- Pipeline: docs/PIPELINE.md
- Configuration: docs/CONFIGURATION.md
- Installation: docs/INSTALL.md

---

## Project status

- Version: **1.3.0**
- Status: **stable**
- Behavior is documented and treated as a contract
- New features are added via explicit feature requests

- System install: docs/INSTALL-SYSTEM.md
- CLI reference: docs/CLI.md
- Maintenance: docs/MAINTENANCE.md
