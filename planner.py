from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .normalize import ascii_text, to_surname_dot_name, looks_like_author_dir

AUDIO_EXTS = {".mp3", ".m4a"}


@dataclass(frozen=True)
class BookCandidate:
    root: Path
    kind: str                  # "dir" | "file"
    audio: list[Path]
    cover_candidates: list[Path]
    sidecars: list[Path]
    suggest_author: str
    suggest_title: str
    notes: list[str]


def find_audio_leaf_dirs(src_root: Path) -> list[Path]:
    # A directory is a leaf if it contains audio files directly and none of its subdirs does.
    dirs_with_audio = []
    for d in sorted([p for p in src_root.rglob("*") if p.is_dir()], key=lambda p: p.as_posix().lower()):
        if any(f.is_file() and f.suffix.lower() in AUDIO_EXTS for f in d.iterdir()):
            dirs_with_audio.append(d)

    direct = set(dirs_with_audio)
    leaf = []
    for d in dirs_with_audio:
        has_child = False
        for c in d.rglob("*"):
            if c.is_dir() and c != d and c in direct:
                has_child = True
                break
        if not has_child:
            leaf.append(d)

    return sorted(leaf, key=lambda p: p.as_posix().lower())


def _cover_candidates(d: Path, allow_guess_single_image: bool) -> list[Path]:
    cands = []
    for name in ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp"):
        p = d / name
        if p.exists() and p.is_file():
            cands.append(p)

    if cands:
        return cands

    if allow_guess_single_image:
        imgs = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        imgs = [p for p in imgs if not p.name.lower().startswith("lic")]
        if len(imgs) == 1:
            return imgs

    return []


def _sidecars(d: Path) -> list[Path]:
    keep = []
    for p in d.iterdir():
        if p.is_file() and p.suffix.lower() in {".nfo", ".m3u", ".jpg", ".jpeg", ".png", ".webp"}:
            keep.append(p)
    return sorted(keep, key=lambda p: p.as_posix().lower())


def _cleanup_title(t: str) -> str:
    t = ascii_text(t)
    t = re.sub(r"\(\s*\d{4}\s*\)", "", t)
    t = re.sub(r"\b(CZ|SK|EN)\b", "", t, flags=re.I)
    t = re.sub(r"\baudiokniha\b", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -_")
    return t or "Unknown"


def suggest_author_title_from_name(name: str) -> tuple[str, str]:
    raw = ascii_text(name)

    # "Author - Title"
    m = re.split(r"\s[-–—]\s", raw, maxsplit=1)
    if len(m) == 2:
        a_raw, t_raw = m[0], m[1]
        author = to_surname_dot_name(a_raw) or ""
        title = _cleanup_title(t_raw)
        return author, title

    # "Firstname Lastname Title..."
    toks = raw.split()
    if len(toks) >= 3:
        maybe = " ".join(toks[:2])
        author = to_surname_dot_name(maybe)
        if author:
            title = _cleanup_title(" ".join(toks[2:]))
            return author, title

    return "", _cleanup_title(raw)


def build_candidates(stage_src: Path, allow_guess_single_image: bool = True) -> list[BookCandidate]:
    author_from_root = stage_src.name if looks_like_author_dir(stage_src.name) else ""

    cands: list[BookCandidate] = []

    # Leaf dirs containing audio directly
    for d in find_audio_leaf_dirs(stage_src):
        audio = sorted(
            [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTS],
            key=lambda p: p.as_posix().lower(),
        )
        sug_a, sug_t = suggest_author_title_from_name(d.name)
        if author_from_root:
            sug_a = author_from_root

        notes = []
        # multi-disc hint: filenames like 1-01,2-01...
        if any(re.match(r"^\d+\s*[-_]\s*\d+", f.stem) for f in audio if f.suffix.lower() == ".mp3"):
            notes.append("multi_disc_filenames_detected")

        cands.append(
            BookCandidate(
                root=d,
                kind="dir",
                audio=audio,
                cover_candidates=_cover_candidates(d, allow_guess_single_image=allow_guess_single_image),
                sidecars=_sidecars(d),
                suggest_author=sug_a,
                suggest_title=sug_t,
                notes=notes,
            )
        )

    # Standalone audio files in stage/src (e.g. .m4a in root)
    for f in sorted(
        [p for p in stage_src.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS],
        key=lambda p: p.as_posix().lower(),
    ):
        sug_a, sug_t = suggest_author_title_from_name(f.stem)
        if author_from_root:
            sug_a = author_from_root

        cands.append(
            BookCandidate(
                root=f,
                kind="file",
                audio=[f],
                cover_candidates=[],
                sidecars=[],
                suggest_author=sug_a,
                suggest_title=sug_t,
                notes=["standalone_audio_file"],
            )
        )

    return sorted(cands, key=lambda c: c.root.as_posix().lower())
