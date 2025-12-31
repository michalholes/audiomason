from pathlib import Path
import os

# Env override (used by tests + legacy)
AUDIOMASON_ROOT = os.environ.get("AUDIOMASON_ROOT")
BASE_ROOT = Path(AUDIOMASON_ROOT).expanduser().resolve() if AUDIOMASON_ROOT else Path.cwd().resolve()

def _base_root(cfg) -> Path:
    # ISSUE #25: never scatter outputs to CWD; derive base from AUDIOMASON_ROOT or config inbox parent.
    env_root = os.environ.get("AUDIOMASON_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    try:
        inbox = (cfg or {}).get("paths", {}).get("inbox")
        if inbox:
            p = Path(inbox).expanduser().resolve()
            return p.parent
    except Exception:
        pass
    # last-resort: keep prior behavior
    return Path.cwd().resolve()

def _defaults_for(cfg) -> dict[str, Path]:
    base = _base_root(cfg)
    return {
        "inbox": (base / "abooksinbox").resolve(),
        "stage": (base / "_am_stage").resolve(),
        "output": (base / "abooks_ready").resolve(),
        "archive": (base / "abooks").resolve(),
        "cache": (base / ".cover_cache").resolve(),
    }


# ======================
# Archive extensions
# ======================
ARCHIVE_EXTS = {".zip", ".rar", ".7z"}

# ======================
# Default portable paths (STRICT CONTRACT)
# All derived from BASE_ROOT / AUDIOMASON_ROOT
# ======================
_DEFAULT_INBOX = (_defaults_for({})["inbox"]).resolve()
_DEFAULT_STAGE = (_defaults_for({})["stage"]).resolve()
_DEFAULT_OUTPUT = (_defaults_for({})["output"]).resolve()
_DEFAULT_ARCHIVE = (_defaults_for({})["archive"]).resolve()
_DEFAULT_CACHE = (_defaults_for({})["cache"]).resolve()

# ======================
# Config-based resolvers
# ======================
def _get(cfg, key, default: Path) -> Path:
    try:
        paths = cfg.get("paths", {})
        if isinstance(key, (list, tuple)):
            for k in key:
                val = paths.get(k)
                if val:
                    return Path(val).expanduser().resolve()
            val = None
        else:
            val = paths.get(key)
        if val:
            return Path(val).expanduser().resolve()
    except Exception:
        pass
    return default


def get_drop_root(cfg) -> Path:
    return _get(cfg, "inbox", _defaults_for(cfg)["inbox"])


def get_stage_root(cfg) -> Path:
    return _get(cfg, "stage", _defaults_for(cfg)["stage"])


def get_output_root(cfg) -> Path:
    return _get(cfg, ("output", "ready"), _defaults_for(cfg)["output"])

def get_archive_root(cfg) -> Path:
    try:
        paths = cfg.get("paths", {})
        val = paths.get("archive") or paths.get("archive_ro")
        if val:
            return Path(val).expanduser().resolve()
    except Exception:
        pass
    return _defaults_for(cfg)["archive"]


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

IGNORE_FILE = get_ignore_file({})
COVER_NAME = "cover.jpg"

# ======================
# Tag defaults
# ======================
GENRE = "Audiobook"

# Legacy constants (kept for backward compatibility)
TITLE_PREFIX = ""
AUTHOR_PREFIX = ""
BOOK_PREFIX = ""
