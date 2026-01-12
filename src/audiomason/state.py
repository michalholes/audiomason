from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEBUG = False
VERBOSE = False


@dataclass
class Opts:
    yes: bool = False
    dry_run: bool = False
    config: object | None = None
    quiet: bool = False
    publish: Optional[bool] = None  # None => ask unless --yes, else True/False
    wipe_id3: Optional[bool] = None  # None => ask unless --yes, else True/False
    source_prefix: object | None = None
    loudnorm: bool = False
    q_a: str = "2"
    verify: bool = False
    verify_root: Path = Path(".")
    lookup: bool = False
    cleanup_stage: bool = False
    clean_inbox_mode: str = "ask"  # ask | yes | no
    split_chapters: bool = True
    ff_loglevel: str = "warning"  # warning | error | info
    cpu_cores: int | None = None

    debug: bool = False

    json: bool = False


# During refactor we keep global state for compatibility with legacy code.

# During refactor we keep global state for compatibility with legacy code.
OPTS: Opts | None = None
