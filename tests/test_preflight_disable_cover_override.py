from __future__ import annotations

import pytest

from audiomason import import_flow


def test_pf_prompt_cover_disabled_returns_default_without_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("prompt() must not be called when preflight is disabled")

    monkeypatch.setattr(import_flow, "prompt", _boom)

    cfg: dict = {"preflight_disable": ["cover"]}
    ret = import_flow._pf_prompt(cfg, "cover", "Cover URL or file path (Enter=skip)", "")
    assert ret == ""


def test_pf_prompt_yes_no_cover_disabled_returns_default_without_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("prompt_yes_no() must not be called when preflight is disabled")

    monkeypatch.setattr(import_flow, "prompt_yes_no", _boom)

    cfg: dict = {"preflight_disable": ["cover"]}
    assert import_flow._pf_prompt_yes_no(cfg, "cover", "Use embedded cover?", default_no=False) is True
    assert import_flow._pf_prompt_yes_no(cfg, "cover", "Use embedded cover?", default_no=True) is False
