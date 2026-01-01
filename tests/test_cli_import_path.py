from __future__ import annotations

from pathlib import Path
import sys
import importlib
import pytest
from audiomason.util import AmExit


def test_cli_import_accepts_path(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    # minimal contract layout
    (tmp_path / "abooksinbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_am_stage").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_ready").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks").mkdir(parents=True, exist_ok=True)
    # parse_args is internal; we only assert that argparse accepts the positional PATH.
    import audiomason.cli as cli
    monkeypatch.setattr(sys, "argv", ["audiomason", "import", "/some/where/SomeBook"])
    ns = cli._parse_args()
    assert ns.cmd == "import"
    assert isinstance(ns.path, Path)
    assert str(ns.path) == "/some/where/SomeBook"


def test_resolve_source_arg_enforces_drop_root(tmp_path):
    from audiomason.import_flow import _resolve_source_arg

    drop = tmp_path / "abooksinbox"
    drop.mkdir(parents=True)
    inside = drop / "Book1"
    inside.mkdir()

    assert _resolve_source_arg(drop, inside) == inside.resolve()
    assert _resolve_source_arg(drop, Path("Book1")) == inside.resolve()

    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(AmExit):
        _resolve_source_arg(drop, outside)
