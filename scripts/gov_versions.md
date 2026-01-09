# gov_versions.py

Helper tool for verifying and updating **Governance Set** versions for the AudioMason repository.

This tool is intentionally **local-only** (no network) and **deterministic** (stable ordering).

## Discovery

- The tool discovers governance documents dynamically by scanning:

  `docs/governance/*.md`

- Ordering is deterministic: files are processed in lexicographic order by path.

Any new governance document added to `docs/governance/` (including future laws) is automatically included in:

- `--list`
- `--check`
- `--set-version`

## Version line rules

The tool recognizes version declarations case-insensitively, with optional leading `#`:

- `Version: <value>`
- `# VERSION: <value>`

### Header-only parsing (important)

To avoid false positives from examples in document bodies (e.g. `Version: vX.Y` shown in documentation),
the tool scans **only the document header** (first `HEADER_SCAN_LINES = 60` lines) when reading or validating
the version line.

Implications:

- A document may contain example snippets later in the file without causing ambiguity.
- Ambiguity is raised only if **multiple version lines exist within the header region**.

## Commands

### List versions

```bash
python scripts/gov_versions.py --list
```

Output shows one row per governance doc and prints the count of discovered documents.

### Validate versions

```bash
python scripts/gov_versions.py --check
```

Default mode is `lockstep`, meaning all governance documents must share the same version.

To check only presence (no lockstep constraint):

```bash
python scripts/gov_versions.py --check --mode independent
```

### Set version (write mode)

```bash
python scripts/gov_versions.py --set-version vX.Y
```

Dry-run:

```bash
python scripts/gov_versions.py --set-version vX.Y --dry-run
```

Rules:

- If a file has no version line in the header: **error**.
- If a file has multiple version lines in the header: **error**.
- Only the first matching version line in the file is updated (count=1).

## Exit codes

- `0` success
- `2` validation error (missing/ambiguous version, inconsistent versions, bad args)
- `3` filesystem error (unexpected IO)
