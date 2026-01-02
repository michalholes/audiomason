# System installation notes (Debian / Ubuntu)

This document covers system-level prerequisites and operational notes.
End-user installation steps (APT key/repo install) are documented in:
- README.md
- docs/INSTALL.md

---

## Requirements

- Debian/Ubuntu system with APT
- Python 3.11+
- ffmpeg

AudioMason is packaged as a .deb and installs system-wide.

---

## Paths and permissions

AudioMason reads its configuration from:

- /etc/audiomason/config.yaml

You must configure filesystem paths before first use. Typical layout:

- drop_root: incoming sources (files, folders, archives)
- stage_root: temporary working directory
- output_root: final published library
- archive_root: long-term archive (optional but recommended)

All configured roots must be writable by the user running AudioMason.

---

## Recommended filesystem layout

Example (adjust to your environment):

- /srv/audiobooks/inbox
- /srv/audiobooks/_stage
- /srv/audiobooks/ready
- /srv/audiobooks/archive

Make sure you:
- create the directories
- set correct ownership and permissions
- keep stage on fast storage if possible

---

## First run checklist

1) Confirm installation:

    audiomason --help

2) Confirm config exists:

    sudo ls -la /etc/audiomason/

3) Edit config:

    sudoedit /etc/audiomason/config.yaml

4) Create and permission your configured roots.

5) Run AudioMason from a non-root user.

---

## Troubleshooting

### APT signature warnings

If APT reports signature verification issues:
- stop
- verify the key import and repository URL
- ensure you are using the signed repository instructions in README/docs/INSTALL.md

Maintainer repository details:
- docs/apt/README.md

### Missing ffmpeg

If ffmpeg is missing, install it via APT:

    sudo apt update
    sudo apt install ffmpeg

### Permission denied on configured paths

Fix ownership/permissions for your configured roots.
Do not run AudioMason as root to "make it work".

---

## Related docs

- docs/INSTALL.md
- docs/CONFIGURATION.md
- docs/MAINTENANCE.md
- docs/WORKFLOW.md
