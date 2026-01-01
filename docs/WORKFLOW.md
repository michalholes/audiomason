# Workflow

AudioMason imports a source as a deterministic run with explicit phase boundaries:

- STAGE: materialize source into stage (copy or unpack)
- PREPARE: collect ALL decisions (interactive prompts allowed here only)
- PROCESS: produce destination output (NO prompts)
- FINALIZE: bookkeeping and optional cleanup/reporting

This contract exists to make imports resumable and predictable, and to keep PROCESS fully non-interactive.

## Terms

- Source: a directory or a supported archive placed in the inbox
- Stage run: stage/<slug(source)> with a manifest file
- Book group: either __ROOT_AUDIO__ or a top-level directory containing audio

## High level flow

1) Select source(s) from inbox (ignored sources are filtered out)
2) Stage source into stage run
3) Convert M4A to MP3 in stage (recursive)
4) Detect book groups
5) PREPARE decisions (author, per-book metadata, cover decision, destination conflict resolution)
6) PROCESS each selected book group into destination (no prompts)
7) FINALIZE: mark source as ignored and optionally clean stage on success
8) Optional: print JSON report when enabled

## Phase details

### STAGE

Responsibilities:
- Copy a directory source into stage, OR unpack an archive into stage
- Ensure stage directories exist
- Convert M4A to MP3 in place (recursive)

Notes:
- Stage is a working area and can be deleted safely
- Stage reuse is allowed when the stage fingerprint matches the current source

### PREPARE (preflight)

Responsibilities:
- Global decisions per source:
  - publish (archive vs output destination root)
  - wipe ID3 before tagging
  - clean stage after success
  - author name
- Per-book decisions:
  - title and output title
  - cover mode (file / embedded / skip)
  - destination conflict handling (overwrite or choose an alternative destination/folder)
- Persist decisions to the manifest so PROCESS can run without prompts

Rules:
- PREPARE may prompt when interactive mode is enabled
- PREPARE must not modify destination output trees

### PROCESS

Responsibilities:
- Copy MP3s from selected book group to destination folder
- Optional full ID3 wipe (if selected in PREPARE)
- Apply process steps (order controlled by pipeline_steps):
  - rename
  - tags
  - cover
  - publish (a visibility step; destination root already chosen)

Rules:
- PROCESS must not prompt (even in interactive sessions)
- PROCESS uses manifest decisions only

### FINALIZE

Responsibilities:
- Mark processed source as ignored (so it no longer shows up in inbox selection)
- Optional stage cleanup if selected (successful runs only)
- Optional JSON report output when enabled

## Resume behavior

Stage reuse exists to avoid re-copying and to allow crash-resume:

- If a staged run exists and the fingerprint matches, the user can reuse stage
- If saved answers are reused, prompts are skipped and PROCESS can continue
- Already processed book groups may be skipped only after an explicit user prompt
