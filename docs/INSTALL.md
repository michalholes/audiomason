# Installation

This document describes supported installation methods for AudioMason on Debian/Ubuntu systems.

If you want the simplest and most reliable path, use the signed APT repository.
If you want a direct install from GitHub Releases, use the GitHub method below (no hardcoded versions).

---

## Method 1: Signed APT repository (recommended)

AudioMason is published via a signed APT repository.

### 1) Import repository signing key

    curl -fsSL https://michalholes.github.io/audiomason/docs/apt/audiomason.gpg.asc | sudo tee /etc/apt/trusted.gpg.d/audiomason.asc > /dev/null

### 2) Add APT repository

    echo "deb https://michalholes.github.io/audiomason stable main" | sudo tee /etc/apt/sources.list.d/audiomason.list

### 3) Install

    sudo apt update
    sudo apt install audiomason

### Upgrade

    sudo apt update
    sudo apt upgrade audiomason

### Remove

    sudo apt remove audiomason

Notes:
- Configuration path: /etc/audiomason/config.yaml
- Configuration reference: docs/CONFIGURATION.md
- Maintainer details (repo layout, publishing, GPG): docs/apt/README.md

---

## Method 2: Install from GitHub Releases (.deb)

This method installs AudioMason from the latest GitHub Release asset.
It avoids hardcoded versions by downloading the latest matching .deb.

### Option A: Using GitHub CLI (gh) (recommended for this method)

Requirements:
- gh installed and available in PATH

Download the latest release .deb (matches audiomason_*_all.deb):

    gh release download -R michalholes/audiomason --pattern 'audiomason_*_all.deb' --clobber

Install the downloaded package:

    sudo apt install ./audiomason_*_all.deb

(Optional) Clean up the downloaded file afterwards:

    rm -f ./audiomason_*_all.deb

### Option B: If you do not want gh

Use the signed APT method above.
It is the supported no-surprises path and keeps upgrades simple.

---

## Post-install checklist

1) Verify the command exists:

    audiomason --help

2) Confirm config directory exists:

    sudo ls -la /etc/audiomason/

3) Edit configuration:

    sudoedit /etc/audiomason/config.yaml

System-level notes and maintenance:
- docs/INSTALL-SYSTEM.md
- docs/MAINTENANCE.md
