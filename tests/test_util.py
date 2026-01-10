from audiomason.util import clean_text, slug


def test_slug_basic():
    assert slug("Hello World") == "Hello_World"
    assert slug("Žluťoučký kůň") == "Zlutoucky_kun"

def test_clean_text():
    assert clean_text("  a   b  ") == "a b"
