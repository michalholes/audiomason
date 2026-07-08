from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def source_fingerprint(src: Path) -> str:
    r = src.expanduser().resolve()
    h = hashlib.sha256()
    h.update(str(r).encode("utf-8"))
    if r.is_file():
        st = r.stat()
        h.update(b"|F|")
        h.update(str(st.st_size).encode("utf-8"))
        h.update(b"|")
        h.update(str(st.st_mtime_ns).encode("utf-8"))
        return h.hexdigest()
    h.update(b"|D|")
    # Deterministic directory signature: sorted walk of relpaths + size + mtime_ns
    for root, dirs, files in os.walk(r):
        dirs.sort()
        files.sort()
        rp = Path(root)
        for fn in files:
            p = rp / fn
            try:
                st = p.stat()
            except FileNotFoundError:
                # Source changed during scan -> produce a different fingerprint deterministically
                h.update(b"|MISSING|")
                h.update(str(p.relative_to(r)).encode("utf-8"))
                continue
            rel = str(p.relative_to(r)).encode("utf-8")
            h.update(b"|")
            h.update(rel)
            h.update(b"|")
            h.update(str(st.st_size).encode("utf-8"))
            h.update(b"|")
            h.update(str(st.st_mtime_ns).encode("utf-8"))
    return h.hexdigest()


MANIFEST_NAME = "manifest.json"
SCHEMA_VERSION = 1


def manifest_path(stage_run: Path) -> Path:
    return stage_run / MANIFEST_NAME


def load_manifest(stage_run: Path) -> dict[str, object]:
    p = manifest_path(stage_run)
    if not p.exists():
        return {}
    try:
        raw: dict[str, object] = json.loads(p.read_text(encoding="utf-8"))
        return raw
    except Exception:
        # Must never break the run; treat as missing.
        return {}


def _deep_merge(dst: dict[str, object], src: dict[str, object]) -> dict[str, object]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)  # type: ignore[arg-type]
        else:
            dst[k] = v
    return dst


def write_manifest_atomic(stage_run: Path, data: dict[str, object]) -> None:
    stage_run.mkdir(parents=True, exist_ok=True)
    p = manifest_path(stage_run)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp.replace(p)


def update_manifest(stage_run: Path, patch: dict[str, object]) -> None:
    cur: dict[str, object] = load_manifest(stage_run)
    if not cur:
        cur = {"schema_version": SCHEMA_VERSION}
    elif "schema_version" not in cur:
        cur["schema_version"] = SCHEMA_VERSION
    _deep_merge(cur, patch)
    write_manifest_atomic(stage_run, cur)
