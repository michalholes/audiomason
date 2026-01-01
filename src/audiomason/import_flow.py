from __future__ import annotations
from audiomason.openlibrary import validate_author, validate_book
from audiomason.naming import normalize_name, normalize_sentence

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
from audiomason.covers import choose_cover, find_file_cover, extract_embedded_cover_from_mp3
from audiomason.tags import wipe_id3, write_tags
from audiomason.manifest import update_manifest, load_manifest, source_fingerprint
_AUDIO_EXTS = {".mp3", ".m4a"}


@dataclass(frozen=True)
class BookGroup:
    label: str          # "__ROOT_AUDIO__" or folder name
    group_root: Path    # where to pull audio from (stage src root OR a subdir)
    stage_root: Path    # stage src root (for cover search)
    m4a_hint: Optional[Path]


def _ol_offer_top(kind: str, entered: str, res) -> str:
    top = getattr(res, "top", None)
    if isinstance(top, str):
        top = top.strip()
    if not top:
        return entered
    e = (entered or "").strip()
    if top.casefold() == e.casefold():
        return entered
    from audiomason.util import out, prompt_yes_no
    out(f"[ol] {kind} suggestion: '{e}' -> '{top}'")
    if prompt_yes_no(f"Use suggested {kind} '{top}'?", default_no=True):
        return top
    return entered

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
    nt = normalize_sentence(title)
    if nt != title:
        out(f"[name] book suggestion: '{title}' -> '{nt}'")
        if prompt_yes_no("Apply suggested book title?", default_no=True):
            title = nt

    if not title:
        die("Book title is required")
    return title

def _is_dir_nonempty(p: Path) -> bool:
    return p.exists() and p.is_dir() and any(p.iterdir())

def _next_available_title(author_dir: Path, title: str) -> str:
    # Deterministic: Title, Title (2), Title (3), ...
    if not author_dir.exists():
        return title
    if not _is_dir_nonempty(author_dir / title) and not (author_dir / title).exists():
        return title
    n = 2
    while True:
        cand = f"{title} ({n})"
        if not (author_dir / cand).exists() and not _is_dir_nonempty(author_dir / cand):
            return cand
        n += 1

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


def _write_dry_run_summary(stage_run: Path, author: str, title: str, lines: list[str]) -> None:
    name = f"{author} - {title}.dryrun.txt"
    path = stage_run / name
    header = [
        "AudioMason dry-run summary",
        "",
    ]
    path.write_text("\n".join(header + lines) + "\n", encoding="utf-8")

def _process_book(i: int, n: int, b: BookGroup, stage_run: Path, dest_root: Path, author: str, title: str, out_title: str, wipe: bool, cover_mode: str, overwrite: bool, cfg: dict) -> None:
    out(f"[book] {i}/{n}: {b.label}")

    outdir = _output_dir(dest_root, author, out_title)
    if _is_dir_nonempty(outdir):
        if overwrite:
            if state.OPTS and state.OPTS.dry_run:
                out(f"[dest] would overwrite: {outdir}")
            else:
                out(f"[dest] overwrite: {outdir}")
            if not (state.OPTS and state.OPTS.dry_run):
                shutil.rmtree(outdir, ignore_errors=True)
        else:
            die(f"Conflict: output already exists and is not empty: {outdir}")

    if state.OPTS.dry_run:
        out(f"[dry-run] would create: {outdir}")
        # ISSUE #2: write human-readable dry-run summary file (per book)
        lines = [
            "AudioMason dry-run summary",
            f"Author: {author}",
            f"Title: {out_title}",
            f"Destination root: {dest_root}",
            f"Destination dir: {outdir}",
            f"Overwrite: {bool(overwrite)}",
            f"Cover mode: {cover_mode}",
            f"Wipe ID3: {bool(wipe)}",
        ]
        _write_dry_run_summary(stage_run, author, out_title, lines)
        out(f"[dry-run] wrote: {stage_run / (author + ' - ' + out_title + '.dryrun.txt')}")
        return

    mp3s = _copy_audio_to_out(b.group_root, outdir)

    if wipe:
        wipe_id3(mp3s)

    mp3_first = mp3s[0] if mp3s else None
    out(f"[cover] request: {i}/{n}: {author} / {title}")
    cover = choose_cover(
        cfg=cfg,
        mp3_first=mp3_first,
        m4a_source=b.m4a_hint,
        bookdir=outdir,
        stage_root=b.stage_root,
        group_root=b.group_root,
        mode=cover_mode,
    )
    cover_bytes = cover[0] if cover else None
    cover_mime = cover[1] if cover else None

    write_tags(mp3s, artist=author, album=title, cover=cover_bytes, cover_mime=cover_mime, track_start=1)

def _resolve_source_arg(drop_root: Path, src_path: Path) -> Path:
    p = src_path
    if not p.is_absolute():
        p = drop_root / p
    p = p.expanduser().resolve()
    dr = drop_root.expanduser().resolve()

    if p == dr:
        return p

    if not p.exists():
        die(f"Source path not found: {p}")

    # must be under DROP_ROOT
    if not p.is_relative_to(dr):
        die(f"Source path must be under DROP_ROOT: {dr}")

    name = p.name
    if name.startswith(".") or name.startswith("_") or name in {"_am_stage", "import.log.jsonl", ".DS_Store"}:
        die(f"Invalid source path: {p}")

    # allow only dirs + supported archives
    if p.is_file() and p.suffix.lower() not in ARCHIVE_EXTS:
        die(f"Unsupported source: {p}")
    if not (p.is_dir() or (p.is_file() and p.suffix.lower() in ARCHIVE_EXTS)):
        die(f"Unsupported source: {p}")

    return p

def run_import(cfg: dict, src_path: Optional[Path] = None) -> None:
    drop_root = get_drop_root(cfg)
    stage_root = get_stage_root(cfg)
    archive_root = get_archive_root(cfg)
    output_root = get_output_root(cfg)

    ensure_dir(drop_root)
    ensure_dir(stage_root)
    ensure_dir(archive_root)
    ensure_dir(output_root)
    picked_sources: list[Path]
    forced = False
    if src_path is not None:
        sp = _resolve_source_arg(drop_root, src_path)
        if sp.expanduser().resolve() == drop_root.expanduser().resolve():
            sources = _list_sources(drop_root)
            picked_sources = _choose_source(sources)
            forced = False
        else:
            picked_sources = [sp]
            forced = True
    else:
        sources = _list_sources(drop_root)
        picked_sources = _choose_source(sources)
        forced = False

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

        if (not forced) and (candidates & ignore_norm):
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
        # FEATURE #26: stage cleanup decision (manifest-backed)
        default_clean = bool(dec.get("clean_stage")) if isinstance(dec, dict) and ("clean_stage" in dec) else False
        if reuse_stage and use_manifest_answers and isinstance(dec, dict) and ("clean_stage" in dec):
            clean_stage = bool(dec.get("clean_stage"))
        else:
            clean_stage = prompt_yes_no("Clean stage after successful import?", default_no=(not default_clean))
        update_manifest(stage_run, {"decisions": {"clean_stage": bool(clean_stage)}})
        dest_root = archive_root if publish else output_root

        # AUTHOR is per-source (not per-book)
        default_author = src.name if src.is_dir() else src.stem
        default_author2 = str(dec.get("author") or default_author) if isinstance(dec, dict) else default_author

        if reuse_stage and use_manifest_answers and isinstance(dec, dict) and str(dec.get("author") or "").strip():
            author = str(dec.get("author") or "").strip()
        else:
            author = prompt("[source] Author", default_author2).strip()
            na = normalize_name(author)
            if na != author:
                out(f"[name] author suggestion: '{author}' -> '{na}'")
                if prompt_yes_no("Apply suggested author name?", default_no=True):
                    author = na

            # OpenLibrary suggestion (author) — must run after final author decision
            if getattr(getattr(state, 'OPTS', None), 'lookup', False):
                if getattr(state, "DEBUG", False):
                    out(f"[ol] validate author: '{author}'")
                ar = validate_author(author)
                if (not getattr(ar, 'ok', False)) and (not getattr(ar, 'top', None)):
                    out(f"[ol] author not found: '{author}'")
                if getattr(state, "DEBUG", False):
                    out(f"[ol] author result: ok={getattr(ar,'ok',None)} status={getattr(ar,'status',None)!r} hits={getattr(ar,'hits',None)} top={getattr(ar,'top',None)!r}")
                author = _ol_offer_top('author', author, ar)
        if not author:
            die("Author is required")
        update_manifest(stage_run, {"decisions": {"author": author}})

        # preflight per-book metadata (must happen before touching output)
        # ISSUE #12: unify decisions upfront (title + cover choice). Processing must not prompt.
        meta: list[tuple[BookGroup, str, str, Path, str, bool]] = []
        for bi, b in enumerate(picked_books, 1):
            # title
            bm_entry2 = (bm.get(b.label, {}) if isinstance(bm, dict) else {})
            default_title = str((bm_entry2.get("out_title") or bm_entry2.get("title") or "")).strip()

            if reuse_stage and use_manifest_answers and default_title:
                title = default_title
            else:
                title = _preflight_book(bi, len(picked_books), b, default_title=default_title)

                # OpenLibrary suggestion (book title)
                if getattr(getattr(state, 'OPTS', None), 'lookup', False):
                    if getattr(state, "DEBUG", False):
                        out(f"[ol] validate book: author='{author}' title='{title}'")
                    br = validate_book(author, title)
                    if (not getattr(br, 'ok', False)) and (not getattr(br, 'top', None)):
                        out(f"[ol] book not found: author='{author}' title='{title}'")
                    if getattr(state, "DEBUG", False):
                        out(f"[ol] book result: ok={getattr(br,'ok',None)} status={getattr(br,'status',None)!r} hits={getattr(br,'hits',None)} top={getattr(br,'top',None)!r}")
                    title = _ol_offer_top('book title', title, br)
            # cover decision (stored as mode: 'file'|'embedded'|'skip')
            default_cover_mode = str(bm.get(b.label, {}).get("cover_mode") or "").strip() if isinstance(bm, dict) else ""
            mp3s = _collect_audio_files(b.group_root)
            mp3_first = mp3s[0] if mp3s else None
            file_cover = find_file_cover(b.stage_root, b.group_root)
            embedded = extract_embedded_cover_from_mp3(mp3_first) if mp3_first else None

            cover_mode = ""
            if reuse_stage and use_manifest_answers and default_cover_mode:
                cover_mode = default_cover_mode
            else:
                # deterministic default (no prompt) unless both options exist and user is interactive
                if file_cover:
                    cover_mode = "file"
                elif embedded:
                    cover_mode = "embedded"
                else:
                    cover_mode = "skip"

                if file_cover and embedded and not (state.OPTS and state.OPTS.yes):
                    # prompt with defaults from manifest if present
                    d = "2"
                    if default_cover_mode == "embedded":
                        d = "1"
                    elif default_cover_mode == "skip":
                        d = "s"
                    out(f"[cover-meta] {bi}/{len(picked_books)}: {author} / {title}")
                    out("Cover options:")
                    out("  1) embedded cover from audio")
                    out(f"  2) {file_cover.name} (preferred)")
                    out("  s) skip cover")
                    ans = prompt("Choose cover [1/2/s]", d).strip().lower()
                    if ans == "1":
                        cover_mode = "embedded"
                    elif ans == "s":
                        cover_mode = "skip"
                    else:
                        cover_mode = "file"

            # ISSUE #1: destination conflict handling (prompt overwrite, else fallback to abooks_ready, else offer new folder)
            bm_entry = (bm.get(b.label, {}) if isinstance(bm, dict) else {})
            if reuse_stage and use_manifest_answers:
                m_overwrite = bool(bm_entry.get("overwrite") is True)
                m_dest_kind = str(bm_entry.get("dest_kind") or "")
                m_out_title = str(bm_entry.get("out_title") or "").strip()
            else:
                m_overwrite = False
                m_dest_kind = ""
                m_out_title = ""

            dest_root2 = dest_root
            if m_dest_kind == "output":
                dest_root2 = output_root
            elif m_dest_kind == "archive":
                dest_root2 = archive_root

            out_title = m_out_title or title
            overwrite = m_overwrite

            # compute candidate outdir
            outdir = _output_dir(dest_root2, author, out_title)
            if _is_dir_nonempty(outdir) and not (reuse_stage and use_manifest_answers):
                # conflict: 1) offer overwrite
                if not (state.OPTS and state.OPTS.yes):
                    out(f"[dest] exists: {outdir}")
                    overwrite = prompt_yes_no("Destination exists. Overwrite?", default_no=True)
                else:
                    overwrite = False

                if not overwrite:
                    # 2) fallback to abooks_ready if we are not already there
                    if dest_root2 != output_root:
                        dest_root2 = output_root
                        outdir = _output_dir(dest_root2, author, out_title)

                    # 3) if still conflict, offer new folder (interactive), else deterministic next available title
                    if _is_dir_nonempty(outdir):
                        if not (state.OPTS and state.OPTS.yes):
                            out(f"[dest] exists in abooks_ready: {outdir}")
                            mk_new = prompt_yes_no("Create new destination folder?", default_no=False)
                            if mk_new:
                                author_dir = _output_dir(dest_root2, author, "").parent
                                out_title = _next_available_title(author_dir, title)
                        else:
                            # non-interactive: deterministic new folder name
                            author_dir = _output_dir(dest_root2, author, "").parent
                            out_title = _next_available_title(author_dir, title)

            # persist
            dest_kind = "archive" if dest_root2 == archive_root else "output"
            meta.append((b, title, cover_mode, dest_root2, out_title, overwrite))
            update_manifest(stage_run, {"book_meta": {b.label: {"title": title, "cover_mode": cover_mode, "dest_kind": dest_kind, "out_title": out_title, "overwrite": bool(overwrite)}}})

        # processing phase (no prompts)
        for bi, (b, title, cover_mode, dest_root2, out_title, overwrite) in enumerate(meta, 1):
            _process_book(bi, len(meta), b, stage_run, dest_root2, author, title, out_title, wipe, cover_mode, overwrite)

        # FEATURE #26: clean stage at end (successful run only)

