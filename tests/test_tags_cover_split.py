from pathlib import Path

from mutagen.id3 import ID3

from audiomason.tags import write_tags, write_cover


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
    assert any(k.startswith("APIC") for k in id3.keys())

    # deterministic clear
    write_cover([mp3], cover=None, cover_mime=None)
    id3 = ID3(mp3)
    assert not any(k.startswith("APIC") for k in id3.keys())
