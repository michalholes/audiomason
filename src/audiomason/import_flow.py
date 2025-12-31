from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import audiomason.state as state
from audiomason.paths import get_drop_root, get_stage_root, get_archive_root, ARCHIVE_EXTS
from audiomason.util import out, die, ensure_dir, slug, prompt, prompt_yes_no
from audiomason.ignore import load_ignore, add_ignore
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place
from audiomason.rename import natural_sort, rename_sequential
from audiomason.covers import choose_cover
from audiomason.tags import wipe_id3, write_tags


_AUDIO_EXTS = {".mp3", ".m4a"}


@dataclass(frozen=True)
class BookGroup:
    label: str          # "__ROOT_AUDIO__" or folder name
    group_root: Path    # where to pull audio from (stage src root OR a subdir)
    stage_root: Path    # stage src root (for cover search)
    m4a_hint: Optional[Path]


def _list_sources(drop_root: Path) -> list[Path]:
    if not drop_root.exists():
        ensure_dir(drop_root)
        return []
    items = []
    for p in sorted(drop_root.iterdir(), key=lambda x: x.name.lower()):
        if p.name.startswith("."):
            continue
        if p.is_dir():
            items.append(p)
            continue
        if p.is_file() and p.suffix.lower() in ARCHIVE_EXTS:
            items.append(p)
    return items


def _choose_source(sources: list[Path]) -> list[Path]:
    if not sources:
        out("[inbox] empty")
        return []
    out("[inbox] sources:")
    for i, p in enumerate(sources, 1):
        out(f"  {i}) {p.name}")
    ans = prompt("Choose source number, or 'a' for all", "1").strip().lower()
    if ans == "a":
        return sources
    try:
        n = int(ans)
        if 1 <= n <= len(sources):
            return [sources[n - 1]]
    except Exception:
        pass
    die("Invalid source selection")
    return []


def _reset_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    ensure_dir(p)


def _stage_source(src: Path, stage_src: Path) -> None:
    _reset_dir(stage_src)
    if src.is_dir():
        # copy tree into stage (deterministic)
        for item in src.rglob("*"):
            rel = item.relative_to(src)
            dst = stage_src / rel
            if item.is_dir():
                ensure_dir(dst)
            else:
                ensure_dir(dst.parent)
                shutil.copy2(item, dst)
        return

    if src.is_file() and src.suffix.lower() in ARCHIVE_EXTS:
        unpack(src, stage_src)
        return

    die(f"Unsupported source: {src}")


def _has_audio_files_here(p: Path) -> bool:
    for f in p.iterdir():
        if f.is_file() and f.suffix.lower() in _AUDIO_EXTS:
            return True
    return False


def _find_first_m4a(p: Path) -> Optional[Path]:
    for f in sorted(p.rglob("*.m4a"), key=lambda x: x.as_posix().lower()):
        if f.is_file():
            return f
    return None


def _detect_books(stage_src: Path) -> list[BookGroup]:
    books: list[BookGroup] = []

    # root audio => "__ROOT_AUDIO__"
    if stage_src.exists() and stage_src.is_dir() and _has_audio_files_here(stage_src):
        books.append(BookGroup("__ROOT_AUDIO__", stage_src, stage_src, _find_first_m4a(stage_src)))

    # each top-level dir that contains any audio anywhere inside => book
    for d in sorted([x for x in stage_src.iterdir() if x.is_dir()], key=lambda x: x.name.lower()):
        has_any = any((f.is_file() and f.suffix.lower() in _AUDIO_EXTS) for f in d.rglob("*"))
        if has_any:
            books.append(BookGroup(d.name, d, stage_src, _find_first_m4a(d)))

    if not books:
        die("No books found in source (no mp3/m4a in root or top-level subdirs)")
    return books


def _choose_books(books: list[BookGroup]) -> list[BookGroup]:
    if len(books) == 1:
        return books
    out(f"[books] found {len(books)}:")
    for i, b in enumerate(books, 1):
        out(f"  {i}) {b.label}")
    ans = prompt("Choose book number, or 'a' for all", "1").strip().lower()
    if ans == "a":
        return books
    try:
        n = int(ans)
        if 1 <= n <= len(books):
            return [books[n - 1]]
    except Exception:
        pass
    die("Invalid book selection")
    return []


def _collect_audio_files(group_root: Path) -> list[Path]:
    mp3s = [p for p in group_root.rglob("*.mp3") if p.is_file()]
    m4as = [p for p in group_root.rglob("*.m4a") if p.is_file()]
    # NOTE: m4a should have been converted already; but keep mp3-only output deterministic.
    if not mp3s and not m4as:
        die(f"No audio found in selected book group: {group_root}")
    return natural_sort(mp3s)


def _preflight_global() -> tuple[bool, bool]:
    # publish (placeholder, but must be decided before processing)
    if state.OPTS.publish is None:
        pub = prompt_yes_no("Publish after import?", default_no=True)
    else:
        pub = bool(state.OPTS.publish)

    # wipe ID3 decision
    if state.OPTS.wipe_id3 is None:
        wipe = prompt_yes_no("Full wipe ID3 tags before tagging?", default_no=True)
    else:
        wipe = bool(state.OPTS.wipe_id3)

    return (pub, wipe)


def _preflight_book(i: int, n: int, b: BookGroup) -> tuple[str, str]:
    out(f"[book] {i}/{n}: {b.label}")
    default_author = b.label if b.label != "__ROOT_AUDIO__" else ""
    author = prompt(f"[book {i}/{n}] Author", default_author).strip()
    if not author:
        die("Author is required")
    default_title = b.label if b.label != "__ROOT_AUDIO__" else "Untitled"
    title = prompt(f"[book {i}/{n}] Book title", default_title).strip()
    if not title:
        die("Book title is required")
    return (author, title)


def _output_dir(archive_root: Path, author: str, title: str) -> Path:
    # NO slug() in output paths; keep as user entered
    return archive_root / author / title


def _copy_audio_to_out(group_root: Path, outdir: Path) -> list[Path]:
    ensure_dir(outdir)
    src_mp3s = _collect_audio_files(group_root)
    if not src_mp3s:
        die("No mp3 files to import (convert step did not produce mp3)")
    copied: list[Path] = []
    for p in src_mp3s:
        dst = outdir / p.name
        shutil.copy2(p, dst)
        copied.append(dst)
    copied = natural_sort(copied)
    return rename_sequential(outdir, copied)


def _process_book(i: int, n: int, b: BookGroup, archive_root: Path, author: str, title: str, wipe: bool) -> None:
    out(f"[book] {i}/{n}: {b.label}")

    outdir = _output_dir(archive_root, author, title)
    if outdir.exists() and any(outdir.iterdir()):
        die(f"Conflict: output already exists and is not empty: {outdir}")

    if state.OPTS.dry_run:
        out(f"[dry-run] would create: {outdir}")
        return

    mp3s = _copy_audio_to_out(b.group_root, outdir)

    if wipe:
        wipe_id3(mp3s)

    mp3_first = mp3s[0] if mp3s else None
    cover = choose_cover(
        mp3_first=mp3_first,
        m4a_source=b.m4a_hint,
        bookdir=outdir,
        stage_root=b.stage_root,
        group_root=b.group_root,
    )
    cover_bytes = cover[0] if cover else None
    cover_mime = cover[1] if cover else None

    write_tags(mp3s, artist=author, album=title, cover=cover_bytes, cover_mime=cover_mime, track_start=1)


def run_import(cfg: dict) -> None:
    drop_root = get_drop_root(cfg)
    stage_root = get_stage_root(cfg)
    archive_root = get_archive_root(cfg)

    ensure_dir(drop_root)
    ensure_dir(stage_root)
    ensure_dir(archive_root)

    sources = _list_sources(drop_root)
    picked_sources = _choose_source(sources)

    for si, src in enumerate(picked_sources, 1):
        if slug(src.name) in load_ignore(drop_root):
            out(f"[source] {si}/{len(picked_sources)}: {src.name}")
            out("[source] skipped (ignored)")
            continue

        out(f"[source] {si}/{len(picked_sources)}: {src.name}")

        stage_run = stage_root / slug(src.stem)
        stage_src = stage_run / "src"
        _stage_source(src, stage_src)

        # Always convert m4a before book detection (so mp3s exist everywhere)
        convert_m4a_in_place(stage_src, recursive=True)

        books = _detect_books(stage_src)
        picked_books = _choose_books(books)

        publish, wipe = _preflight_global()  # decided before any output writes

        # preflight per-book metadata (must happen before touching output)
        meta: list[tuple[BookGroup, str, str]] = []
        for bi, b in enumerate(picked_books, 1):
            author, title = _preflight_book(bi, len(picked_books), b)
            meta.append((b, author, title))

        # processing phase (no prompts)
        for bi, (b, author, title) in enumerate(meta, 1):
            _process_book(bi, len(meta), b, archive_root, author, title, wipe)

        if publish:
            out("[publish] skipped (not implemented)")

