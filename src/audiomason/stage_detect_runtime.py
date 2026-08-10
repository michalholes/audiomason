from __future__ import annotations
# ruff: noqa: I001

import shutil
from pathlib import Path

from audiomason.util import ensure_dir


def _by_name_casefold(p: Path) -> str:
    return p.name.casefold()


def _by_posix_lower(p: Path) -> str:
    return p.as_posix().lower()


# Local audio extensions (keep in sync with import_flow._AUDIO_EXTS)
_AUDIO_EXTS = {".mp3", ".m4a", ".opus"}


def reset_dir(p: Path) -> None:
    """Remove directory if it exists and recreate it.

    Uses async FS where available via the global loop; falls back to shutil.
    """
    if p.exists():
        # Use plain shutil; async bridge no longer needed here
        shutil.rmtree(p, ignore_errors=True)
    ensure_dir(p)


def stage_source(src: Path, stage_src: Path) -> None:
    """Copy directory or unpack archive into stage_src deterministically."""
    reset_dir(stage_src)
    if src.is_dir():
        # copy tree into stage (deterministic)
        def _do_copy(src_file: Path, dst_file: Path) -> None:
            shutil.copy2(src_file, dst_file)

        for item in src.rglob("*"):
            rel = item.relative_to(src)
            dst = stage_src / rel
            if item.is_dir():
                ensure_dir(dst)
            else:
                ensure_dir(dst.parent)
                _do_copy(item, dst)
        return

    from audiomason.archives import unpack
    from audiomason.paths import ARCHIVE_EXTS

    if src.is_file() and src.suffix.lower() in ARCHIVE_EXTS:
        unpack(src, stage_src)
        return

    from audiomason.util import die

    die(f"Unsupported source: {src}")


def has_audio_files_here(p: Path) -> bool:
    return any(f.is_file() and f.suffix.lower() in _AUDIO_EXTS for f in p.iterdir())


def find_first_m4a(p: Path) -> Path | None:
    for f in sorted(p.rglob("*.m4a"), key=_by_posix_lower):
        if f.is_file():
            return f
    return None


def collect_audio_files(group_root: Path) -> list[Path]:
    mp3s = sorted(
        [p for p in group_root.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"],
        key=_by_name_casefold,
    )
    m4as = sorted(
        [p for p in group_root.iterdir() if p.is_file() and p.suffix.lower() == ".m4a"],
        key=_by_name_casefold,
    )
    opuses = sorted(
        [p for p in group_root.iterdir() if p.is_file() and p.suffix.lower() == ".opus"],
        key=_by_name_casefold,
    )
    return mp3s + m4as + opuses
