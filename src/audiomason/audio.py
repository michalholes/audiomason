from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import audiomason.state as state
from audiomason.util import out, die, ensure_dir


def ffprobe_json(path: Path) -> dict:
    if not shutil.which("ffprobe"):
        die("ffprobe not found (install ffmpeg package)")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        str(path),
    ]
    if state.OPTS and state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return {}
    p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    return json.loads(p.stdout.decode("utf-8", errors="ignore") or "{}")


def m4a_chapters(path: Path) -> list[dict]:
    data = ffprobe_json(path)
    ch = data.get("chapters") or []
    out(f"[chapters] {path.name}: {len(ch)} chapter(s)")
    return ch


def ffmpeg_common_input() -> list[str]:
    return ["-hide_banner", "-nostdin", "-stats", "-loglevel", state.OPTS.ff_loglevel]


def m4a_to_mp3_single(src: Path, dst: Path) -> None:
    if not shutil.which("ffmpeg"):
        die("ffmpeg not installed")
    cmd = ["ffmpeg"] + ffmpeg_common_input() + ["-y", "-i", str(src), "-vn"]
    if state.OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += ["-codec:a", "libmp3lame", "-q:a", state.OPTS.q_a, str(dst)]
    if state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def m4a_split_by_chapters(src: Path, outdir: Path) -> list[Path]:
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

        dst = outdir / f"{i:02d}.mp3"
        out(f"[split] {i}/{len(ch)} {start} -> {end} -> {dst.name}")

        cmd = ["ffmpeg"] + ffmpeg_common_input() + [
            "-y",
            "-i", str(src),
            "-vn",
            "-ss", str(start),
            "-to", str(end),
        ]
        if state.OPTS.loudnorm:
            cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
        cmd += ["-codec:a", "libmp3lame", "-q:a", state.OPTS.q_a, str(dst)]

        if state.OPTS.dry_run:
            out("[dry-run] " + " ".join(cmd))
        else:
            subprocess.run(cmd, check=True)

        produced.append(dst)

    if not state.OPTS.dry_run:
        produced = [p for p in produced if p.exists() and p.stat().st_size > 0]
    return produced


def convert_m4a_in_place(stage: Path, recursive: bool = True) -> None:
    m4as = sorted((stage.rglob("*.m4a") if recursive else stage.glob("*.m4a")), key=lambda p: p.as_posix().lower())
    if not m4as:
        return

    out(f"[convert] found {len(m4as)} m4a")

    for idx, src in enumerate(m4as, 1):
        out(f"[convert] {idx}/{len(m4as)} {src.name}")

        if state.OPTS.split_chapters:
            produced = m4a_split_by_chapters(src, src.parent)
            if produced:
                out(f"[convert] split produced {len(produced)} mp3")
                continue

        dst = src.with_suffix(".mp3")
        out("[convert] no chapters split -> single mp3")
        m4a_to_mp3_single(src, dst)
