from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import audiomason.state as state
from audiomason.paths import get_drop_root, get_stage_root, get_output_root, get_archive_root, ARCHIVE_EXTS
from audiomason.util import out, die, ensure_dir, slug, prompt, prompt_yes_no
from audiomason.ignore import load_ignore, add_ignore
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place
from audiomason.rename import natural_sort, rename_sequential
from audiomason.covers import choose_cover
from audiomason.tags import wipe_id3, write_tags
from audiomason.manifest import update_manifest, load_manifest, source_fingerprint
_AUDIO_EXTS = {".mp3", ".m4a"}


@dataclass(frozen=True)
class BookGroup:
    label: str          # "__ROOT_AUDIO__" or folder name
    group_root: Path    # where to pull audio from (stage src root OR a subdir)
    stage_root: Path    # stage src root (for cover search)
    m4a_hint: Optional[Path]


def _list_sources(drop_root: Path) -> list[Path]:
    # Filter ignored sources here so they never appear in the prompt list.
    import unicodedata
    from audiomason.util import slug
    from audiomason.ignore import load_ignore

    def _norm(s: str) -> str:
        return unicodedata.normalize("NFKC", s).strip().casefold()

    ignore_raw = load_ignore(drop_root)
    ignore_norm = {_norm(k) for k in ignore_raw}
    ignore_norm |= {_norm(slug(k)) for k in ignore_raw}

    if not drop_root.exists():
        ensure_dir(drop_root)
        return []

    items: list[Path] = []
    for src in sorted(drop_root.iterdir(), key=lambda x: x.name.lower()):
        name = src.name
        if name.startswith("."):
            continue
        # never treat internal/work artifacts as sources
        if name in {"_am_stage", "import.log.jsonl", ".DS_Store"}:
            continue
        if name.startswith("_"):
            continue

        # allow only dirs + supported archives
        if src.is_file() and src.suffix.lower() not in ARCHIVE_EXTS:
            continue
        if not (src.is_dir() or (src.is_file() and src.suffix.lower() in ARCHIVE_EXTS)):
            continue

        candidates = {
            _norm(src.name),
            _norm(src.stem),
            _norm(slug(src.name)),
            _norm(slug(src.stem)),
        }
        if candidates & ignore_norm:
            continue

        items.append(src)

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


def _choose_books(books: list[BookGroup], default_ans: str = "1") -> list[BookGroup]:
    if len(books) == 1:
        return books
    out(f"[books] found {len(books)}:")
    for i, b in enumerate(books, 1):
        out(f"  {i}) {b.label}")
    ans = prompt("Choose book number, or 'a' for all", default_ans).strip().lower()
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


def _preflight_book(i: int, n: int, b: BookGroup, default_title: str = "") -> str:
    out(f"[book-meta] {i}/{n}: {b.label}")
    default_title = (default_title or (b.label if b.label != "__ROOT_AUDIO__" else "Untitled"))
    title = prompt(f"[book {i}/{n}] Book title", default_title).strip()
    if not title:
        die("Book title is required")
    return title

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


def _process_book(i: int, n: int, b: BookGroup, dest_root: Path, author: str, title: str, wipe: bool) -> None:
    out(f"[book] {i}/{n}: {b.label}")

    outdir = _output_dir(dest_root, author, title)
    if outdir.exists() and any(outdir.iterdir()):
        die(f"Conflict: output already exists and is not empty: {outdir}")

    if state.OPTS.dry_run:
        out(f"[dry-run] would create: {outdir}")
        return

    mp3s = _copy_audio_to_out(b.group_root, outdir)

    if wipe:
        wipe_id3(mp3s)

    mp3_first = mp3s[0] if mp3s else None
    out(f"[cover] request: {i}/{n}: {author} / {title}")
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
    output_root = get_output_root(cfg)

    ensure_dir(drop_root)
    ensure_dir(stage_root)
    ensure_dir(archive_root)
    ensure_dir(output_root)

    sources = _list_sources(drop_root)
    picked_sources = _choose_source(sources)

    for si, src in enumerate(picked_sources, 1):
        out(f"[source] {si}/{len(picked_sources)}: {src.name}")

        import unicodedata

        def _norm(s: str) -> str:
            return unicodedata.normalize("NFKC", s).strip().casefold()

        ignore_raw = load_ignore(drop_root)
        ignore_norm = {_norm(k) for k in ignore_raw}
        ignore_norm |= {_norm(slug(k)) for k in ignore_raw}

        candidates = {
            _norm(src.name),
            _norm(src.stem),
            _norm(slug(src.name)),
            _norm(slug(src.stem)),
        }

        if candidates & ignore_norm:
            out("[source] skipped (ignored)")
            continue

        stage_run = stage_root / slug(src.stem)
        stage_src = stage_run / "src"

        fp = source_fingerprint(src)
        update_manifest(stage_run, {"source": {"fingerprint": fp}})
        mf = load_manifest(stage_run)
        dec = mf.get("decisions", {})
        bm = mf.get("book_meta", {})

        reuse_possible = bool(stage_src.exists() and mf.get("source", {}).get("fingerprint") == fp)
        reuse_stage = False
        if reuse_possible:
            reuse_stage = prompt_yes_no("[stage] Reuse existing staged source?", default_no=False)

        use_manifest_answers = False
        if reuse_stage:
            out("[stage] reuse")
            use_manifest_answers = prompt_yes_no("[manifest] Use saved answers (skip prompts)?", default_no=False)
        else:
            if reuse_possible:
                out("[stage] delete")
                shutil.rmtree(stage_run, ignore_errors=True)
                # reset locals; we'll recreate stage + manifest below
                mf = {}
                dec = {}
                bm = {}

            ensure_dir(stage_run)
            update_manifest(stage_run, {
                "source": {
                    "name": src.name,
                    "stem": src.stem,
                    "is_dir": bool(src.is_dir()),
                    "is_file": bool(src.is_file()),
                    "path": str(src),
                    "fingerprint": fp,
                },
            })
            _stage_source(src, stage_src)

        # Always convert m4a before book detection (so mp3s exist everywhere)
        convert_m4a_in_place(stage_src, recursive=True)

        books = _detect_books(stage_src)

        # book selection (skip when allowed, otherwise prompt with defaults)
        picked_books: list[BookGroup] = []
        picked = mf.get("books", {}).get("picked") if isinstance(mf, dict) else None
        if reuse_stage and use_manifest_answers and isinstance(picked, list) and picked:
            by_label = {b.label: b for b in books}
            picked_books = [by_label[l] for l in picked if l in by_label]

        default_ans = "1"
        if (not picked_books) and isinstance(picked, list) and picked:
            if len(picked) == len(books):
                default_ans = "a"
            else:
                try:
                    first = picked[0]
                    idx = [b.label for b in books].index(first) + 1
                    default_ans = str(idx)
                except Exception:
                    default_ans = "1"

        if not picked_books:
            picked_books = _choose_books(books, default_ans=default_ans)

        update_manifest(stage_run, {
            "books": {
                "detected": [b.label for b in books],
                "picked": [b.label for b in picked_books],
            },
        })

        # publish/wipe (skip when allowed, otherwise prompt with defaults)
        default_publish = bool(dec.get("publish")) if isinstance(dec, dict) and "publish" in dec else False
        default_wipe = bool(dec.get("wipe_id3")) if isinstance(dec, dict) and "wipe_id3" in dec else False

        if reuse_stage and use_manifest_answers and isinstance(dec, dict) and ("publish" in dec) and ("wipe_id3" in dec):
            publish = bool(dec.get("publish"))
            wipe = bool(dec.get("wipe_id3"))
        else:
            # honor CLI overrides
            if state.OPTS.publish is None:
                publish = prompt_yes_no("Publish after import?", default_no=(not default_publish))
            else:
                publish = bool(state.OPTS.publish)
            if state.OPTS.wipe_id3 is None:
                wipe = prompt_yes_no("Full wipe ID3 tags before tagging?", default_no=(not default_wipe))
            else:
                wipe = bool(state.OPTS.wipe_id3)

        update_manifest(stage_run, {"decisions": {"publish": bool(publish), "wipe_id3": bool(wipe)}})
        dest_root = archive_root if publish else output_root

        # AUTHOR is per-source (not per-book)
        default_author = src.name if src.is_dir() else src.stem
        default_author2 = str(dec.get("author") or default_author) if isinstance(dec, dict) else default_author

        if reuse_stage and use_manifest_answers and isinstance(dec, dict) and str(dec.get("author") or "").strip():
            author = str(dec.get("author") or "").strip()
        else:
            author = prompt("[source] Author", default_author2).strip()
        if not author:
            die("Author is required")
        update_manifest(stage_run, {"decisions": {"author": author}})

        # preflight per-book metadata (must happen before touching output)
        meta: list[tuple[BookGroup, str]] = []
        for bi, b in enumerate(picked_books, 1):
            default_title = str(bm.get(b.label, {}).get("title") or "").strip() if isinstance(bm, dict) else ""
            if reuse_stage and use_manifest_answers and default_title:
                title = default_title
            else:
                title = _preflight_book(bi, len(picked_books), b, default_title=default_title)
            meta.append((b, title))
            update_manifest(stage_run, {"book_meta": {b.label: {"title": title}}})
        # processing phase (no prompts)
        for bi, (b, title) in enumerate(meta, 1):
            _process_book(bi, len(meta), b, dest_root, author, title, wipe)

        if publish:
            out("[publish] skipped (not implemented)")

