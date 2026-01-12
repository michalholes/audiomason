from __future__ import annotations

import shutil
from pathlib import Path


def publish_tree(
    *,
    src: Path,
    dest: Path,
    overwrite: bool,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        if not overwrite:
            raise FileExistsError(dest)
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()

    shutil.copytree(src, dest)
