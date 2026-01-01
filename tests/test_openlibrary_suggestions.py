from __future__ import annotations

from audiomason.openlibrary import _sanitize_title_suggestion


def test_ol_suggestion_dediacritizes_when_different():
    entered = 'Nadace'
    suggested = 'Nadace – 1. díl'
    out = _sanitize_title_suggestion(entered, suggested)
    assert out == 'Nadace 1. dil'


def test_ol_suggestion_suppressed_when_same_after_normalize():
    entered = 'Vychovavame deti a rosteme s nimi'
    suggested = 'Vychováváme děti a rosteme s nimi'
    # After de-diacritization, it matches entered -> suppress
    assert _sanitize_title_suggestion(entered, suggested) is None
