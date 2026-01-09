from __future__ import annotations

from pathlib import Path


def test_preflight_prompts_do_not_bypass_pf_wrappers():
    txt = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

    # Legacy bypass branches must not exist
    assert "if _prompt_disabled(cfg, 'choose_source')" not in txt
    assert "if _prompt_disabled(cfg, 'choose_books')" not in txt
    assert "def _choose_books_disabled" not in txt

    # Direct prompt calls must not exist for these preflight decisions
    assert "prompt(\"Choose source number, or 'a' for all\"" not in txt
    assert "prompt(\"Choose book number, or 'a' for all\"" not in txt
    assert "prompt_yes_no(\"Skip already processed books?\"" not in txt
    assert "prompt_yes_no(\"Destination exists. Overwrite?\"" not in txt
