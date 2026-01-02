# AudioMason

AudioMason is a deterministic audiobook processing pipeline.
Same input. Same output. Every time.
If that ever changes, it is a bug — not a feature, not magic.

## Philosophy

AudioMason is built around strict determinism:
- no hidden state
- no random decisions
- no "best effort" guessing

Failures should be boring.
Debugging should be possible.
Surprises are reserved for audiobooks, not tooling.

## Installation (APT)

AudioMason is distributed via a **signed APT repository**.

### 1. Import repository signing key

Download and install the public GPG key:

    curl -fsSL https://michalholes.github.io/audiomason/docs/apt/audiomason.gpg.asc | sudo tee /etc/apt/trusted.gpg.d/audiomason.asc > /dev/null

### 2. Add APT repository

Create repository source entry:

    echo "deb https://michalholes.github.io/audiomason stable main" | sudo tee /etc/apt/sources.list.d/audiomason.list

### 3. Install AudioMason

    sudo apt update
    sudo apt install audiomason

APT will verify signatures automatically.  
If it does not, something is wrong — stop and investigate.

Detailed system-level notes:
- docs/INSTALL.md
- docs/INSTALL-SYSTEM.md

## Upgrade

Standard APT upgrade applies:

    sudo apt update
    sudo apt upgrade audiomason

## Removal

    sudo apt remove audiomason

Configuration files are not removed automatically.

## Configuration

Main configuration file:

    /etc/audiomason/config.yaml

Configuration reference:
- docs/CONFIGURATION.md

Example configurations:
- configuration.example.yaml
- configuration.minimal.yaml

## Command Line Interface

CLI usage, flags, and modes:
- docs/CLI.md

## Processing Pipeline

How AudioMason processes audio deterministically:
- docs/PIPELINE.md
- docs/WORKFLOW.md

## Covers

Cover download and embedding rules:
- docs/COVERS.md

## APT Repository (Maintainers)

Repository layout, publishing flow, and GPG handling:
- docs/apt/README.md
