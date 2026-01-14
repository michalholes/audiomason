#!/usr/bin/env python3
"""Standalone helper: sync GitHub issues into deterministic markdown archives.

Hard constraints:
- NOT part of AudioMason runtime/CLI
- NO imports from audiomason
- Non-interactive
- Deterministic + idempotent
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_OPEN = ROOT / "docs/issues/open_issues.md"
OUT_CLOSED = ROOT / "docs/issues/closed_issues.md"

COMMIT_MESSAGE = "Docs: sync GitHub issues archive (open/closed)"


def run(cmd: List[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr)
        raise SystemExit(p.returncode)
    return p.stdout


def autodetect_repo(_run: Callable[[List[str]], str]) -> str:
    out = _run(["gh", "repo", "view", "--json", "nameWithOwner"]).strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        raise SystemExit("ERROR: failed to parse gh repo view output as JSON")
    repo = data.get("nameWithOwner")
    if not repo:
        raise SystemExit("ERROR: gh repo view returned no nameWithOwner")
    return repo


def load_issues(repo: str, _run: Callable[[List[str]], str]) -> List[Dict[str, Any]]:
    raw = _run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "number,title,state,labels,assignees,milestone,createdAt,updatedAt,closedAt,body",
        ]
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit("ERROR: failed to parse gh issue list output as JSON")


def _names(items: Optional[List[Dict[str, Any]]]) -> str:
    if not items:
        return "—"
    return ", ".join(i.get("name", "") for i in items if i.get("name")) or "—"


def split_and_sort(issues: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    open_issues = [i for i in issues if i.get("state") == "OPEN"]
    closed_issues = [i for i in issues if i.get("state") == "CLOSED"]
    open_issues.sort(key=lambda x: int(x["number"]))
    closed_issues.sort(key=lambda x: ((x.get("closedAt") or ""), int(x["number"])), reverse=True)
    return open_issues, closed_issues


def render_issue(i: Dict[str, Any]) -> str:
    num = i["number"]
    title = i.get("title") or ""
    state = i.get("state") or ""
    labels = _names(i.get("labels"))
    assignees = _names(i.get("assignees"))
    milestone = (i.get("milestone") or {}).get("title") if i.get("milestone") else "—"
    created = i.get("createdAt") or ""
    updated = i.get("updatedAt") or ""
    body = i.get("body") or ""
    lines: List[str] = []
    lines.append(f"## #{num} – {title}")
    lines.append(f"- State: **{state}**")
    lines.append(f"- Labels: {labels}")
    lines.append(f"- Assignees: {assignees}")
    lines.append(f"- Milestone: {milestone}")
    lines.append(f"- Created: {created}")
    lines.append(f"- Updated: {updated}")
    if state == "CLOSED":
        lines.append(f"- Closed: {i.get('closedAt') or ''}")
    lines.append("")
    lines.append(body)
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def render_archive(title: str, issues: List[Dict[str, Any]]) -> str:
    parts: List[str] = [f"# {title}", ""]
    for i in issues:
        parts.append(render_issue(i))
    text = "\n".join(parts)
    if not text.endswith("\n"):
        text += "\n"
    return text


def ensure_clean_git(_run: Callable[[List[str]], str], allow_dirty: bool) -> None:
    if allow_dirty:
        return
    if _run(["git", "status", "--porcelain"]).strip():
        raise SystemExit("ERROR: dirty working tree")


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    p.write_text(s, encoding="utf-8")


def main(
    argv: Optional[List[str]] = None,
    *,
    _run: Callable[[List[str]], str] = run,
    _load_issues: Callable[[str, Callable[[List[str]], str]], List[Dict[str, Any]]] = load_issues,
    _autodetect_repo: Callable[[Callable[[List[str]], str]], str] = autodetect_repo,
) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="owner/name (if omitted, auto-detect via gh)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-commit", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    args = ap.parse_args(argv)

    ensure_clean_git(_run, args.allow_dirty)

    repo = args.repo or _autodetect_repo(_run)
    issues = _load_issues(repo, _run)
    open_issues, closed_issues = split_and_sort(issues)
    open_md = render_archive("Open Issues", open_issues)
    closed_md = render_archive("Closed Issues", closed_issues)

    if OUT_OPEN.exists() and OUT_CLOSED.exists():
        if read_text(OUT_OPEN) == open_md and read_text(OUT_CLOSED) == closed_md:
            print("No changes.")
            return 0

    if args.dry_run:
        print("DRY RUN: changes detected")
        return 0

    write_text(OUT_OPEN, open_md)
    write_text(OUT_CLOSED, closed_md)

    if args.no_commit:
        return 0

    _run(["git", "add", str(OUT_OPEN), str(OUT_CLOSED)])
    _run(["git", "commit", "-m", COMMIT_MESSAGE])

    if args.no_push:
        return 0

    _run(["git", "push"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
