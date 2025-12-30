from __future__ import annotations


from audiomason.archives import peek_archive_hint

from pathlib import Path

import audiomason.state as state
from audiomason.paths import (
    DROP_ROOT,
    STAGE_ROOT,
    OUTPUT_ROOT,
    ARCHIVE_ROOT,
    ARCHIVE_EXTS,
)
from audiomason.util import (
    out,
    ensure_dir,
    slug,
    prompt,
    prompt_yes_no,
    prune_empty_dirs,
)
from audiomason.ignore import load_ignore, add_ignore
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place
from audiomason.rename import natural_sort, rename_sequential
from audiomason.covers import choose_cover
from audiomason.tags import write_tags


def _list_sources(inbox: Path) -> list[Path]:
    items: list[Path] = []
    if not inbox.exists():
        return items

    # 1) Directories (top-level)
    for p in sorted(inbox.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir():
            if p.name.startswith("."):
                continue
            items.append(p)

    # 2) Archives (top-level)
    exts = {".rar", ".zip", ".7z"}
    for p in sorted(inbox.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and p.suffix.lower() in exts:
            items.append(p)

    return items


