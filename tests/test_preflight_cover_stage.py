from __future__ import annotations

from pathlib import Path

from audiomason.import_flow import _stage_cover_from_raw


def test_stage_cover_from_local_path(tmp_path: Path):
    # Arrange: local 'image' file (bytes don't matter for staging)
    img = tmp_path / "x.jpg"
    img.write_bytes(b"fakejpg")
    group = tmp_path / "book"
    group.mkdir()

    cfg = {"paths": {"cache": str(tmp_path / "cache")}}

    # Act
    staged = _stage_cover_from_raw(cfg, str(img), group)

    # Assert
    assert staged is not None
    assert staged.name == "cover.jpg"
    assert staged.exists()
    assert staged.read_bytes() == b"fakejpg"
