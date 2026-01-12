#!/usr/bin/env python3
"""Governance Version Sync Script

Scans docs/governance/*.md and reads the canonical Version line from the document
header only (first HEADER_SCAN_LINES lines), intentionally ignoring any example
snippets later in the file (e.g. "Version: vX.Y" shown in docs).

Recognized version lines (case-insensitive; optional leading '#'):
  Version: <value>
  # VERSION: <value>

Capabilities:
- --list: print a table file -> version (or MISSING)
- --check: validate presence, and optionally lockstep consistency
- --set-version X.Y: set Version: line in all governance docs (write mode)
- --dry-run: for --set-version, show what would change without writing
- --mode lockstep (default lockstep; independent mode is not supported by governance)

Exit codes:
- 0 success
- 2 validation error (missing/ambiguous version, inconsistent versions, bad args)
- 3 filesystem error (unexpected IO)

Design goals:
- deterministic ordering (sorted paths)
- fail-fast with explicit errors
- minimal, local-only (no network)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

VERSION_RE = re.compile(
    r"^(?P<prefix>\s*(?:#\s*)?)version\s*:\s*(?P<val>\S+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

VERSION_VALUE_RE = re.compile(r"^v?\d+\.\d+$")

# Only scan the document header to avoid matching examples in body text.
HEADER_SCAN_LINES = 60


@dataclass(frozen=True)
class DocVersion:
    path: Path
    version: Optional[str]  # None if missing


class GovVersionError(Exception):
    pass


def governance_dir(repo_root: Path) -> Path:
    return repo_root / "docs" / "governance"


def list_governance_files(repo_root: Path) -> List[Path]:
    gdir = governance_dir(repo_root)
    if not gdir.is_dir():
        raise GovVersionError(f"governance directory not found: {gdir}")
    files = sorted(p for p in gdir.glob("*.md") if p.is_file())
    if not files:
        raise GovVersionError(f"no .md files found in: {gdir}")
    return files


def read_version_line(text: str) -> Tuple[Optional[str], int]:
    header = "\n".join(text.splitlines()[:HEADER_SCAN_LINES])
    matches = [m for m in VERSION_RE.finditer(header)]
    if not matches:
        return (None, 0)
    if len(matches) > 1:
        return (matches[0].group("val"), len(matches))
    return (matches[0].group("val"), 1)


def load_versions(repo_root: Path) -> List[DocVersion]:
    out: List[DocVersion] = []
    for p in list_governance_files(repo_root):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            raise GovVersionError(f"failed to read {p}: {e}") from e
        ver, count = read_version_line(text)
        if count > 1:
            raise GovVersionError(f"ambiguous Version: line (multiple matches in header) in {p}")
        out.append(DocVersion(path=p, version=ver))
    return out


def validate(versions: List[DocVersion], mode: str) -> None:
    # Governance requires lockstep. Accepted Version formats (per tests): X.Y or vX.Y

    if mode != "lockstep":
        raise GovVersionError("invalid mode: governance requires lockstep")

    missing = [dv.path for dv in versions if dv.version is None]
    if missing:
        msg = "missing Version: in: " + ", ".join(str(p) for p in missing)
        raise GovVersionError(msg)

    invalid = [dv for dv in versions if not VERSION_VALUE_RE.match(dv.version)]
    if invalid:
        pairs = ", ".join(f"{dv.path.name}={dv.version}" for dv in invalid)
        raise GovVersionError(f"invalid Version: format (expected X.Y or vX.Y): {pairs}")

    uniq = sorted({dv.version for dv in versions})
    if len(uniq) != 1:
        pairs = ", ".join(f"{dv.path.name}={dv.version}" for dv in versions)
        raise GovVersionError(f"inconsistent versions (lockstep): {pairs}")


def format_table(rows: List[Tuple[str, str]]) -> str:
    col1 = max(len(r[0]) for r in rows) if rows else 4
    lines: List[str] = []
    lines.append(f"{'FILE'.ljust(col1)}  VERSION")
    lines.append(f"{'-' * col1}  -------")
    for f, v in rows:
        lines.append(f"{f.ljust(col1)}  {v}")
    return "\n".join(lines)


def cmd_list(repo_root: Path, versions: List[DocVersion]) -> int:
    gdir = governance_dir(repo_root)
    rows: List[Tuple[str, str]] = []
    for dv in versions:
        rel = str(dv.path.relative_to(gdir))
        rows.append((rel, dv.version if dv.version is not None else "MISSING"))
    print(format_table(rows))
    print(f"Found governance documents: {len(rows)}")
    return 0


def set_version(repo_root: Path, new_version: str, dry_run: bool) -> int:
    # Ensure --set-version accepts exactly the same formats as --check.
    if not VERSION_VALUE_RE.match(new_version):
        raise GovVersionError(f"invalid Version: format (expected X.Y or vX.Y): {new_version}")

    files = list_governance_files(repo_root)
    gdir = governance_dir(repo_root)
    planned: List[Tuple[Path, str, str]] = []

    for p in files:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            raise GovVersionError(f"failed to read {p}: {e}") from e

        header = "\n".join(text.splitlines()[:HEADER_SCAN_LINES])
        matches = list(VERSION_RE.finditer(header))

        if not matches:
            raise GovVersionError(f"cannot set version; missing Version: in {p}")
        if len(matches) != 1:
            raise GovVersionError(f"cannot set version; ambiguous (multiple Version: lines in header) in {p}")

        m = matches[0]
        old_val = m.group("val")
        new_line = f"{m.group('prefix')}Version: {new_version}"
        new_text = VERSION_RE.sub(new_line, text, count=1)
        planned.append((p, old_val, new_version))

        if not dry_run:
            try:
                p.write_text(new_text, encoding="utf-8")
            except OSError as e:
                raise GovVersionError(f"failed to write {p}: {e}") from e

    rows = [(str(p.relative_to(gdir)), f"{old} -> {new}") for p, old, new in planned]
    print(format_table(rows))
    print(f"Found governance documents: {len(rows)}")
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="gov_versions.py", add_help=True)
    ap.add_argument("--mode", choices=["lockstep"], default="lockstep")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set-version", dest="set_version", metavar="X.Y|vX.Y")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-root", default=None)

    ns = ap.parse_args(argv)

    if not (ns.list or ns.check or ns.set_version):
        ap.error("must specify at least one of --list, --check, or --set-version")

    if ns.dry_run and not ns.set_version:
        ap.error("--dry-run requires --set-version")

    return ns


def autodetect_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "pyproject.toml").is_file():
            return p
    raise GovVersionError("could not auto-detect repo root (pyproject.toml not found)")


def run(argv: List[str]) -> int:
    try:
        ns = parse_args(argv)
        repo_root = Path(ns.repo_root).resolve() if ns.repo_root else autodetect_repo_root(Path.cwd())

        if ns.set_version:
            set_version(repo_root, ns.set_version, ns.dry_run)

        versions = load_versions(repo_root)

        if ns.list:
            cmd_list(repo_root, versions)

        if ns.check:
            validate(versions, ns.mode)
            print("OK")

        return 0
    except GovVersionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
