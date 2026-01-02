# Maintenance

This document covers operational and maintenance notes for AudioMason on Debian/Ubuntu.

Installation steps:
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

AudioMason works with:
- drop_root: incoming sources
- stage_root: temporary working area
- output_root: final library (published)
- archive_root: long-term archive (optional)

Recommended practices:
- keep stage_root on fast storage
- monitor free space (stage can temporarily grow during processing)
- use stable mount points

---

## Logs and debugging

Prefer running with explicit logging controls:
- docs/CLI.md

If a run fails:
- keep the source input intact
- capture full terminal output
- provide a minimal reproduction when possible

---

## Repository and packaging (maintainers)

Maintainer APT repository details:
- docs/apt/README.md

---

## Related docs

- docs/WORKFLOW.md
- docs/PIPELINE.md
- docs/COVERS.md
