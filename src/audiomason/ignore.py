from __future__ import annotations

from pathlib import Path

from audiomason.paths import IGNORE_FILE
from audiomason.state import OPTS
from audiomason.util import out, slug

IGNORE_BASENAME = ".abook_ignore"


def _resolve_ignore_file(path: Path | None, *, source_list: bool) -> Path:
    # Legacy/global behavior: if path is None, use the canonical state file.
    if path is None:
        return IGNORE_FILE

    # Source list ignore must stay outside the inbox.
    if source_list:
        return path.parent / IGNORE_BASENAME

    # Per-source/book ignore must also stay outside the inbox.
    base = path.parent.parent if path.parent.parent != path.parent else path.parent
    return base / f"{path.name}{IGNORE_BASENAME}"


def load_ignore(drop_root: Path, *, source_list: bool = False) -> set[str]:
    keys: set[str] = set()
    f = _resolve_ignore_file(drop_root, source_list=source_list)
    if not f.exists():
        return keys

    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s == "~" or s.startswith("#"):
            continue
        keys.add(s)
    return keys


def add_ignore(
    path_or_name: Path | str,
    name: str | None = None,
    *,
    source_list: bool = False,
) -> None:
    # Back-compat:
    #   add_ignore("Some.Source") -> global IGNORE_FILE
    # New:
    #   add_ignore(Path(dir), "BookDir") -> canonical state location
    if name is None:
        dir_path: Path | None = None
        raw = str(path_or_name)
    else:
        dir_path = Path(path_or_name)
        raw = name

    key = slug(raw)
    if not key:
        return

    f = _resolve_ignore_file(dir_path, source_list=source_list)

    if dir_path is not None and key in load_ignore(dir_path, source_list=source_list):
        return
    if OPTS is not None and OPTS.dry_run:
        out(f"[dry-run] would ignore: {key}")
        return

    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fp:
        fp.write(key + "\n")
    out(f"[ignore] added {key}")
