from audiomason.guess import (
    guess_author_book,
    guess_book_title_default,
    guess_source_author_default,
)


def test_guess_author_book_dash():
    a, b = guess_author_book("Dan Brown - Inferno", "_ROOT_")
    assert a == "Brown.Dan"
    assert b == "Inferno"


def test_guess_book_only():
    a, b = guess_author_book("Inferno", "_ROOT_")
    assert a is None
    assert b == "Inferno"


def test_guess_source_author_default_strips_noise_and_flips_comma():
    assert guess_source_author_default("Měyrink, Gustáv (audio) [mp3]") == "Gustav Meyrink"


def test_guess_book_title_default_strips_duration_suffix():
    assert (
        guess_book_title_default("Gustav Meyrink - Obrazy vepsané do vzduchu (SK) (0h29m)")
        == "Obrazy vepsane do vzduchu"
    )
