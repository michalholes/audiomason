#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, List

from mutagen.id3 import (
    ID3, ID3NoHeaderError,
    TIT2, TALB, TPE1, TPE2, TRCK, APIC, TCON
)

# ===================== PATHS =====================

from audiomason.paths import (
    ARCHIVE_ROOT,
    DROP_ROOT,
    STAGE_ROOT,
    IGNORE_FILE,
    OUTPUT_ROOT,
    CACHE_ROOT,
    ARCHIVE_EXTS,
    COVER_NAME,
    GENRE,
    TITLE_PREFIX,
)

# ===================== CLI / STATE =====================

from audiomason.state import Opts, OPTS
# ===================== UTIL =====================

from audiomason.util import (
    out,
    die,
    strip_diacritics,
    clean_text,
    slug,
    two,
    ensure_dir,
    unique_path,
    prompt,
    prompt_yes_no,
    prune_empty_dirs,
    is_url,
)

# ===================== IGNORE =====================

from audiomason.ignore import load_ignore, add_ignore

# ===================== ARCHIVES =====================

from audiomason.archives import unpack

# ===================== SORT / RENAME =====================

from audiomason.rename import extract_track_num, natural_sort, rename_sequential

# ===================== ffprobe helpers =====================

from audiomason.audio import (
    ffprobe_json,
    m4a_chapters,
    ffmpeg_common_input,
    m4a_to_mp3_single,
    m4a_split_by_chapters,
    convert_m4a_in_place,
)

# ===================== COVER (embedded / file / URL / from M4A) =====================

def extract_embedded_cover_from_mp3(mp3: Path) -> Optional[Tuple[bytes, str]]:
    try:
        id3 = ID3(mp3)
    except ID3NoHeaderError:
        return None
    for tag in id3.values():
        if isinstance(tag, APIC) and getattr(tag, "data", None):
            return tag.data, (tag.mime or "image/jpeg")
    return None

def convert_image_to_jpg(src: Path, dst: Path) -> bytes:
    if not shutil.which("ffmpeg"):
        die("ffmpeg required for image conversion (sudo apt-get install -y ffmpeg)")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-i", str(src),
        "-frames:v", "1",
        "-update", "1",
        "-pix_fmt", "yuv420p",
        str(dst),
    ]
    if OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return b""
    subprocess.run(cmd, check=True)
    return dst.read_bytes()

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def download_url(url: str, outpath: Path):
    ensure_dir(outpath.parent)
    if OPTS.dry_run:
        out(f"[dry-run] would download: {url} -> {outpath}")
        return
    if shutil.which("curl"):
        subprocess.run(["curl", "-fsSL", "-o", str(outpath), url], check=True)
        return
    if shutil.which("wget"):
        subprocess.run(["wget", "-qO", str(outpath), url], check=True)
        return
    die("Need curl or wget to download URL covers")

def cover_from_input(raw: str, bookdir: Path) -> Optional[Path]:
    raw = raw.strip()
    if not raw:
        return None

    if is_url(raw):
        ensure_dir(CACHE_ROOT)
        cache_file = CACHE_ROOT / (sha1(raw) + ".img")
        if cache_file.exists():
            out("[cover] using cached URL cover")
            return cache_file
        out("[cover] downloading URL cover...")
        download_url(raw, cache_file)
        return cache_file

    p = Path(raw).expanduser()
    if p.exists() and p.is_file():
        return p

    out("[cover] invalid path/url")
    return None

def find_file_cover(stage_root: Path, group_root: Path) -> Optional[Path]:
    for ext in [".avif", ".jpg", ".jpeg", ".png", ".webp"]:
        for cand in [group_root / f"cover{ext}", stage_root / f"cover{ext}"]:
            if cand.exists() and cand.is_file():
                return cand
    return None

def extract_cover_from_m4a(m4a: Path, bookdir: Path) -> Optional[Tuple[bytes, str]]:
    """
    Try to extract attached picture stream from M4A into cover.jpg.
    """
    if not shutil.which("ffmpeg"):
        return None
    dst = bookdir / COVER_NAME

    # Map video stream(s) only. In many m4a, cover is a video stream marked "attached pic".
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-i", str(m4a),
        "-an",
        "-map", "0:v:0",
        "-frames:v", "1",
        "-update", "1",
        "-pix_fmt", "yuv420p",
        str(dst),
    ]
    if OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return None
    try:
        subprocess.run(cmd, check=True)
        if dst.exists() and dst.stat().st_size > 0:
            out("[cover] extracted from m4a container")
            return dst.read_bytes(), "image/jpeg"
    except Exception:
        return None
    return None

def choose_cover(
    mp3_first: Optional[Path],
    m4a_source: Optional[Path],
    bookdir: Path,
    stage_root: Path,
    group_root: Path
) -> Optional[Tuple[bytes, str]]:
    file_cover = find_file_cover(stage_root, group_root)
    embedded = extract_embedded_cover_from_mp3(mp3_first) if mp3_first else None

    # If both exist, ask which one (default: file cover)
    if embedded and file_cover and not OPTS.yes:
        print("Cover options found:")
        print("  1) embedded cover from audio")
        print(f"  2) {file_cover.name} (preferred)")
        try:
            ans = input("Choose cover [1/2] (default: 2): ").strip()
        except KeyboardInterrupt:
            out("\n[cover] skipped")
            return None
        if ans == "1":
            data, mime = embedded
            if not OPTS.dry_run:
                (bookdir / COVER_NAME).write_bytes(data)
            out("[cover] used embedded cover")
            return data, mime
        # else use file
    # Prefer file cover if present
    if file_cover:
        dst = bookdir / COVER_NAME
        ext = file_cover.suffix.lower()
        if ext in {".jpg", ".jpeg"}:
            data = file_cover.read_bytes() if not OPTS.dry_run else b""
            if not OPTS.dry_run:
                dst.write_bytes(data)
            out(f"[cover] used {file_cover.name}")
            return data, "image/jpeg"
        data = convert_image_to_jpg(file_cover, dst)
        out(f"[cover] used {file_cover.name}")
        return data, "image/jpeg"

    # Else embedded
    if embedded:
        data, mime = embedded
        if not OPTS.dry_run:
            (bookdir / COVER_NAME).write_bytes(data)
        out("[cover] used embedded cover")
        return data, mime

    # Else try extract from m4a container
    if m4a_source:
        got = extract_cover_from_m4a(m4a_source, bookdir)
        if got:
            return got

    # Else prompt path or URL
    raw = prompt("No cover found. Path or URL to image (jpg/png/avif/webp) (Enter=skip)", "")
    if not raw:
        return None
    img = cover_from_input(raw, bookdir)
    if img is None:
        return None
    dst = bookdir / COVER_NAME
    ext = img.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        data = img.read_bytes() if not OPTS.dry_run else b""
        if not OPTS.dry_run:
            dst.write_bytes(data)
        out("[cover] saved cover.jpg")
        return data, "image/jpeg"
    data = convert_image_to_jpg(img, dst)
    out("[cover] saved cover.jpg")
    return data, "image/jpeg"

# ===================== ID3 WRITE =====================

def write_tags(mp3: Path, author: str, book: str, tn: int, total: int, cover: Optional[Tuple[bytes, str]]):
    author = clean_text(author)
    book = clean_text(book)

    if OPTS.dry_run:
        return

    try:
        ID3(mp3).delete(mp3)
    except ID3NoHeaderError:
        pass

    id3 = ID3()
    id3.add(TPE1(encoding=3, text=author))
    id3.add(TPE2(encoding=3, text=author))
    id3.add(TALB(encoding=3, text=book))
    id3.add(TIT2(encoding=3, text=f"{TITLE_PREFIX} {two(tn)}"))
    id3.add(TRCK(encoding=3, text=f"{tn}/{total}"))
    id3.add(TCON(encoding=3, text=GENRE))
    if cover and cover[0]:
        id3.add(APIC(encoding=3, mime=cover[1], type=3, desc="Cover", data=cover[0]))
    id3.save(mp3)

# ===================== AUDIO CONVERT (M4A) =====================

def ffmpeg_common_input() -> list[str]:
    return ["-hide_banner", "-nostdin", "-stats", "-loglevel", OPTS.ff_loglevel]

def m4a_to_mp3_single(src: Path, dst: Path):
    if not shutil.which("ffmpeg"):
        die("ffmpeg not installed (sudo apt-get install -y ffmpeg)")
    cmd = ["ffmpeg"] + ffmpeg_common_input() + ["-y", "-i", str(src), "-vn"]
    if OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += ["-codec:a", "libmp3lame", "-q:a", OPTS.q_a, str(dst)]
    if OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return
    subprocess.run(cmd, check=True)

def m4a_split_by_chapters(src: Path, outdir: Path) -> list[Path]:
    """
    If chapters exist, produce 01.mp3..N.mp3 into outdir.
    Returns list of produced mp3 paths.
    """
    ch = m4a_chapters(src)
    if not ch or len(ch) < 2:
        return []

    ensure_dir(outdir)
    out(f"[split] splitting by chapters: {len(ch)} tracks")

    produced: list[Path] = []
    for i, c in enumerate(ch, 1):
        start = c.get("start_time")
        end = c.get("end_time")
        if start is None or end is None:
            continue
        # Use -ss/-to with input AFTER -i for accurate seek (slower but safe)
        dst = outdir / f"{two(i)}.mp3"
        out(f"[split] {i}/{len(ch)} {start} -> {end} -> {dst.name}")

        cmd = ["ffmpeg"] + ffmpeg_common_input() + [
            "-y",
            "-i", str(src),
            "-vn",
            "-ss", str(start),
            "-to", str(end),
        ]
        if OPTS.loudnorm:
            cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
        cmd += ["-codec:a", "libmp3lame", "-q:a", OPTS.q_a, str(dst)]

        if OPTS.dry_run:
            out("[dry-run] " + " ".join(cmd))
        else:
            subprocess.run(cmd, check=True)
        produced.append(dst)

    # If something went wrong and produced empty, return []
    if not OPTS.dry_run:
        produced = [p for p in produced if p.exists() and p.stat().st_size > 0]
    return produced

def convert_m4a_in_place(stage: Path):
    """
    Convert/split all .m4a files found in stage.
    - If --split-chapters and m4a has >=2 chapters -> split into mp3 tracks (per m4a).
    - Else -> convert to single mp3 next to m4a.
    We do NOT delete originals.
    """
    m4as = sorted(stage.rglob("*.m4a"), key=lambda p: p.as_posix().lower())
    if not m4as:
        return
    out(f"[convert] found {len(m4as)} m4a")

    for idx, src in enumerate(m4as, 1):
        out(f"[convert] {idx}/{len(m4as)} {src.name}")
        # If splitting, write tracks into same folder as m4a (so grouping works)
        if OPTS.split_chapters:
            outdir = src.parent
            produced = m4a_split_by_chapters(src, outdir)
            if produced:
                out(f"[convert] split produced {len(produced)} mp3")
                continue

        # fallback single file
        dst = src.with_suffix(".mp3")
        out("[convert] no chapters split (or only 1 chapter) -> single mp3")
        m4a_to_mp3_single(src, dst)

# ===================== AUTO AUTHOR/BOOK (ASCII-only) =====================

def to_surname_dot_name(person: str) -> Optional[str]:
    person = clean_text(person)
    person = re.sub(r"[\(\[].*?[\)\]]", "", person).strip()
    person = re.sub(r"[,_]+", " ", person).strip()
    parts = [p for p in person.split(" ") if p]
    if len(parts) < 2:
        return None
    first, last = parts[0], parts[-1]
    return f"{slug(last)}.{slug(first)}"

def cleanup_title(title: str) -> str:
    t = clean_text(title)
    t = re.sub(r"\(\s*\d{4}\s*\)", "", t)
    t = re.sub(r"\b(CZ|SK|EN)\b", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -_")
    return t

def guess_author_book(source_name: str, group_name: str) -> Tuple[Optional[str], Optional[str]]:
    name = group_name if group_name != "_ROOT_" else source_name
    raw = clean_text(name)

    m = re.split(r"\s[-–—]\s", raw, maxsplit=1)
    if len(m) == 2:
        a_raw, b_raw = m[0], m[1]
        author = to_surname_dot_name(a_raw)
        book = cleanup_title(b_raw)
        return (author, slug(book) if book else None)

    tokens = raw.split()
    if len(tokens) >= 3:
        maybe_person = " ".join(tokens[:2])
        author = to_surname_dot_name(maybe_person)
        if author:
            book = cleanup_title(" ".join(tokens[2:]))
            return (author, slug(book) if book else None)

    book = cleanup_title(raw)
    return (None, slug(book) if book else None)

# ===================== METADATA FILE =====================

def write_book_json(dest_dir: Path, meta: dict):
    if OPTS.dry_run:
        return
    p = dest_dir / "book.json"
    p.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")

# ===================== PUBLISH =====================

def publish_one(src_ready: Path, dest: Path):
    ensure_dir(dest.parent)
    if dest.exists():
        die(f"Destination exists: {dest}")
    if OPTS.dry_run:
        out(f"[dry-run] would publish {src_ready} -> {dest}")
        return

    if shutil.which("rsync"):
        subprocess.run(["rsync", "-a", f"{src_ready}/", f"{dest}/"], check=True)
    else:
        shutil.copytree(src_ready, dest)

    # After successful publish -> remove from ready
    shutil.rmtree(src_ready, ignore_errors=True)
    prune_empty_dirs(src_ready.parent, OUTPUT_ROOT)

# ===================== VERIFY MODE =====================

def verify_library(root: Path) -> int:
    root = root.resolve()
    if not root.exists():
        die(f"verify root not found: {root}")

    problems = 0
    for author_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        for book_dir in sorted([p for p in author_dir.iterdir() if p.is_dir()]):
            mp3s = sorted(book_dir.glob("*.mp3"))
            if not mp3s:
                continue

            cover_file = book_dir / COVER_NAME
            if not cover_file.exists():
                problems += 1
                print(f"[verify][NO_COVER_FILE] {author_dir.name}/{book_dir.name}")

            emb = extract_embedded_cover_from_mp3(mp3s[0])
            if not emb:
                problems += 1
                print(f"[verify][NO_EMBEDDED_COVER] {author_dir.name}/{book_dir.name}")

            try:
                id3 = ID3(mp3s[0])
                need = ["TPE1", "TALB", "TIT2", "TRCK"]
                for t in need:
                    if t not in id3:
                        problems += 1
                        print(f"[verify][MISSING_{t}] {author_dir.name}/{book_dir.name}")
                        break
            except Exception:
                problems += 1
                print(f"[verify][BAD_ID3] {author_dir.name}/{book_dir.name}")

    print(f"[verify] done. problems={problems}")
    return 0 if problems == 0 else 1

# ===================== MAIN IMPORT =====================

def main_import():
    # Always start with clean stage
    if STAGE_ROOT.exists():
        out(f"[startup] cleaning stage: {STAGE_ROOT}")
        if not OPTS.dry_run:
            shutil.rmtree(STAGE_ROOT, ignore_errors=True)
    ensure_dir(STAGE_ROOT)
    ensure_dir(OUTPUT_ROOT)
    ensure_dir(CACHE_ROOT)

    ignores = load_ignore()

    items = [
        p for p in DROP_ROOT.iterdir()
        if p.name not in {"stage", ".cover_cache"}
        and slug(p.name) not in ignores
        and (p.is_dir() or p.suffix.lower() in ARCHIVE_EXTS)
    ]
    if not items:
        die("Inbox empty")

    # Select source
    if OPTS.yes and len(items) == 1:
        src = items[0]
    else:
        print("Select source:")
        for i, p in enumerate(items, 1):
            print(f"  {i}) {p.name}")
        if OPTS.yes:
            src = items[0]
            out(f"[auto] selected: {src.name}")
        else:
            src = items[int(input("Choose: ")) - 1]

    stage = unique_path(STAGE_ROOT / slug(src.stem if src.is_file() else src.name))
    ensure_dir(stage)

    # Stage content
    if src.is_file():
        out(f"[unpack] {src}")
        if not OPTS.dry_run:
            unpack(src, stage)
    else:
        out(f"[copy] {src}")
        if not OPTS.dry_run:
            shutil.copytree(src, stage, dirs_exist_ok=True)

    # Convert M4A: split-by-chapters OR single file
    convert_m4a_in_place(stage)

    # Now gather mp3s
    mp3s = list(stage.rglob("*.mp3"))
    if not mp3s:
        die("No MP3 found after unpack/copy/convert")

    # Group by top-level dir; root files -> _ROOT_
    groups: Dict[str, List[Path]] = {}
    for m in mp3s:
        rel = m.relative_to(stage)
        key = rel.parts[0] if len(rel.parts) > 1 else "_ROOT_"
        groups.setdefault(key, []).append(m)

    ready_items: list[tuple[Path, str, str]] = []  # (ready_path, author_key, book_key)

    for idx, (gname, files) in enumerate(groups.items(), 1):
        files = list(files)
        print(f"\n[BOOK {idx}/{len(groups)}] {gname} ({len(files)} tracks)")

        sug_author, sug_book = guess_author_book(src.name, gname)
        out("Author format: Surname.Name (ASCII only)")
        out("Examples: Adams.Douglas | Coelho.Paulo | Dan.Dominik")

        author_in = prompt("Author (Surname.Name)", sug_author or "")
        book_in   = prompt("Book", sug_book or slug(gname if gname != "_ROOT_" else src.stem))

        author_key = slug(author_in)
        book_key   = slug(book_in)

        tag_author = clean_text(author_in)
        tag_book   = clean_text(book_in)

        # Working directory
        mp3dir = stage / f"book_{idx}" / "mp3"
        ensure_dir(mp3dir)

        # Copy tracks to working dir
        if not OPTS.dry_run:
            for f in files:
                shutil.copy2(f, mp3dir / f.name)

        # Sort/rename
        ordered: list[Path] = []
        if not OPTS.dry_run:
            ordered = natural_sort(list(mp3dir.glob("*.mp3")))
            ordered = rename_sequential(mp3dir, ordered)

        group_root = stage if gname == "_ROOT_" else (stage / gname)

        # Pick an m4a source in this group (for cover extraction fallback)
        m4a_source: Optional[Path] = None
        if not OPTS.dry_run:
            # try to find any m4a in same group_root or stage
            cand = list(group_root.rglob("*.m4a")) if group_root.exists() else []
            if not cand:
                cand = list(stage.rglob("*.m4a"))
            m4a_source = cand[0] if cand else None

        # Cover selection (file > embedded mp3 > extract from m4a > prompt path/url)
        cover: Optional[Tuple[bytes, str]] = None
        if not OPTS.dry_run:
            mp3_first = ordered[0] if ordered else None
            cover = choose_cover(mp3_first, m4a_source, mp3dir.parent, stage, group_root)

        # Write ID3
        if not OPTS.dry_run:
            total = len(ordered)
            out(f"[id3] writing tags for {total} tracks...")
            for i, m in enumerate(ordered, 1):
                if i == 1 or i == total or (total >= 50 and i % 25 == 0):
                    out(f"[id3] {i}/{total}")
                write_tags(m, tag_author, tag_book, i, total, cover)

        # Move to ready
        dest_ready = OUTPUT_ROOT / author_key / book_key
        out(f"[ready] -> {dest_ready}")
        if dest_ready.exists() and not OPTS.dry_run:
            die(f"Destination already exists in ready: {dest_ready}")
        if not OPTS.dry_run:
            ensure_dir(dest_ready.parent)
            shutil.move(mp3dir, dest_ready)

            meta = {
                "author_dir": author_key,
                "book_dir": book_key,
                "author_tag": tag_author,
                "book_tag": tag_book,
                "tracks": len(list(dest_ready.glob("*.mp3"))),
                "source": src.name,
                "group": gname,
                "split_chapters": OPTS.split_chapters,
                "loudnorm": OPTS.loudnorm,
                "q_a": OPTS.q_a,
                "imported_ts": int(time.time()),
            }
            write_book_json(dest_ready, meta)

        ready_items.append((dest_ready, author_key, book_key))

    # Auto-ignore source
    add_ignore(src.name)

    # Publish?
    if ready_items:
        do_publish = False
        if OPTS.publish is True:
            do_publish = True
        elif OPTS.publish is False:
            do_publish = False
        else:
            do_publish = prompt_yes_no(f"\nPublish {len(ready_items)} book(s) to archive?", default_no=True)

        if do_publish:
            for src_ready, a, b in ready_items:
                publish_one(src_ready, ARCHIVE_ROOT / a / b)
            out("[publish] done")
        else:
            out("[publish] skipped")

    # Cleanup stage after success
    if OPTS.cleanup_stage:
        out(f"[cleanup] removing stage: {STAGE_ROOT}")
        if not OPTS.dry_run:
            shutil.rmtree(STAGE_ROOT, ignore_errors=True)

    out("[SUCCESS]")

def parse_args() -> Opts:
    ap = argparse.ArgumentParser(prog="abook_import", add_help=True)
    ap.add_argument("--yes", action="store_true", help="non-interactive (take defaults, skip prompts)")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen, do nothing")
    ap.add_argument("--quiet", action="store_true", help="less output")
    ap.add_argument("--publish", choices=["yes", "no", "ask"], default="ask", help="publish to /mnt/warez/abooks")
    ap.add_argument("--loudnorm", action="store_true", help="normalize loudness during m4a->mp3")
    ap.add_argument("--q-a", default="2", help="lame VBR quality (2=high, 4=faster ok for audiobooks)")
    ap.add_argument("--verify", action="store_true", help="verify library (covers+tags)")
    ap.add_argument("--verify-root", default=str(OUTPUT_ROOT), help="root for --verify (abooks_ready or abooks)")
    ap.add_argument("--no-cleanup-stage", action="store_true", help="keep stage after success (debug)")
    ap.add_argument("--split-chapters", action="store_true", help="split m4a by chapters when available")
    ap.add_argument("--no-split-chapters", action="store_true", help="disable split-by-chapters")
    ap.add_argument("--ff-loglevel", choices=["info", "warning", "error"], default="warning", help="ffmpeg loglevel")
    ns = ap.parse_args()

    pub = {"yes": True, "no": False, "ask": None}[ns.publish]
    split = True
    if ns.no_split_chapters:
        split = False
    if ns.split_chapters:
        split = True

    return Opts(
        yes=ns.yes,
        dry_run=ns.dry_run,
        quiet=ns.quiet,
        publish=pub,
        loudnorm=ns.loudnorm,
        q_a=str(ns.q_a),
        verify=ns.verify,
        verify_root=Path(ns.verify_root),
        lookup=False,
        cleanup_stage=(not ns.no_cleanup_stage),
        split_chapters=split,
        ff_loglevel=ns.ff_loglevel,
    )

def main():
    import audiomason.state as _state
    _state.OPTS = parse_args()
    if OPTS.verify:
        rc = verify_library(OPTS.verify_root)
        raise SystemExit(rc)

    main_import()

if __name__ == "__main__":
    main()
