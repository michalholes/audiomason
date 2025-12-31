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
    find_archive_match,
    out,
    ensure_dir,
    slug,
    prompt,
    prompt_yes_no,
    prune_empty_dirs,
)
from audiomason.ignore import load_ignore, add_ignore
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place
from audiomason.rename import natural_sort, rename_sequential
from audiomason.covers import choose_cover
from audiomason.tags import write_tags


def _copy_dir_into(src: Path, dst: Path) -> None:
    ensure_dir(dst)
    # copy contents of src into dst (dst already exists)
    for item in src.iterdir():
        if item.name.startswith("."):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)

@dataclass(frozen=True)
class PeekResult:
    has_single_root: bool
    top_level_name: str | None


def peek_source(src: Path) -> PeekResult:
    if src.is_dir():
        try:
            items = [p for p in src.iterdir() if not p.name.startswith(".")]
        except Exception:
            return PeekResult(False, None)
        if len(items) == 1 and items[0].is_dir():
            return PeekResult(True, items[0].name)
        return PeekResult(False, None)

def list_archive_books(archive: Path, root: str) -> list[str]:
    # Return sorted immediate subdirectories under the single-root folder in the archive
    try:
        p = subprocess.run(
            ["7z", "l", "-slt", str(archive)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
    except Exception:
        return []

    subs: set[str] = set()
    rootp = root.replace("\\", "/").strip("/")

    for line in p.stdout.splitlines():
        if not line.startswith("Path = "):
            continue
        path = line.split("=", 1)[1].strip().replace("\\", "/").strip("/")
        if not path:
            continue
        if not path.startswith(rootp + "/"):
            continue
        rest = path[len(rootp) + 1 :]
        parts = [x for x in rest.split("/") if x]
        if len(parts) >= 1:
            subs.add(parts[0])

    return sorted(subs, key=lambda s: s.lower())


    # archive
    try:
        p = subprocess.run(
            ["7z", "l", "-slt", str(src)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
    except Exception:
        return PeekResult(False, None)

    roots: set[str] = set()
    for line in p.stdout.splitlines():
        if line.startswith("Path = "):
            path = line.split("=", 1)[1].strip().replace("\\", "/")
            if "/" in path:
                roots.add(path.split("/", 1)[0])

    if len(roots) == 1:
        return PeekResult(True, next(iter(roots)))
    return PeekResult(False, None)


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
                or (p.is_file() and p.suffix.lower() in ARCHIVE_EXTS)
            )
        ),
        key=lambda p: p.name.lower(),
    )


def _human_book_title(name: str) -> str:
    return name.replace('_', ' ').strip()


def _guess_author_book(stem: str) -> tuple[str, str]:
    # Heuristics: "Author - Book", "Author.Book", "Author_Book"
    s = stem.replace("_", " ").strip()
    if " - " in s:
        a, b = s.split(" - ", 1)
        return a.strip(), b.strip()
    if "." in s:
        parts = [x.strip() for x in s.split(".") if x.strip()]
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
    return s, s


def _pick_sources_interactive(sources: list[Path]) -> list[Path]:
    if not sources:
        return []
    out("[inbox] sources:")
    for i, p in enumerate(sources, 1):
        out(f"  {i}) {p.name}")

    ans = prompt("Choose source number, or 'a' for all", "1").strip().lower()
    if ans in {"a", "all"}:
        return sources

    try:
        idx = int(ans)
        if 1 <= idx <= len(sources):
            return [sources[idx - 1]]
    except ValueError:
        pass

    out("[pick] invalid choice -> using 1")
    return [sources[0]]


def _pick_books_interactive(author_dir: Path, book_dirs: list[Path]) -> list[Path]:
    out(f"[books] found {len(book_dirs)} in {author_dir.name}:")
    for i, b in enumerate(book_dirs, 1):
        out(f"  {i}) {b.name}")

    ans = prompt("Choose book number, or 'a' for all", "a").strip().lower()
    if ans in {"a", "all"}:
        return book_dirs

    try:
        idx = int(ans)
        if 1 <= idx <= len(book_dirs):
            return [book_dirs[idx - 1]]
    except ValueError:
        pass

    out("[pick] invalid choice -> using all")
    return book_dirs


def _decide_publish(archive_root: Path) -> bool:
    # state.OPTS.publish: True/False/None(ask)
    if state.OPTS is None:
        return False
    if state.OPTS.publish is True:
        return True
    if state.OPTS.publish is False:
        return False
    # ask
    return prompt_yes_no(f"Publish to archive ({archive_root})?", default_no=False)


def run_import(cfg) -> None:
    state.CFG = cfg
    archive_root = get_archive_root(cfg)
    if state.OPTS is None:
        raise SystemExit(2)

    DROP_ROOT = get_drop_root(cfg)
    STAGE_ROOT = get_stage_root(cfg)
    OUTPUT_ROOT = get_output_root(cfg)
    try:
        if state.OPTS is None:
            raise SystemExit(2)

        inbox = DROP_ROOT
        ignore = load_ignore(inbox)

        sources = _list_sources(inbox, cfg)
        if not sources:
            out("[inbox] empty (no .rar/.zip/.7z)")
            return

        try:
            chosen = _pick_sources_interactive(sources)
        except KeyboardInterrupt:
            out("[abort]")
            return

        # If an author directory contains multiple book subdirectories, ask whether to process all or one.
        expanded: list[Path] = []
        chosen_labels: list[str] = []
        archive_book_choice: dict[Path, str] = {}
        for src0 in chosen:
            if src0.is_dir():
                subs = sorted(
                    [
                        d for d in src0.iterdir()
                        if d.is_dir()
                        and not d.name.startswith(".")
                        and slug(d.name) not in load_ignore(src0)
                    ],
                    key=lambda x: x.name.lower(),
                )
                if len(subs) > 1:
                    picked = _pick_books_interactive(src0, subs)
                    for b in picked:
                        expanded.append(b)
                        chosen_labels.append(f"{src0.name} / {b.name}")
                    continue
            if src0.is_file() and src0.suffix.lower() in ARCHIVE_EXTS:
                pk = peek_source(src0) or PeekResult(False, None)
                if pk.has_single_root and pk.top_level_name:
                    books = list_archive_books(src0, pk.top_level_name)
                    if len(books) > 1:
                        out(f"[books] found {len(books)} in {src0.name}:")
                        for i, b in enumerate(books, 1):
                            out(f"  {i}) {b}")
                        ans = prompt("Choose book number", "1").strip()
                        try:
                            bi = int(ans)
                            if 1 <= bi <= len(books):
                                archive_book_choice[src0] = books[bi - 1]
                                expanded.append(src0)
                                chosen_labels.append(f"{src0.name} / {books[bi - 1]}")
                                continue
                        except ValueError:
                            pass
                        archive_book_choice[src0] = books[0]
                        expanded.append(src0)
                        chosen_labels.append(f"{src0.name} / {books[0]}")
                        continue
            expanded.append(src0)
            chosen_labels.append(src0.name)

        chosen = expanded

        # Batch preflight: ask everything BEFORE any work starts
        meta_by_src: dict[Path, tuple[str, str]] = {}
        publish_override: bool | None = None
        cover_mode = "ask"  # embedded/file/ask

        if len(chosen) > 1:
            # If all chosen are book dirs under one author dir, ask author once
            parents = {
                src.parent
                for src in chosen
                if src.is_dir()
                and src.parent != DROP_ROOT
                and src.parent.is_dir()
                and src.parent.parent == DROP_ROOT
            }
            author_all: str | None = None
            if len(parents) == 1 and len(chosen) == len(parents) * len(chosen):
                author_all = next(iter(parents)).name

            if author_all is not None:
                author_all = prompt("Author (all books)", author_all.replace(".", " ")).strip() or author_all.replace(".", " ")

            # Ask book titles for all upfront
            for src in chosen:
                peek = peek_source(src) or PeekResult(False, None)
                if src.is_dir() and src.parent != DROP_ROOT and src.parent.is_dir() and src.parent.parent == DROP_ROOT:
                    g_a, g_b = (author_all or src.parent.name), _human_book_title(src.name)
                else:
                    name_for_guess = (
                        peek.top_level_name
                        if peek.has_single_root and peek.top_level_name
                        else (src.stem if src.is_file() else src.name)
                    )
                    g_a, g_b = _guess_author_book(name_for_guess)
                    g_b = _human_book_title(g_b)

                a = author_all or (prompt(f"Author for {src.name}", g_a.replace(".", " ")).strip() or g_a.replace(".", " "))
                b = prompt(f"Book for {src.name}", _human_book_title(g_b)).strip() or _human_book_title(g_b)
                meta_by_src[src] = (a, b)

            # Cover policy (numeric)
            out("[covers] choose policy for all books:")
            out("  1) Embedded cover (from audio files)")
            out("  2) Cover file in folder (cover.jpg/png/etc)")
            out("  3) Ask per book (current behavior)")
            c = prompt("Choose cover policy", "3").strip()
            cover_mode = {"1": "embedded", "2": "file", "3": "ask"}.get(c, "ask")

            # Publish policy (once)
            publish_override = _decide_publish(archive_root)

        for idx, src in enumerate(chosen, 1):

            # Unified source key (archive and directory behave the same)
            peek = peek_source(src) or PeekResult(False, None)
            source_key = (
                peek.top_level_name
                if peek.has_single_root and peek.top_level_name
                else (
                    f"{src.parent.name}-{src.name}"
                    if src.is_dir() and src.parent != DROP_ROOT and src.parent.is_dir()
                    else (src.stem if src.is_file() else src.name)
                )
            )
            key = source_key
            if slug(key) in ignore:
                out(f"[skip] ignored: {src.name}")
                continue

            out(f"[book] {idx}/{len(chosen)}: {chosen_labels[idx-1]}")
            out(f"[import] {src.name}")

            # Ask author/book (defaults guessed from source shape)
            peek = peek_source(src) or PeekResult(False, None)

            # If we are importing a book directory under an author dir: Author = parent, Book = dir name
            if src.is_dir() and src.parent != DROP_ROOT and src.parent.is_dir() and src.parent.parent == DROP_ROOT:
                guess_a, guess_b = src.parent.name, src.name
            else:
                name_for_guess = (
                    peek.top_level_name
                    if peek.has_single_root and peek.top_level_name
                    else key
                )
                guess_a, guess_b = _guess_author_book(name_for_guess)

            # archive-first defaults: try to match an existing book in archive_ro before prompting
            archive_ro = cfg.get("paths", {}).get("archive_ro", "")
            am_a, am_b = find_archive_match(archive_ro, guess_a, guess_b)
            if am_a and am_b:
                guess_a, guess_b = am_a, am_b

            if src in meta_by_src:
                author, book = meta_by_src[src]
            else:
                author = prompt("Author", guess_a.replace('.', ' ')).strip() or guess_a.replace('.', ' ')
                book = prompt("Book", _human_book_title(guess_b)).strip() or _human_book_title(guess_b)

            book_key = f"{slug(author)}.{slug(book)}"
            stage = STAGE_ROOT / slug(source_key)
            ensure_dir(stage)

            # ignore whole source (author folder) after success
            source_root = src
            if (
                src.is_dir()
                and src.parent != DROP_ROOT
                and src.parent.is_dir()
                and src.parent.parent == DROP_ROOT
            ):
                source_root = src.parent

            try:
                if src.is_dir():
                    _copy_dir_into(src, stage)
                else:
                    unpack(src, stage)
            except Exception as e:
                out(f"[error] unpack failed: {e}")
                continue

            convert_m4a_in_place(stage)

            work_stage = stage
            if src.is_file() and src in archive_book_choice:
                pk = peek_source(src)
                if pk.has_single_root and pk.top_level_name:
                    work_stage = stage / pk.top_level_name / archive_book_choice[src]

            mp3s = natural_sort(list(work_stage.rglob("*.mp3")))
            if not mp3s:
                out("[skip] no mp3 found after unpack/convert")
                continue

            # Rename sequential in the mp3 folder
            mp3dir = mp3s[0].parent
            mp3s = rename_sequential(mp3dir, mp3s)

            # Choose cover (batch policy: embedded/file/ask)
            m4as = sorted(work_stage.rglob("*.m4a"))
            old_yes = state.OPTS.yes
            try:
                if cover_mode in {"embedded", "file"}:
                    state.OPTS.yes = True  # auto-accept default choices
                if cover_mode == "embedded":
                    # embedded: still write cover into mp3dir if choose_cover decides to materialize cover.jpg
                    cover = choose_cover(
                        mp3_first=mp3s[0] if mp3s else None,
                        m4a_source=None,
                        bookdir=mp3dir,
                        stage_root=stage,
                        group_root=mp3dir,
                    )
                elif cover_mode == "file":
                    # bias to existing cover files in folder
                    cover = choose_cover(
                        mp3_first=None,
                        m4a_source=None,
                        bookdir=mp3dir,
                        stage_root=stage,
                        group_root=mp3dir,
                    )
                else:
                    cover = choose_cover(
                        mp3_first=mp3s[0] if mp3s else None,
                        m4a_source=m4as[0] if m4as else None,
                        bookdir=mp3dir,          # cover will be written here first if needed
                        stage_root=stage,
                        group_root=mp3dir,
                    )
            finally:
                state.OPTS.yes = old_yes
            cover_bytes = cover[0] if cover else None
            cover_mime = cover[1] if cover else None

            # Write tags
            write_tags(
                mp3s,
                artist=author,
                album=book,
                cover=cover_bytes,
                cover_mime=cover_mime,
                track_start=1,
            )

            # Move to output + optionally publish
            publish = publish_override if publish_override is not None else _decide_publish(archive_root)
            target_root = archive_root if publish else OUTPUT_ROOT
            bookdir_out = target_root / author / book
            ensure_dir(bookdir_out)

            for mp3 in mp3s:
                shutil.move(str(mp3), str(bookdir_out / mp3.name))

            # Also move cover.jpg if it exists in mp3dir
            cov = mp3dir / "cover.jpg"
            if cov.exists():
                shutil.move(str(cov), str(bookdir_out / "cover.jpg"))

            out(f"[done] {book_key} -> {bookdir_out}")
            add_ignore(inbox, source_root.name)

            

            # Cleanup stage if enabled
            if state.OPTS.cleanup_stage and not state.OPTS.dry_run:
                try:
                    # remove stage dir if empty-ish
                    for p in sorted(stage.rglob("*"), reverse=True):
                        if p.is_file():
                            p.unlink(missing_ok=True)
                        elif p.is_dir():
                            try:
                                p.rmdir()
                            except OSError:
                                pass
                    try:
                        stage.rmdir()
                    except OSError:
                        pass
                    prune_empty_dirs(stage.parent, STAGE_ROOT)
                except Exception:
                    pass
    except KeyboardInterrupt:
        out("[abort]")
        return
