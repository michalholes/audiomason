#!/usr/bin/env python3
"""Standalone helper: sync GitHub issues into deterministic markdown archives.

Hard constraints:
- NOT part of AudioMason runtime/CLI
- NO imports from audiomason
- Non-interactive
- Deterministic + idempotent

This tool writes:
- docs/issues/open_issues.md
- docs/issues/closed_issues.md
- docs/issues/all_issues.yaml
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
OUT_ALL = ROOT / "docs/issues/all_issues.yaml"

COMMIT_MESSAGE = "Docs: sync GitHub issues archive (open/closed)"


def run(cmd: List[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr)
        raise SystemExit(p.returncode)
    return p.stdout


def autodetect_repo(_run: Callable[[List[str]], str]) -> str:
    out = _run(["gh", "repo", "view", "--json", "nameWithOwner"]).strip()
    data = json.loads(out)
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
    return json.loads(raw)


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


def _gh_api_json(_run: Callable[[List[str]], str], path: str, *, headers: Optional[List[str]] = None) -> Any:
    cmd = ["gh", "api"]
    if headers:
        for h in headers:
            cmd.extend(["-H", h])
    cmd.append(path)
    raw = _run(cmd)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(f"ERROR: failed to parse gh api output as JSON for {path}")


def _gh_api_paginated_list(
    _run: Callable[[List[str]], str],
    path: str,
    *,
    headers: Optional[List[str]] = None,
    per_page: int = 100,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        page_path = f"{path}{sep}per_page={per_page}&page={page}"
        data = _gh_api_json(_run, page_path, headers=headers)
        if not isinstance(data, list):
            raise SystemExit(f"ERROR: expected list from gh api for {page_path}")
        if not data:
            break
        out.extend([x for x in data if isinstance(x, dict)])
        page += 1
    return out


def _user_stub(u: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(u, dict):
        return None
    login = u.get("login")
    uid = u.get("id")
    if login is None and uid is None:
        return None
    d: Dict[str, Any] = {}
    if login is not None:
        d["login"] = login
    if uid is not None:
        d["id"] = uid
    return d


def _sort_by_created_at(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(x: Dict[str, Any]) -> Tuple[str, str, int]:
        created = str(x.get("created_at") or x.get("createdAt") or "")
        event = str(x.get("event") or "")
        ident = x.get("id")
        try:
            iid = int(ident) if ident is not None else 0
        except Exception:
            iid = 0
        return (created, event, iid)

    return sorted(items, key=key)


def _issue_core_export(issue: Dict[str, Any]) -> Dict[str, Any]:
    ms = issue.get("milestone")
    out: Dict[str, Any] = {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "html_url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "closed_at": issue.get("closed_at"),
        "user": _user_stub(issue.get("user")),
        "closed_by": _user_stub(issue.get("closed_by")),
        "labels": [{"name": l.get("name")} for l in (issue.get("labels") or []) if isinstance(l, dict) and l.get("name")],
        "assignees": [_user_stub(a) for a in (issue.get("assignees") or []) if _user_stub(a)],
        "milestone": None,
        "body": issue.get("body"),
    }
    if isinstance(ms, dict):
        out["milestone"] = {"title": ms.get("title"), "number": ms.get("number"), "state": ms.get("state")}
    return out


def _comment_export(c: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": c.get("id"),
        "html_url": c.get("html_url"),
        "user": _user_stub(c.get("user")),
        "created_at": c.get("created_at"),
        "updated_at": c.get("updated_at"),
        "body": c.get("body"),
    }


def _timeline_event_export(e: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": e.get("id"),
        "event": e.get("event"),
        "created_at": e.get("created_at"),
        "actor": _user_stub(e.get("actor")),
    }
    # Common fields used by "referenced" events
    if "commit_id" in e:
        out["commit_id"] = e.get("commit_id")
    if "commit_url" in e:
        out["commit_url"] = e.get("commit_url")
    # Some events include nested source.commit
    src = e.get("source")
    if isinstance(src, dict) and isinstance(src.get("commit"), dict):
        out["source"] = {"commit": {"sha": src["commit"].get("sha"), "html_url": src["commit"].get("html_url")}}
    return out


def _yaml_scalar(v: Any) -> str:
    # YAML 1.2 JSON-subset (safe + deterministic)
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _yaml_dump(obj: Any, indent: int = 0) -> str:
    sp = "  " * indent
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return sp + _yaml_scalar(obj)
    if isinstance(obj, list):
        if not obj:
            return sp + "[]"
        lines: List[str] = []
        for item in obj:
            if item is None or isinstance(item, (bool, int, float, str)):
                lines.append(sp + "- " + _yaml_scalar(item))
            else:
                lines.append(sp + "-")
                lines.append(_yaml_dump(item, indent + 1))
        return "\n".join(lines)
    if isinstance(obj, dict):
        if not obj:
            return sp + "{}"
        lines = []
        for k in sorted(obj.keys()):
            v = obj[k]
            if v is None or isinstance(v, (bool, int, float, str)):
                lines.append(f"{sp}{k}: {_yaml_scalar(v)}")
            else:
                lines.append(f"{sp}{k}:")
                lines.append(_yaml_dump(v, indent + 1))
        return "\n".join(lines)
    return sp + _yaml_scalar(str(obj))


def build_all_issues_yaml(repo: str, issues: List[Dict[str, Any]], _run: Callable[[List[str]], str]) -> str:
    nums = sorted({int(i.get("number")) for i in issues if i.get("number") is not None})

    headers_core = [
        "Accept: application/vnd.github+json",
        "X-GitHub-Api-Version: 2022-11-28",
    ]
    headers_timeline = [
        "Accept: application/vnd.github.mockingbird-preview+json",
        "X-GitHub-Api-Version: 2022-11-28",
    ]

    issues_out: List[Dict[str, Any]] = []
    for n in nums:
        core = _gh_api_json(_run, f"repos/{repo}/issues/{n}", headers=headers_core)
        if not isinstance(core, dict):
            raise SystemExit(f"ERROR: expected issue object from gh api for #{n}")

        comments = _gh_api_paginated_list(_run, f"repos/{repo}/issues/{n}/comments", headers=headers_core)
        timeline = _gh_api_paginated_list(_run, f"repos/{repo}/issues/{n}/timeline", headers=headers_timeline)

        comments_sorted = _sort_by_created_at(comments)
        timeline_sorted = _sort_by_created_at(timeline)

        issues_out.append(
            {
                "issue": _issue_core_export(core),
                "comments": [_comment_export(c) for c in comments_sorted],
                "timeline": [_timeline_event_export(e) for e in timeline_sorted],
            }
        )

    payload: Dict[str, Any] = {"repo": repo, "issues": issues_out}
    return _yaml_dump(payload) + "\n"


def main(
    argv: Optional[List[str]] = None,
    *,
    _run: Callable[[List[str]], str] = run,
    _load_issues: Callable[[str, Callable[[List[str]], str]], List[Dict[str, Any]]] = load_issues,
    _autodetect_repo: Callable[[Callable[[List[str]], str]], str] = autodetect_repo,
) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
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
    all_yaml = build_all_issues_yaml(repo, issues, _run)

    if OUT_OPEN.exists() and OUT_CLOSED.exists() and OUT_ALL.exists():
        if read_text(OUT_OPEN) == open_md and read_text(OUT_CLOSED) == closed_md and read_text(OUT_ALL) == all_yaml:
            print("No changes.")
            return 0

    if args.dry_run:
        print("DRY RUN: changes detected")
        return 0

    write_text(OUT_OPEN, open_md)
    write_text(OUT_CLOSED, closed_md)
    write_text(OUT_ALL, all_yaml)

    if args.no_commit:
        return 0

    _run(["git", "add", str(OUT_OPEN), str(OUT_CLOSED), str(OUT_ALL)])
    _run(["git", "commit", "-m", COMMIT_MESSAGE])

    if args.no_push:
        return 0

    _run(["git", "push"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
