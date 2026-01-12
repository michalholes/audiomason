# System installation notes (Debian / Ubuntu)

This document covers system-level prerequisites and operational notes.
End-user installation steps are documented in:
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

Configuration file location:

- /etc/audiomason/config.yaml

You must configure filesystem paths before first use.

Typical roots:
- drop_root: incoming sources
- stage_root: temporary working directory
- output_root: final library
- archive_root: long-term archive (optional)

All configured roots must exist and be writable by the user running AudioMason.

---

## Recommended filesystem layout

Example (adjust to your environment):

- /srv/audiobooks/inbox
- /srv/audiobooks/_stage
- /srv/audiobooks/ready
- /srv/audiobooks/archive

Ensure correct ownership and permissions.
Keep stage_root on fast storage if possible.

---

## First run checklist

1) Verify installation:

    audiomason --help

2) Confirm config exists:

    sudo ls -la /etc/audiomason/

3) Edit config:

    sudoedit /etc/audiomason/config.yaml

4) Create and permission your configured roots.

5) Run AudioMason as a non-root user.

---

## Troubleshooting

### APT signature warnings

If APT reports signature verification issues:
- stop
- verify key import and repository URL
- ensure you used the signed repository instructions

Maintainer repository details:
- docs/apt/README.md

### Missing ffmpeg

Install via APT:

    sudo apt update
    sudo apt install ffmpeg

### Permission denied on paths

Fix ownership/permissions for configured roots.
Do not run AudioMason as root to bypass permissions.

---

## Related docs

- docs/INSTALL.md
- docs/CONFIGURATION.md
- docs/MAINTENANCE.md
- docs/WORKFLOW.md
