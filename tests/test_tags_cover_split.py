from pathlib import Path

from mutagen.id3 import ID3
from mutagen.id3._frames import TALB, TIT2, TPE1, TRCK

from audiomason.tags import summarize_id3_files, write_cover, write_tags


def _mk_id3_file(p: Path) -> None:
    ID3().save(p)


def test_write_tags_does_not_write_cover(tmp_path: Path):
    mp3 = tmp_path / "01.mp3"
    _mk_id3_file(mp3)

    write_tags([mp3], artist="A", album="B", cover=b"X", cover_mime="image/jpeg", track_start=1)

    id3 = ID3(mp3)
    assert "APIC:" not in str(id3.keys())


def test_write_cover_adds_and_can_clear(tmp_path: Path):
    mp3 = tmp_path / "01.mp3"
    _mk_id3_file(mp3)

    write_cover([mp3], cover=b"IMG", cover_mime="image/png")
    id3 = ID3(mp3)
    assert any(k.startswith("APIC") for k in id3)

    # deterministic clear
    write_cover([mp3], cover=None, cover_mime=None)
    id3 = ID3(mp3)
    assert not any(k.startswith("APIC") for k in id3)


def test_summarize_id3_files_reads_existing_tags(tmp_path: Path):
    mp3 = tmp_path / "01.mp3"
    id3 = ID3()
    id3.add(TIT2(encoding=3, text="Title One"))
    id3.add(TPE1(encoding=3, text="Artist One"))
    id3.add(TALB(encoding=3, text="Album One"))
    id3.add(TRCK(encoding=3, text="7"))
    id3.save(mp3)

    out = summarize_id3_files([mp3])

    assert out == [
        {
            "file": "01.mp3",
            "title": "Title One",
            "artist": "Artist One",
            "album": "Album One",
            "track": "7",
        }
    ]
