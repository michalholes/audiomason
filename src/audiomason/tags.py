from __future__ import annotations

# pyright: reportPrivateImportUsage=false, reportUnknownMemberType=false
from collections.abc import Iterable
from pathlib import Path

from mutagen.id3 import (  # type: ignore[attr-defined]
    APIC,
    ID3,
    TALB,
    TCON,
    TIT2,
    TPE1,
    TRCK,
    ID3NoHeaderError,
)

from audiomason.paths import GENRE
from audiomason.util import out


def _load_id3(p: Path) -> ID3:
    try:
        return ID3(p)  # type: ignore[no-untyped-call]
    except ID3NoHeaderError:
        id3 = ID3()  # type: ignore[no-untyped-call]
        id3.save(p)
        return ID3(p)  # type: ignore[no-untyped-call]


def wipe_id3(files: Iterable[Path]) -> None:
    for mp3 in files:
        try:
            ID3(mp3).delete(mp3)  # type: ignore[no-untyped-call]
            out(f"[id3] wiped {mp3.name}")
        except ID3NoHeaderError:
            pass


def write_tags(
    files: Iterable[Path],
    *,
    artist: str,
    album: str,
    cover: bytes | None,
    cover_mime: str | None,
    track_start: int = 1,
) -> None:
    for i, mp3 in enumerate(files, track_start):
        id3 = _load_id3(mp3)

        id3.delall("TIT2")  # type: ignore[no-untyped-call]
        id3.delall("TALB")  # type: ignore[no-untyped-call]
        id3.delall("TPE1")  # type: ignore[no-untyped-call]
        id3.delall("TRCK")  # type: ignore[no-untyped-call]
        id3.delall("TCON")  # type: ignore[no-untyped-call]
        id3.delall("APIC")  # type: ignore[no-untyped-call]

        id3.add(TIT2(encoding=3, text=mp3.stem))  # type: ignore[no-untyped-call]
        id3.add(TALB(encoding=3, text=album))  # type: ignore[no-untyped-call]
        id3.add(TPE1(encoding=3, text=artist))  # type: ignore[no-untyped-call]
        id3.add(TRCK(encoding=3, text=str(i)))  # type: ignore[no-untyped-call]
        id3.add(TCON(encoding=3, text=GENRE))  # type: ignore[no-untyped-call]

        id3.save(mp3)
        out(f"[tags] {mp3.name}")


def write_cover(
    mp3s: Iterable[Path],
    cover: bytes | None,
    cover_mime: str | None = None,
) -> None:
    for mp3 in mp3s:
        id3 = _load_id3(mp3)

        # Always reset cover art deterministically
        id3.delall("APIC")  # type: ignore[no-untyped-call]

        if cover:
            id3.add(  # type: ignore[no-untyped-call]
                APIC(  # type: ignore[no-untyped-call]
                    encoding=3,
                    mime=cover_mime or "image/jpeg",
                    type=3,
                    desc="Cover",
                    data=cover,
                )
            )

        id3.save(mp3)
        out(f"[cover] {mp3.name}")
