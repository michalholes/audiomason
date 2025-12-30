from __future__ import annotations

from pathlib import Path
import os
import yaml

DEFAULT_CFG = Path("/etc/audiomason/config.yaml")
USER_CFG = Path("~/.config/audiomason/config.yaml").expanduser()


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    # Allow override by env var for dev/test
    env_path = os.environ.get("AUDIOMASON_CONFIG")
    paths = [Path(env_path)] if env_path else [DEFAULT_CFG, USER_CFG]

    cfg: dict = {}
    loaded_any = False
    for p in paths:
        if p and p.exists():
            loaded_any = True
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            cfg = _deep_merge(cfg, data)

    if not loaded_any:
        raise SystemExit(f"Missing config. Expected {DEFAULT_CFG} (and optional {USER_CFG})")

    return cfg
