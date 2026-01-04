from pathlib import Path
import audiomason.import_flow as imp

def _mk(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")

def test_issue_75_nested_sources_detect_multiple_books(tmp_path: Path):
    stage = tmp_path / "src"
    # Jano tree fragment:
    # stage/Jano/kniha1.mp3
    # stage/Jano/kniha/fff.mp3
    # stage/Jano/seria/kniha1/fff.mp3
    root = stage / "Jano"
    _mk(root / "kniha1.mp3")
    _mk(root / "kniha" / "fff.mp3")
    _mk(root / "seria" / "kniha1" / "fff.mp3")
    _mk(root / "seria" / "kniha2" / "fff.mp3")
    _mk(root / "seria" / "kniha3" / "fff.mp3")

    books = imp._detect_books(root)
    labels = sorted([b.label for b in books], key=lambda x: str(x).casefold())
    assert labels == ["__ROOT_AUDIO__", "kniha", "seria/kniha1", "seria/kniha2", "seria/kniha3"]

def test_issue_75_nonrecursive_collect_does_not_steal_subdir_audio(tmp_path: Path):
    root = tmp_path / "src"
    _mk(root / "01.mp3")
    _mk(root / "sub" / "02.mp3")

    files = imp._collect_audio_files(root)
    # should only include root/01.mp3
    names = [p.name for p in files]
    assert names == ["01.mp3"]
