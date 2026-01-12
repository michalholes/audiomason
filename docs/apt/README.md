# APT repository (maintainers)

This document describes how the signed APT repository is structured and published.
End-user installation steps belong in the root README and docs/INSTALL.md.

---

## Repository layout

The published APT repository is served from GitHub Pages.

High-level structure:

- dists/
  - stable/
    - InRelease
    - Release
    - Release.gpg
    - main/
      - binary-all/ (and/or arch-specific)
      - Contents
- pool/
  - main/
    - a/
      - audiomason/
        - audiomason_*_all.deb

The public signing key is published alongside docs:

- docs/apt/audiomason.gpg.asc

---

## GitHub Pages behavior

The repository is served under:

- https://michalholes.github.io/audiomason/

Important: GitHub Pages uses the repository's Pages root configuration.
This repo expects Pages to serve the content that includes:
- dists/ (APT metadata)
- pool/ (packages)
- docs/ (documentation published with Pages)

Keep paths consistent with what README and docs/INSTALL.md instruct users to use.

---

## Signing

APT clients validate the repository using:
- InRelease (preferred, inline-signed), or
- Release + Release.gpg

The signing key used for publishing must match the public key distributed as:
- docs/apt/audiomason.gpg.asc

If signatures do not verify, do not publish. Fix signing first.

---

## Publishing checklist

1) Build packages (.deb) in a clean environment.
2) Place packages into pool/ under the expected path.
3) Regenerate APT metadata in dists/ (Packages, Release, InRelease, Release.gpg).
4) Verify repository integrity locally:
   - apt update against a local file:// or test endpoint
   - confirm no signature warnings
5) Commit repository changes and push to main.
6) Confirm GitHub Pages is serving updated content.

---

## Configuration files

User config lives at:

- /etc/audiomason/config.yaml

Package installs defaults, but users must set real paths before first run.

---

## Tools and configs in this directory

- apt-ftparchive.conf
  - Configuration used to generate Packages and Release metadata.
- audiomason.gpg.asc
  - Public key distributed to clients for signature verification.

---
## Policy: .deb artifacts stored in Git

This repository intentionally stores `.deb` artifacts directly in Git
under the `docs/apt/` directory.

### Purpose

The `docs/apt/` subtree serves as a **docs-hosted APT repository** for AudioMason.
Storing `.deb` packages in Git is a deliberate choice to ensure:

- transparency of released binaries,
- offline availability,
- simple hosting without external infrastructure,
- reproducible and auditable release history.

These `.deb` files are **release artifacts**, not temporary build outputs.

### Canonical location

All `.deb` artifacts MUST be stored exclusively under:

docs/apt/pool/main/

No other locations in the repository are permitted for `.deb` files.

### Update rules

- `.deb` artifacts are added only as part of an explicit release.
- Each release MUST introduce a new versioned `.deb` file.
- Existing `.deb` files MUST NOT be modified, replaced, or overwritten.
- The repository history represents the authoritative archive of released packages.

### Guardrails (strict)

The following are explicitly forbidden:

- committing locally built or experimental `.deb` files,
- storing `.deb` files outside of `docs/apt/`,
- overwriting an existing `.deb` with a different binary,
- treating `.deb` files as CI build artifacts.

If CI is used, it may build `.deb` packages, but the final release
artifact committed to Git must be an explicit, intentional action.

### Responsibility

The project owner is responsible for:

- deciding when a `.deb` is released,
- ensuring version correctness,
- committing the artifact into the canonical location.

### Related documentation

- `docs/apt/README.md` (this file)
---
