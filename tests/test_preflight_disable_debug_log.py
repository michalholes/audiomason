from __future__ import annotations


import audiomason.state as state
from audiomason.import_flow import _pf_prompt_yes_no, _pf_prompt


def test_preflight_disable_debug_log_yes_no(capsys, monkeypatch):
    # Enable debug traces (same condition as other [TRACE] lines)
    monkeypatch.setattr(state, "DEBUG", True, raising=False)

    cfg = {"preflight_disable": ["publish"]}
    ret = _pf_prompt_yes_no(cfg, "publish", "Publish after import?", default_no=True)
    assert ret is False

    out = capsys.readouterr()
    combined = (out.out or "") + (out.err or "")
    assert "[preflight] disabled: publish" in combined
    assert "default: no" in combined


def test_preflight_disable_debug_log_prompt(capsys, monkeypatch):
    monkeypatch.setattr(state, "DEBUG", True, raising=False)

    cfg = {"preflight_disable": ["cover"]}
    ret = _pf_prompt(cfg, "cover", "Choose cover", "2")
    assert ret == "2"

    out = capsys.readouterr()
    combined = (out.out or "") + (out.err or "")
    assert "[preflight] disabled: cover" in combined
    assert "default: 2" in combined
