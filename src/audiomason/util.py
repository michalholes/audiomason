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
