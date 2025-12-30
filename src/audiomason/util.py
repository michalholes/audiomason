from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional

from audiomason.state import OPTS


def out(msg: str) -> None:
    if OPTS is None or not OPTS.quiet:
        print(msg, flush=True)


def die(msg: str, code: int = 2) -> None:
    print(f"[FATAL] {msg}", flush=True)
    raise SystemExit(code)


def strip_diacritics(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def clean_text(s: str) -> str:
    s = strip_diacritics(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def slug(s: str) -> str:
    s = strip_diacritics(s)
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "Unknown"


def two(n: int) -> str:
    return f"{n:02d}"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def unique_path(p: Path) -> Path:
    outp = p
    i = 2
    while outp.exists():
        outp = Path(str(p) + f"__{i}")
        i += 1
    return outp


def prompt(msg: str, default: Optional[str] = None) -> str:
    if OPTS is not None and OPTS.yes:
        return default or ""
    try:
        if default is not None and default != "":
            s = input(f"{msg} [{default}]: ").strip()
            return s if s else default
        s = input(f"{msg}: ").strip()
        return s
    except KeyboardInterrupt:
        out("\n[skip]")
        raise
        return default or ""


def prompt_yes_no(msg: str, default_no: bool = True) -> bool:
    if OPTS is not None and OPTS.yes:
        return False if default_no else True
    d = "y/N" if default_no else "Y/n"
    try:
        ans = input(f"{msg} [{d}] ").strip().lower()
    except KeyboardInterrupt:
        out("\n[skip]")
        return False if default_no else True
    if not ans:
        return False if default_no else True
    return ans in {"y", "yes"}


def prune_empty_dirs(start: Path, stop_at: Path) -> None:
    try:
        p = start
        while p != stop_at and p.exists():
            if any(p.iterdir()):
                break
            p.rmdir()
            p = p.parent
    except Exception:
        pass


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), flags=re.I))


def find_archive_match(archive_ro: str, author_hint: str, book_hint: str):
    """
    Best-effort lookup in archive_ro for an existing book.
    Returns (author_dirname, book_dirname) if exactly one strong match is found,
    otherwise (None, None).

    Matching is conservative: ignore very short hints to avoid false positives.
    """
    from pathlib import Path

    if not archive_ro:
        return (None, None)

    root = Path(archive_ro)
    if not root.exists():
        return (None, None)

    a = (author_hint or "").strip()
    b = (book_hint or "").strip()

    # Too short hints are ambiguous (e.g. "sp")
    if len(b) < 4 and len(a) < 4:
        return (None, None)

    a_slug = slug(a).lower() if a else ""
    b_slug = slug(b).lower() if b else ""

    hits = []

    for author_dir in root.iterdir():
        if not author_dir.is_dir():
            continue

        # if author hint exists, require author match
        if a_slug and slug(author_dir.name).lower() != a_slug and a_slug not in slug(author_dir.name).lower():
            continue

        for book_dir in author_dir.iterdir():
            if not book_dir.is_dir():
                continue
            bd = book_dir.name
            bd_slug = slug(bd).lower()

            if b_slug:
                if bd_slug == b_slug:
                    hits.append((author_dir.name, book_dir.name, 2))
                elif b_slug in bd_slug:
                    hits.append((author_dir.name, book_dir.name, 1))
            else:
                # no book hint: don't guess
                continue

    # prefer exact match
    exact = [(a,b) for a,b,score in hits if score == 2]
    if len(exact) == 1:
        return exact[0]

    # if only one fuzzy hit overall, accept
    uniq = []
    seen = set()
    for a,b,_ in hits:
        if (a,b) not in seen:
            seen.add((a,b))
            uniq.append((a,b))
    if len(uniq) == 1:
        return uniq[0]

    return (None, None)
