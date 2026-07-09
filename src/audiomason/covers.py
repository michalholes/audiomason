from __future__ import annotations

import hashlib
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from mutagen.id3._util import ID3NoHeaderError

import audiomason.state as state
from audiomason.paths import COVER_NAME, get_cache_root
from audiomason.util import die, ensure_dir, is_url, out, prompt, run_cmd


def extract_embedded_cover_from_mp3(mp3: Path) -> tuple[bytes, str] | None:
    try:
        id3 = ID3(mp3)  # type: ignore[no-untyped-call]
    except ID3NoHeaderError:
        return None
    for tag in id3.values():  # type: ignore[no-untyped-call, misc]
        if isinstance(tag, APIC) and tag.data:  # type: ignore[attr-defined, misc]
            return tag.data, (tag.mime or "image/jpeg")  # type: ignore[attr-defined, misc]
    return None


def convert_image_to_jpg(src: Path, dst: Path) -> bytes:
    if not shutil.which("ffmpeg"):
        die("ffmpeg required for image conversion")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-frames:v",
        "1",
        "-update",
        "1",
        "-pix_fmt",
        "yuv420p",
        str(dst),
    ]
    if state.OPTS is not None and state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return b""
    run_cmd(cmd)
    return dst.read_bytes()


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _sniff_image_ext(data: bytes) -> tuple[str, str]:
    if len(data) >= 3 and data[0:3] == b"\xff\xd8\xff":
        return ("jpg", "image/jpeg")
    if len(data) >= 8 and data[0:8] == b"\x89PNG\r\n\x1a\n":
        return ("png", "image/png")
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("webp", "image/webp")
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"mif1"):
        return ("avif", "image/avif")
    return ("img", "application/octet-stream")


def download_url(url: str, outpath: Path) -> None:
    ensure_dir(outpath.parent)
    if state.OPTS is not None and state.OPTS.dry_run:
        out(f"[dry-run] would download: {url} -> {outpath}")
        return
    if shutil.which("curl"):
        run_cmd(["curl", "-fsSL", "-o", str(outpath), url], check=True)
        return
    if shutil.which("wget"):
        run_cmd(["wget", "-qO", str(outpath), url], check=True)
        return
    die("Need curl or wget to download URL covers")


def cover_from_input(cfg: Mapping[str, object], raw: str) -> Path | None:
    raw = raw.strip()
    if not raw:
        return None

    if is_url(raw):
        cache_root = get_cache_root(cfg)
        ensure_dir(cache_root)
        sha = _sha1(raw)
        for ext in ("jpg", "png", "webp", "img"):
            cand = cache_root / f"{sha}.{ext}"
            if cand.exists():
                out("[cover] using cached URL cover")
                return cand

        if state.OPTS is not None and state.OPTS.dry_run:
            if state.OPTS.debug:
                out("[cover][debug] dry-run: would download; mime=unknown ext=.img")
            return cache_root / f"{sha}.img"

        tmp = cache_root / f"{sha}.tmp"
        out("[cover] downloading URL cover...")
        download_url(raw, tmp)
        data = tmp.read_bytes()
        ext, mime = _sniff_image_ext(data)
        if state.OPTS is not None and state.OPTS.debug:
            out(f"[cover][debug] mime={mime} ext=.{ext}")
        outpath = cache_root / f"{sha}.{ext}"
        if outpath.exists():
            tmp.unlink(missing_ok=True)
            return outpath
        tmp.replace(outpath)
        return outpath

    p = Path(raw).expanduser()
    if p.exists() and p.is_file():
        return p

    out("[cover] invalid path/url")
    return None


def find_file_cover(stage_root: Path, group_root: Path) -> Path | None:
    for ext in [".avif", ".jpg", ".jpeg", ".png", ".webp"]:
        for cand in [group_root / f"cover{ext}", stage_root / f"cover{ext}"]:
            if cand.exists() and cand.is_file():
                return cand
    return None


def extract_cover_from_m4a(m4a: Path, bookdir: Path) -> tuple[bytes, str] | None:
    if not shutil.which("ffmpeg"):
        return None
    dst = bookdir / COVER_NAME
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(m4a),
        "-an",
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-update",
        "1",
        "-pix_fmt",
        "yuv420p",
        str(dst),
    ]
    if state.OPTS is not None and state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return None
    try:
        run_cmd(cmd)
        if dst.exists() and dst.stat().st_size > 0:
            out("[cover] extracted from m4a container")
            return dst.read_bytes(), "image/jpeg"
    except Exception:
        return None
    return None


def choose_cover(
    cfg: Mapping[str, object],
    mp3_first: Path | None,
    m4a_source: Path | None,
    bookdir: Path,
    stage_root: Path,
    group_root: Path,
    mode: str | None = None,
) -> tuple[bytes, str] | None:
    file_cover = find_file_cover(stage_root, group_root)
    embedded = extract_embedded_cover_from_mp3(mp3_first) if mp3_first else None

    if mode == "skip":
        out("[cover] skipped")
        return None
    if mode == "embedded":
        if embedded:
            data, mime = embedded
            if not (state.OPTS is not None and state.OPTS.dry_run):
                (bookdir / COVER_NAME).write_bytes(data)
            out("[cover] used embedded cover")
            return data, mime
        out("[cover] skipped")
        return None
    if mode == "file":
        if file_cover:
            dst = bookdir / COVER_NAME
            ext = file_cover.suffix.lower()
            if ext in {".jpg", ".jpeg"}:
                data = (
                    file_cover.read_bytes()
                    if not (state.OPTS is not None and state.OPTS.dry_run)
                    else b""
                )
                if not (state.OPTS is not None and state.OPTS.dry_run):
                    dst.write_bytes(data)
                out(f"[cover] used file cover: {file_cover.name}")
                return (data, "image/jpeg")
            if ext == ".png":
                data = (
                    file_cover.read_bytes()
                    if not (state.OPTS is not None and state.OPTS.dry_run)
                    else b""
                )
                if not (state.OPTS is not None and state.OPTS.dry_run):
                    dst.write_bytes(data)
                out(f"[cover] used file cover: {file_cover.name}")
                return (data, "image/png")
            data = convert_image_to_jpg(file_cover, dst)
            out(f"[cover] used file cover: {file_cover.name}")
            return data, "image/jpeg"
        if embedded:
            data, mime = embedded
            if not (state.OPTS is not None and state.OPTS.dry_run):
                (bookdir / COVER_NAME).write_bytes(data)
            out("[cover] used embedded cover")
            return data, mime
        out("[cover] skipped")
        return None

    if embedded and file_cover and not (state.OPTS is not None and state.OPTS.yes):
        out("Cover options found:")
        out("  1) embedded cover from audio")
        out(f"  2) {file_cover.name} (preferred)")
        try:
            prompts = cast(Mapping[str, object], cfg.get("prompts", {}))
            dis = cast(list[object], prompts.get("disable", []))
            if dis == ["*"] or "choose_cover" in (cast(list[str], dis) if dis else []):
                ans = "2"
            else:
                ans = prompt("Choose cover [1/2]", "2").strip()
        except KeyboardInterrupt:
            out("\n[cover] skipped")
            return None
        if ans == "1":
            data, mime = embedded
            if not (state.OPTS is not None and state.OPTS.dry_run):
                (bookdir / COVER_NAME).write_bytes(data)
            out("[cover] used embedded cover")
            return data, mime

    if file_cover:
        dst = bookdir / COVER_NAME
        ext = file_cover.suffix.lower()
        if ext in {".jpg", ".jpeg"}:
            data = (
                file_cover.read_bytes()
                if not (state.OPTS is not None and state.OPTS.dry_run)
                else b""
            )
            if not (state.OPTS is not None and state.OPTS.dry_run):
                dst.write_bytes(data)
            out(f"[cover] used {file_cover.name}")
            return data, "image/jpeg"
        data = convert_image_to_jpg(file_cover, dst)
        out(f"[cover] used {file_cover.name}")
        return data, "image/jpeg"

    if embedded:
        data, mime = embedded
        if not (state.OPTS is not None and state.OPTS.dry_run):
            (bookdir / COVER_NAME).write_bytes(data)
        out("[cover] used embedded cover")
        return data, mime

    if m4a_source:
        got = extract_cover_from_m4a(m4a_source, bookdir)
        if got:
            return got

    prompts = cast(Mapping[str, object], cfg.get("prompts", {}))
    dis = cast(list[object], prompts.get("disable", []))
    if dis == ["*"] or "cover_input" in (cast(list[str], dis) if dis else []):
        raw = ""
    else:
        raw = prompt("No cover found. Path or URL to image (Enter=skip)", "")
    if not raw:
        return None

    img = cover_from_input(cfg, raw)
    if img is None:
        return None

    dst = bookdir / COVER_NAME
    ext = img.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        data = img.read_bytes() if not (state.OPTS is not None and state.OPTS.dry_run) else b""
        if not (state.OPTS is not None and state.OPTS.dry_run):
            dst.write_bytes(data)
        out("[cover] saved cover.jpg")
        return data, "image/jpeg"

    data = convert_image_to_jpg(img, dst)
    out("[cover] saved cover.jpg")
    return data, "image/jpeg"
