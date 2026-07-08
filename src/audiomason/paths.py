from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from audiomason.util import AmConfigError

_Cfg = Mapping[str, object]


def _as_dict(value: object) -> dict[str, object]:
    return (
        cast(dict[str, object], value) if isinstance(value, dict) else cast(dict[str, object], {})
    )


def _default_user_base() -> Path:
    # Safe runtime default (does not require AUDIOMASON_ROOT / repo).
    # Debian package must work for unprivileged users.
    return (Path.home() / ".local" / "share" / "audiomason").resolve()


def _find_repo_root() -> Path | None:
    # Deterministic bootstrap: repo root is the first parent containing pyproject.toml
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


# Env override (used by tests + runtime)
AUDIOMASON_ROOT = os.environ.get("AUDIOMASON_ROOT")


DEBIAN_DEFAULT_ROOT = Path("/etc/audiomason")


def require_audiomason_root() -> Path:
    env = os.environ.get("AUDIOMASON_ROOT")
    if env:
        return Path(env)

    if DEBIAN_DEFAULT_ROOT.exists():
        return DEBIAN_DEFAULT_ROOT

    repo = _find_repo_root()
    if repo:
        return repo

    raise AmConfigError(
        "AUDIOMASON_ROOT is not set and no default config found. "
        "Expected /etc/audiomason/configuration.yaml."
    )


def _data_base() -> Path:
    global _base
    if _base is not None:
        return _base
    # Base for resolving relative paths in configuration (data roots), safe for unprivileged users.
    env = os.environ.get("AUDIOMASON_DATA_ROOT")
    if env:
        _base = Path(env).expanduser().resolve()
        return _base
    _base = _default_user_base()
    return _base


def _defaults_for(cfg: _Cfg) -> dict[str, Path]:
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


def validate_paths_contract(cfg: _Cfg) -> Path:
    # NOTE: AUDIOMASON_ROOT is app-root (config discovery). Data paths may live anywhere.
    base = require_audiomason_root()
    cfg2 = _as_dict(cfg)
    paths = _as_dict(cfg2.get("paths"))

    # validate configured paths (if present)
    for key in ("inbox", "stage", "output", "ready", "archive", "archive_ro", "cache"):
        val = paths.get(key)
        if val and isinstance(val, str):
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
def _get(cfg: _Cfg, key: str | tuple[str, ...], default: Path) -> Path:
    cfg0 = _as_dict(cfg)
    paths = _as_dict(cfg0.get("paths"))

    if isinstance(key, (list, tuple)):
        for k in key:
            val = paths.get(k)
            if val and isinstance(val, str):
                p = _resolve_path(val)
                _ensure_abs(f"paths.{k}", p)
                return p
    else:
        val = paths.get(key)
        if val and isinstance(val, str):
            p = _resolve_path(val)
            _ensure_abs(f"paths.{key}", p)
            return p

    d = default if default.is_absolute() else (_data_base() / default).resolve()
    _ensure_abs("default", d)
    return d


def get_drop_root(cfg: _Cfg) -> Path:
    return _get(cfg, ("inbox", "drop_root"), _defaults_for(cfg)["inbox"])


def get_stage_root(cfg: _Cfg) -> Path:
    return _get(cfg, ("stage", "stage_root"), _defaults_for(cfg)["stage"])


def get_output_root(cfg: _Cfg) -> Path:
    return _get(cfg, ("output", "ready", "output_root"), _defaults_for(cfg)["output"])


def get_archive_root(cfg: _Cfg) -> Path:
    return _get(cfg, ("archive", "archive_ro", "archive_root"), _defaults_for(cfg)["archive"])


def get_cache_root(cfg: _Cfg) -> Path:
    return _get(cfg, "cache", _defaults_for(cfg)["cache"])


def get_ignore_file(cfg: _Cfg) -> Path:
    return get_drop_root(cfg) / ".abook_ignore"


# ======================
# Backward-compatible symbols
# (DO NOT REMOVE)
# NOTE: Strict enforcement happens via validate_paths_contract() + getters.
# ======================
_base: Path | None = None  # lazy-initialized

DROP_ROOT = (_default_user_base() / "abooksinbox").resolve()
STAGE_ROOT = (_default_user_base() / "_am_stage").resolve()
OUTPUT_ROOT = (_default_user_base() / "abooks_ready").resolve()
ARCHIVE_ROOT = (_default_user_base() / "abooks").resolve()
CACHE_ROOT = (_default_user_base() / "am_cache").resolve()

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
