from __future__ import annotations

from pathlib import Path

import pytest

from audiomason import import_flow


def test_apply_book_steps_write_tags_call_includes_cover_kwargs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called: dict = {}

    def _stub_write_tags(mp3s, **kwargs):
        called["mp3s"] = list(mp3s)
        called["kwargs"] = dict(kwargs)

    monkeypatch.setattr(import_flow, "write_tags", _stub_write_tags)

    b = import_flow.BookGroup(label="B", group_root=tmp_path / "g", stage_root=tmp_path / "s")
    mp3 = tmp_path / "x.mp3"
    mp3.write_bytes(b"ID3")

    import_flow._apply_book_steps(
        steps=["tags"],
        mp3s=[mp3],
        outdir=tmp_path / "out",
        author="Author",
        title="Title",
        out_title="Title",
        i=1,
        n=1,
        b=b,
        cfg={},
        cover_mode="skip",
    )

    assert "kwargs" in called
    assert called["kwargs"].get("cover") is None
    assert called["kwargs"].get("cover_mime") is None
