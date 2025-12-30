AudioMason

AudioMason is a deterministic, ASCII-only CLI tool for importing, normalizing,
splitting, tagging, and organizing audiobooks on Linux systems.


STATUS

Version: 1.0.0
Stability: stable
CI: GitHub Actions (pytest)
Python: 3.11+
Execution model: CLI (no daemon)


DESIGN GOALS

- Safe by default (never overwrite existing books)
- Deterministic output (same input -> same structure)
- ASCII-only filenames and tags
- Interactive by default, non-interactive when requested
- No background services, no watchers
- Explicit stages: inbox -> stage -> ready -> optional publish


INSTALLATION (development / local)

python3 -m venv .venv
. .venv/bin/activate
pip install -e .

Optional convenience wrapper (repo-local):

./am --help


USAGE

Default command (implicit import):

audiomason

Explicit equivalent:

audiomason import

Verify existing library:

audiomason verify

Global flags:

--yes          non-interactive (accept defaults)
--dry-run      show actions without modifying data
--quiet        minimal output
--verbose      verbose output


IMPORT WORKFLOW (v1.0.0)

1. Scan inbox (ignores .abook_ignore)
2. Stage input:
   - unpack .rar, .zip, .7z
   - or copy directory / file
3. Detect audiobook candidates
4. Audio processing:
   - .m4a -> MP3
   - split by chapters if available
   - fallback to single MP3
5. Rename tracks: 01.mp3 ... N.mp3
6. Cover selection (first match wins):
   - cover.* sidecar
   - embedded cover
   - attached picture in M4A
   - manual prompt
7. ID3 tagging (every MP3):
   - Artist (Surname.Name)
   - Album
   - Track number i/N
   - Genre = Audiobook
   - Embedded cover
8. Cleanup (remove non-MP3 artifacts)
9. Publish (ask / yes / no)
10. Stage cleanup (skipped in --dry-run)


VERIFY MODE

audiomason verify

Checks:

- directory structure: Author/Book/*.mp3
- sequential tracks 01..N
- strict TRCK = i/N
- consistent Artist / Album
- embedded cover present

Exit codes:

0  OK
2  violations found (CI-friendly)

Verify is read-only and has no side effects.


CONFIGURATION

Configuration load order:

1. Built-in defaults
2. /etc/audiomason/config.yaml
3. ~/.config/audiomason/config.yaml

Later sources override earlier ones.

Example configuration:

paths:
  inbox: /mnt/warez/abooksinbox
  stage: /mnt/warez/_am_stage
  ready: /mnt/warez/_am_ready
  archive_ro: /mnt/warez/abooks

publish: ask

ffmpeg:
  loglevel: warning
  loudnorm: false
  q_a: 2


CONSTRAINTS

- ASCII-only filenames and tags
- Author format: Surname.Name
- Track filenames: 01.mp3, 02.mp3, ...
- No automatic metadata fetching
- No background processing


REPOSITORY LAYOUT

src/audiomason/
  cli.py          CLI entrypoint
  import_flow.py  main orchestration
  audio.py        audio conversion
  covers.py       cover detection and embedding
  tags.py         ID3 tagging
  verify.py       archive verification
  util.py         shared helpers
  planner.py      public planning helpers (v1.1+)
  _legacy/        compatibility code


WHAT v1.0.0 DOES NOT INCLUDE

- Batch non-interactive mode
- Metadata providers (ISBN, APIs)
- Cover cache
- Cue sheet / chapters.txt parsing
- Docker-first workflow

These are intentionally deferred to later versions.


LICENSE

See LICENSE.


AudioMason is designed to be boring, predictable, and safe.
That is a feature.
