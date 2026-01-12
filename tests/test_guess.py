from audiomason.guess import guess_author_book


def test_guess_author_book_dash():
    a, b = guess_author_book("Dan Brown - Inferno", "_ROOT_")
    assert a == "Brown.Dan"
    assert b == "Inferno"


def test_guess_book_only():
    a, b = guess_author_book("Inferno", "_ROOT_")
    assert a is None
    assert b == "Inferno"
