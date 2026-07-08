from __future__ import annotations

import pytest

from audiomason.import_flow import _pf_prompt, _pf_prompt_yes_no, _resolved_preflight_disable
from audiomason.util import AmConfigError


def test_preflight_disable_unknown_key_fails_fast():
    cfg = {"preflight_disable": ["nope"]}
    with pytest.raises(AmConfigError):
        _resolved_preflight_disable(cfg)


def test_preflight_disable_yes_no_uses_existing_default_without_prompt(monkeypatch):
    # default_no=True => default answer is NO (False)
    cfg = {"preflight_disable": ["publish"]}

    def boom(*args, **kwargs):
        raise AssertionError("prompt_yes_no should not be called when disabled")

    import audiomason.import_flow as imp

    monkeypatch.setattr(imp, "prompt_yes_no", boom)
    assert _pf_prompt_yes_no(cfg, "publish", "Publish after import?", default_no=True) is False


def test_preflight_disable_prompt_uses_default_without_prompt(monkeypatch):
    cfg = {"preflight_disable": ["cover"]}

    def boom(*args, **kwargs):
        raise AssertionError("prompt should not be called when disabled")

    import audiomason.import_flow as imp

    monkeypatch.setattr(imp, "prompt", boom)
    assert _pf_prompt(cfg, "cover", "Choose cover [1/2/s/u]", "2") == "2"
