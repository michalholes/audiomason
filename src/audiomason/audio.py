from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import audiomason.state as state
from audiomason.util import run_cmd, out, die, ensure_dir


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
    p = run_cmd(cmd, check=True, stdout=subprocess.PIPE)
    return json.loads(p.stdout.decode("utf-8", errors="ignore") or "{}")


def m4a_chapters(path: Path) -> list[dict]:
    data = ffprobe_json(path)
    ch = data.get("chapters") or []
    out(f"[chapters] {path.name}: {len(ch)} chapter(s)")
    return ch


def ffmpeg_common_input() -> list[str]:
    import os
    cores = getattr(state.OPTS, "cpu_cores", None) or os.cpu_count() or 1
    # Deterministic conservative default (RPi-safe)
    threads = min(2, max(1, int(cores) // 2))
    return ["-hide_banner", "-nostdin", "-stats", "-loglevel", state.OPTS.ff_loglevel, "-threads", str(threads)]


def opus_to_mp3_single(src: Path, dst: Path) -> None:
    if not shutil.which("ffmpeg"):
        die("ffmpeg not installed")
    cmd = ["ffmpeg"] + ffmpeg_common_input() + ["-y", "-i", str(src), "-vn"]
    if state.OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += ["-codec:a", "libmp3lame", "-q:a", state.OPTS.q_a, str(dst)]
    if state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return
    run_cmd(cmd, check=True)


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
    run_cmd(cmd, check=True)


def m4a_split_by_chapters(src: Path, outdir: Path) -> list[Path]:
    ch = m4a_chapters(src)
    if not ch or len(ch) < 2:
        return []

    times: list[tuple[float, float]] = []
    for c in ch:
        try:
            st = float(c["start_time"])
            et = float(c["end_time"])
        except Exception:
            return []
        if et <= st:
            return []
        times.append((st, et))

    for i in range(1, len(times)):
        if times[i][0] < times[i - 1][1]:
            return []

    start0 = times[0][0]
    ends = [et for _, et in times]
    total = ends[-1] - start0
    if total <= 0:
        return []

    split_points = []
    for e in ends[:-1]:
        t = e - start0
        if t <= 0:
            return []
        split_points.append(t)

    ensure_dir(outdir)
    out(f"[split] splitting by chapters: {len(times)} tracks (single-pass)")

    dst_pat = outdir / "%02d.mp3"
    cmd = ["ffmpeg"] + ffmpeg_common_input() + [
        "-y",
        "-ss", str(start0),
        "-i", str(src),
        "-vn",
        "-t", str(total),
        "-map", "0:a:0",
    ]
    if state.OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += [
        "-codec:a", "libmp3lame",
        "-q:a", state.OPTS.q_a,
        "-f", "segment",
        "-segment_times", ",".join(str(x) for x in split_points),
        "-segment_start_number", "1",
        "-reset_timestamps", "1",
        str(dst_pat),
    ]

    produced = [outdir / f"{i:02d}.mp3" for i in range(1, len(times) + 1)]

    if state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return produced

    run_cmd(cmd, check=True)
    return [p for p in produced if p.exists() and p.stat().st_size > 0]


def convert_opus_in_place(stage: Path, recursive: bool = True) -> None:
    opuses = sorted((stage.rglob("*.opus") if recursive else stage.glob("*.opus")), key=lambda p: p.as_posix().lower())
    if not opuses:
        return

    out(f"[convert] found {len(opuses)} opus")

    for idx, src in enumerate(opuses, 1):
        out(f"[convert] {idx}/{len(opuses)} {src.name}")

        dst = src.with_suffix(".mp3")
        if dst.exists() and dst.stat().st_size > 0:
            out(f"[convert] skip (mp3 exists): {dst.name}")
            continue

        out("[convert] opus -> mp3")
        opus_to_mp3_single(src, dst)


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
