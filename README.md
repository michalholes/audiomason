# AudioMason (skeleton)

This zip contains a ready-to-install Python package layout with a **legacy runner**
so you can run the existing monolithic script immediately, while we refactor into modules.

## Quick start (macOS)

```bash
cd /path/to/audiomason
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
audiomason --help
```

## Raspberry Pi / server (michal.holes.sk)

```bash
cd ~/src/audiomason
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
audiomason --dry-run
```

### Notes
- Current `audiomason` command executes the legacy monolith located at:
  `src/audiomason/_legacy/abook_import.py`
- Refactor modules exist as placeholders in `src/audiomason/` and will be filled next.
