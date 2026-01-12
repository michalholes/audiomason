from __future__ import annotations

from pathlib import Path
from typing import Iterable

from audiomason.import_types import BookGroup


def list_sources(inbox: Path) -> list[Path]:
    # Pure filesystem listing, deterministic order
    return sorted(p for p in inbox.iterdir() if p.is_dir())


def choose_sources_by_indices(
    sources: list[Path],
    indices: Iterable[int],
) -> list[Path]:
    max_n = len(sources)
    picked: list[Path] = []
    for i in indices:
        if i < 1 or i > max_n:
            raise ValueError(f"index out of range: {i}")
        picked.append(sources[i - 1])
    return picked


def build_book_groups(
    label: str,
    roots: list[Path],
    stage_root: Path,
) -> list[BookGroup]:
    groups: list[BookGroup] = []
    for root in roots:
        groups.append(
            BookGroup(
                label=label,
                group_root=root,
                stage_root=stage_root,
            )
        )
    return groups
