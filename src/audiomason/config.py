from __future__ import annotations

import os
from pathlib import Path

import yaml

from audiomason.util import AmConfigError
from audiomason.version import __version__ as AM_VERSION

DEFAULTS: dict[str, object] = {
    "pipeline_steps": None,
    "cpu_cores": None,
    "split_chapters": True,
    "paths": {},
    "publish": "ask",
    "preflight_disable": [],
    "prompts": {"disable": []},
    "processing_log": {"enabled": False, "path": None},
    "openlibrary": {"enabled": True},
    "version-banner": True,
    # FEATURE #65: inbox cleanup control (delete processed source under DROP_ROOT)
    # Default preserves current behavior: never delete inbox sources unless explicitly configured.
    "clean_inbox": "no",  # ask | yes | no
    "cover": {
        "cache": "memory",
        "cache_dir": None,
    },
    "ffmpeg": {
        "loglevel": "warning",
        "loudnorm": False,
        "q_a": "2",
    },
}


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_yaml(p: Path) -> dict:
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise AmConfigError(f"Invalid configuration root in {p}: expected mapping, got {type(data).__name__}")
        return data


SYSTEM_CONFIG_PATH = Path("/etc/audiomason/config.yaml")


def user_config_path() -> Path:
    """Deterministic user-space config path (XDG preferred)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "audiomason" / "config.yaml"
    return Path.home() / ".config" / "audiomason" / "config.yaml"


# Issue #76: global prompt disable (config validation)
PROMPT_DISABLE_KEYS = {
    # preflight keys (existing)
    "normalize_author",
    "normalize_book_title",
    "publish",
    "wipe_id3",
    "reuse_stage",
    "cover",
    # non-preflight keys
    "choose_source",
    "choose_books",
    "skip_processed_books",
    "overwrite_destination",
    "source_author",
    "book_title",
    # cover module prompts (non-preflight)
    "choose_cover",
    "cover_input",
}


def _validate_prompts_disable(cfg: dict) -> None:
    prm = cfg.get("prompts", {})
    if prm is None:
        prm = {}
    if not isinstance(prm, dict):
        raise AmConfigError("Invalid config: prompts must be a mapping")
    raw = prm.get("disable", [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise AmConfigError("Invalid config: prompts.disable must be a list")
    seen: set[str] = set()
    for x in raw:
        if not isinstance(x, str):
            raise AmConfigError("Invalid config: prompts.disable items must be strings")
        if x in seen:
            raise AmConfigError(f"Invalid config: duplicate prompts.disable key: {x}")
        seen.add(x)
    if "*" in seen and len(seen) != 1:
        raise AmConfigError("Invalid config: prompts.disable cannot combine '*' with other keys")
    unknown = sorted(k for k in seen if k != "*" and k not in PROMPT_DISABLE_KEYS)
    if unknown:
        allowed = ", ".join(sorted(PROMPT_DISABLE_KEYS))
        raise AmConfigError(f"Invalid config: unknown prompts.disable key(s): {', '.join(unknown)}. Allowed: {allowed}")


def load_config(config_path: Path | None = None) -> dict:
    tried: list[Path] = []

    if config_path is not None:
        p = config_path
        tried.append(p)
        if not p.exists():
            raise AmConfigError(
                f"Config not found: {p}. "
                "Resolution order: --config, $XDG_CONFIG_HOME/audiomason/config.yaml "
                "(or ~/.config/audiomason/config.yaml), /etc/audiomason/config.yaml."
            )
    else:
        up = user_config_path()
        tried.append(up)
        if up.exists():
            p = up
        else:
            tried.append(SYSTEM_CONFIG_PATH)
            if SYSTEM_CONFIG_PATH.exists():
                p = SYSTEM_CONFIG_PATH
            else:
                tried_s = ", ".join(str(x) for x in tried)
                raise AmConfigError(
                    "Config not found. Tried (in order): " + tried_s + ". "
                    "Provide --config or create a user-space config under "
                    "$XDG_CONFIG_HOME/audiomason/config.yaml (or ~/.config/audiomason/config.yaml), "
                    "or install /etc/audiomason/config.yaml."
                )

    cfg = _deep_merge(DEFAULTS, _load_yaml(p))
    # Issue #76: validate prompts.disable (global prompt disable)
    _pr = cfg.get("prompts", {})
    if not isinstance(_pr, dict):
        raise AmConfigError("Invalid config: prompts must be a mapping")
    _disable = _pr.get("disable", [])
    if _disable is None:
        _disable = []
    if not isinstance(_disable, list):
        raise AmConfigError("Invalid config: prompts.disable must be a list of keys")

    _allowed = {
        "*",
        # preflight keys
        "publish",
        "wipe_id3",
        "clean_stage",
        "clean_inbox",
        "reuse_stage",
        "use_manifest_answers",
        "normalize_author",
        "normalize_book_title",
        "cover",
        # non-preflight keys
        "choose_source",
        "choose_books",
        "skip_processed_books",
        "enter_author",
        "enter_book_title",
        "dest_overwrite",
    }
    _seen: set[str] = set()
    for x in _disable:
        k = str(x).strip()
        if not k:
            continue
        if k not in _allowed:
            raise AmConfigError(f"Invalid config: unknown prompts.disable key: {k}")
        if k in _seen:
            raise AmConfigError(f"Invalid config: duplicate prompts.disable key: {k}")
        _seen.add(k)
    if "*" in _seen and len(_seen) != 1:
        raise AmConfigError("Invalid config: prompts.disable cannot combine '*' with other keys")
    # Issue #82: validate openlibrary config
    _validate_prompts_disable(cfg)
    _ol = cfg.get("openlibrary", {})
    if not isinstance(_ol, dict):
        raise AmConfigError("Invalid config: openlibrary must be a mapping")
    if "enabled" in _ol and not isinstance(_ol.get("enabled"), bool):
        raise AmConfigError("Invalid config: openlibrary.enabled must be boolean")
    cfg["loaded_from"] = str(p)
    # Feature #72: expose runtime version (single source of truth)
    _rt = cfg.get("runtime", {})
    if not isinstance(_rt, dict):
        _rt = {}
    _rt = dict(_rt)
    _rt["version"] = AM_VERSION
    cfg["runtime"] = _rt
    return cfg
