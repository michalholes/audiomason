# AudioMason APT Repository

This directory contains the Debian APT repository served via GitHub Pages.

Base URL:
https://michalholes.github.io/audiomason/apt

## Structure

- pool/ – Debian packages (.deb)
- dists/stable/ – APT metadata (Release, InRelease, Packages)
- audiomason.gpg.asc – public signing key

## Publishing a new version

1. Build the .deb locally
2. Copy it into pool:
   pool/main/a/audiomason/
3. Regenerate Packages and Release
4. Sign Release (InRelease + Release.gpg)
5. Commit and push to main

GitHub Pages publishes /docs automatically.
