from __future__ import annotations

from pathlib import Path
import os

# Env override (used by tests + runtime)
AUDIOMASON_ROOT = os.environ.get("AUDIOMASON_ROOT")

def _env_base() -> Path | None:
    env_root = os.environ.get("AUDIOMASON_ROOT")
    if not env_root:
        return None
    return Path(env_root).expanduser().resolve()

def require_audiomason_root() -> Path:
    base = _env_base()
    if base is None:
        raise RuntimeError(
            "AUDIOMASON_ROOT is not set. "
            "Export AUDIOMASON_ROOT to the parent directory that contains "
            "abooksinbox/, _am_stage/, abooks_ready/, and abooks/."
        )
    return base

def _defaults_for(cfg) -> dict[str, Path]:
    base = require_audiomason_root()
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

def _ensure_under_base(label: str, p: Path, base: Path) -> None:
    try:
        ok = p.is_relative_to(base)
    except Exception:
        ok = str(p).startswith(str(base))
    if not ok:
        raise RuntimeError(f"{label} must be under AUDIOMASON_ROOT ({base}): {p}")

def validate_paths_contract(cfg) -> Path:
    base = require_audiomason_root()
    cfg = cfg or {}
    paths = cfg.get("paths", {}) if isinstance(cfg.get("paths", {}), dict) else {}

    # validate configured paths (if present)
    for key in ("inbox", "stage", "output", "ready", "archive", "archive_ro", "cache"):
        val = paths.get(key)
        if val:
            p = Path(val).expanduser().resolve()
            _ensure_under_base(f"paths.{key}", p, base)

    # validate effective roots
    _ensure_under_base("DROP_ROOT", get_drop_root(cfg), base)
    _ensure_under_base("STAGE_ROOT", get_stage_root(cfg), base)
    _ensure_under_base("OUTPUT_ROOT", get_output_root(cfg), base)
    _ensure_under_base("ARCHIVE_ROOT", get_archive_root(cfg), base)
    _ensure_under_base("CACHE_ROOT", get_cache_root(cfg), base)
    return base

# ======================
# Config-based resolvers
# ======================
def _get(cfg, key, default: Path) -> Path:
    base = require_audiomason_root()
    try:
        paths = (cfg or {}).get("paths", {})
        if isinstance(key, (list, tuple)):
            for k in key:
                val = paths.get(k)
                if val:
                    p = Path(val).expanduser().resolve()
                    _ensure_under_base(f"paths.{k}", p, base)
                    return p
            val = None
        else:
            val = paths.get(key)
        if val:
            p = Path(val).expanduser().resolve()
            _ensure_under_base(f"paths.{key}", p, base)
            return p
    except Exception:
        pass
    _ensure_under_base("default", default, base)
    return default

def get_drop_root(cfg) -> Path:
    return _get(cfg, "inbox", _defaults_for(cfg)["inbox"])

def get_stage_root(cfg) -> Path:
    return _get(cfg, "stage", _defaults_for(cfg)["stage"])

def get_output_root(cfg) -> Path:
    return _get(cfg, ("output", "ready"), _defaults_for(cfg)["output"])

def get_archive_root(cfg) -> Path:
    base = require_audiomason_root()
    try:
        paths = (cfg or {}).get("paths", {})
        val = paths.get("archive") or paths.get("archive_ro")
        if val:
            p = Path(val).expanduser().resolve()
            _ensure_under_base("paths.archive", p, base)
            return p
    except Exception:
        pass
    return _defaults_for(cfg)["archive"]

def get_cache_root(cfg) -> Path:
    return _get(cfg, "cache", _defaults_for(cfg)["cache"])

def get_ignore_file(cfg) -> Path:
    return get_drop_root(cfg) / ".abook_ignore"

# ======================
# Backward-compatible symbols
# (DO NOT REMOVE)
# NOTE: Strict enforcement happens via validate_paths_contract() + getters.
# ======================
_base = _env_base()
if _base is None:
    # best-effort placeholders to keep imports working; runtime will fail fast via validator/getters
    _base = Path("/__AUDIOMASON_ROOT_UNSET__").resolve()

DROP_ROOT = (_base / "abooksinbox").resolve()
STAGE_ROOT = (_base / "_am_stage").resolve()
OUTPUT_ROOT = (_base / "abooks_ready").resolve()
ARCHIVE_ROOT = (_base / "abooks").resolve()
CACHE_ROOT = (_base / ".cover_cache").resolve()

IGNORE_FILE = (DROP_ROOT / ".abook_ignore").resolve()
COVER_NAME = "cover.jpg"

# ======================
# Tag defaults
# ======================
GENRE = "Audiobook"

# Legacy constants (kept for backward compatibility)
TITLE_PREFIX = ""
AUTHOR_PREFIX = ""
BOOK_PREFIX = ""
