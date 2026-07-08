from __future__ import annotations

import os
from pathlib import Path
from typing import IO, cast

import yaml

from audiomason.util import AmConfigError
from audiomason.version import __version__


def _as_dict(value: object) -> dict[str, object]:
    return (
        cast(dict[str, object], value) if isinstance(value, dict) else cast(dict[str, object], {})
    )


def _safe_load_yaml(stream: IO[str]) -> dict[str, object]:
    data = cast(object, yaml.safe_load(stream))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise AmConfigError(f"Invalid YAML: expected mapping, got {type(data).__name__}")
    return cast(dict[str, object], data)


_Cfg = dict[str, object]

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
    "ai": {
        "enabled": False,
        "provider": "openai_compatible",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "timeout_s": 20,
        "max_completion_tokens": 80,
    },
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


def _deep_merge(a: dict[str, object], b: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _load_yaml(p: Path) -> dict[str, object]:
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return _safe_load_yaml(f)


SYSTEM_CONFIG_PATH = Path("/etc/audiomason/config.yaml")


def user_config_path() -> Path:
    """Deterministic user-space config path (XDG preferred)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "audiomason1" / "config.yaml"
    return Path.home() / ".config" / "audiomason1" / "config.yaml"


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


def validate_prompts_disable(cfg: dict[str, object]) -> None:
    prm = _as_dict(cfg.get("prompts"))
    raw_disable = prm.get("disable")
    if raw_disable is None:
        raw_disable = []
    if not isinstance(raw_disable, list):
        raise AmConfigError("Invalid config: prompts.disable must be a list")
    seen: set[str] = set()
    for x in cast(list[object], raw_disable):
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
        unknown_str = ", ".join(unknown)
        raise AmConfigError(
            f"Invalid config: unknown prompts.disable key(s): {unknown_str}. Allowed: {allowed}"
        )


def load_config(config_path: Path | None = None) -> dict[str, object]:
    tried: list[Path] = []

    if config_path is not None:
        p = config_path
        tried.append(p)
        if not p.exists():
            raise AmConfigError(
                f"Config not found: {p}. Resolution order: --config,"
                " $XDG_CONFIG_HOME/audiomason1/config.yaml"
                " (or ~/.config/audiomason1/config.yaml),"
                " /etc/audiomason/config.yaml."
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
                    "Provide --config or create a user-space config under"
                    " $XDG_CONFIG_HOME/audiomason1/config.yaml"
                    " (or ~/.config/audiomason1/config.yaml),"
                    " or install /etc/audiomason/config.yaml."
                )

    cfg = _deep_merge(DEFAULTS, _load_yaml(p))
    # Issue #76: validate prompts.disable (global prompt disable)
    _pr = _as_dict(cfg.get("prompts"))
    raw_disable = _pr.get("disable")
    if raw_disable is None:
        raw_disable = []
    if not isinstance(raw_disable, list):
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
    for x in cast(list[object], raw_disable):
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
    validate_prompts_disable(cfg)
    _ol = _as_dict(cfg.get("openlibrary"))
    if "enabled" in _ol and not isinstance(_ol.get("enabled"), bool):
        raise AmConfigError("Invalid config: openlibrary.enabled must be boolean")
    _ai = _as_dict(cfg.get("ai"))
    if "enabled" in _ai and not isinstance(_ai.get("enabled"), bool):
        raise AmConfigError("Invalid config: ai.enabled must be boolean")
    if "provider" in _ai and not isinstance(_ai.get("provider"), str):
        raise AmConfigError("Invalid config: ai.provider must be a string")
    if "endpoint" in _ai and not isinstance(_ai.get("endpoint"), str):
        raise AmConfigError("Invalid config: ai.endpoint must be a string")
    if "model" in _ai and not isinstance(_ai.get("model"), str):
        raise AmConfigError("Invalid config: ai.model must be a string")
    if "api_key_env" in _ai and not isinstance(_ai.get("api_key_env"), str):
        raise AmConfigError("Invalid config: ai.api_key_env must be a string")
    if "timeout_s" in _ai:
        _timeout = _ai.get("timeout_s")
        if not isinstance(_timeout, (int, float)) or float(_timeout) <= 0:
            raise AmConfigError("Invalid config: ai.timeout_s must be a positive number")
    if "max_completion_tokens" in _ai:
        _max_completion_tokens = _ai.get("max_completion_tokens")
        if not isinstance(_max_completion_tokens, int) or _max_completion_tokens <= 0:
            raise AmConfigError(
                "Invalid config: ai.max_completion_tokens must be a positive integer"
            )
    cfg["loaded_from"] = str(p)
    # Feature #72: expose runtime version (single source of truth)
    _rt = dict(_as_dict(cfg.get("runtime")))
    _rt["version"] = __version__
    cfg["runtime"] = _rt
    return cfg
