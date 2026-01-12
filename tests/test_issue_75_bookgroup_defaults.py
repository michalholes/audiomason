from pathlib import Path

import audiomason.import_flow as imp


def test_issue_75_bookgroup_defaults(tmp_path: Path):
    b = imp.BookGroup(label="X", group_root=tmp_path, stage_root=tmp_path)
    assert b.rel_path == Path(".")
    assert b.m4a_hint is None
