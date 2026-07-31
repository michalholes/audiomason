# Change: User-space install script

Added `scripts/install-audiomason.sh` — a self-contained installer that
downloads AudioMason from GitHub Releases and installs it into user space
(~/.local) without root access.

The script:
- Downloads the .deb package from GitHub Releases
- Creates a Python venv with required dependencies
- Extracts the audiomason package into the venv
- Creates a wrapper in ~/.local/bin/
- Copies the example config on first install

Supports `--version`, `--dir`, and `--dry-run` flags.
