from __future__ import annotations

from pathlib import Path

from audiomason.paths import IGNORE_FILE
from audiomason.state import OPTS
from audiomason.util import out, slug

IGNORE_BASENAME = ".abook_ignore"


def _resolve_ignore_file(path: Path | None) -> Path:
    # Legacy/global behavior: if path is None, use IGNORE_FILE (paths.py)
    if path is None:
        return IGNORE_FILE
    # Per-directory behavior: if path is a dir, use <dir>/.abook_ignore
    if path.exists() and path.is_dir():
        return path / IGNORE_BASENAME
    # If caller passes a file path, use it directly
    return path


def load_ignore(drop_root: Path) -> set[str]:
    keys: set[str] = set()
    for name in (".abook_ignore", ".ignore"):
        f = drop_root / name
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s == "~" or s.startswith("#"):
                continue
            keys.add(s)
    return keys


def add_ignore(path_or_name: Path | str, name: str | None = None) -> None:
    # Back-compat:
    #   add_ignore("Some.Source") -> global IGNORE_FILE
    # New:
    #   add_ignore(Path(dir), "BookDir") -> dir/.abook_ignore
    if name is None:
        dir_path: Path | None = None
        raw = str(path_or_name)
    else:
        dir_path = Path(path_or_name)
        raw = name

    key = slug(raw)
    if not key:
        return

    f = _resolve_ignore_file(dir_path)

    if dir_path is not None and key in load_ignore(dir_path):
        return
    if OPTS is not None and OPTS.dry_run:
        out(f"[dry-run] would ignore source: {key}")
        return

    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fp:
        fp.write(key + "\n")
    out(f"[ignore] added {key}")
