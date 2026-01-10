from __future__ import annotations

from audiomason.googlebooks import _pick_best


def test_googlebooks_pick_best_strong_match_cs():
    entered_title = "Stoparuv pruvodce galaxii"
    author = "Douglas Adams"
    items = [
        {"volumeInfo": {"title": "The Hitch Hiker's Guide to the Galaxy", "authors": ["Douglas Adams"], "language": "en"}},
        {"volumeInfo": {"title": "Stopařův průvodce po Galaxii", "authors": ["Douglas Adams"], "language": "cs"}},
        {"volumeInfo": {"title": "Stoparuv pruvodce po galaxii", "authors": ["Douglas Adams"], "language": "cs"}},
    ]
    # best should be one of the localized variants
    best = _pick_best(entered_title, author, items)
    assert best in {"Stopařův průvodce po Galaxii", "Stoparuv pruvodce po galaxii"}


def test_googlebooks_pick_best_requires_author_match():
    entered_title = "Stoparuv pruvodce galaxii"
    author = "Douglas Adams"
    items = [
        {"volumeInfo": {"title": "Stoparuv pruvodce po galaxii", "authors": ["Someone Else"], "language": "cs"}},
    ]
    assert _pick_best(entered_title, author, items) is None


def test_googlebooks_pick_best_weak_match_none():
    entered_title = "Steparuv pruvodce po galaxii 1"
    author = "Douglas Adams"
    items = [
        {"volumeInfo": {"title": "Totally different book", "authors": ["Douglas Adams"], "language": "cs"}},
        {"volumeInfo": {"title": "Another unrelated title", "authors": ["Douglas Adams"], "language": "cs"}},
    ]
    assert _pick_best(entered_title, author, items) is None
