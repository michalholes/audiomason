from __future__ import annotations

import json
from pathlib import Path

from audiomason.import_flow import _build_json_report
from audiomason.manifest import update_manifest


def test_build_json_report_minimal(tmp_path: Path) -> None:
    sr = tmp_path / "stage_run"
    update_manifest(sr, {
        "source": {"name": "S", "stem": "S", "path": "/x", "fingerprint": "fp"},
        "books": {"detected": ["A"], "picked": ["A"], "processed": ["A"]},
        "decisions": {"publish": True, "wipe_id3": False, "author": "Auth", "clean_stage": True},
        "book_meta": {"A": {"title": "T", "out_title": "T", "cover_mode": "skip", "dest_kind": "output", "overwrite": False}},
    })
    rep = _build_json_report([sr])
    assert set(rep.keys()) == {"sources", "books", "decisions", "results"}
    s = json.dumps(rep, ensure_ascii=False, sort_keys=True)
    parsed = json.loads(s)
    assert parsed["results"]["books_total"] == 1
    assert parsed["results"]["books_processed"] == 1
