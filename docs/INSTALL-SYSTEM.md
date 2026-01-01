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
