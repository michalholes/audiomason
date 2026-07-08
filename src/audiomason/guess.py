from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import cast

from audiomason.util import strip_diacritics


def guess_author_book(name: str, root_name: str = "__ROOT_AUDIO__") -> tuple[str | None, str]:
    """Heuristic: 'Author - Title' -> ('Surname.GivenNames', 'Title'); otherwise (None, 'Title')."""
    s = (name or "").strip()
    if not s or s == root_name:
        return None, s

    if " - " in s:
        left, right = s.split(" - ", 1)
        left = left.strip()
        right = right.strip()
        if left and right:
            parts = [p for p in left.split() if p]
            if len(parts) >= 2:
                surname = parts[-1]
                given = "".join(parts[:-1])
                return f"{surname}.{given}", right
            return left, right

    return None, s


def _strip_label_noise(s: str) -> str:
    out = " ".join((s or "").strip().split())
    while True:
        new = re.sub(r"\s*(?:\([^()]*\)|\[[^\[\]]*\])\s*$", "", out).strip()
        if new == out:
            return out
        out = new


def guess_source_author_default(name: str) -> str:
    s = _strip_label_noise(name)
    if "," in s:
        left, right = s.split(",", 1)
        left = left.strip()
        right = right.strip()
        if left and right:
            s = f"{right} {left}"
    return " ".join(strip_diacritics(s).split()).strip()


def guess_book_title_default(label: str, root_name: str = "__ROOT_AUDIO__") -> str:
    s = _strip_label_noise(label)
    _, title = guess_author_book(s, root_name=root_name)
    title = _strip_label_noise(title)
    if not title or title == root_name:
        return "Untitled"
    return " ".join(strip_diacritics(title).split()).strip()


def _roman_to_int(token: str) -> int | None:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(token.upper()):
        cur = values.get(ch)
        if cur is None:
            return None
        if cur < prev:
            total -= cur
        else:
            total += cur
            prev = cur
    return total if total > 0 else None


def _int_to_roman(value: int) -> str | None:
    if value <= 0 or value >= 4000:
        return None
    parts = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out: list[str] = []
    n = value
    for num, roman in parts:
        while n >= num:
            out.append(roman)
            n -= num
    return "".join(out)


def _detect_numbering_style(title: str) -> str | None:
    s = (title or "").strip()
    if not s:
        return None
    m = re.search(r"\b([IVXLCDM]+\.?|\d+)\b", s, flags=re.I)
    if m is None:
        return None
    token = str(cast(object, m.group(1))).rstrip(".")
    if token.isdigit():
        return "arabic"
    if _roman_to_int(token) is not None:
        return "roman"
    return None


def guess_series_numbering_style(books: Sequence[Mapping[str, object]]) -> str | None:
    counts = {"arabic": 0, "roman": 0}
    for b in books:
        raw_title = b.get("default_title")
        if not isinstance(raw_title, str) or not raw_title.strip():
            raw_title = b.get("title")
        title = raw_title.strip() if isinstance(raw_title, str) else ""
        style = _detect_numbering_style(title)
        if style is None:
            continue
        counts[style] += 1
    if counts["arabic"]:
        return "arabic"
    if counts["roman"]:
        return "roman"
    return None


def normalize_series_numbering(title: str, style: str | None) -> str:
    s = (title or "").strip()
    if not s or style not in {"arabic", "roman"}:
        return title

    def _replace(m: re.Match[str]) -> str:
        token = str(cast(object, m.group(1)))
        suffix = "." if token.endswith(".") else ""
        raw = token.rstrip(".")
        if style == "arabic":
            if raw.isdigit():
                return raw + suffix
            value = _roman_to_int(raw)
            return f"{value}{suffix}" if value is not None else token
        if raw.isdigit():
            roman = _int_to_roman(int(raw))
            return f"{roman}{suffix}" if roman is not None else token
        value = _roman_to_int(raw)
        return f"{raw.upper()}{suffix}" if value is not None else token

    return re.sub(r"\b([IVXLCDM]+\.?|\d+)\b", _replace, s, count=1, flags=re.I)
