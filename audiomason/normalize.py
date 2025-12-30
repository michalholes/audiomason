from __future__ import annotations

import re
import unicodedata

_ALLOWED = re.compile(r"[^A-Za-z0-9 ._-]+")


def strip_diacritics(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def ascii_text(s: str) -> str:
    return clean_spaces(strip_diacritics(s))


def path_component(s: str, use_spaces: bool = True) -> str:
    s = ascii_text(s)
    s = s.replace("/", " ")
    s = _ALLOWED.sub(" ", s)
    s = clean_spaces(s)
    if not use_spaces:
        s = s.replace(" ", "_")
        s = re.sub(r"_+", "_", s).strip("_")
    return s or "Unknown"


def looks_like_author_dir(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]+[.][A-Za-z0-9]+", name))


def to_surname_dot_name(person: str) -> str | None:
    raw = ascii_text(person)
    raw = re.sub(r"[\(\[].*?[\)\]]", "", raw).strip()
    raw = re.sub(r"[,_]+", " ", raw).strip()
    parts = [p for p in raw.split(" ") if p]
    if len(parts) < 2:
        return None
    first, last = parts[0], parts[-1]
    last_s = path_component(last, use_spaces=False)
    first_s = path_component(first, use_spaces=False)
    return f"{last_s}.{first_s}"
