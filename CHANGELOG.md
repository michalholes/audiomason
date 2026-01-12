# Changelog
## [1.3.0] - 2026-01-02### Added- Complete end-user documentation (workflow, covers, pipeline, configuration)- Example and minimal configuration files### Fixed- Preserve embedded MP3 cover across full ID3 wipe (#55)- Multiple OpenLibrary edge cases and crashes- Stage cleanup and resume robustness### Changed- Preflight now fully owns all interactive decisions- PROCESS phase is strictly non-interactive- Configuration paths are portable and environment-rooted
All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [1.1.0] - 2025-01-XX
### Added
- Stable CLI for audiobook import (`audiomason`)
- Deterministic import pipeline (inbox → stage → ready → publish)
- Verify contract with CI-friendly exit codes
- Unit tests and CI (GitHub Actions)

### Fixed
- Packaging to src-layout
- CLI default behavior (implicit import)

### Notes
- ASCII-only paths and tags
- Author format: Surname.Name
