from pathlib import Path

import audiomason.import_flow as imp


def test_pipeline_steps_controls_process_order(monkeypatch, tmp_path: Path):
    calls = []

    def ren(outdir, mp3s):
        calls.append("rename")
        return mp3s

    def tags(mp3s, **kwargs):
        calls.append("tags")

    def cov(**kwargs):
        calls.append("choose_cover")
        return (b"IMG", "image/jpeg")

    def wc(mp3s, **kwargs):
        calls.append("write_cover")

    monkeypatch.setattr(imp, "rename_sequential", ren)
    monkeypatch.setattr(imp, "write_tags", tags)
    monkeypatch.setattr(imp, "choose_cover", cov)
    monkeypatch.setattr(imp, "write_cover", wc)

    b = imp.BookGroup(
        label="X",
        group_root=tmp_path,
        stage_root=tmp_path,
        m4a_hint=None,
    )

    mp3s = [tmp_path / "01.mp3", tmp_path / "02.mp3"]
    steps = ["tags", "rename", "cover", "publish"]

    imp._apply_book_steps(
        steps=steps,
        mp3s=mp3s,
        outdir=tmp_path,
        author="A",
        title="T",
        out_title="T",
        i=1,
        n=1,
        b=b,
        cfg={},
        cover_mode="embedded",
    )

    assert calls == ["tags", "rename", "choose_cover", "write_cover"]
