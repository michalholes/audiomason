import pytest
import audiomason.openlibrary as ol


@pytest.fixture(autouse=True)
def disable_external_book_metadata(monkeypatch):
    """
    Disable all external book metadata lookups in tests.

    This fixture ensures:
    - no OpenLibrary HTTP calls
    - no Google Books fallback calls
    - no artificial sleeps
    Tests remain fast, offline, and deterministic.
    """

    # Disable OpenLibrary author validation
    monkeypatch.setattr(
        ol,
        "validate_author",
        lambda name: ol.OLResult(False, "author:not_found", 0, None),
    )

    # Disable OpenLibrary + Google Books book validation
    monkeypatch.setattr(
        ol,
        "validate_book",
        lambda author, title: ol.OLResult(False, "book:not_found", 0, None),
    )

