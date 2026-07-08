from audiomason.guess import (
    guess_author_book,
    guess_book_title_default,
    guess_series_numbering_style,
    guess_source_author_default,
    normalize_series_numbering,
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


def test_guess_series_numbering_style_prefers_arabic_when_mixed():
    books = [
        {
            "default_title": "Stoparuv pruvodce Galaxii V. - Prevazne neskodna",
            "root_audio": True,
        },
        {
            "default_title": "Stoparuv pruvodce Galaxii 2 Restaurant Na Konci Vesmiru",
            "root_audio": False,
        },
        {"default_title": "Stoparuv pruvodce galaxii 3", "root_audio": False},
    ]
    assert guess_series_numbering_style(books) == "arabic"


def test_normalize_series_numbering_converts_first_number_token():
    assert (
        normalize_series_numbering(
            "Stoparuv pruvodce Galaxii 2 Restaurant Na Konci Vesmiru",
            "roman",
        )
        == "Stoparuv pruvodce Galaxii II Restaurant Na Konci Vesmiru"
    )
