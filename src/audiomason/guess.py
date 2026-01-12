from __future__ import annotations

from typing import Optional


def guess_author_book(name: str, root_name: str = "__ROOT_AUDIO__") -> tuple[Optional[str], str]:
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
