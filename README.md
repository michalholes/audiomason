# AudioMason

AudioMason is a deterministic audiobook processing pipeline.
Same input. Same output. Every time.
If that ever changes, it is a bug — not a feature, not magic.

## Philosophy

AudioMason is built around strict determinism:
- no hidden state
- no random decisions
- no "best effort" guessing

This makes failures boring and debugging possible.

## Installation (APT)

AudioMason is distributed via a signed APT repository.

See full installation details:
- docs/INSTALL.md
- docs/INSTALL-SYSTEM.md

## Upgrade

Standard APT upgrade applies:

    apt update
    apt upgrade audiomason

## Removal

    apt remove audiomason

## Configuration

Configuration file location:

    /etc/audiomason/config.yaml

Configuration reference:
- docs/CONFIGURATION.md

## Command Line Interface

CLI usage and flags:
- docs/CLI.md

## Processing Pipeline

How AudioMason processes audio:
- docs/PIPELINE.md
- docs/WORKFLOW.md

## Covers

Cover handling rules:
- docs/COVERS.md

## APT Repository (Maintainers)

APT repository structure and publishing:
- docs/apt/README.md
