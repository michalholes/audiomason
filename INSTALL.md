INSTALLATION – AudioMason v1.0.0

This document describes supported installation methods for AudioMason.
AudioMason is a CLI tool intended for local, explicit execution.
There is no daemon, service, or background component.


SUPPORTED PLATFORMS

- Linux (tested on Debian-based systems)
- Python 3.11+
- ffmpeg available in PATH
- Standard Unix tools (unzip, rsync, etc.)

macOS and Windows are not officially supported.


RUNTIME DEPENDENCIES

The following tools must be installed system-wide:

- python3 (>= 3.11)
- ffmpeg
- unzip
- rsync

Optional (depending on input formats):

- p7zip-full
- unrar-free


INSTALL DEPENDENCIES (Debian / Ubuntu)

sudo apt update
sudo apt install -y   python3   python3-venv   ffmpeg   unzip   rsync   p7zip-full   unrar-free


INSTALLATION METHODS


METHOD 1 – Local virtualenv (recommended)

1. Clone repository:

git clone https://github.com/michalholes/audiomason.git
cd audiomason

2. Create virtual environment:

python3 -m venv .venv
. .venv/bin/activate

3. Install AudioMason:

pip install -e .

4. Verify:

audiomason --help

Deactivate when done:

deactivate


METHOD 2 – Repo-local wrapper (optional)

If the repository contains the ./am helper script, it can be used
as a convenience wrapper around the venv-installed binary.

./am --help


METHOD 3 – pipx (advanced users)

pipx install git+https://github.com/michalholes/audiomason.git


CONFIGURATION FILES

Load order:

1. Built-in defaults
2. /etc/audiomason/config.yaml
3. ~/.config/audiomason/config.yaml


VERIFY INSTALLATION

audiomason --dry-run --yes
audiomason verify


UNINSTALL

Virtualenv:
rm -rf .venv

pipx:
pipx uninstall audiomason


DESIGN NOTE

AudioMason is intentionally boring, predictable, and safe.
That is a feature.
