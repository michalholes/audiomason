from __future__ import annotations

READ_ONLY_VERIFY = True



from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError

from audiomason.paths import COVER_NAME
from audiomason.util import out


def verify_library(root: Path) -> None:
    """
    Verify audiobook library:
    - each book dir has cover.jpg
    - mp3 files have ID3 tags
    """
    books = [p for p in root.iterdir() if p.is_dir()]
    out(f"[verify] scanning {len(books)} book(s) under {root}")

    missing_cover = 0
    missing_tags = 0

    for book in books:
        cover = book / COVER_NAME
        if not cover.exists():
            out(f"[verify] missing cover: {book.name}")
            missing_cover += 1

        mp3s = sorted(book.glob("*.mp3"))
        for mp3 in mp3s:
            try:
                ID3(mp3)
            except ID3NoHeaderError:
                out(f"[verify] missing ID3 tags: {book.name}/{mp3.name}")
                missing_tags += 1

    out(
        f"[verify] done: "
        f"books={len(books)}, "
        f"missing_cover={missing_cover}, "
        f"missing_tags={missing_tags}"
    )
