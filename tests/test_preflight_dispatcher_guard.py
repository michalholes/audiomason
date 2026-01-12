from __future__ import annotations

from pathlib import Path

import pytest

from audiomason import import_flow


def test_choose_source_routes_input_through_pf_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def _boom(*args, **kwargs):
        raise AssertionError("direct prompt() call is forbidden in this test")

    def _stub_pf_prompt(cfg: dict, key: str, question: str, default: str) -> str:
        calls.append((key, question, default))
        return "1"

    monkeypatch.setattr(import_flow, "prompt", _boom)
    monkeypatch.setattr(import_flow, "_pf_prompt", _stub_pf_prompt)

    cfg: dict = {}
    sources = [Path("A"), Path("B")]
    picked = import_flow._choose_source(cfg, sources)

    assert picked == [sources[0]]
    assert calls and calls[0][0] == "choose_source"


def test_choose_books_routes_input_through_pf_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def _boom(*args, **kwargs):
        raise AssertionError("direct prompt() call is forbidden in this test")

    def _stub_pf_prompt(cfg: dict, key: str, question: str, default: str) -> str:
        calls.append((key, question, default))
        return "a"

    monkeypatch.setattr(import_flow, "prompt", _boom)
    monkeypatch.setattr(import_flow, "_pf_prompt", _stub_pf_prompt)

    cfg: dict = {}
    b1 = import_flow.BookGroup(label="B1", group_root=tmp_path / "b1", stage_root=tmp_path / "s1")
    b2 = import_flow.BookGroup(label="B2", group_root=tmp_path / "b2", stage_root=tmp_path / "s2")
    picked = import_flow._choose_books(cfg, [b1, b2], default_ans="1")

    assert picked == [b1, b2]
    assert calls and calls[0][0] == "choose_books"
