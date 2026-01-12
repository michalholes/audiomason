# Covers

Covers are decided in PREPARE (preflight) and applied in PROCESS.

The core idea:
- PREPARE makes a deterministic cover decision per book
- PROCESS applies that decision and never prompts

## Cover sources

AudioMason can use covers from these sources:

- File cover in the book folder or stage root (cover.jpg, cover.jpeg, cover.png, cover.webp, cover.avif)
- Embedded MP3 cover (ID3 APIC)
- Embedded M4A cover (when available and extractable)
- URL or file path provided by the user (downloaded or copied into stage)

## Cover modes

PREPARE persists a cover_mode per book:

- file: use a detected or staged cover file
- embedded: use embedded cover from the first MP3
- skip: do not apply a cover

In non-interactive runs, cover_mode is chosen deterministically:
- prefer file cover when present
- otherwise use embedded cover when present
- otherwise skip

## URL covers and cache

When a URL is provided:
- AudioMason downloads it and stores it in the cache directory
- The cache filename is a stable hash of the URL with a detected extension
- Subsequent runs reuse cached data when present

## Wipe behavior (guarantee)

If the user selects full ID3 wipe before tagging:
- If the input MP3 already has an embedded cover, AudioMason preserves it across wipe
- The cover is re-applied automatically after wiping ID3
- This preserves existing art without requiring an intermediate cover file

If a different cover is chosen in PREPARE (file or URL override), that choice is applied later and may replace the preserved embedded cover.
