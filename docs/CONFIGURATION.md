# Configuration

AudioMason uses a single system configuration file:

- /etc/audiomason/config.yaml

This file is installed by the package and is safe by default, but you must set real paths before first use.

Installation:
- README.md
- docs/INSTALL.md

System notes:
- docs/INSTALL-SYSTEM.md

---

## Core concept: roots

AudioMason operates on configured filesystem roots. Typical keys:

- drop_root: incoming sources (files, folders, archives)
- stage_root: temporary working directory for processing
- output_root: final published library
- archive_root: long-term archive (optional but recommended)

All configured roots must exist and be writable by the user running AudioMason.

---

## Minimal example

```yaml
paths:
  drop_root: /srv/audiobooks/inbox
  stage_root: /srv/audiobooks/_stage
  output_root: /srv/audiobooks/ready
  archive_root: /srv/audiobooks/archive

import:
  publish: ask
```

---

## Guidance

Recommended practices:
- keep stage_root on reliable, fast storage
- keep output_root and archive_root on stable mount points
- avoid changing configured roots between runs unless you know exactly why

---

## Global prompt disable: `prompts.disable`

AudioMason supports a **global prompt-disable list** to make imports fully deterministic / unattended.

Config key:

```yaml
prompts:
  disable: ["*"]   # disable ALL prompts (preflight + non-preflight)
```

Selective disable:

```yaml
prompts:
  disable:
    - choose_source
    - choose_books
    - skip_processed_books
```

Rules (fail-fast validation):
- `prompts.disable` must be a **list**
- unknown keys are an error
- duplicates are an error
- `"*"` must not be combined with other keys

Behavior when a prompt is disabled:
- use the **existing deterministic default** (same behavior as pressing Enter)
- if there is no deterministic default for the situation, AudioMason **fails fast**

## Related docs

- docs/WORKFLOW.md
- docs/PIPELINE.md
- docs/MAINTENANCE.md
