from __future__ import annotations

from pathlib import Path

import audiomason.import_flow as imp


def test_issue_75_output_dir_author_and_title_only():
    dest = Path("/tmp/out")
    assert imp._output_dir(dest, "Doe John", "Book A") == dest / "Doe John" / "Book A"


def test_issue_75_output_dir_rejects_empty():
    dest = Path("/tmp/out")
    try:
        imp._output_dir(dest, "", "X")
        assert False, "expected error"
    except Exception:
        pass
    try:
        imp._output_dir(dest, "A", "")
        assert False, "expected error"
    except Exception:
        pass
