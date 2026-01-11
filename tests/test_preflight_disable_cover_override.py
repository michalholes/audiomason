from __future__ import annotations

import re
from pathlib import Path


def test_preflight_disable_cover_override_is_routed_via_pf_prompt() -> None:
    txt = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

    # No direct prompt(...) bypass.
    assert 'raw = prompt("Cover URL or file path (Enter=skip)", "").strip()' not in txt

    # Formatting-robust: ensure that the preflight-wrapped prompt is still used.
    pattern = (
        r"raw\s*=\s*_pf_prompt\(\s*cfg\s*,\s*\"cover\"\s*,\s*"
        r"\"Cover URL or file path \(Enter=skip\)\"\s*,\s*\"\"\s*\)\.strip\(\)"
    )
    assert len(re.findall(pattern, txt)) == 3
