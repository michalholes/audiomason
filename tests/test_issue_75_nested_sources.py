from __future__ import annotations

from pathlib import Path
import audiomason.import_flow as imp


def _mk(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def test_issue_75_nested_sources_detect_multiple_books(tmp_path: Path):
    root = tmp_path / "Jano"
    _mk(root / "kniha1.mp3")  # root audio => __ROOT_AUDIO__
    _mk(root / "kniha" / "fff.mp3")
    _mk(root / "kniha2" / "fff.mp3")
    _mk(root / "kniha3" / "fff.mp3")
    _mk(root / "seria" / "kniha1" / "fff.mp3")
    _mk(root / "seria" / "kniha2" / "fff.mp3")
    _mk(root / "seria" / "kniha3" / "fff.mp3")

    books = imp._detect_books(root)
    labels = sorted([b.label for b in books], key=lambda x: str(x).casefold())
    assert labels == ["__ROOT_AUDIO__", "kniha", "kniha2", "kniha3", "seria/kniha1", "seria/kniha2", "seria/kniha3"]


def test_issue_75_nonrecursive_collect_does_not_steal_subdir_audio(tmp_path: Path):
    root = tmp_path / "src"
    _mk(root / "01.mp3")
    _mk(root / "sub" / "02.mp3")

    files = imp._collect_audio_files(root)
    names = [p.name for p in files]
    assert names == ["01.mp3"]


def test_issue_75_output_dir_is_author_and_title_only(tmp_path: Path):
    archive = tmp_path / "archive"
    out = imp._output_dir(archive, "Doe John", "My Book")
    assert out == archive / "Doe John" / "My Book"
