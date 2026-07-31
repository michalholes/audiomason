#!/bin/bash
set -euo pipefail

# AudioMason user-space installer.
# Downloads the latest .deb from GitHub Releases, extracts the Python
# package into a local venv, and creates a wrapper in ~/.local/bin.
# No root access required.

REPO="michalholes/audiomason"
INSTALL_DIR="${HOME}/.local"
CACHE_DIR="${HOME}/.cache/audiomason"
DRY_RUN=0
VERSION=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install AudioMason to user space (no root required).

Options:
  --version VER   Install a specific version (default: latest)
  --dir DIR       Install directory (default: ~/.local)
  --dry-run       Print commands without executing
  -h, --help      Show this help
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

log() { echo "==> $*"; }
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "    $*"
    else
        "$@"
    fi
}

# --- Preflight checks ---

if [ "$(uname -s)" != "Linux" ]; then
    echo "Error: this installer supports Linux only." >&2
    exit 1
fi

for cmd in curl python3 dpkg-deb; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: required command not found: $cmd" >&2
        exit 1
    fi
done

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "Error: Python 3.11+ required, found $PYTHON_VERSION." >&2
    exit 1
fi

# --- Resolve version ---

if [ -z "$VERSION" ]; then
    log "Resolving latest release..."
    VERSION=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'].lstrip('v'))")
    log "Latest version: $VERSION"
fi

DEB_NAME="audiomason_${VERSION}_all.deb"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/v${VERSION}/${DEB_NAME}"

# --- Setup directories ---

VENV_DIR="${INSTALL_DIR}/share/audiomason/venv"
BIN_DIR="${INSTALL_DIR}/bin"
PKG_DIR="${INSTALL_DIR}/share/audiomason/pkg"
CONFIG_DIR="${HOME}/.config/audiomason1"

run mkdir -p "$CACHE_DIR"
run mkdir -p "$BIN_DIR"

# --- Download .deb ---

DEB_PATH="${CACHE_DIR}/${DEB_NAME}"
if [ -f "$DEB_PATH" ]; then
    log "Using cached $DEB_NAME"
else
    log "Downloading $DEB_NAME..."
    run curl -fSL -o "$DEB_PATH" "$DOWNLOAD_URL"
fi

# --- Create venv and install dependencies ---

if [ ! -d "$VENV_DIR" ] || [ "$DRY_RUN" -eq 1 ]; then
    log "Creating virtual environment..."
    run python3 -m venv "$VENV_DIR"
    log "Installing dependencies..."
    run "${VENV_DIR}/bin/pip" install -q \
        mutagen pydantic rich typer pyyaml
fi

# --- Extract audiomason package from .deb ---

log "Extracting audiomason package..."
run mkdir -p "$PKG_DIR"
run dpkg-deb -x "$DEB_PATH" "$PKG_DIR"

# Copy the audiomason Python package into the venv site-packages
if [ "$DRY_RUN" -eq 1 ]; then
    SITE_PACKAGES="${VENV_DIR}/lib/python${PYTHON_VERSION}/site-packages"
else
    SITE_PACKAGES=$("${VENV_DIR}/bin/python3" \
        -c "import site; print(site.getsitepackages()[0])")
fi
run cp -r "${PKG_DIR}/usr/lib/python3/dist-packages/audiomason" \
    "$SITE_PACKAGES/"

# --- Create wrapper script ---

WRAPPER="${BIN_DIR}/audiomason"
log "Creating wrapper: $WRAPPER"
if [ "$DRY_RUN" -eq 0 ]; then
    cat > "$WRAPPER" <<WRAPPER_EOF
#!${VENV_DIR}/bin/python3
from audiomason.cli import main
raise SystemExit(main())
WRAPPER_EOF
    chmod +x "$WRAPPER"
else
    echo "    cat > $WRAPPER <<..."
    echo "    chmod +x $WRAPPER"
fi

# --- Copy example config ---

run mkdir -p "$CONFIG_DIR"
EXAMPLE_CONFIG="${PKG_DIR}/usr/share/doc/audiomason/examples/config.yaml"
if [ -f "$EXAMPLE_CONFIG" ] && [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    log "Copying example config..."
    run cp "$EXAMPLE_CONFIG" "${CONFIG_DIR}/config.yaml"
fi

# --- Verify ---

log "Verifying installation..."
if [ "$DRY_RUN" -eq 0 ]; then
    if "${BIN_DIR}/audiomason" --help >/dev/null 2>&1; then
        log "AudioMason installed successfully."
    else
        echo "Warning: audiomason --help failed. Check your setup." >&2
    fi
fi

# --- Cleanup cache ---

log "Cleaning up cached .deb..."
run rm -f "$DEB_PATH"

# --- PATH hint ---

case ":${PATH}:" in
    *":${BIN_DIR}:"*) ;;
    *)
        echo ""
        echo "Add ${BIN_DIR} to your PATH:"
        echo "  export PATH=\"${BIN_DIR}:\$PATH\""
        echo ""
        ;;
esac

log "Done."
