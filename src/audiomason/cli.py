from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path
from typing import List, Optional

from .version import __version__


def _legacy_path() -> Path:
    return Path(__file__).resolve().parent / "_legacy" / "abook_import.py"


def _validate_legacy_file(p: Path) -> None:
    if not p.exists():
        raise SystemExit(f"[FATAL] legacy script not found: {p}")

    txt = p.read_text(encoding="utf-8", errors="replace")
    if txt.startswith("\ufeff"):
        txt = txt.lstrip("\ufeff")

    first = ""
    for ln in txt.splitlines():
        if ln.strip():
            first = ln.strip()
            break

    if not first:
        raise SystemExit(f"[FATAL] legacy script is empty: {p}")

    if (" $" in first and "@" in first) or first.startswith(("pi@", "root@", "macos:", "mholes@")):
        raise SystemExit(
            "[FATAL] legacy script starts with a shell prompt line.\n"
            f"File: {p}\n"
            f"First line: {first}\n"
            "Fix: remove the prompt/header lines so the file starts with Python code."
        )


def _parse_wrapper_args(argv: Optional[List[str]]) -> tuple[argparse.Namespace, list[str]]:
    ap = argparse.ArgumentParser(
        prog="audiomason",
        add_help=True,
        description="AudioMason wrapper (legacy runner during refactor).",
    )
    ap.add_argument("--version", action="store_true", help="show version and exit")
    ap.add_argument("--self-check", action="store_true", help="validate legacy script and exit (no IO)")
    ap.add_argument("--legacy-help", action="store_true", help="show legacy help and exit")
    ns, rest = ap.parse_known_args(argv)
    return ns, rest


def main(argv: Optional[List[str]] = None) -> int:
    ns, rest = _parse_wrapper_args(argv)

    legacy = _legacy_path()
    _validate_legacy_file(legacy)

    if ns.version:
        print(__version__)
        return 0

    if ns.self_check:
        print(f"OK: legacy script found and looks sane: {legacy}")
        return 0

    if ns.legacy_help:
        sys.argv = ["abook_import", "--help"]
        runpy.run_path(str(legacy), run_name="__main__")
        return 0

    # Forward args to legacy exactly (it uses argparse on sys.argv).
    sys.argv = ["abook_import"] + rest
    runpy.run_path(str(legacy), run_name="__main__")
    return 0
