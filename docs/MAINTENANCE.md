# Maintenance

This document covers operational and maintenance notes for AudioMason on Debian/Ubuntu.

Installation steps are documented in:
- README.md
- docs/INSTALL.md

System prerequisites and first-run notes:
- docs/INSTALL-SYSTEM.md

---

## Upgrade

If installed via the signed APT repository:

    sudo apt update
    sudo apt upgrade audiomason

---

## Configuration management

Main config file:

- /etc/audiomason/config.yaml

Recommended workflow:
- keep paths stable
- keep stage_root on reliable storage
- treat archive_root as immutable output storage where practical

Configuration reference:
- docs/CONFIGURATION.md

---

## Filesystem hygiene

AudioMason works with three main areas:
- drop_root: incoming sources
- stage_root: temporary working area
- output_root: final library (published)
- archive_root: long-term archive (optional)

Recommended practices:
- keep stage_root on fast storage
- monitor free space (stage can temporarily grow during processing)
- use stable mount points (avoid changing roots between runs)

---

## Logs and debugging

Prefer running with explicit logging controls as documented in:
- docs/CLI.md

If a run fails:
- keep the source input intact
- capture the full terminal output
- provide the directory structure and a minimal reproduction if possible

---

## Repository and packaging (maintainers)

Maintainer APT repository details:
- docs/apt/README.md

---

## Related docs

- docs/WORKFLOW.md
- docs/PIPELINE.md
- docs/COVERS.md
