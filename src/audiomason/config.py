from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None


CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "audiomason" / "config.toml"


def load_config() -> Dict[str, Any]:
    if tomllib is None:
        return {}
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}
