from __future__ import annotations
from pathlib import Path
import yaml
from audiomason.paths import require_audiomason_root

DEFAULTS = {
    "cpu_cores": None,
    "paths": {},
    "publish": "ask",
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
            raise RuntimeError(f"Invalid configuration root in {path}: expected mapping, got {type(data).__name__}")
        return data

def load_config() -> dict:
    cfg = DEFAULTS
    base = require_audiomason_root()
    cfg = _deep_merge(cfg, _load_yaml(base / "configuration.yaml"))
    return cfg

