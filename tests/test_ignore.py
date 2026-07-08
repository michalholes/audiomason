from __future__ import annotations

from pathlib import Path

from audiomason.ignore import add_ignore, load_ignore
from audiomason.util import slug


def test_add_ignore_for_file_uses_sidecar(tmp_path: Path):
    inbox = tmp_path / "abooksinbox"
    inbox.mkdir()
    src = inbox / "archive.zip"
    src.write_bytes(b"x")

    add_ignore(src, "Book One")

    assert load_ignore(src) == {slug("Book One")}
    assert (tmp_path / "archive.zip.abook_ignore").exists()
    assert not (inbox / "archive.zip.abook_ignore").exists()
