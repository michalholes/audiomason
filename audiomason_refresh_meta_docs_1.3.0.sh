#!/usr/bin/env bash
set -euo pipefail

# AudioMason docs/metadata refresh to 1.3.0
# Updates:
# - ROADMAP (ROADMAP.md or docs/ROADMAP.md if present)
# - docs/INSTALL-SYSTEM.md (rewrite)
# - requirements.txt (mark as legacy if present; keep existing deps)
# - audiomason/am (only replaces version strings if present)
# - pyproject.toml (set version to 1.3.0 if a version field exists)
#
# Run from repo root.

if [ ! -f "pyproject.toml" ]; then
  echo "ERROR: run this from the AudioMason repo root (pyproject.toml not found)."
  exit 1
fi

VERSION="1.3.0"
DATE="$(date +%Y-%m-%d)"

# -----------------------------
# ROADMAP
# -----------------------------
ROADMAP_PATH=""
if [ -f "ROADMAP.md" ]; then
  ROADMAP_PATH="ROADMAP.md"
elif [ -f "docs/ROADMAP.md" ]; then
  ROADMAP_PATH="docs/ROADMAP.md"
fi

if [ -n "$ROADMAP_PATH" ]; then
  cat > "$ROADMAP_PATH" <<MD
# Roadmap

This roadmap reflects the project state as of **v${VERSION}** (${DATE}).

## Current status (v${VERSION})

- Core import workflow is stable and documented.
- Phase contract is established: STAGE → PREPARE → PROCESS → FINALIZE.
- Processing is deterministic and resumable (manifest-backed decisions).
- Covers are robust (file/embedded/URL) and embedded MP3 covers are preserved across full ID3 wipe.

## Near-term goals

### Packaging
- Finish Debian packaging (buildable .deb, versioned release artifacts).
- Install defaults:
  - /etc/audiomason/config.yaml
  - /var/lib/audiomason as a reasonable default data root (override via AUDIOMASON_DATA_ROOT).

### Documentation polish
- Keep README/INSTALL in sync with releases.
- Add a short troubleshooting section (common ffmpeg / permissions issues).
- Optional: add a man page (audiomason(1)).

### UX improvements (optional)
- Shell completion (bash/zsh) for the CLI.
- Clearer error messages for missing ffmpeg / invalid sources.

## Future ideas (not committed)
- Optional automated cover fetching from external services (opt-in).
- Optional library validation tools (verify outputs, detect duplicates).
MD
  echo "OK: wrote $ROADMAP_PATH"
else
  echo "WARN: ROADMAP.md not found (skipped)"
fi

# -----------------------------
# docs/INSTALL-SYSTEM.md (rewrite)
# -----------------------------
mkdir -p docs
cat > docs/INSTALL-SYSTEM.md <<'MD'
# System installation

This document describes installing AudioMason as a system tool (no manual venv management).

Preferred approaches:
- pipx (isolated, user-level)
- Debian package (system-level)

If you are packaging for Debian, use the `debian/` skeleton in this repo as a starting point.

## Requirements

- Python 3.11+
- ffmpeg

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3 ffmpeg
```

## Option A: pipx (recommended)

pipx gives you an isolated environment without you managing a venv:

```bash
sudo apt-get install -y pipx
pipx ensurepath
pipx install "git+https://github.com/michalholes/audiomason.git"
```

Run:

```bash
audiomason
```

Upgrade:

```bash
pipx upgrade audiomason
```

## Option B: Debian package (target layout)

A Debian package should install:

- CLI: /usr/bin/audiomason
- Config: /etc/audiomason/config.yaml (conffile)
- Default data root: /var/lib/audiomason (users may override via AUDIOMASON_DATA_ROOT)

After install, create or adjust your configuration at:

- /etc/audiomason/config.yaml

Then run:

```bash
audiomason
```

## Configuration roots

Recommended portable approach:

```bash
export AUDIOMASON_DATA_ROOT="$HOME/audiomason_data"
```

All relative paths in configuration resolve relative to AUDIOMASON_DATA_ROOT.
MD
echo "OK: wrote docs/INSTALL-SYSTEM.md"

# -----------------------------
# requirements.txt (legacy marker)
# -----------------------------
if [ -f "requirements.txt" ]; then
  if ! head -n 5 requirements.txt | grep -q "LEGACY"; then
    tmp="$(mktemp)"
    cat > "$tmp" <<'HDR'
# LEGACY: requirements.txt is not the primary install path for AudioMason.
# Prefer one of:
#   pipx install "git+https://github.com/michalholes/audiomason.git"
#   python3 -m pip install --user -U "git+https://github.com/michalholes/audiomason.git"
# For development:
#   pip install -e .
HDR
    cat requirements.txt >> "$tmp"
    mv "$tmp" requirements.txt
    echo "OK: updated requirements.txt header"
  else
    echo "OK: requirements.txt already marked as legacy"
  fi
else
  echo "WARN: requirements.txt not found (skipped)"
fi

# -----------------------------
# audiomason/am (version string replacement only)
# -----------------------------
if [ -f "audiomason/am" ]; then
  # Replace obvious version mentions like "1.0.0" or "v1.0.0" with current VERSION
  # Only touch if any of these patterns are present.
  if grep -qE "v?1\.0\.0" "audiomason/am"; then
    sed -i -E "s/\bv?1\.0\.0\b/v${VERSION}/g; s/\b1\.0\.0\b/${VERSION}/g" "audiomason/am"
    echo "OK: updated version strings in audiomason/am"
  else
    echo "OK: audiomason/am has no 1.0.0 version strings (no change)"
  fi
else
  echo "WARN: audiomason/am not found (skipped)"
fi

# -----------------------------
# pyproject.toml (set version if present)
# -----------------------------
if grep -qE '^\s*version\s*=\s*"' pyproject.toml; then
  sed -i -E "s/^(\s*version\s*=\s*\")([^\"]+)(\".*)$/\1${VERSION}\3/" pyproject.toml
  echo "OK: set pyproject.toml version=${VERSION}"
else
  echo "WARN: pyproject.toml has no version= field (skipped)"
fi

# -----------------------------
# Ensure README has up-to-date docs links (idempotent)
# -----------------------------
if [ -f README.md ]; then
  if ! grep -q "^## Documentation" README.md; then
    # do nothing; README may use a different structure after rewrite
    :
  fi
  # Ensure INSTALL-SYSTEM link is present somewhere under documentation section
  if ! grep -q "docs/INSTALL-SYSTEM.md" README.md; then
    # Try to insert under "## Documentation" if exists; otherwise append a small block at end.
    if grep -q "^## Documentation" README.md; then
      awk '
        BEGIN{added=0}
        {print}
        $0=="## Documentation" && added==0 {
          # next lines already printed; add after existing list end later is tricky
        }
      ' README.md > /tmp/readme.$$ || true
      # Simple append (safe and deterministic)
      printf '\n- System install: docs/INSTALL-SYSTEM.md\n' >> README.md
    else
      printf '\n\n## System install\n\nSee: docs/INSTALL-SYSTEM.md\n' >> README.md
    fi
    echo "OK: added docs/INSTALL-SYSTEM.md reference to README.md"
  else
    echo "OK: README already references docs/INSTALL-SYSTEM.md"
  fi
else
  echo "WARN: README.md not found (skipped)"
fi

# -----------------------------
# Tests + commit + push
# -----------------------------
. .venv/bin/activate && \
python -m pytest -q && \
git add -A && \
git commit -m "Docs: refresh roadmap/system install and align metadata for v1.3.0" && \
git push && \
deactivate
