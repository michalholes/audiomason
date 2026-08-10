Type: internal
Area: core
Summary: Extract staging and detection helpers into stage_detect_runtime (no behavior change)
Details:
- New module src/audiomason/stage_detect_runtime.py with reset_dir, stage_source, has_audio_files_here, find_first_m4a, collect_audio_files.
- import_flow now calls thin wrappers delegating to the new helpers, reducing monolith surface.
- Behavior preserved; ordering and logs unchanged.
