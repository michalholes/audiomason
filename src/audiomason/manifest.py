from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

MANIFEST_NAME = "manifest.json"
SCHEMA_VERSION = 1

def manifest_path(stage_run: Path) -> Path:
    return stage_run / MANIFEST_NAME

def load_manifest(stage_run: Path) -> Dict[str, Any]:
    p = manifest_path(stage_run)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # Must never break the run; treat as missing.
        return {}

def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)  # type: ignore[index]
        else:
            dst[k] = v
    return dst

def write_manifest_atomic(stage_run: Path, data: Dict[str, Any]) -> None:
    stage_run.mkdir(parents=True, exist_ok=True)
    p = manifest_path(stage_run)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)

def update_manifest(stage_run: Path, patch: Dict[str, Any]) -> None:
    cur = load_manifest(stage_run)
    if not cur:
        cur = {"schema_version": SCHEMA_VERSION}
    elif "schema_version" not in cur:
        cur["schema_version"] = SCHEMA_VERSION
    _deep_merge(cur, patch)
    write_manifest_atomic(stage_run, cur)
