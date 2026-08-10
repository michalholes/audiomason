from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import audiomason.state as state
from audiomason.async_proc import run_cmd_async
from audiomason.concurrency import async_ffmpeg_slot
from audiomason.util import die, ensure_dir, out


async def ffprobe_json_async(path: Path) -> dict[str, object]:
    if not shutil.which("ffprobe"):
        die("ffprobe not found (install ffmpeg package)")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        str(path),
    ]
    if state.OPTS is not None and state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return {}
    async with async_ffmpeg_slot():
        p = await run_cmd_async(cmd, check=True, capture_stdout=True)
    raw = p.stdout or b"{}"
    return cast(dict[str, object], json.loads(raw.decode("utf-8", errors="replace")))


async def m4a_chapters_async(path: Path) -> list[dict[str, object]]:
    data = await ffprobe_json_async(path)
    ch_raw = data.get("chapters")
    ch: list[dict[str, object]] = (
        cast(list[dict[str, object]], ch_raw) if isinstance(ch_raw, list) else []
    )
    out(f"[chapters] {path.name}: {len(ch)} chapter(s)")
    return ch


def _ffmpeg_common_input() -> list[str]:
    import os

    cores: int = os.cpu_count() or 1
    if state.OPTS is not None and state.OPTS.cpu_cores is not None:
        cores = state.OPTS.cpu_cores
    threads = min(2, max(1, cores // 2))
    loglevel = "warning"
    if state.OPTS is not None:
        loglevel = state.OPTS.ff_loglevel
    return [
        "-hide_banner",
        "-nostdin",
        "-stats",
        "-loglevel",
        loglevel,
        "-threads",
        str(threads),
    ]


async def opus_to_mp3_single_async(src: Path, dst: Path) -> None:
    if not shutil.which("ffmpeg"):
        die("ffmpeg not installed")
    if state.OPTS is None:
        return
    cmd = ["ffmpeg"] + _ffmpeg_common_input() + ["-y", "-i", str(src), "-vn"]
    if state.OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += ["-codec:a", "libmp3lame", "-q:a", state.OPTS.q_a, str(dst)]
    if state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return
    async with async_ffmpeg_slot():
        await run_cmd_async(cmd, check=True)


async def m4a_to_mp3_single_async(src: Path, dst: Path) -> None:
    if not shutil.which("ffmpeg"):
        die("ffmpeg not installed")
    if state.OPTS is None:
        return
    cmd = ["ffmpeg"] + _ffmpeg_common_input() + ["-y", "-i", str(src), "-vn"]
    if state.OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += ["-codec:a", "libmp3lame", "-q:a", state.OPTS.q_a, str(dst)]
    if state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return
    async with async_ffmpeg_slot():
        await run_cmd_async(cmd, check=True)


async def m4a_split_by_chapters_async(src: Path, outdir: Path) -> list[Path]:
    ch = await m4a_chapters_async(src)
    if not ch or len(ch) < 2:
        return []

    times: list[tuple[float, float]] = []
    for c in ch:
        try:
            st = float(str(c["start_time"]))
            et = float(str(c["end_time"]))
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

    split_points: list[float] = []
    for e in ends[:-1]:
        t = e - start0
        if t <= 0:
            return []
        split_points.append(t)

    ensure_dir(outdir)
    out(f"[split] splitting by chapters: {len(times)} tracks (single-pass)")

    if state.OPTS is None:
        return []

    dst_pat = outdir / "%02d.mp3"
    cmd = (
        ["ffmpeg"]
        + _ffmpeg_common_input()
        + [
            "-y",
            "-ss",
            str(start0),
            "-i",
            str(src),
            "-vn",
            "-t",
            str(total),
            "-map",
            "0:a:0",
        ]
    )
    if state.OPTS.loudnorm:
        cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"]
    cmd += [
        "-codec:a",
        "libmp3lame",
        "-q:a",
        state.OPTS.q_a,
        "-f",
        "segment",
        "-segment_times",
        ",".join(str(x) for x in split_points),
        "-segment_start_number",
        "1",
        "-reset_timestamps",
        "1",
        str(dst_pat),
    ]

    produced = [outdir / f"{i:02d}.mp3" for i in range(1, len(times) + 1)]

    if state.OPTS.dry_run:
        out("[dry-run] " + " ".join(cmd))
        return produced

    async with async_ffmpeg_slot():
        await run_cmd_async(cmd, check=True)
    return [p for p in produced if p.exists() and p.stat().st_size > 0]


def _sort_key(p: Path) -> str:
    return p.as_posix().lower()


def _sorted_audio_files(stage: Path, ext: str, recursive: bool) -> list[Path]:
    pattern = f"*.{ext}"
    files = list(stage.rglob(pattern)) if recursive else list(stage.glob(pattern))
    return sorted(files, key=_sort_key)


async def convert_opus_in_place_async(stage: Path, recursive: bool = True) -> None:
    opuses = _sorted_audio_files(stage, "opus", recursive)
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
        await opus_to_mp3_single_async(src, dst)


async def convert_m4a_in_place_async(stage: Path, recursive: bool = True) -> None:
    m4as = _sorted_audio_files(stage, "m4a", recursive)
    if not m4as:
        return

    out(f"[convert] found {len(m4as)} m4a")

    for idx, src in enumerate(m4as, 1):
        out(f"[convert] {idx}/{len(m4as)} {src.name}")

        if state.OPTS is not None and state.OPTS.split_chapters:
            produced = await m4a_split_by_chapters_async(src, src.parent)
            if produced:
                out(f"[convert] split produced {len(produced)} mp3")
                continue

        dst = src.with_suffix(".mp3")
        out("[convert] no chapters split -> single mp3")
        await m4a_to_mp3_single_async(src, dst)
