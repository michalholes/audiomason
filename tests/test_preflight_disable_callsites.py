from __future__ import annotations

from pathlib import Path


def test_preflight_disable_callsites_do_not_bypass_pf_prompt_yes_no():
    p = Path("src/audiomason/import_flow.py")
    txt = p.read_text(encoding="utf-8")

    # These exact call-sites previously bypassed preflight_disable by calling prompt_yes_no directly.
    assert (
        'use_manifest_answers = prompt_yes_no("[manifest] Use saved answers (skip prompts)?", default_no=False)'
        not in txt
    )
    assert 'publish = prompt_yes_no("Publish after import?", default_no=(not default_publish))' not in txt
    assert 'wipe = prompt_yes_no("Full wipe ID3 tags before tagging?", default_no=(not default_wipe))' not in txt
    assert (
        'clean_stage = prompt_yes_no("Clean stage after successful import?", default_no=(not default_clean))' not in txt
    )

    # And we expect the _pf_prompt_yes_no variants to be present.
    assert (
        '_pf_prompt_yes_no(cfg, "use_manifest_answers", "[manifest] Use saved answers (skip prompts)?", default_no=False)'
        in txt
    )
    assert '_pf_prompt_yes_no(cfg, "publish", "Publish after import?", default_no=(not default_publish))' in txt
    assert (
        '_pf_prompt_yes_no(cfg, "wipe_id3", "Full wipe ID3 tags before tagging?", default_no=(not default_wipe))' in txt
    )
    assert (
        '_pf_prompt_yes_no(cfg, "clean_stage", "Clean stage after successful import?", default_no=(not default_clean))'
        in txt
    )
