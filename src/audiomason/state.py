from __future__ import annotations

from audiomason.version import __version__ as APP_VERSION

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
    clean_inbox_mode: str            # ask | yes | no
    split_chapters: bool
    ff_loglevel: str                 # warning | error | info
    cpu_cores: int | None


    json: bool
# During refactor we keep global state for compatibility with legacy code.
OPTS: Opts | None = None
