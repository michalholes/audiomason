from __future__ import annotations
from pathlib import Path
import yaml
from audiomason.util import AmConfigError
from audiomason.paths import require_audiomason_root

DEFAULTS = {
    "pipeline_steps": None,
    "cpu_cores": None,
    "split_chapters": True,
    "paths": {},
    "publish": "ask",
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

CONFIG_PATH = Path("/etc/audiomason/config.yaml")
def load_config(config_path: Path | None = None) -> dict:
    p = config_path or CONFIG_PATH
    if not p.exists():
        raise AmConfigError(
            f"Config not found: {p}. "
            "AudioMason requires /etc/audiomason/config.yaml"
        )
    cfg = _deep_merge(DEFAULTS, _load_yaml(p))
    cfg['loaded_from'] = str(p)
    return cfg

