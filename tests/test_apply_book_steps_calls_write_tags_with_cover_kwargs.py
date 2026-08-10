from unittest.mock import MagicMock

from audiomason.import_flow import (  # pyright: ignore[reportPrivateUsage]
    BookGroup,
    _apply_book_steps,
)


def test_apply_book_steps_passes_cover_kwargs_to_write_tags(tmp_path, monkeypatch):
    """_apply_book_steps must forward cover=None, cover_mime=None to write_tags."""
    mock_write_tags = MagicMock()
    monkeypatch.setattr("audiomason.import_flow.write_tags", mock_write_tags)

    mp3s = [tmp_path / "01.mp3"]
    mp3s[0].write_bytes(b"")

    book = BookGroup(
        label="Test Book",
        group_root=tmp_path,
        stage_root=tmp_path,
    )

    _apply_book_steps(
        steps=["tags"],
        mp3s=mp3s,
        outdir=tmp_path,
        author="Author",
        title="Title",
        out_title="Title",
        i=1,
        n=1,
        b=book,
        cfg={},
        cover_mode="skip",
    )

    mock_write_tags.assert_called_once()
    _, kwargs = mock_write_tags.call_args
    assert "cover" in kwargs, "write_tags must receive cover kwarg"
    assert "cover_mime" in kwargs, "write_tags must receive cover_mime kwarg"
    assert kwargs["cover"] is None
    assert kwargs["cover_mime"] is None
