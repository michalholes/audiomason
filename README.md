<p align="center">
  <img src="docs/assets/audiomason-logo.png" alt="AudioMason logo" width="200">
</p>

## AudioMason

Deterministic, ASCII-only CLI tool for **importing, normalizing, tagging, and publishing audiobooks** from messy real-world sources.

AudioMason is designed for people who:
- have large audiobook libraries
- receive files in inconsistent formats (RARs, folders, bad tags, mixed encodings)
- want **repeatable, predictable results** instead of GUI guessing

If the same input ever produces a different result, something is wrong - and that is taken seriously.

---

## What AudioMason does

- Imports audiobooks from directories or archives
- Normalizes structure and filenames
- Applies clean, deterministic tagging
- Optionally fetches metadata (OpenLibrary, Google Books)
- Publishes finished audiobooks to a final library

**Core principles:**
- Deterministic output (same input -> same result)
- ASCII-safe paths
- Fail-fast (no silent guessing)
- CLI-first, scriptable

---

## Installation (Debian / Ubuntu)

AudioMason is distributed via a **signed APT repository**.

### 1. Import repository signing key

```
curl -fsSL https://michalholes.github.io/audiomason/docs/apt/audiomason.gpg.asc | sudo tee /etc/apt/trusted.gpg.d/audiomason.asc > /dev/null
```

### 2. Add APT repository

```
echo "deb https://michalholes.github.io/audiomason stable main" | sudo tee /etc/apt/sources.list.d/audiomason.list
```

### 3. Install

```
sudo apt update
sudo apt install audiomason
```

APT will verify signatures automatically.
If it does not, stop - do not continue and do not guess.

Other installation methods (including GitHub Releases) are documented in:
- docs/INSTALL.md

---

## Configuration

AudioMason uses a single system configuration file:

```
/etc/audiomason/config.yaml
```

The file installed by the package is **fully commented** and safe by default.
You must uncomment and set paths before first use.

Minimal example:

```yaml
paths:
  drop_root: /srv/audiobooks/inbox
  stage_root: /srv/audiobooks/_stage
  output_root: /srv/audiobooks/ready
  archive_root: /srv/audiobooks/archive

import:
  publish: ask
```

Full reference:
- docs/CONFIGURATION.md

---

## Basic usage

```
audiomason
```

AudioMason will:
1. Scan the drop directory
2. Ask which sources to import
3. Normalize and tag audio
4. Publish to the output directory

Non-interactive mode:

```
audiomason --yes
```

Dry-run (no filesystem changes):

```
audiomason --dry-run
```

---

## Why not another audiobook tool?

AudioMason intentionally avoids:
- GUI workflows
- fuzzy auto-guessing
- hidden state

Instead, it provides:
- explicit prompts
- reproducible pipelines
- transparent logs

It is built for **long-term library maintenance**, not one-off imports.

---

## Status

AudioMason is actively developed and used in real libraries.

Expect:
- breaking changes before 2.0
- conservative defaults
- preference for correctness over convenience

---

## Bugs & feature requests

Please report bugs and request features via GitHub Issues:

https://github.com/michalholes/audiomason/issues

Include:
- command used
- relevant logs
- sample directory structure (if possible)

---

## License

MIT

---

## Author

Michal Holeš  
https://github.com/michalholes

## Support AudioMason

If you find AudioMason useful, you can support its development here:

- https://buymeacoffee.com/audiomason

Support is fully optional and never enabled by default.

- `audiomason --support` prints the support link and exits.
- `audiomason --version` includes the support link.
- Set `AUDIOMASON_SUPPORT=1` to show the support link after a successful run (never enabled by default).

### Support banner behavior

- After a successful `import`, AudioMason prints the support link by default.
- The banner is suppressed automatically in `--quiet` and `--json` modes.
- Disable it explicitly with `import --no-support` or in config:

  ```yaml
  support:
    enabled: false
  ```
