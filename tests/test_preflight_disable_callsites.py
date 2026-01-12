from __future__ import annotations

import re
from pathlib import Path


def test_preflight_disable_callsites_do_not_bypass_pf_prompt_yes_no() -> None:
    txt = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

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

    # Formatting-robust: expect the _pf_prompt_yes_no variants to be present, regardless of wrapping/newlines.
    def must_have_pf_yes_no(key: str, prompt: str, default_expr: str) -> None:
        pattern = (
            r"_pf_prompt_yes_no\(\s*cfg\s*,\s*"
            + re.escape(f'"{key}"')
            + r"\s*,\s*"
            + re.escape(f'"{prompt}"')
            + r"\s*,\s*default_no\s*=\s*"
            + default_expr
            + r"\s*\)"
        )
        assert re.search(pattern, txt), f"expected _pf_prompt_yes_no call-site for {key!r} (formatting-robust)"

    must_have_pf_yes_no("use_manifest_answers", "[manifest] Use saved answers (skip prompts)?", r"False")
    must_have_pf_yes_no("publish", "Publish after import?", r"\(not\s+default_publish\)")
    must_have_pf_yes_no("wipe_id3", "Full wipe ID3 tags before tagging?", r"\(not\s+default_wipe\)")
    must_have_pf_yes_no("clean_stage", "Clean stage after successful import?", r"\(not\s+default_clean\)")
