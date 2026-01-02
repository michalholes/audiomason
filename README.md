# AudioMason

Deterministic, ASCII‑only CLI tool for **importing, normalizing, tagging, and publishing audiobooks** from messy real‑world sources.

AudioMason is designed for people who:
- have large audiobook libraries
- receive files in inconsistent formats (RARs, folders, bad tags, mixed encodings)
- want **repeatable, predictable results** instead of GUI guessing

---

## What AudioMason does

- Imports audiobooks from directories or archives
- Normalizes structure and filenames
- Applies clean, deterministic tagging
- Optionally fetches metadata (OpenLibrary, Google Books)
- Publishes finished audiobooks to a final library

**Core principles:**
- Deterministic output (same input → same result)
- ASCII‑safe paths
- Fail‑fast (no silent guessing)
- CLI‑first, scriptable

---

## Installation (Debian / Ubuntu)

Download the `.deb` from **GitHub Releases** and install:

- Releases: https://github.com/michalholes/audiomason/releases

```bash
sudo dpkg -i audiomason_1.3.0_all.deb
```

Dependencies (installed automatically):
- Python 3.11+
- ffmpeg

After installation:

```bash
audiomason --help
```

---

## Configuration

AudioMason uses a single system config file:

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

---

## Basic usage

```bash
audiomason
```

AudioMason will:
1. Scan the drop directory
2. Ask which sources to import
3. Normalize and tag audio
4. Publish to the output directory

Non‑interactive mode:

```bash
audiomason --yes
```

Dry‑run (no filesystem changes):

```bash
audiomason --dry-run
```

---

## Why not another audiobook tool?

AudioMason intentionally avoids:
- GUI workflows
- fuzzy auto‑guessing
- hidden state

Instead, it provides:
- explicit prompts
- reproducible pipelines
- transparent logs

It is built for **long‑term library maintenance**, not one‑off imports.

---

## Status

AudioMason is **actively developed** and used in real libraries.

Expect:
- breaking changes before 2.0
- conservative defaults
- preference for correctness over convenience

---

## Bugs & feature requests

Please report bugs and request features via GitHub Issues:

👉 https://github.com/michalholes/audiomason/issues

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

