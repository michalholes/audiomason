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


## Support banner (Buy Me a Coffee)

After every successful `import`, AudioMason prints a short support link:

`Support AudioMason: https://buymeacoffee.com/audiomason`

The banner is suppressed automatically in machine/silent modes:

- `--quiet`
- `--json`

You can disable the banner explicitly:

### Disable via CLI

Use `--no-support` on the `import` subcommand:

- `audiomason import --no-support ...`

### Disable via configuration

Add this to your configuration:

```yaml
support:
  enabled: false
```

Notes:

- Default is `support.enabled: true` (banner shown after successful import).
- The `audiomason --support` flag prints the link and exits with code 0.

AudioMason supports two related mechanisms for running **fully unattended**:

### 1) Global prompt disable: `prompts.disable`

Disables **all** interactive prompts (preflight + non-preflight).

```yaml
prompts:
  disable: ["*"]   # disable EVERYTHING
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

### 2) Preflight-only disable: `preflight_disable`

Disables only **preflight steps** (those governed by the preflight registry/orchestrator).

```yaml
preflight_disable:
  - publish
  - wipe_id3
  - cover
```

Rules are the same (list / unknown / duplicates / `"*"` exclusivity), and behavior is identical:
use the deterministic default or fail-fast if no default exists.

> Guardrail: preflight prompts must route through the preflight wrappers/dispatcher.
> Issue #94 adds a test to prevent reintroducing legacy bypasses.

## Related docs

- docs/WORKFLOW.md
- docs/PIPELINE.md
- docs/MAINTENANCE.md\n\n## Preflight step order (Issue #66)\n\nYou can configure the **deterministic order** of preflight questions using `preflight_steps`.\n\nExample:\n\n```yaml\npreflight_steps:\n  - reuse_stage\n  - use_manifest_answers\n  - choose_books\n  - skip_processed_books\n  - publish\n  - wipe_id3\n  - clean_stage\n  - source_author\n  - book_title\n  - cover\n  - overwrite_destination\n```\n\nValidation (fail-fast, before staging / disk writes):\n\n* unknown `step_key` → error\n* duplicate `step_key` → error\n* missing required step → error\n\nIf `preflight_steps` is not set, AudioMason uses the built-in default order.\n

## Preflight step order

You can configure the **deterministic order** of preflight decisions using `preflight_steps`.

Example:

```yaml
preflight_steps:
  - reuse_stage
  - use_manifest_answers
  - choose_source
  - choose_books
  - skip_processed_books
  - publish
  - wipe_id3
  - clean_stage
  - source_author
  - book_title
  - cover
  - overwrite_destination
```

Validation (fail-fast, before staging / disk writes):

- unknown `step_key` → error
- duplicate `step_key` → error
- missing required step → error
- required relative ordering constraints → error

Notes (post-Issue #93):

- Ordering is a **single linear list**. There are no user-visible run/source/book groups.
- `choose_source` and `choose_books` are **structural steps**:
  they must exist in the list, are validated, and are not offered as movable options in interactive selection.
- All preflight prompts are executed via the **preflight registry + orchestrator/dispatcher**.
  Direct ad-hoc prompts in `import_flow.py` are treated as regressions.

