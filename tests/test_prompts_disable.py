from __future__ import annotations

from pathlib import Path

import pytest

from audiomason.import_flow import BookGroup, _choose_books, _choose_source, _resolved_prompts_disable
from audiomason.util import AmConfigError


def test_prompts_disable_invalid_type_fails_fast():
    cfg = {"prompts": {"disable": "nope"}}
    with pytest.raises(AmConfigError):
        _resolved_prompts_disable(cfg)


def test_prompts_disable_unknown_key_fails_fast():
    cfg = {"prompts": {"disable": ["nope"]}}
    with pytest.raises(AmConfigError):
        _resolved_prompts_disable(cfg)


def test_prompts_disable_duplicate_fails_fast():
    cfg = {"prompts": {"disable": ["choose_source", "choose_source"]}}
    with pytest.raises(AmConfigError):
        _resolved_prompts_disable(cfg)


def test_prompts_disable_star_cannot_be_combined():
    cfg = {"prompts": {"disable": ["*", "choose_source"]}}
    with pytest.raises(AmConfigError):
        _resolved_prompts_disable(cfg)


def test_disable_all_skips_choose_source_prompt(monkeypatch):
    from audiomason import import_flow as mod

    def boom(*args, **kwargs):
        raise AssertionError("prompt() must not be called")

    monkeypatch.setattr(mod, "prompt", boom)

    cfg = {"prompts": {"disable": ["*"]}}
    got = _choose_source(cfg, [Path("A"), Path("B")])
    assert got == [Path("A")]


def test_disable_choose_books_skips_prompt(monkeypatch, tmp_path: Path):
    from audiomason import import_flow as mod

    def boom(*args, **kwargs):
        raise AssertionError("prompt() must not be called")

    monkeypatch.setattr(mod, "prompt", boom)

    cfg = {"prompts": {"disable": ["choose_books"]}}
    b1 = BookGroup(label="One", group_root=tmp_path, stage_root=tmp_path, rel_path=Path("."), m4a_hint=None)
    b2 = BookGroup(label="Two", group_root=tmp_path, stage_root=tmp_path, rel_path=Path("."), m4a_hint=None)
    got = _choose_books(cfg, [b1, b2], default_ans="1")
    assert got == [b1]
