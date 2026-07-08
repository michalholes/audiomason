from __future__ import annotations

import re

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
