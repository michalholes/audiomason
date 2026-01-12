"""CONTRACT tests for import_flow discovery + selection.

These tests lock behavior as the fixed point for Issue #117 refactor:
- behavior is asserted (paths/selection/errors), not prompt strings
- import_flow keeps compatibility wrappers even if internals move

NOTE: Selection input is read via import_flow._pf_prompt (not builtins.input).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from audiomason import import_flow
from audiomason.util import AmExit


def test_list_sources_filters_and_orders(tmp_path: Path) -> None:
    drop = tmp_path / "drop"
    drop.mkdir()

    # candidates (dirs)
    (drop / "b").mkdir()
    (drop / "A").mkdir()

    # ignored-by-convention
    (drop / "_am_stage").mkdir()
    (drop / "_private").mkdir()
    (drop / ".hidden").mkdir()
    (drop / ".DS_Store").write_text("x", encoding="utf-8")
    (drop / "import.log.jsonl").write_text("x", encoding="utf-8")

    # ignore list (per-dir): .abook_ignore
    (drop / ".abook_ignore").write_text("b\n", encoding="utf-8")

    items = import_flow._list_sources(drop)

    # Only "A" should remain: "b" is ignored by .abook_ignore, others are filtered.
    names = [p.name for p in items]
    assert names == ["A"]


def test_choose_source_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sources = [tmp_path / "s1", tmp_path / "s2"]
    monkeypatch.setattr(import_flow, "_pf_prompt", lambda _cfg, _key, _msg, _default: "a")
    out = import_flow._choose_source({}, sources)
    assert out == sources


def test_choose_source_single(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sources = [tmp_path / "s1", tmp_path / "s2"]
    monkeypatch.setattr(import_flow, "_pf_prompt", lambda _cfg, _key, _msg, _default: "1")
    out = import_flow._choose_source({}, sources)
    assert out == [sources[0]]


@pytest.mark.parametrize("bad", ["0", "3", "x", "-1", ""])
def test_choose_source_invalid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad: str) -> None:
    sources = [tmp_path / "s1", tmp_path / "s2"]
    monkeypatch.setattr(import_flow, "_pf_prompt", lambda _cfg, _key, _msg, _default: bad)
    with pytest.raises(AmExit):
        import_flow._choose_source({}, sources)
