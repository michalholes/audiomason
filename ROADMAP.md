# Roadmap

This roadmap reflects the project state as of **v1.3.0** (2026-01-02).

## Current status (v1.3.0)

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
