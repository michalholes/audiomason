# CLI

This document describes the AudioMason command-line interface.

Installation steps:
- README.md
- docs/INSTALL.md

Configuration:
- /etc/audiomason/config.yaml
- docs/CONFIGURATION.md

---

## Basic run

Run AudioMason in interactive mode:

    audiomason

AudioMason will scan the configured drop_root and guide you through source selection and processing.

---

## Non-interactive mode

Automatically accept prompts (use with care):

    audiomason --yes

This is intended for scripted workflows where input structure is already known and stable.

---

## Dry-run

Show what would happen without modifying the filesystem:

    audiomason --dry-run

Dry-run is recommended when validating a new configuration or new source structure.

---

## Quiet vs debug

Use quiet mode to reduce output:

    audiomason --quiet

Use debug logging for deep troubleshooting:

    audiomason --debug

When reporting bugs, include relevant debug output when possible.

---

## Publish control

Publishing behavior is controlled by configuration and can typically be overridden via CLI options (if available in your build).

Reference:
- docs/CONFIGURATION.md
- docs/WORKFLOW.md

---

## Exit behavior

AudioMason is designed to fail-fast:
- errors are surfaced early
- it avoids silent guessing

If a run fails:
- keep input intact
- capture full output
- include your config paths and a minimal directory listing when filing an issue

---

## Related docs

- docs/WORKFLOW.md
- docs/PIPELINE.md
- docs/COVERS.md
