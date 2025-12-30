from __future__ import annotations
from pathlib import Path
import yaml

DEFAULTS = {
    "paths": {
        "inbox": "/mnt/warez/abooksinbox",
        "stage": "/mnt/warez/_am_stage",
        "ready": "/mnt/warez/_am_ready",
        "archive_ro": "/mnt/warez/abooks",
    },
    "publish": "ask",
    "ffmpeg": {
        "loglevel": "warning",
        "loudnorm": False,
        "q_a": "2",
    },
}

SYSTEM_CONFIG = Path("/etc/audiomason/config.yaml")
USER_CONFIG = Path.home() / ".config/audiomason/config.yaml"

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
        return yaml.safe_load(f) or {}

def load_config() -> dict:
    cfg = DEFAULTS
    cfg = _deep_merge(cfg, _load_yaml(SYSTEM_CONFIG))
    cfg = _deep_merge(cfg, _load_yaml(USER_CONFIG))
    return cfg
