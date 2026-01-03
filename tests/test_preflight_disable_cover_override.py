from __future__ import annotations

from pathlib import Path


def test_preflight_disable_cover_override_is_routed_via_pf_prompt():
    txt = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

    assert 'raw = prompt("Cover URL or file path (Enter=skip)", "").strip()' not in txt
    assert txt.count('raw = _pf_prompt(cfg, "cover", "Cover URL or file path (Enter=skip)", "").strip()') == 3
