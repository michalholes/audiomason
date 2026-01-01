from __future__ import annotations

from pathlib import Path
import os
from audiomason.util import AmConfigError


def _find_repo_root() -> Path | None:
    # Deterministic bootstrap: repo root is the first parent containing pyproject.toml
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


# Env override (used by tests + runtime)
AUDIOMASON_ROOT = os.environ.get("AUDIOMASON_ROOT")


def _env_base() -> Path | None:
    env_root = os.environ.get("AUDIOMASON_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    # Fallback: repo root (pyproject.toml) where AudioMason app lives
    return _find_repo_root()


def require_audiomason_root() -> Path:
    base = _env_base()
    if base is None:
        raise AmConfigError(
            "AUDIOMASON_ROOT is not set and repo root could not be detected (pyproject.toml). "
            "Set AUDIOMASON_ROOT to the AudioMason app root (repo containing pyproject.toml). "
            "It is used to locate configuration.yaml."
        )
    return base


def _data_base() -> Path:
    # Base for resolving relative paths in configuration.yaml
    env = os.environ.get("AUDIOMASON_DATA_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return require_audiomason_root()


def _defaults_for(cfg) -> dict[str, Path]:
    base = _data_base()
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


def _ensure_abs(label: str, p: Path) -> None:
    if not p.is_absolute():
        raise AmConfigError(f"{label} must be an absolute path: {p}")


def _resolve_path(val: str) -> Path:
    p0 = Path(val).expanduser()
    if p0.is_absolute():
        return p0.resolve()
    return (_data_base() / p0).resolve()


def validate_paths_contract(cfg) -> Path:
    # NOTE: AUDIOMASON_ROOT is app-root (config discovery). Data paths may live anywhere.
    base = require_audiomason_root()
    cfg = cfg or {}
    paths = cfg.get("paths", {}) if isinstance(cfg.get("paths", {}), dict) else {}

    # validate configured paths (if present)
    for key in ("inbox", "stage", "output", "ready", "archive", "archive_ro", "cache"):
        val = paths.get(key)
        if val:
            p = _resolve_path(val)
            _ensure_abs(f"paths.{key}", p)

    # validate effective roots
    _ensure_abs("DROP_ROOT", get_drop_root(cfg))
    _ensure_abs("STAGE_ROOT", get_stage_root(cfg))
    _ensure_abs("OUTPUT_ROOT", get_output_root(cfg))
    _ensure_abs("ARCHIVE_ROOT", get_archive_root(cfg))
    _ensure_abs("CACHE_ROOT", get_cache_root(cfg))
    return base


# ======================
# Config-based resolvers
# ======================
def _get(cfg, key, default: Path) -> Path:
    cfg0 = cfg or {}
    if not isinstance(cfg0, dict):
        raise AmConfigError(f"Invalid configuration: expected mapping at root, got {type(cfg0).__name__}")

    paths = cfg0.get("paths", {}) or {}
    if not isinstance(paths, dict):
        raise AmConfigError(f"Invalid configuration: 'paths' must be a mapping, got {type(paths).__name__}")

    if isinstance(key, (list, tuple)):
        for k in key:
            val = paths.get(k)
            if val:
                p = _resolve_path(val)
                _ensure_abs(f"paths.{k}", p)
                return p
    else:
        val = paths.get(key)
        if val:
            p = _resolve_path(val)
            _ensure_abs(f"paths.{key}", p)
            return p

    d = default if default.is_absolute() else (_data_base() / default).resolve()
    _ensure_abs("default", d)
    return d


def get_drop_root(cfg) -> Path:
    return _get(cfg, "inbox", _defaults_for(cfg)["inbox"])


def get_stage_root(cfg) -> Path:
    return _get(cfg, "stage", _defaults_for(cfg)["stage"])


def get_output_root(cfg) -> Path:
    return _get(cfg, ("output", "ready"), _defaults_for(cfg)["output"])


def get_archive_root(cfg) -> Path:
    return _get(cfg, ("archive", "archive_ro"), _defaults_for(cfg)["archive"])


def get_cache_root(cfg) -> Path:
    return _get(cfg, "cache", _defaults_for(cfg)["cache"])


def get_ignore_file(cfg) -> Path:
    return get_drop_root(cfg) / ".abook_ignore"


# ======================
# Backward-compatible symbols
# (DO NOT REMOVE)
# NOTE: Strict enforcement happens via validate_paths_contract() + getters.
# ======================
_base = _data_base()

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
