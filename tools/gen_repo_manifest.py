#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src" / "audiomason"
DOCS = ROOT / "docs"
OUT = DOCS / "repo_manifest.yaml"

def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def file_sha1(p: Path) -> str:
    return sha1_text(p.read_text(encoding="utf-8", errors="ignore"))

def yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def domains_for(path: str, src: str) -> list[str]:
    p = path.lower()
    tags = set()
    if p.startswith("docs/"):
        tags.add("docs")
    if "cli" in p:
        tags.add("cli")
    if "config" in p:
        tags.add("config")
    if "import_flow" in p or "pipeline" in p or "flow" in p:
        tags.add("pipeline")
    if "audio" in p or "ffmpeg" in src or ".opus" in src or ".m4a" in src:
        tags.add("audio")
    if "publish" in p or ("output" in src and "copy" in src):
        tags.add("publish")
    if "prompt" in p or "_pf_" in src:
        tags.add("prompts")
    if not tags:
        tags.add("misc")
    return sorted(tags)

def extract_anchors(p: Path) -> list[dict]:
    src = p.read_text(encoding="utf-8", errors="ignore")
    lines = src.splitlines()
    anchors = []

    try:
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef):
                anchors.append(f"def {n.name}(")
            elif isinstance(n, ast.ClassDef):
                anchors.append(f"class {n.name}")
    except SyntaxError:
        anchors.append("SYNTAX_ERROR_FILE")

    for t in ("DEFAULTS", "PREPARE", "PROCESS", "add_argument"):
        if t in src:
            anchors.append(t)

    for q in ("'", '"'):
        i = 0
        while True:
            i = src.find(f"{q}--", i)
            if i < 0:
                break
            j = src.find(q, i + 1)
            if j > i:
                anchors.append(src[i + 1:j])
            i += 1

    uniq = []
    for a in anchors:
        if a not in uniq:
            uniq.append(a)

    out = []
    for a in uniq:
        idxs = [i for i, l in enumerate(lines) if a in line]
        if not idxs:
            continue
        i = idxs[0]
        out.append({
            "anchor": a,
            "first_line": i + 1,
            "count": len(idxs),
            "context_before": lines[i - 1].strip() if i > 0 else "",
            "context_after": lines[i + 1].strip() if i + 1 < len(lines) else "",
        })
    return out

entries = []

for p in sorted(SRC.rglob("*.py")):
    src = p.read_text(encoding="utf-8", errors="ignore")
    entries.append({
        "path": p.relative_to(ROOT).as_posix(),
        "domains": domains_for(str(p), src),
        "file_sha1": file_sha1(p),
        "anchors": extract_anchors(p),
    })

lines = []
lines.append("version: 1")
lines.append("project: AudioMason")
lines.append("rules:")
lines.append("  authoritative: true")
lines.append("  latest_wins: true")
lines.append("  anchors_required: true")
lines.append("  fail_fast_on_missing_anchor: true")
lines.append("  fail_fast_on_missing_file: true")
lines.append("files:")

for e in entries:
    lines.append(f"- path: {e['path']}")
    lines.append(f"  domains: {e['domains']}")
    lines.append(f"  file_sha1: \"{e['file_sha1']}\"")
    lines.append("  anchors:")
    for a in e["anchors"]:
        lines.append(f"    - anchor: \"{yaml_escape(a['anchor'])}\"")
        lines.append(f"      first_line: {a['first_line']}")
        lines.append(f"      count: {a['count']}")
        lines.append(f"      context_before: \"{yaml_escape(a['context_before'])}\"")
        lines.append(f"      context_after: \"{yaml_escape(a['context_after'])}\"")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"OK: wrote {OUT}")
