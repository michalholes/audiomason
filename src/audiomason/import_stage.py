from __future__ import annotations

import shutil
from pathlib import Path


def ensure_empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def stage_tree(src: Path, dst: Path) -> None:
    ensure_empty_dir(dst)
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dst / item.name)
