from pathlib import Path

# ======================
# Archive extensions
# ======================
ARCHIVE_EXTS = {".zip", ".rar", ".7z"}

# ======================
# Default portable paths
# (used as fallback when config is missing)
# ======================
_DEFAULT_INBOX = Path("./inbox").resolve()
_DEFAULT_STAGE = Path("./stage").resolve()
_DEFAULT_OUTPUT = Path("./output").resolve()
_DEFAULT_ARCHIVE = Path("./archive").resolve()
_DEFAULT_CACHE = Path("./.cover_cache").resolve()

# ======================
# Config-based resolvers
# ======================
def _get(cfg, key: str, default: Path) -> Path:
    try:
        val = cfg.get("paths", {}).get(key)
        if val:
            return Path(val).expanduser().resolve()
    except Exception:
        pass
    return default


def get_drop_root(cfg) -> Path:
    return _get(cfg, "inbox", _DEFAULT_INBOX)


def get_stage_root(cfg) -> Path:
    return _get(cfg, "stage", _DEFAULT_STAGE)


def get_output_root(cfg) -> Path:
    return _get(cfg, "output", _DEFAULT_OUTPUT)


def get_archive_root(cfg) -> Path:
    try:
        paths = cfg.get("paths", {})
        val = paths.get("archive") or paths.get("archive_ro")
        if val:
            return Path(val).expanduser().resolve()
    except Exception:
        pass
    return _DEFAULT_ARCHIVE


def get_cache_root(cfg) -> Path:
    return _get(cfg, "cache", _DEFAULT_CACHE)


def get_ignore_file(cfg) -> Path:
    return get_drop_root(cfg) / ".abook_ignore"


# ======================
# Backward-compatible symbols
# (DO NOT REMOVE)
# ======================
DROP_ROOT = _DEFAULT_INBOX
STAGE_ROOT = _DEFAULT_STAGE
OUTPUT_ROOT = _DEFAULT_OUTPUT
ARCHIVE_ROOT = _DEFAULT_ARCHIVE
CACHE_ROOT = _DEFAULT_CACHE

IGNORE_FILE = Path(".abook_ignore")
COVER_NAME = "cover.jpg"

# ======================
# Tag defaults
# ======================
GENRE = "Audiobook"

# Legacy constants (kept for backward compatibility)
TITLE_PREFIX = ""
AUTHOR_PREFIX = ""
BOOK_PREFIX = ""
