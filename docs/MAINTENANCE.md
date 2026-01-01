# Maintenance and versioning

This document defines the **maintenance contract** for AudioMason starting with **v1.3.0**.
Its purpose is to keep behavior stable, predictable, and auditable over time.

---

## Stability contract

- Documented behavior is treated as a **contract**.
- Changes that alter documented behavior require a **new feature request** and a **minor or major version bump**.
- Undocumented behavior must not be relied upon.

---

## Versioning policy (SemVer)

AudioMason follows semantic versioning: MAJOR.MINOR.PATCH

### PATCH (x.y.Z)
Used for:
- bug fixes that do NOT change documented behavior
- internal refactors with identical observable behavior
- documentation fixes and clarifications

Requirements:
- reproducible bug report
- tests updated or added when applicable
- no new configuration keys
- no CLI behavior changes

### MINOR (x.Y.0)
Used for:
- new features
- new CLI flags or subcommands
- new configuration keys
- changes that extend documented behavior

Requirements:
- documentation update
- feature request or design note
- clear migration notes (if relevant)

### MAJOR (X.0.0)
Used for:
- breaking changes
- removal or renaming of CLI flags
- changes to workflow phase contracts
- changes to default filesystem layout

Requirements:
- explicit migration guide
- clear announcement of breaking changes

---

## Configuration changes

- `configuration.example.yaml` is the **single source of truth** for supported configuration keys.
- If a key is not present there, it is not supported.
- Adding or changing configuration keys requires at least a MINOR version bump.

---

## CLI changes

- The CLI reference in `docs/CLI.md` is authoritative.
- Adding flags or subcommands requires a MINOR version bump.
- Removing or changing flags requires a MAJOR version bump.

---

## Bug fixes

A bug fix must:
- preserve documented behavior
- not introduce new prompts or side effects
- not change default outcomes

If a bug fix changes observable behavior, it is considered a feature change.

---

## Documentation

- Documentation must be updated in the same release as behavior changes.
- README is an overview and index.
- Detailed contracts live in `docs/`.

---

## Release checklist

Before tagging a release:
- tests are green
- README reflects current capabilities
- docs/ are consistent with behavior
- CHANGELOG.md is updated

---

## Maintenance mode

AudioMason is in **maintenance-first mode**:
- stability over novelty
- changes are deliberate and documented
- regressions are treated as release blockers
