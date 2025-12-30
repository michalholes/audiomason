from __future__ import annotations

from audiomason.paths import IGNORE_FILE
from audiomason.state import OPTS
from audiomason.util import out, slug


def load_ignore() -> set[str]:
    if not IGNORE_FILE.exists():
        return set()
    return {
        line.strip()
        for line in IGNORE_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def add_ignore(name: str) -> None:
    key = slug(name)
    if not key:
        return
    if key in load_ignore():
        return
    if OPTS is not None and OPTS.dry_run:
        out(f"[dry-run] would ignore source: {key}")
        return
    IGNORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with IGNORE_FILE.open("a", encoding="utf-8") as f:
        f.write(key + "\n")
    out(f"[ignore] added {key}")
