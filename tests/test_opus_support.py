from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import audiomason.state as state
from audiomason.state import Opts
from audiomason import audio
from audiomason import import_flow as imp


def test_convert_opus_in_place_creates_mp3(monkeypatch, tmp_path: Path) -> None:
    # Arrange
    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(dry_run=False, loudnorm=False, q_a="2", ff_loglevel="warning", cpu_cores=None)
        src = tmp_path / "track.opus"
        src.write_bytes(b"fake-opus")

        monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else "/usr/bin/ffprobe")

        def fake_run_cmd(cmd, check=True, stdout=None):
            dst = Path(cmd[-1])
            dst.write_bytes(b"fake-mp3")
            return SimpleNamespace(stdout=b"")

        monkeypatch.setattr(audio, "run_cmd", fake_run_cmd)

        # Act
        audio.convert_opus_in_place(tmp_path, recursive=False)

        # Assert
        assert (tmp_path / "track.mp3").exists()
    finally:
        state.OPTS = old_opts


def test_detect_books_after_opus_conversion(monkeypatch, tmp_path: Path) -> None:
    # Arrange: opus-only folder should become a detectable book once converted to mp3
    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(dry_run=False, loudnorm=False, q_a="2", ff_loglevel="warning", cpu_cores=None)

        stage = tmp_path / "stage"
        stage.mkdir()
        (stage / "01.opus").write_bytes(b"fake-opus")

        monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else "/usr/bin/ffprobe")

        def fake_run_cmd(cmd, check=True, stdout=None):
            dst = Path(cmd[-1])
            dst.write_bytes(b"fake-mp3")
            return SimpleNamespace(stdout=b"")

        monkeypatch.setattr(audio, "run_cmd", fake_run_cmd)

        # Act: convert then detect
        audio.convert_opus_in_place(stage, recursive=True)
        books = imp._detect_books(stage)

        # Assert: at least one book group exists
        assert books, "expected at least one detected book after opus conversion"
    finally:
        state.OPTS = old_opts
