import os
import urllib.request

import pytest

import audiomason.metadata_lookup as ml
import audiomason.openlibrary as ol


@pytest.fixture(autouse=True)
def disable_external_book_metadata(monkeypatch):
    """
    Disable all external book metadata lookups in tests.

    Why this exists:
    - Some production modules may import OpenLibrary functions by value
      (e.g. `from audiomason.openlibrary import validate_book`).
      Patching only `audiomason.openlibrary.validate_book` then DOES NOT affect
      already-bound references inside other modules.

    This fixture patches provider functions used by metadata lookup:
    - audiomason.openlibrary.validate_author / validate_book
    - audiomason.ai_lookup.suggest_author / suggest_title
    - optionally blocks *all* urllib network access (default ON)

    Opt-out:
      AM_TEST_ALLOW_NET=1 pytest ...
    """
    allow_net = os.environ.get("AM_TEST_ALLOW_NET") == "1"

    def _stub_author(name):
        return ol.OLResult(False, "author:not_found", 0, None)

    def _stub_book(author, title):
        return ol.OLResult(False, "book:not_found", 0, None)

    def _stub_ai(*args, **kwargs):
        return None

    # Patch OpenLibrary module API
    monkeypatch.setattr(ol, "validate_author", _stub_author, raising=True)
    monkeypatch.setattr(ol, "validate_book", _stub_book, raising=True)

    # Patch the provider functions used by metadata_lookup
    monkeypatch.setattr(ml.openlibrary, "validate_author", _stub_author, raising=True)
    monkeypatch.setattr(ml.openlibrary, "validate_book", _stub_book, raising=True)
    monkeypatch.setattr(ml.ai_lookup, "suggest_author", _stub_ai, raising=True)
    monkeypatch.setattr(ml.ai_lookup, "suggest_title", _stub_ai, raising=True)

    # As a safety net, block any accidental network access in tests
    if not allow_net:

        def _blocked_urlopen(*args, **kwargs):
            raise AssertionError(
                "Network access is disabled in tests. "
                "If you really need it, run with AM_TEST_ALLOW_NET=1."
            )

        monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen, raising=True)
