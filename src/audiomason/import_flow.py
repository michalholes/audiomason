from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import subprocess
import shutil

import audiomason.state as state
from audiomason.paths import (
    get_drop_root,
    get_stage_root,
    get_output_root,
    get_archive_root,
    ARCHIVE_EXTS,
)
from audiomason.util import (
    out,
    ensure_dir,
    slug,
    prompt,
    prompt_yes_no,
)
from audiomason.ignore import load_ignore, add_ignore
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place
from audiomason.rename import natural_sort, rename_sequential
from audiomason.tags import write_tags, wipe_id3
from audiomason.covers import choose_cover

AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".m4b"}


def _human_book_title(name: str) -> str:
    return name.replace("_", " ").strip()


def _cover_mime_from_ext(ext: str) -> str:
    e = ext.lower().lstrip('.')
    if e in {'jpg', 'jpeg'}:
        return 'image/jpeg'
    if e == 'png':
        return 'image/png'
    return 'application/octet-stream'


def _first_m4a(p: Path, recursive: bool) -> Path | None:
    it = (p.rglob('*.m4a') if recursive else p.glob('*.m4a'))
    for x in it:
        if x.is_file():
            return x
    return None


def _guess_author_book(stem: str) -> tuple[str, str]:
    s = stem.replace("_", " ").strip()
    if " - " in s:
        a, b = s.split(" - ", 1)
        return a.strip(), b.strip()
    if "." in s:
        parts = [x.strip() for x in s.split(".") if x.strip()]
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
    return s, s


def _copy_dir_into(src: Path, dst: Path) -> None:
    ensure_dir(dst)
    for item in src.iterdir():
        if item.name.startswith("."):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _list_sources(inbox: Path, cfg) -> list[Path]:
    ensure_dir(inbox)
    ignore = load_ignore(inbox)
    stage_root = get_stage_root(cfg).resolve()
    return sorted(
        (
            p for p in inbox.iterdir()
            if not p.name.startswith(".")
            and slug(p.stem if p.is_file() else p.name) not in ignore
            and p.resolve() != stage_root
            and (
                p.is_dir()
                or p.suffix.lower() in ARCHIVE_EXTS
                or p.suffix.lower() in AUDIO_EXTS
            )
        ),
        key=lambda p: p.name.lower(),
    )


def _normalize_single_root(stage: Path) -> Path:
    try:
        vis = [p for p in stage.iterdir() if not p.name.startswith(".")]
        if len(vis) == 1 and vis[0].is_dir():
            return vis[0]
    except Exception:
        pass
    return stage


def _has_audio_anywhere(p: Path) -> bool:
    return any(x.suffix.lower() in AUDIO_EXTS for x in p.rglob("*") if x.is_file())


def _has_audio_here(p: Path) -> bool:
    return any(x.is_file() and x.suffix.lower() in AUDIO_EXTS for x in p.iterdir())


def _book_candidates(stage: Path) -> list[Path]:
    """
    Candidate "book roots" inside stage:
      - stage itself IF it contains audio files directly (root-level m4a/mp3)
      - each immediate subdir that contains any audio recursively
    """
    cands: list[Path] = []
    if _has_audio_here(stage):
        cands.append(stage)

    subs = sorted(
        [d for d in stage.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda x: x.name.lower(),
    )
    for d in subs:
        if _has_audio_anywhere(d):
            cands.append(d)

    seen: set[Path] = set()
    outc: list[Path] = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            outc.append(c)
    return outc


def run_import(cfg) -> None:
    state.CFG = cfg
    DROP_ROOT = get_drop_root(cfg)
    STAGE_ROOT = get_stage_root(cfg)
    OUTPUT_ROOT = get_output_root(cfg)
    ARCHIVE_ROOT = get_archive_root(cfg)

    if state.OPTS is None:
        raise SystemExit(2)

    inbox = DROP_ROOT
    ignore = load_ignore(inbox)

    sources = _list_sources(inbox, cfg)
    if not sources:
        out("[inbox] empty")
        return

    out("[inbox] sources:")
    for i, p in enumerate(sources, 1):
        out(f"  {i}) {p.name}")

    ans = prompt("Choose source number, or 'a' for all", "1").strip().lower()
    if ans in {"a", "all"}:
        chosen_sources = sources
    else:
        try:
            chosen_sources = [sources[int(ans) - 1]]
        except Exception:
            chosen_sources = [sources[0]]

    # ---- ID3 WIPE (ONCE PER RUN, NUMERIC, DEFAULT NO) ----
    if state.OPTS.wipe_id3 is None:
        if state.OPTS.yes:
            state.OPTS.wipe_id3 = False
        else:
            out("[id3] full wipe before tagging?")
            out("  1) No")
            out("  2) Yes")
            state.OPTS.wipe_id3 = (prompt("Choose", "1").strip() == "2")

    for sidx, src in enumerate(chosen_sources, 1):
        out(f"[source] {sidx}/{len(chosen_sources)}: {src.name}")

        stage = STAGE_ROOT / slug(src.stem if src.is_file() else src.name)
        ensure_dir(stage)

        # if stage already has something -> do NOT unpack/copy again
        if not any(stage.iterdir()):
            if src.is_dir():
                _copy_dir_into(src, stage)
            elif src.suffix.lower() in ARCHIVE_EXTS:
                unpack(src, stage)
            elif src.suffix.lower() in AUDIO_EXTS:
                shutil.copy2(src, stage / src.name)

        stage = _normalize_single_root(stage)

        if not _has_audio_anywhere(stage):
            out("[skip] no audio found")
            continue

        books = _book_candidates(stage)
        if not books:
            out("[skip] no book candidates")
            continue

        picked: list[Path] = books
        if len(books) > 1 and not state.OPTS.yes:
            out(f"[books] found {len(books)} in {src.name}:")
            for i, b in enumerate(books, 1):
                label = "__ROOT_AUDIO__" if b == stage else b.name
                out(f"  {i}) {label}")
            bsel = prompt("Choose book number, or 'a' for all", "a").strip().lower()
            if bsel in {"a", "all"}:
                picked = books
            else:
                try:
                    bi = int(bsel)
                    picked = [books[bi - 1]] if 1 <= bi <= len(books) else [books[0]]
                except Exception:
                    picked = [books[0]]

        meta_by_label: dict[str, tuple[str, str]] = {}
        cover_by_label: dict[str, tuple[bytes | None, str | None]] = {}
        if len(picked) > 1 and not state.OPTS.yes:
            # Ask ALL metadata upfront (author once, then book per folder) BEFORE doing any work
            guess_a, _ = _guess_author_book(src.stem)
            out(f"[meta] preflight: {src.name}")
            author_all = prompt(f"Author [{guess_a}]", guess_a).strip() or guess_a

            for br in picked:
                lbl = "__ROOT_AUDIO__" if br == stage else br.name
                _, guess_b = _guess_author_book(src.stem if lbl == "__ROOT_AUDIO__" else lbl)
                out(f"[meta] {src.name} -> {lbl}")
                book_name = prompt(f"Book [{guess_b}]", _human_book_title(guess_b)).strip() or _human_book_title(guess_b)
                meta_by_label[lbl] = (author_all, book_name)


        if len(picked) > 1 and not state.OPTS.yes:
            out(f"[cover] preflight: {src.name}")
            for br in picked:
                lbl = "__ROOT_AUDIO__" if br == stage else br.name
                out(f"[cover] {src.name} -> {lbl}")
                m4a = _first_m4a(br, recursive=(br != stage))
                got = choose_cover(
                    mp3_first=None,
                    m4a_source=m4a,
                    bookdir=br,
                    stage_root=stage,
                    group_root=br,
                )
                if got:
                    cb, ext = got
                    cover_by_label[lbl] = (cb, _cover_mime_from_ext(ext))
                else:
                    cover_by_label[lbl] = (None, None)

        # Publish preflight: ask ONCE right before processing files
        publish_choice = None
        if not state.OPTS.yes:
            out('[publish] preflight')
            publish_choice = prompt('Publish after processing? [y/N]', 'n').strip().lower() in {'y','yes'}

        for bidx, book_root in enumerate(picked, 1):
            label = "__ROOT_AUDIO__" if book_root == stage else book_root.name
            out(f"[book] {bidx}/{len(picked)}: {src.name} -> {label}")

            if meta_by_label:
                author, book = meta_by_label[label]
            else:
                guess_a, guess_b = _guess_author_book(src.stem if label == "__ROOT_AUDIO__" else label)
                out(f"[meta] {src.name} -> {label}")
                author = prompt(f"Author [{guess_a}]", guess_a).strip() or guess_a
                book = prompt(f"Book [{guess_b}]", _human_book_title(guess_b)).strip() or _human_book_title(guess_b)

            cover = None
            cover_mime = None
            if cover_by_label:
                cover, cover_mime = cover_by_label.get(label, (None, None))
            else:
                m4a = _first_m4a(book_root, recursive=(book_root != stage))
                got = choose_cover(
                    mp3_first=None,
                    m4a_source=m4a,
                    bookdir=book_root,
                    stage_root=stage,
                    group_root=book_root,
                )
                if got:
                    cb, ext = got
                    cover, cover_mime = (cb, _cover_mime_from_ext(ext))

            convert_m4a_in_place(book_root, recursive=(book_root != stage))

            # IMPORTANT: for __ROOT_AUDIO__ only take files in stage root, not recursively
            if book_root == stage:
                mp3s = natural_sort(list(book_root.glob("*.mp3")))
            else:
                mp3s = natural_sort(list(book_root.rglob("*.mp3")))
            if not mp3s:
                out("[skip] no mp3")
                continue

            mp3dir = mp3s[0].parent
            mp3s = rename_sequential(mp3dir, mp3s)

            if state.OPTS.wipe_id3 and not state.OPTS.dry_run:
                wipe_id3(mp3s)

            try:
                write_tags(mp3s, artist=author, album=book, cover=cover, cover_mime=cover_mime)
            except TypeError:
                write_tags(mp3s, artist=author, album=book)

            if publish_choice is None:
                publish = prompt_yes_no(f"Publish to archive ({ARCHIVE_ROOT})?", default_no=False)
            else:
                publish = bool(publish_choice)
            target = ARCHIVE_ROOT if publish else OUTPUT_ROOT
            outdir = target / author / book
            ensure_dir(outdir)

            for mp3 in mp3s:
                shutil.move(str(mp3), str(outdir / mp3.name))

            out(f"[done] {author} / {book} -> {outdir}")

        add_ignore(inbox, src.name)
