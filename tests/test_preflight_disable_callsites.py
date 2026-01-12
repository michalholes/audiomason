from __future__ import annotations

import pytest

import audiomason.state as state
from audiomason import import_flow


def test_preflight_global_routes_yes_no_prompts_through_pf_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, bool]] = []

    def _boom(*args, **kwargs):
        raise AssertionError("direct prompt_yes_no() call is forbidden in this test")

    def _stub_pf_yes_no(cfg: dict, key: str, question: str, *, default_no: bool) -> bool:
        calls.append((key, question, default_no))
        return {"publish": False, "wipe_id3": True}.get(key, True)

    monkeypatch.setattr(import_flow, "prompt_yes_no", _boom)
    monkeypatch.setattr(import_flow, "_pf_prompt_yes_no", _stub_pf_yes_no)

    state.OPTS = state.Opts(publish=None, wipe_id3=None)

    pub, wipe = import_flow._preflight_global(cfg={})

    assert pub is False
    assert wipe is True
    assert [c[0] for c in calls] == ["publish", "wipe_id3"]
