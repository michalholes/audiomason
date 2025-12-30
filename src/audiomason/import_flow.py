from __future__ import annotations

from pathlib import Path

from audiomason.state import OPTS
from audiomason.paths import DROP_ROOT, STAGE_ROOT, OUTPUT_ROOT, ARCHIVE_EXTS
from audiomason.util import out, die, ensure_dir
from audiomason.ignore import load_ignore, add_ignore
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place
from audiomason.rename import natural_sort, rename_sequential
from audiomason.covers import choose_cover
from audiomason.tags import write_tags
from audiomason.verify import verify_library


def run_import() -> None:
    inbox = DROP_ROOT
    ensure_dir(inbox)

    ignore = load_ignore()

    sources = sorted(
        p for p in inbox.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix.lower() in ARCHIVE_EXTS
    )
    if not sources:
        out("[inbox] empty")
        return

    for src in sources:
        key = src.stem
        if key in ignore:
            out(f"[skip] ignored: {src.name}")
            continue

        out(f"[import] {src.name}")

        stage = STAGE_ROOT / key
        ensure_dir(stage)

        try:
            unpack(src, stage)
        except Exception as e:
            out(f"[error] unpack failed: {e}")
            add_ignore(key)
            continue

        convert_m4a_in_place(stage)

        mp3s = natural_sort(list(stage.rglob("*.mp3")))
        if not mp3s:
            out("[skip] no mp3 found")
            continue

        mp3s = rename_sequential(mp3s[0].parent, mp3s)

        bookdir = OUTPUT_ROOT / key
        ensure_dir(bookdir)

        cover = choose_cover(
            mp3_first=mp3s[0],
            m4a_source=None,
            bookdir=bookdir,
            stage_root=stage,
            group_root=stage,
        )

        write_tags(
            mp3s,
            artist=key,
            album=key,
            cover=cover[0] if cover else None,
            cover_mime=cover[1] if cover else None,
        )

        for mp3 in mp3s:
            mp3.rename(bookdir / mp3.name)

        out(f"[done] {key}")

    if OPTS.verify:
        verify_library(OUTPUT_ROOT)
