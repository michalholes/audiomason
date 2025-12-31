# Changelog
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
