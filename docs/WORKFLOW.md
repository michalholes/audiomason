
# AudioMason workflow

AudioMason runs an import as a deterministic sequence with explicit phase boundaries:

- STAGE: copy/unpack source into stage
- PREPARE: all interactive decisions (title, cover choice, destination conflict handling)
- PROCESS: filesystem writes to destination, tagging, cover application (no prompts)
- FINALIZE: ignore bookkeeping + optional stage cleanup + optional JSON report

## Stage + resume
- If a staged run exists and fingerprint matches, AudioMason can reuse stage.
- If manifest answers are reused, prompts are skipped (except where required by flags).

## Phases
### STAGE
- Copies source under stage/<slug>/src
- Converts .m4a to .mp3 (and chapter split when possible)

### PREPARE
- Author decision is per-source.
- Per-book: title, cover_mode, destination conflict resolution are decided and persisted to manifest.

### PROCESS
- Copies mp3s to destination
- Optional full ID3 wipe
- Applies process steps according to pipeline order: rename/tags/cover/publish

### FINALIZE
- Adds processed source to ignore list
- Optional clean stage on success
- Optional JSON report mode (if enabled)
