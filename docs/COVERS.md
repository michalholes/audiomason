
# Covers

Covers are decided in PREPARE (preflight) and applied in PROCESS.

## Sources (priority in non-interactive mode)
- File cover: `cover.<ext>` found in book group or stage root
- Embedded MP3 cover (APIC)
- Else: skip

In interactive mode, user may also provide a URL/path override.

## URL covers + cache
URL covers are downloaded and cached under `paths.cache` (hashed by URL).
Subsequent runs reuse cached variants.

## Wipe behavior
If the user chooses full ID3 wipe, AudioMason must preserve an existing embedded MP3 cover across wipe (re-applied automatically).
