from __future__ import annotations

from pathlib import Path

import pytest

import audiomason.metadata_lookup as ml
import audiomason.openlibrary as ol


def _stub_validate_book(author: str, title: str) -> ol.OLResult:
    return ol.OLResult(False, "book:not_found", 0, None)


def _stub_suggest_title(
    author: str,
    title: str,
    cfg: dict[str, object] | None = None,
    *,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> str:
    return "Nadace"


def _stub_validate_author(name: str) -> ol.OLResult:
    return ol.OLResult(True, "author:ok", 12, "Douglas Adams")


def _stub_suggest_author(
    name: str,
    cfg: dict[str, object] | None = None,
    *,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> str:
    return "Should Not Use"


def test_metadata_lookup_ai_fallback_for_book(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ml.ai_lookup, "_dry_run", lambda: False, raising=True)
    monkeypatch.setattr(
        ml.openlibrary,
        "validate_book",
        _stub_validate_book,
        raising=True,
    )
    monkeypatch.setattr(ml.ai_lookup, "suggest_title", _stub_suggest_title, raising=True)

    out = ml.validate_book("Isaac Asimov", "Nadace", cfg={"ai": {"enabled": True}})
    assert out.ok is True
    assert out.top == "Nadace"
    assert out.source == "ai"


def test_metadata_lookup_public_result_wins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ml.ai_lookup, "_dry_run", lambda: False, raising=True)
    monkeypatch.setattr(
        ml.openlibrary,
        "validate_author",
        _stub_validate_author,
        raising=True,
    )
    monkeypatch.setattr(ml.ai_lookup, "suggest_author", _stub_suggest_author, raising=True)

    out = ml.validate_author(
        "Douglas Adams", cfg={"openlibrary": {"enabled": True}, "ai": {"enabled": True}}
    )
    assert out.ok is True
    assert out.top == "Douglas Adams"
