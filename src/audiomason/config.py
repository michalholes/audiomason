from __future__ import annotations
from pathlib import Path
import os
import yaml
from audiomason.util import AmConfigError
from audiomason.paths import require_audiomason_root
from audiomason.version import __version__ as AM_VERSION

DEFAULTS = {
    "pipeline_steps": None,
    "cpu_cores": None,
    "split_chapters": True,
    "paths": {},
    "publish": "ask",
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

def load_config(config_path: Path | None = None) -> dict:
    tried: list[Path] = []

    if config_path is not None:
        p = config_path
        tried.append(p)
        if not p.exists():
            raise AmConfigError(
                f"Config not found: {p}. "
                "Resolution order: --config, $XDG_CONFIG_HOME/audiomason/config.yaml (or ~/.config/audiomason/config.yaml), /etc/audiomason/config.yaml."
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
                    "Provide --config or create a user-space config under $XDG_CONFIG_HOME/audiomason/config.yaml (or ~/.config/audiomason/config.yaml), "
                    "or install /etc/audiomason/config.yaml."
                )

    cfg = _deep_merge(DEFAULTS, _load_yaml(p))
    cfg['loaded_from'] = str(p)
    # Feature #72: expose runtime version (single source of truth)
    _rt = cfg.get('runtime', {})
    if not isinstance(_rt, dict):
        _rt = {}
    _rt = dict(_rt)
    _rt['version'] = AM_VERSION
    cfg['runtime'] = _rt
    return cfg

