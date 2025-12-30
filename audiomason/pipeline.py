from __future__ import annotations

import unicodedata
import os
from pathlib import Path
import re
import shutil
import time
import subprocess
import json
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TRCK, TCON, APIC

from .planner import build_candidates
from .archives import is_archive, unpack
from .normalize import path_component


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _clean_dir(p: Path):
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def _log(cfg: dict, msg: str, force: bool = False) -> None:
    rt = cfg.get("runtime", {}) if isinstance(cfg, dict) else {}
    if force:
        print(msg, flush=True)
        return
    if rt.get("quiet"):
        return
    print(msg, flush=True)


def _should_tick(i: int, n: int) -> bool:
    # show start/end always; in the middle show every 25 for large sets
    if i <= 1 or i >= n:
        return True
    if n >= 50 and i % 25 == 0:
        return True
    if n >= 200 and i % 50 == 0:
        return True
    return False


def _prompt(msg: str, default: str, yes: bool) -> str:
    if yes:
        return default
    s = input(f"{msg} [{default}]: ").strip()
    return s if s else default


def _stage_run(cfg: dict) -> Path:
    stage = Path(cfg["paths"]["stage"])
    ts = time.strftime("run-%Y%m%d-%H%M%S")
    return stage / ts


def _prepare_stage(cfg: dict, run: Path):
    stage_root = Path(cfg["paths"]["stage"])
    if cfg["behavior"].get("clean_stage_on_start", True):
        _clean_dir(stage_root)
    _ensure_dir(run / "src")


def _stage_input(cfg: dict, input_path: Path, dst_src: Path):
    _log(cfg, f"[stage] input={input_path}")
    if not input_path.exists():
        raise SystemExit(f"[FATAL] input path not found: {input_path}")

    if input_path.is_dir():
        _log(cfg, "[stage] copying directory -> stage")
        shutil.copytree(input_path, dst_src, dirs_exist_ok=True)
        return

    if is_archive(input_path):
        _log(cfg, "[stage] unpacking archive -> stage")
        _ensure_dir(dst_src)
        unpack(input_path, dst_src)
        return

    _log(cfg, "[stage] copying file -> stage")
    _ensure_dir(dst_src)
    shutil.copy2(input_path, dst_src / input_path.name)


def cmd_inspect(cfg: dict, path: Path) -> int:
    # Inspect must be fast & read-only (no staging, no copying, no cleaning)
    stage_src = path if path.is_dir() else path.parent

    allow_guess = bool(cfg.get("covers", {}).get("allow_guess_single_image_if_no_cover", True))
    _log(cfg, "[process] scanning stage for book candidates")
    cands = build_candidates(stage_src, allow_guess_single_image=allow_guess)
    _log(cfg, f"[process] found {len(cands)} candidate(s)")

    print(f"FOUND {len(cands)} book candidate(s)\n")
    for i, c in enumerate(cands, 1):
        rel = c.root.relative_to(stage_src)
        print(f"[{i}] kind={c.kind} root={rel}")
        print(f"    audio={len(c.audio)} cover_candidates={len(c.cover_candidates)} sidecars={len(c.sidecars)}")
        print(f"    author_suggest={c.suggest_author!r}")
        print(f"    title_suggest={c.suggest_title!r}")
        if c.notes:
            print(f"    notes={','.join(c.notes)}")
        for cc in c.cover_candidates:
            print(f"    cover_candidate={cc.name}")
        print()
    return 0


def cmd_process(cfg: dict, path: Path, yes: bool, dry_run: bool = False) -> int:
    _log(cfg, f"[process] starting: {path}")
    run = _stage_run(cfg)
    _prepare_stage(cfg, run)

    stage_src = run / "src"
    _stage_input(cfg, path, stage_src)

    ready = Path(cfg["paths"]["ready"])
    _ensure_dir(ready)

    allow_guess = bool(cfg.get("covers", {}).get("allow_guess_single_image_if_no_cover", True))
    _log(cfg, "[process] scanning stage for book candidates")
    cands = build_candidates(stage_src, allow_guess_single_image=allow_guess)
    _log(cfg, f"[process] found {len(cands)} candidate(s)")

    use_spaces = bool(cfg.get("naming", {}).get("use_spaces_in_dirs", True))

    for idx, c in enumerate(cands, 1):
        _log(cfg, f"[process] [{idx}/{len(cands)}] processing")

        author_in = _prompt("Author (Surname.Name)", c.suggest_author, yes=yes)
        title_in = _prompt("Book", c.suggest_title, yes=yes)

        author_dir = path_component(author_in, use_spaces=False)  # Surname.Name stays ASCII-ish
        book_dir = path_component(title_in, use_spaces=use_spaces)

        out_dir = ready / author_dir / book_dir
        if out_dir.exists() and any(out_dir.iterdir()):
            raise SystemExit(f"[FATAL] output already exists (refusing to overwrite): {out_dir}")

        _log(cfg, f"[PLAN] {c.root.relative_to(stage_src)} -> {out_dir}")
        _ensure_dir(out_dir)

        # 1) Produce MP3s into out_dir
        audio_files = list(c.audio)
        if not audio_files:
            _log(cfg, "[audio] no audio files found")
        else:
            _log(cfg, f"[audio] inputs={len(audio_files)}")

        for i, src in enumerate(audio_files, 1):
            if _should_tick(i, len(audio_files)):
                _log(cfg, f"[audio] {i}/{len(audio_files)} {src.name}")

            if src.suffix.lower() == ".m4a":
                # Try chapter split first
                did_split = _m4a_split_by_chapters(src, out_dir)
                if not did_split:
                    dst = out_dir / (src.stem + ".mp3")
                    _m4a_to_mp3_single(src, dst)
            else:
                shutil.copy2(src, out_dir / src.name)

        # 2) Rename MP3s sequentially 01..N
        mp3s = list(out_dir.glob("*.mp3"))
        if mp3s:
            mp3s = _natural_sort(mp3s)
            _log(cfg, f"[rename] sequential -> {len(mp3s)} track(s)")
            _rename_sequential(out_dir, mp3s)
        else:
            _log(cfg, "[FATAL] no mp3 produced (check m4a/ffmpeg)", force=True)
            raise SystemExit("[FATAL] no mp3 produced")

        # 3) Cover + ID3
        allow_guess = bool(cfg.get("covers", {}).get("allow_guess_single_image_if_no_cover", True))
        best = _find_best_cover(c.root, list(c.audio), allow_guess_single_image=allow_guess)
        cover_candidates = list(c.cover_candidates)
        if best is not None and best not in cover_candidates:
            cover_candidates.insert(0, best)
        cover = _pick_cover(cover_candidates, yes=yes)

        artist_tag = path_component(author_in, use_spaces=False)
        album_tag = path_component(title_in, use_spaces=True)
        _tag_mp3_dir(out_dir, artist=artist_tag, album=album_tag, cover_path=cover)

        # Summary + cleanup
        tracks = len(list(out_dir.glob('*.mp3')))
        _log(cfg, f"[summary] tracks={tracks} cover={'yes' if cover else 'no'} out={out_dir}")
        _cleanup_out_dir(cfg, out_dir, dry_run=dry_run)


    # Publish ready output
    archive_root = Path(cfg["paths"].get("archive_ro", ""))
    if archive_root:
        if _publish_decision(cfg, yes=yes):
            _log(cfg, "[publish] confirmed")
            for d in ready.iterdir():
                if d.is_dir():
                    for book in d.iterdir():
                        if book.is_dir():
                            _publish_dir(book, archive_root, dry_run=dry_run)
        else:
            _log(cfg, "[publish] skipped (left in ready)")
    if cfg["behavior"].get("clean_stage_on_success", True):
        if dry_run:
            _log(cfg, "[dry-run] stage cleanup skipped")
        else:
            _clean_dir(Path(cfg["paths"]["stage"]))
    return 0


# ===================== inbox import (monolith-like) =====================

def _slug_ascii(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "Unknown"


def _inbox_root(cfg: dict) -> Path:
    # Prefer config, fallback to old monolith default
    return Path(cfg.get("paths", {}).get("inbox", "/mnt/warez/abooksinbox"))


def _ignore_file(cfg: dict) -> Path:
    return _inbox_root(cfg) / ".abook_ignore"


def _load_ignore(cfg: dict) -> set[str]:
    f = _ignore_file(cfg)
    if not f.exists():
        return set()
    lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
    out = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def _add_ignore(cfg: dict, name: str) -> None:
    key = _slug_ascii(name)
    f = _ignore_file(cfg)
    cur = _load_ignore(cfg)
    if key in cur:
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fp:
        fp.write(key + "\n")
    print(f"[ignore] added {key}")


def _scan_inbox(cfg: dict, all_items: bool) -> list[Path]:
    root = _inbox_root(cfg)
    if not root.exists():
        raise SystemExit(f"[FATAL] inbox not found: {root}")

    ignores = _load_ignore(cfg)

    items: list[Path] = []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if p.name in {"stage", ".cover_cache"}:
            continue
        if p.name.startswith("."):
            # ignore dotfiles + .abook_ignore
            continue
        if (not all_items) and (_slug_ascii(p.name) in ignores):
            continue
        if p.is_dir() or is_archive(p):
            items.append(p)
    return items


def cmd_import(cfg: dict, yes: bool, all_items: bool = False) -> int:
    # Scan inbox and run process() on a selected source (monolith-like)
    items = _scan_inbox(cfg, all_items=all_items)
    if not items:
        raise SystemExit("[FATAL] Inbox empty")

    src: Path
    if yes and len(items) == 1:
        src = items[0]
    else:
        print("Select source:")
        for i, p in enumerate(items, 1):
            print(f"  {i}) {p.name}")
        if yes:
            src = items[0]
            print(f"[auto] selected: {src.name}")
        else:
            ans = input("Choose: ").strip()
            try:
                idx = int(ans)
            except ValueError:
                raise SystemExit("[FATAL] invalid choice")
            if idx < 1 or idx > len(items):
                raise SystemExit("[FATAL] choice out of range")
            src = items[idx - 1]

    rc = cmd_process(cfg, src, yes=yes, dry_run=dry_run)

    # Only auto-ignore on success
    if rc == 0:
        _add_ignore(cfg, src.name)

    return rc


# ===================== copy + rename (monolith-like) =====================

def _extract_track_num(name: str) -> int | None:
    m = re.search(r"(?:^|\D)(\d{1,4})(?:\D|$)", name)
    return int(m.group(1)) if m else None

def _natural_sort(paths: list[Path]) -> list[Path]:
    def key(p: Path):
        n = _extract_track_num(p.name)
        return (n is None, n or 0, p.name.lower())
    return sorted(paths, key=key)

def _two(i: int) -> str:
    return f"{i:02d}"

def _rename_sequential(dirp: Path, files: list[Path]) -> list[Path]:
    # Two-step rename to avoid collisions
    tmp: list[Path] = []
    for i, f in enumerate(files, 1):
        t = dirp / f".__tmp__{i:04d}.mp3"
        f.rename(t)
        tmp.append(t)
    out: list[Path] = []
    for i, t in enumerate(tmp, 1):
        o = dirp / f"{_two(i)}.mp3"
        t.rename(o)
        out.append(o)
    return out


# ===================== cover + id3 tagging (monolith-like) =====================

def _mime_for_image(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    # fallback
    return "image/jpeg"


def _pick_cover(cover_candidates: list[Path], yes: bool) -> Path | None:
    if not cover_candidates:
        print("[cover] no cover candidates")
        return None
    if yes:
        c = cover_candidates[0]
        print(f"[cover] auto: {c.name}")
        return c

    print("[cover] choose:")
    for i, c in enumerate(cover_candidates, 1):
        print(f"  {i}) {c.name}")
    print("  0) none")
    ans = input("Cover: ").strip()
    if ans == "0" or ans == "":
        # default: 1 if empty
        if ans == "":
            return cover_candidates[0]
        return None
    try:
        idx = int(ans)
    except ValueError:
        raise SystemExit("[FATAL] invalid cover choice")
    if idx < 1 or idx > len(cover_candidates):
        raise SystemExit("[FATAL] cover choice out of range")
    return cover_candidates[idx - 1]


def _write_id3_mp3(mp3_path: Path, artist: str, album: str, trackno: int, total: int, cover: bytes | None, cover_mime: str | None) -> None:
    try:
        tag = ID3(mp3_path)
    except ID3NoHeaderError:
        tag = ID3()

    # Basic tags (ASCII-only expected by design)
    tag.delall("TPE1")
    tag.delall("TALB")
    tag.delall("TRCK")
    tag.delall("TCON")
    tag.delall("TIT2")
    tag.add(TPE1(encoding=3, text=[artist]))
    tag.add(TALB(encoding=3, text=[album]))
    tag.add(TRCK(encoding=3, text=[f"{trackno:02d}/{total:02d}"]))
    tag.add(TCON(encoding=3, text=["Audiobook"]))
    tag.add(TIT2(encoding=3, text=[f"{trackno:02d}"]))

    # Cover
    tag.delall("APIC")
    if cover is not None and cover_mime is not None:
        tag.add(APIC(encoding=3, mime=cover_mime, type=3, desc="Cover", data=cover))

    tag.save(mp3_path)


def _tag_mp3_dir(out_dir: Path, artist: str, album: str, cover_path: Path | None) -> None:
    mp3s = sorted(out_dir.glob("*.mp3"))
    if not mp3s:
        print("[id3] no mp3 files to tag")
        return

    cover_bytes = None
    cover_mime = None
    if cover_path is not None:
        cover_bytes = cover_path.read_bytes()
        cover_mime = _mime_for_image(cover_path)
        _log(cfg, f"[cover] embedding: {cover_path.name} ({cover_mime})")

    total = len(mp3s)
    _log(cfg, f"[id3] tagging {total} track(s)")
    for i, mp3 in enumerate(mp3s, 1):
        if i == 1 or i == total or (total >= 50 and i % 25 == 0):
            _log(cfg, f"[id3] {i}/{total} {mp3.name}")
        _write_id3_mp3(mp3, artist=artist, album=album, trackno=i, total=total, cover=cover_bytes, cover_mime=cover_mime)


# ===================== publish (monolith-like) =====================

def _publish_decision(cfg: dict, yes: bool) -> bool:
    mode = cfg.get("paths", {}).get("publish", "ask")
    if yes:
        return True
    if mode == "yes":
        return True
    if mode == "no":
        return False

    # ask
    ans = input("Publish to archive? [y/N] ").strip().lower()
    return ans in {"y", "yes"}


def _publish_dir(src: Path, dst_root: Path, dry_run: bool = False) -> None:
    dst = dst_root / src.parent.name / src.name
    if dst.exists():
        raise SystemExit(f"[FATAL] archive target already exists: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    _log(cfg, f"[publish] {src} -> {dst}", force=True)
    if dry_run:
        _log(cfg, "[dry-run] publish move skipped", force=True)
        return
    shutil.move(str(src), str(dst))


# ===================== verify (monolith-like) =====================

def _is_track_name_ok(name: str) -> bool:
    # Accept 01.mp3 .. 9999.mp3 (but expect 2 digits normally)
    return bool(re.match(r"^\d{2,4}\.mp3$", name.lower()))


def _read_id3(path: Path):
    try:
        return ID3(path)
    except ID3NoHeaderError:
        return None
    except Exception:
        return None


def cmd_verify(cfg: dict) -> int:
    archive = Path(cfg.get("paths", {}).get("archive_ro", ""))
    if not str(archive):
        raise SystemExit("[FATAL] config missing paths.archive_ro")
    if not archive.exists():
        raise SystemExit(f"[FATAL] archive_ro not found: {archive}")

    problems: list[str] = []
    books_ok = 0
    books_bad = 0

    # Expect: archive/Author/Book/*.mp3
    authors = [p for p in sorted(archive.iterdir()) if p.is_dir()]
    if not authors:
        print("[verify] no authors found")
        return 0

    print(f"[verify] scanning: {archive}")
    for a in authors:
        books = [b for b in sorted(a.iterdir()) if b.is_dir()]
        for b in books:
            mp3s = sorted([f for f in b.iterdir() if f.is_file() and f.suffix.lower() == ".mp3"], key=lambda x: x.name.lower())
            if not mp3s:
                problems.append(f"{a.name}/{b.name}: no mp3 files")
                books_bad += 1
                continue

            # Filename check
            bad_names = [f.name for f in mp3s if not _is_track_name_ok(f.name)]
            if bad_names:
                problems.append(f"{a.name}/{b.name}: bad track filenames: {', '.join(bad_names[:8])}" + (" ..." if len(bad_names) > 8 else ""))

            # Sequential check (01..N)
            expected = [f"{i:02d}.mp3" for i in range(1, len(mp3s) + 1)]
            got = [f.name for f in mp3s]
            if got != expected:
                problems.append(f"{a.name}/{b.name}: track sequence mismatch (expected 01..{len(mp3s):02d})")

            # ID3 check
            has_cover = False
            id3_missing = 0
            artist_set = set()
            album_set = set()
            for f in mp3s:
                tag = _read_id3(f)
                if tag is None:
                    id3_missing += 1
                    continue
                if tag.getall("APIC"):
                    has_cover = True

                # required frames
                tpe1 = tag.getall("TPE1")
                if not tpe1:
                    problems.append(f"{a.name}/{b.name}/{f.name}: missing TPE1 (artist)")
                else:
                    artist_set.add(str(tpe1[0].text[0]))
                talb = tag.getall("TALB")
                if not talb:
                    problems.append(f"{a.name}/{b.name}/{f.name}: missing TALB (album)")
                else:
                    album_set.add(str(talb[0].text[0]))
                trcks = tag.getall("TRCK")
                if not trcks:
                    problems.append(f"{a.name}/{b.name}/{f.name}: missing TRCK (track)")
                else:
                    tv = str(trcks[0].text[0]) if getattr(trcks[0], 'text', None) else ""
                    tn, tt = _parse_trck(tv)
                    # Expect tn == track index from filename order; tt == total
                    exp_total = len(mp3s)
                    exp_no = int(f.stem)
                    if tn != exp_no:
                        problems.append(f"{a.name}/{b.name}/{f.name}: TRCK value mismatch (got {tv!r}, expected {exp_no}/{exp_total})")
                    if tt is not None and tt != exp_total:
                        problems.append(f"{a.name}/{b.name}/{f.name}: TRCK total mismatch (got {tv!r}, expected */{exp_total})")

            if id3_missing:
                problems.append(f"{a.name}/{b.name}: {id3_missing}/{len(mp3s)} file(s) missing ID3 header")

            if not has_cover:
                problems.append(f"{a.name}/{b.name}: no embedded cover (APIC) found")
            if len(artist_set) > 1:
                problems.append(f"{a.name}/{b.name}: inconsistent artist tags: {sorted(artist_set)[:5]}")
            if len(album_set) > 1:
                problems.append(f"{a.name}/{b.name}: inconsistent album tags: {sorted(album_set)[:5]}")

            # Decide book ok/bad
            # If any problem lines start with this book prefix => bad
            prefix = f"{a.name}/{b.name}:"
            prefix2 = f"{a.name}/{b.name}/"
            book_has_problem = any(x.startswith(prefix) or x.startswith(prefix2) for x in problems)
            if book_has_problem:
                books_bad += 1
            else:
                books_ok += 1

    if problems:
        print(f"[verify] FAIL: problems={len(problems)} books_ok={books_ok} books_bad={books_bad}")
        for line in problems[:200]:
            print(" -", line)
        if len(problems) > 200:
            print(f" - ... ({len(problems)-200} more)")
        return 2

    print(f"[verify] OK: books_ok={books_ok} books_bad={books_bad}")
    return 0


# ===================== m4a -> mp3 (monolith-like) =====================

def _ffprobe_chapters(path: Path) -> list[dict]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_chapters",
        str(path),
    ]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    data = json.loads(r.stdout.decode("utf-8", errors="ignore") or "{}")
    return data.get("chapters") or []


def _m4a_split_by_chapters(src: Path, outdir: Path) -> bool:
    ch = _ffprobe_chapters(src)
    if not ch or len(ch) < 2:
        return False

    _log({"runtime": {}}, f"[m4a] splitting by chapters: {len(ch)}", force=True)
    outdir.mkdir(parents=True, exist_ok=True)

    for i, c in enumerate(ch, 1):
        start = c.get("start_time")
        end = c.get("end_time")
        if start is None or end is None:
            continue
        dst = outdir / f"{i:02d}.mp3"
        print(f"[m4a] {i}/{len(ch)} {start} -> {end}", flush=True)
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(src),
            "-vn",
            "-ss", str(start),
            "-to", str(end),
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(dst),
        ]
        subprocess.run(cmd, check=True)

    return True


def _m4a_to_mp3_single(src: Path, dst: Path) -> None:
    print(f"[m4a] convert single -> {dst.name}", flush=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(src),
        "-vn",
        "-codec:a", "libmp3lame",
        "-q:a", "2",
        str(dst),
    ]
    subprocess.run(cmd, check=True)



def _parse_trck(value: str) -> tuple[int|None, int|None]:
    # accepts "1/12", "01/12", "1", "01"
    value = (value or "").strip()
    if "/" in value:
        a, b = value.split("/", 1)
        try:
            return int(a), int(b)
        except ValueError:
            return None, None
    try:
        return int(value), None
    except ValueError:
        return None, None


def _cleanup_out_dir(cfg: dict, out_dir: Path, dry_run: bool) -> None:
    leftovers = [p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() != ".mp3"]
    if not leftovers:
        return
    _log(cfg, f"[cleanup] leftovers={len(leftovers)}")
    for f in leftovers:
        _log(cfg, f"[cleanup] rm {f.name}")
        if not dry_run:
            try:
                f.unlink()
            except Exception:
                pass
