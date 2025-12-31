from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import subprocess

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
            path = line.split("=", 1)[1].strip()
            if "/" in path:
                roots.add(path.split("/", 1)[0])

    if len(roots) == 1:
        return PeekResult(True, next(iter(roots)))
    return PeekResult(False, None)


def _list_sources(inbox: Path) -> list[Path]:
    ensure_dir(inbox)
    ignore = load_ignore()
    stage_root = STAGE_ROOT.resolve()
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


def _decide_publish() -> bool:
    # state.OPTS.publish: True/False/None(ask)
    if state.OPTS is None:
        return False
    if state.OPTS.publish is True:
        return True
    if state.OPTS.publish is False:
        return False
    # ask
    return prompt_yes_no("Publish to archive (/mnt/warez/abooks)?", default_no=False)


def run_import() -> None:
    if state.OPTS is None:
        raise SystemExit(2)

    cfg = state.load_config()
    DROP_ROOT = get_drop_root(cfg)
    STAGE_ROOT = get_stage_root(cfg)
    OUTPUT_ROOT = get_output_root(cfg)
    ARCHIVE_ROOT = get_archive_root(cfg)
    try:
        if state.OPTS is None:
            raise SystemExit(2)

        inbox = DROP_ROOT
        ignore = load_ignore()

        sources = _list_sources(inbox)
        if not sources:
            out("[inbox] empty (no .rar/.zip/.7z)")
            return

        try:
            chosen = _pick_sources_interactive(sources)
        except KeyboardInterrupt:
            out("[abort]")
            return

        for src in chosen:
            # Unified source key (archive and directory behave the same)
            peek = peek_source(src)
            source_key = (
                peek.top_level_name
                if peek.has_single_root and peek.top_level_name
                else src.stem if src.is_file() else src.name
            )
            key = source_key
            if slug(key) in ignore:
                out(f"[skip] ignored: {src.name}")
                continue

            out(f"[import] {src.name}")

            # Ask author/book (defaults guessed from source shape)
            peek = peek_source(src)
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

            author = prompt("Author", guess_a).strip() or guess_a
            book = prompt("Book", guess_b).strip() or guess_b

            book_key = f"{slug(author)}.{slug(book)}"
            stage = STAGE_ROOT / slug(source_key)
            ensure_dir(stage)

            try:
                unpack(src, stage)
            except Exception as e:
                out(f"[error] unpack failed: {e}")
                add_ignore(key)
                continue

            convert_m4a_in_place(stage)

            mp3s = natural_sort(list(stage.rglob("*.mp3")))
            if not mp3s:
                out("[skip] no mp3 found after unpack/convert")
                continue

            # Rename sequential in the mp3 folder
            mp3dir = mp3s[0].parent
            mp3s = rename_sequential(mp3dir, mp3s)

            # Choose cover (embedded/file/url prompt)
            m4as = sorted(stage.rglob("*.m4a"))
            cover = choose_cover(
                mp3_first=mp3s[0] if mp3s else None,
                m4a_source=m4as[0] if m4as else None,
                bookdir=mp3dir,          # cover will be written here first if needed
                stage_root=stage,
                group_root=mp3dir,
            )
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
            target_root = ARCHIVE_ROOT if _decide_publish() else OUTPUT_ROOT
            ensure_dir(target_root)
            bookdir_out = target_root / book_key
            ensure_dir(bookdir_out)

            for mp3 in mp3s:
                mp3.rename(bookdir_out / mp3.name)

            # Also move cover.jpg if it exists in mp3dir
            cov = mp3dir / "cover.jpg"
            if cov.exists():
                cov.rename(bookdir_out / "cover.jpg")

            out(f"[done] {book_key} -> {bookdir_out}")

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
