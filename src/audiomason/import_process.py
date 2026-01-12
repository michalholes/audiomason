from __future__ import annotations

from pathlib import Path
from typing import Iterable

from audiomason.import_types import BookGroup
from audiomason.tags import write_tags


def apply_book_steps(
    *,
    steps: Iterable[str],
    mp3s: list[Path],
    outdir: Path,
    author: str,
    title: str,
    out_title: str,
    i: int,
    n: int,
    b: BookGroup,
    cfg: dict,
    cover_mode: str,
) -> None:
    for step in steps:
        if step == "tags":
            write_tags(
                mp3s,
                artist=author,
                album=out_title,
                cover=None,
                cover_mime=None,
            )
        else:
            continue


def process_book(
    *,
    i: int,
    n: int,
    b: BookGroup,
    stage_run: Path,
    dest_root: Path,
    author: str,
    title: str,
    out_title: str,
    wipe: bool,
    cover_mode: str,
    overwrite: bool,
    cfg: dict,
    final_root: Path,
    steps: Iterable[str],
) -> None:
    from audiomason import import_flow as _legacy

    _legacy._process_book(
        i,
        n,
        b,
        stage_run,
        dest_root,
        author=author,
        title=title,
        out_title=out_title,
        wipe=wipe,
        cover_mode=cover_mode,
        overwrite=overwrite,
        cfg=cfg,
        final_root=final_root,
        steps=list(steps),
    )
