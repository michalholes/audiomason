from __future__ import annotations

import re
from pathlib import Path


def test_preflight_disable_callsites_do_not_bypass_pf_prompt_yes_no():
    p = Path("src/audiomason/import_flow.py")
    txt = p.read_text(encoding="utf-8")

    # These exact call-sites previously bypassed preflight_disable
    # by calling prompt_yes_no directly (without cfg param).
    assert "use_manifest_answers = prompt_yes_no(" not in txt
    assert 'publish = prompt_yes_no("Publish after import?"' not in txt
    assert 'wipe = prompt_yes_no("Full wipe ID3 tags' not in txt
    assert 'clean_stage = prompt_yes_no("Clean stage after' not in txt

    # And we expect the pf_prompt_yes_no variants to be present.
    # (may be multi-line, so use regex with DOTALL)
    assert re.search(r'pf_prompt_yes_no\(\s*cfg,\s*"use_manifest_answers"', txt, re.DOTALL), (
        "missing pf_prompt_yes_no for use_manifest_answers"
    )
    assert re.search(
        r'pf_prompt_yes_no\(\s*cfg,\s*"publish".*"Publish after import\?"',
        txt,
        re.DOTALL,
    ), "missing pf_prompt_yes_no for publish"
    assert re.search(
        r'pf_prompt_yes_no\(\s*cfg,\s*"wipe_id3".*"Full wipe ID3 tags',
        txt,
        re.DOTALL,
    ), "missing pf_prompt_yes_no for wipe_id3"
    assert re.search(
        r'pf_prompt_yes_no\(\s*cfg,\s*"clean_stage".*"Clean stage after successful import\?"',
        txt,
        re.DOTALL,
    ), "missing pf_prompt_yes_no for clean_stage"
