from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional, Tuple, Protocol, cast

from mutagen.id3 import APIC, ID3, ID3NoHeaderError

import audiomason.state as state
from audiomason.paths import COVER_NAME, get_cache_root
from audiomason.util import die, ensure_dir, is_url, out, prompt, run_cmd


def _dry_run() -> bool:
    return bool(state.OPTS and getattr(state.OPTS, "dry_run", False))


def _yes() -> bool:
    return bool(state.OPTS and getattr(state.OPTS, "yes", False))


def _debug() -> bool:
    return bool(state.OPTS and getattr(state.OPTS, "debug", False))


class APICLike(Protocol):
    data: bytes
    mime: str


def _write_bytes(path: Path, data: bytes) -> None:
    if _dry_run():
        return
    path.write_bytes(data)


def _read_bytes_or_empty(path: Path) -> bytes:
    return b"" if _dry_run() else path.read_bytes()


def extract_embedded_cover_from_mp3(mp3: Path) -> Optional[Tuple[bytes, str]]:
    try:
        id3 = ID3(mp3)
    except ID3NoHeaderError:
        return None

    for tag in id3.values():
        if isinstance(tag, APIC) and getattr(tag, "data", None):
            apic = cast(APICLike, tag)
            return apic.data, (apic.mime or "image/jpeg")

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

    if _dry_run():
        out("[dry-run] " + " ".join(cmd))
        return b""

    run_cmd(cmd)
    return dst.read_bytes()


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _sniff_image_ext(data: bytes) -> tuple[str, str]:
    # Detect image type from magic bytes (no external deps)
    if len(data) >= 3 and data[0:3] == b"\xFF\xD8\xFF":
        return ("jpg", "image/jpeg")
    if len(data) >= 8 and data[0:8] == b"\x89PNG\r\n\x1a\n":
        return ("png", "image/png")
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("webp", "image/webp")
    return ("img", "application/octet-stream")


def download_url(url: str, outpath: Path) -> None:
    ensure_dir(outpath.parent)

    if _dry_run():
        out(f"[dry-run] would download: {url} -> {outpath}")
        return

    if shutil.which("curl"):
        run_cmd(["curl", "-fsSL", "-o", str(outpath), url], check=True)
        return
    if shutil.which("wget"):
        run_cmd(["wget", "-qO", str(outpath), url], check=True)
        return

    die("Need curl or wget to download URL covers")


def cover_from_input(cfg: dict, raw: str) -> Optional[Path]:
    raw = raw.strip()
    if not raw:
        return None

    if is_url(raw):
        cache_root = get_cache_root(cfg)
        ensure_dir(cache_root)
        sha = _sha1(raw)

        # Scan for existing cached variants
        for ext in ("jpg", "png", "webp", "img"):
            cand = cache_root / f"{sha}.{ext}"
            if cand.exists():
                out("[cover] using cached URL cover")
                return cand

        # Respect --dry-run (no writes)
        if _dry_run():
            if _debug():
                out("[cover][debug] dry-run: would download; mime=unknown ext=.img")
            return cache_root / f"{sha}.img"

        tmp = cache_root / f"{sha}.tmp"
        out("[cover] downloading URL cover...")
        download_url(raw, tmp)

        data = tmp.read_bytes()
        ext, mime = _sniff_image_ext(data)
        if _debug():
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


def find_file_cover(stage_root: Path, group_root: Path) -> Optional[Path]:
    for ext in [".avif", ".jpg", ".jpeg", ".png", ".webp"]:
        for cand in [group_root / f"cover{ext}", stage_root / f"cover{ext}"]:
            if cand.exists() and cand.is_file():
                return cand
    return None


def extract_cover_from_m4a(m4a: Path, bookdir: Path) -> Optional[Tuple[bytes, str]]:
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

    if _dry_run():
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


def _covers_prompts_disabled(cfg: dict, key: str) -> bool:
    dis = (cfg.get("prompts", {}) or {}).get("disable", [])
    return dis == ["*"] or key in (dis or [])


def _maybe_prompt(cfg: dict, key: str, message: str, default: str) -> str:
    if _covers_prompts_disabled(cfg, key):
        return default
    return prompt(message, default)


def _use_embedded_cover(bookdir: Path, embedded: Tuple[bytes, str]) -> Tuple[bytes, str]:
    data, mime = embedded
    _write_bytes(bookdir / COVER_NAME, data)
    out("[cover] used embedded cover")
    return data, mime


def _use_file_cover_jpeg_or_png(bookdir: Path, file_cover: Path) -> Optional[Tuple[bytes, str]]:
    # For mode='file' we only accept JPEG/PNG as-is (no conversion).
    ext = file_cover.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        data = _read_bytes_or_empty(file_cover)
        _write_bytes(bookdir / COVER_NAME, data)
        return data, "image/jpeg"
    if ext == ".png":
        data = _read_bytes_or_empty(file_cover)
        _write_bytes(bookdir / COVER_NAME, data)
        return data, "image/png"
    return None


def _use_file_cover_default_path(bookdir: Path, file_cover: Path) -> Tuple[bytes, str]:
    # Legacy/default path: JPEG is used as-is; everything else is converted to JPEG.
    dst = bookdir / COVER_NAME
    ext = file_cover.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        data = _read_bytes_or_empty(file_cover)
        _write_bytes(dst, data)
        return data, "image/jpeg"
    data = convert_image_to_jpg(file_cover, dst)
    return data, "image/jpeg"


def choose_cover(
    cfg: dict,
    mp3_first: Optional[Path],
    m4a_source: Optional[Path],
    bookdir: Path,
    stage_root: Path,
    group_root: Path,
    mode: Optional[str] = None,  # 'file' | 'embedded' | 'skip' | None
) -> Optional[Tuple[bytes, str]]:
    file_cover = find_file_cover(stage_root, group_root)
    embedded = extract_embedded_cover_from_mp3(mp3_first) if mp3_first else None

    # ISSUE #12: allow preflight to force cover choice (no prompts during processing)
    if mode == "skip":
        out("[cover] skipped")
        return None

    if mode == "embedded":
        if embedded:
            return _use_embedded_cover(bookdir, embedded)
        out("[cover] skipped")
        return None

    if mode == "file":
        if file_cover:
            got = _use_file_cover_jpeg_or_png(bookdir, file_cover)
            if got:
                out(f"[cover] used file cover: {file_cover.name}")
                return got
        # fallback
        if embedded:
            return _use_embedded_cover(bookdir, embedded)
        out("[cover] skipped")
        return None

    # interactive/default path (legacy behavior)
    if embedded and file_cover and not _yes():
        out("Cover options found:")
        out("  1) embedded cover from audio")
        out(f"  2) {file_cover.name} (preferred)")
        try:
            ans = _maybe_prompt(cfg, "choose_cover", "Choose cover [1/2]", "2").strip()
        except KeyboardInterrupt:
            out("\n[cover] skipped")
            return None
        if ans == "1":
            return _use_embedded_cover(bookdir, embedded)

    if file_cover:
        data, _mime = _use_file_cover_default_path(bookdir, file_cover)
        out(f"[cover] used {file_cover.name}")
        return data, "image/jpeg"

    if embedded:
        return _use_embedded_cover(bookdir, embedded)

    if m4a_source:
        got = extract_cover_from_m4a(m4a_source, bookdir)
        if got:
            return got

    raw = ""
    if not _covers_prompts_disabled(cfg, "cover_input"):
        raw = prompt("No cover found. Path or URL to image (Enter=skip)", "")
    if not raw:
        return None

    img = cover_from_input(cfg, raw)
    if img is None:
        return None

    dst = bookdir / COVER_NAME
    ext = img.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        data = _read_bytes_or_empty(img)
        _write_bytes(dst, data)
        out("[cover] saved cover.jpg")
        return data, "image/jpeg"

    data = convert_image_to_jpg(img, dst)
    out("[cover] saved cover.jpg")
    return data, "image/jpeg"
