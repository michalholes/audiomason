from __future__ import annotations

import audiomason.metadata_lookup as ml
import audiomason.openlibrary as ol


def test_metadata_lookup_ai_fallback_for_book(monkeypatch):
    monkeypatch.setattr(
        ml.openlibrary,
        "validate_book",
        lambda author, title: ol.OLResult(False, "book:not_found", 0, None),
        raising=True,
    )
    monkeypatch.setattr(
        ml.ai_lookup, "suggest_title", lambda author, title, cfg=None: "Nadace", raising=True
    )

    out = ml.validate_book("Isaac Asimov", "Nadace", cfg={"ai": {"enabled": True}})
    assert out.ok is True
    assert out.top == "Nadace"
    assert out.source == "ai"


def test_metadata_lookup_public_result_wins(monkeypatch):
    monkeypatch.setattr(
        ml.openlibrary,
        "validate_author",
        lambda name: ol.OLResult(True, "author:ok", 12, "Douglas Adams"),
        raising=True,
    )
    monkeypatch.setattr(
        ml.ai_lookup, "suggest_author", lambda name, cfg=None: "Should Not Use", raising=True
    )

    out = ml.validate_author(
        "Douglas Adams", cfg={"openlibrary": {"enabled": True}, "ai": {"enabled": True}}
    )
    assert out.ok is True
    assert out.top == "Douglas Adams"
