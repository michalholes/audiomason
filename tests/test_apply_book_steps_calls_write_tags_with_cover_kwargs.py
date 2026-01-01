from pathlib import Path


def test_apply_book_steps_write_tags_call_includes_cover_kwargs():
    s = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")
    assert "write_tags(mp3s, artist=author, album=title, track_start=1, cover=None, cover_mime=None)" in s
