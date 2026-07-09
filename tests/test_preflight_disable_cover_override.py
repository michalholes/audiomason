from __future__ import annotations

import re
from pathlib import Path


def test_preflight_disable_cover_override_is_routed_via_pf_prompt():
    txt = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

    assert 'raw = prompt("Cover URL or file path (Enter=skip)"' not in txt

    # Count all pf_prompt calls for "Cover URL or file path" (may be multi-line)
    matches = re.findall(
        r'raw = pf_prompt\(\s*cfg,\s*"cover",\s*"Cover URL or file path \(Enter=skip\)"',
        txt,
        re.DOTALL,
    )
    assert len(matches) == 3, f"expected 3 pf_prompt cover calls, got {len(matches)}"
