from __future__ import annotations

from pathlib import Path

from audiomason.util import out

AUDIO_EXTS = {".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".wav", ".aac"}
ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"}


def _is_audio(p: Path) -> bool:
    return p.suffix.lower() in AUDIO_EXTS


def _is_archive(p: Path) -> bool:
    return p.suffix.lower() in ARCHIVE_EXTS


def inspect_source(path: Path) -> None:
    if not path.exists():
        out(f"[inspect] not found: {path}")
        return

    if path.is_file():
        out(f"[inspect] file: {path}")
        if _is_archive(path):
            out("  type: archive")
        elif _is_audio(path):
            out("  type: audio")
        else:
            out("  type: other")
        return

    out(f"[inspect] dir: {path}")

    books = 0
    audio = 0
    archives = 0
    other = 0

    for p in sorted(path.iterdir()):
        if p.is_dir():
            books += 1
            continue
        if not p.is_file():
            continue
        if _is_archive(p):
            archives += 1
        elif _is_audio(p):
            audio += 1
        else:
            other += 1

    out(f"  books: {books}")
    out(f"  audio files: {audio}")
    out(f"  archives: {archives}")
    out(f"  other files: {other}")
