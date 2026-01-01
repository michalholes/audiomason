#!/usr/bin/env bash
set -euo pipefail

# AudioMason RELEASE PREP for v1.3.0
# Run from repo root

if [ ! -f "pyproject.toml" ]; then
  echo "ERROR: run from AudioMason repo root (pyproject.toml not found)"
  exit 1
fi

VERSION="1.3.0"
DATE="$(date +%Y-%m-%d)"

# -------------------------------
# CHANGELOG.md
# -------------------------------
if [ ! -f CHANGELOG.md ]; then
  cat > CHANGELOG.md <<EOF
# Changelog

All notable changes to this project are documented in this file.

## [${VERSION}] - ${DATE}

### Added
- Complete end-user documentation (workflow, covers, pipeline, configuration)
- Example and minimal configuration files

### Fixed
- Preserve embedded MP3 cover across full ID3 wipe (#55)
- Multiple OpenLibrary edge cases and crashes
- Stage cleanup and resume robustness

### Changed
- Preflight now fully owns all interactive decisions
- PROCESS phase is strictly non-interactive
- Configuration paths are portable and environment-rooted

EOF
else
  if ! grep -q "\[${VERSION}\]" CHANGELOG.md; then
    sed -i "1a\
\
## [${VERSION}] - ${DATE}\
\
### Added\
- Complete end-user documentation (workflow, covers, pipeline, configuration)\
- Example and minimal configuration files\
\
### Fixed\
- Preserve embedded MP3 cover across full ID3 wipe (#55)\
- Multiple OpenLibrary edge cases and crashes\
- Stage cleanup and resume robustness\
\
### Changed\
- Preflight now fully owns all interactive decisions\
- PROCESS phase is strictly non-interactive\
- Configuration paths are portable and environment-rooted\
" CHANGELOG.md
  fi
fi

# -------------------------------
# README quick start (append once)
# -------------------------------
if ! grep -q "## Quick start" README.md; then
  cat >> README.md <<'EOF'

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
EOF
fi

# -------------------------------
# Tests + commit
# -------------------------------
. .venv/bin/activate && python -m pytest -q && git add CHANGELOG.md README.md && git commit -m "Release prep: v${VERSION}" && git tag -a "v${VERSION}" -m "AudioMason v${VERSION}" && git push && git push origin "v${VERSION}" && deactivate
