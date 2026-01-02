# AudioMason APT Repository

This directory contains the Debian APT repository served via GitHub Pages.

Base URL:
https://michalholes.github.io/audiomason/apt

## Structure

- pool/ – Debian packages (.deb)
- dists/stable/ – APT metadata (Release, InRelease, Packages)
- audiomason.gpg.asc – public signing key

## Client setup (signed repo)

```bash
curl -fsSL https://michalholes.github.io/audiomason/apt/audiomason.gpg.asc | sudo gpg --dearmor -o /usr/share/keyrings/audiomason-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/audiomason-archive-keyring.gpg] https://michalholes.github.io/audiomason/apt stable main" | sudo tee /etc/apt/sources.list.d/audiomason.list
sudo apt update
sudo apt install audiomason
```

## Publishing a new version (maintainer notes)

1. Build the .deb locally
2. Copy it into pool/main/a/audiomason/
3. Regenerate Packages and Packages.gz
4. Regenerate Release, then sign (InRelease + Release.gpg)
5. Commit and push to main (GitHub Pages publishes /docs)
