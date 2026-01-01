from __future__ import annotations

DEBUG = False
VERBOSE = False
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Opts:
    yes: bool
    dry_run: bool
    quiet: bool
    publish: Optional[bool]          # None => ask unless --yes, else True/False
    wipe_id3: Optional[bool]         # None => ask unless --yes, else True/False
    loudnorm: bool
    q_a: str
    verify: bool
    verify_root: Path
    lookup: bool
    cleanup_stage: bool
    split_chapters: bool
    ff_loglevel: str                 # warning | error | info
    cpu_cores: int | None


    json: bool
# During refactor we keep global state for compatibility with legacy code.
OPTS: Opts | None = None
