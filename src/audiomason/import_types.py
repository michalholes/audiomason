from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class BookGroup:
    label: str
    group_root: Path  # directory containing audio (non-recursive)
    stage_root: Path  # stage src root
    rel_path: Path = field(default_factory=lambda: Path("."))
    m4a_hint: Optional[Path] = None
