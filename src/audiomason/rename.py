from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


_LEADING = re.compile(r"^\s*(\d{1,4})\b")
_ANYWHERE = re.compile(r"(\d{1,4})")
_TRACKISH = re.compile(r"\b(?:track|chapter|kapitola)\s*[_-]?\s*(\d{1,4})\b", re.I)


def extract_track_num(name: str) -> Optional[int]:
    base = Path(name).stem

    m = _LEADING.search(base)
    if m:
        return int(m.group(1))

    m = _TRACKISH.search(base)
    if m:
        return int(m.group(1))

    m = _ANYWHERE.search(base)
    if m:
        return int(m.group(1))

    return None


def natural_sort(files: list[Path]) -> list[Path]:
    def key(p: Path):
        n = extract_track_num(p.name)
        return (n is None, n or 0, p.name.lower())

    return sorted(files, key=key)


def rename_sequential(mp3dir: Path, files: list[Path]) -> list[Path]:
    tmp = []
    for i, f in enumerate(files, 1):
        t = mp3dir / f".__tmp__{i:04d}.mp3"
        f.rename(t)
        tmp.append(t)

    out_files = []
    for i, t in enumerate(tmp, 1):
        f = mp3dir / f"{i:02d}.mp3"
        t.rename(f)
        out_files.append(f)

    return out_files
