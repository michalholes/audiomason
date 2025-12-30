from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def extract_track_num(name: str) -> Optional[int]:
    m = re.search(r"(?:^|\\D)(\\d{1,4})(?:\\D|$)", name)
    return int(m.group(1)) if m else None


def natural_sort(files: list[Path]) -> list[Path]:
    return sorted(
        files,
        key=lambda p: (
            extract_track_num(p.name) is None,
            extract_track_num(p.name) or 0,
            p.name.lower(),
        ),
    )


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
