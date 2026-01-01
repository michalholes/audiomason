#!/usr/bin/env bash
set -euo pipefail

# Rewrite docs/INSTALL.md to reflect AudioMason 1.3.0
# Run from repo root

if [ ! -f "pyproject.toml" ]; then
  echo "ERROR: run from AudioMason repo root"
  exit 1
fi

mkdir -p docs

cat > docs/INSTALL.md <<'MD'
# Installation

This document describes **supported installation methods for AudioMason 1.3.0**.

AudioMason can run without a virtual environment, but **isolated installs are strongly recommended**
to avoid conflicts with system Python packages.

---

## Requirements

- Python **3.11+**
- `ffmpeg` (required for conversion, splitting, and some cover operations)

### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip ffmpeg
```

---

## Installation options

### Option A: pipx (recommended)

`pipx` installs AudioMason into an isolated environment and exposes a global CLI,
without requiring you to manage a virtual environment manually.

```bash
sudo apt-get install -y pipx
pipx ensurepath
pipx install "git+https://github.com/michalholes/audiomason.git"
```

Run:

```bash
audiomason
```

Upgrade later:

```bash
pipx upgrade audiomason
```

---

### Option B: per-user install with pip

Installs under `~/.local` (no system-wide changes).

```bash
python3 -m pip install --user -U "git+https://github.com/michalholes/audiomason.git"
```

Ensure `~/.local/bin` is on your PATH, then run:

```bash
audiomason
```

---

### Option C: system-wide pip install (not recommended)

System installs may conflict with OS-managed Python packages.

On newer Debian-based systems you may need:

```bash
sudo python3 -m pip install --break-system-packages -U "git+https://github.com/michalholes/audiomason.git"
```

Then run:

```bash
audiomason
```

---

## Configuration

AudioMason requires a `configuration.yaml`.

You can start from one of the provided templates:

- `configuration.minimal.yaml`
- `configuration.example.yaml`

### Recommended setup (portable)

Use an explicit data root:

```bash
export AUDIOMASON_DATA_ROOT="$HOME/audiomason_data"
```

All relative paths in `configuration.yaml` resolve relative to this directory.

---

## First run

1. Create the inbox directory (or let AudioMason create it automatically).
2. Drop a source (directory or supported archive) into the inbox.
3. Run:

```bash
audiomason
```

AudioMason will:
- stage the source
- collect decisions in **PREPARE**
- execute a fully non-interactive **PROCESS**
- finalize and optionally clean stage data

---

## Notes

- AudioMason behavior is documented and treated as a **contract**
- Processing is deterministic and resumable
- New features are added via explicit feature requests
MD

. .venv/bin/activate && python -m pytest -q && git add docs/INSTALL.md && git commit -m "Docs: update INSTALL.md for AudioMason 1.3.0" && git push && deactivate
