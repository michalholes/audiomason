from __future__ import annotations

import audiomason.ai_lookup as ai_lookup


def test_ai_lookup_parses_json_suggestion():
    content = '{"suggestion":"Stoparuv pruvodce po galaxii","confidence":0.97}'
    suggestion, confidence = ai_lookup._parse_json_suggestion(content)
    assert suggestion == "Stoparuv pruvodce po galaxii"
    assert confidence == 0.97
    assert (
        ai_lookup._sanitize_suggestion("Stoparuv pruvodce galaxii", suggestion)
        == "Stoparuv pruvodce po galaxii"
    )


def test_ai_lookup_suppresses_low_confidence():
    content = '{"suggestion":"Wrong Thing","confidence":0.2}'
    suggestion, confidence = ai_lookup._parse_json_suggestion(content)
    assert suggestion == "Wrong Thing"
    assert confidence == 0.2
    assert confidence < 0.8
