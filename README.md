# AudioMason

Deterministic, CLI-first tool for importing, normalizing, tagging, and publishing audiobooks from messy real-world sources.

## What it does

- Imports audiobooks from directories or archives
- Normalizes structure and filenames
- Applies clean, deterministic tagging
- Optionally fetches metadata (OpenLibrary, Google Books)
- Publishes finished audiobooks to a final library

Core principles:
- Deterministic output (same input -> same result)
- ASCII-safe paths
- Fail-fast (no silent guessing)
- Scriptable workflows

## Installation (Debian / Ubuntu)

### Recommended: install via APT (GitHub Pages)

```bash
curl -fsSL https://michalholes.github.io/audiomason/apt/audiomason.gpg.asc | sudo gpg --dearmor -o /usr/share/keyrings/audiomason-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/audiomason-archive-keyring.gpg] https://michalholes.github.io/audiomason/apt stable main" | sudo tee /etc/apt/sources.list.d/audiomason.list
sudo apt update
sudo apt install audiomason
```

Upgrade:

```bash
sudo apt update
sudo apt upgrade audiomason
```

Remove:

```bash
sudo apt remove --purge audiomason
```

Verify:

```bash
audiomason --version
man audiomason
```

## Configuration

AudioMason uses a single system config file:

```
/etc/audiomason/config.yaml
```

The package installs a fully-commented template. Uncomment and set your filesystem paths before first use.

## Basic usage

```bash
audiomason
```

Non-interactive mode:

```bash
audiomason --yes
```

Dry-run:

```bash
audiomason --dry-run
```

## Bugs and feature requests

https://github.com/michalholes/audiomason/issues

## License

MIT

## Author

Michal Holeš
https://github.com/michalholes
