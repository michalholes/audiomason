from pathlib import Path
from audiomason.util import out
def inspect_source(path: Path) -> None:
    if not path.exists():
        out(f"[inspect] not found: {path}")
        return

    if path.is_file():
        out(f"[inspect] file: {path.name}")
        if path.suffix.lower() in ARCHIVE_EXTS:
            out("  type: archive")
        elif _is_audio(path):
            out("  type: audio")
        else:
            out("  type: other")
        return

    out(f"[inspect] dir: {path}")
    audio = []
    archives = []
    books = []

    for p in path.iterdir():
        if p.is_dir():
            books.append(p.name)
        elif p.is_file():
            if _is_audio(p):
                audio.append(p.name)
            elif p.suffix.lower() in ARCHIVE_EXTS:
                archives.append(p.name)

    out(f"  books: {len(books)}")
    out(f"  audio files: {len(audio)}")
    out(f"  archives: {len(archives)}")
