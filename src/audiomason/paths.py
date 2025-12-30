from __future__ import annotations

from audiomason.config import load_config
import os
from pathlib import Path

cfg = load_config()
_root_cfg = cfg.get("paths", {}).get("root")
_ROOT = os.environ.get("AUDIOMASON_ROOT") or _root_cfg
ROOT = Path(_ROOT).expanduser().resolve() if _ROOT else None

def _p(default: str, under: str) -> Path:
    if ROOT is None:
        return Path(default)
    return ROOT / under

ARCHIVE_ROOT = _p("/mnt/warez/abooks", "abooks")
DROP_ROOT    = _p("/mnt/warez/abooksinbox", "abooksinbox")
STAGE_ROOT   = DROP_ROOT / "stage"
IGNORE_FILE  = DROP_ROOT / ".abook_ignore"
OUTPUT_ROOT  = _p("/mnt/warez/abooks_ready", "abooks_ready")
CACHE_ROOT   = DROP_ROOT / ".cover_cache"

ARCHIVE_EXTS = {".rar", ".zip", ".7z"}
COVER_NAME   = "cover.jpg"
GENRE        = "Audiobook"
TITLE_PREFIX = "Kapitola"
