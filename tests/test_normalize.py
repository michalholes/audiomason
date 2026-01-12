from audiomason.util import slug


def test_slug_ascii():
    assert slug("Červený kapitán") == "Cerveny_kapitan"
    assert slug("  Hello   World ") == "Hello_World"
    assert slug("Žluťoučký kůň") == "Zlutoucky_kun"
