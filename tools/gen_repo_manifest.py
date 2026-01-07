#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path.cwd()
SRC = ROOT / "src" / "audiomason"
OUT = ROOT / "docs" / "repo_manifest.yaml"

MAX_ANCHORS_PER_FILE = 120  # keep it bounded but still rich

@dataclass
class FileEntry:
    path: str
    anchors: list[str]

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _py_files() -> list[Path]:
    files: list[Path] = []
    for p in SRC.rglob("*.py"):
        if p.name == "__pycache__":
            continue
        files.append(p)
    return sorted(files)

def _extract_anchors_from_ast(tree: ast.AST) -> list[str]:
    anchors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            anchors.append(f"def {node.name}(")
        elif isinstance(node, ast.ClassDef):
            anchors.append(f"class {node.name}")
    return anchors

def _extract_flags_textually(src: str) -> list[str]:
    # quick-and-dirty flag extraction: any literal starting with -- inside quotes
    flags: list[str] = []
    for q in ('"', "'"):
        needle = f"{q}--"
        idx = 0
        while True:
            i = src.find(needle, idx)
            if i < 0:
                break
            j = i + len(q)
            k = src.find(q, j)
            if k > j:
                lit = src[j:k]
                # keep plausible flags only
                if lit.startswith("--") and " " not in lit and len(lit) <= 64:
                    flags.append(lit)
            idx = i + 1
    return flags

def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _prefer_stable(anchors: list[str]) -> list[str]:
    # Put class/def first, then flags, then everything else.
    def_key = [a for a in anchors if a.startswith("def ") or a.startswith("class ")]
    flags = [a for a in anchors if a.startswith("--")]
    rest  = [a for a in anchors if a not in set(def_key) and a not in set(flags)]
    return def_key + flags + rest

def _file_entry(p: Path) -> FileEntry:
    rel = p.relative_to(ROOT).as_posix()
    src = _read(p)

    anchors: list[str] = []

    # AST-based anchors
    try:
        tree = ast.parse(src)
        anchors.extend(_extract_anchors_from_ast(tree))
    except SyntaxError:
        # if file is broken, still include something deterministic
        anchors.append("SYNTAX_ERROR_FILE")

    # Textual anchors that are useful and stable-ish
    for token in ("DEFAULTS", "AmConfigError", "ArgumentParser", "add_argument", "PREPARE", "PROCESS"):
        if token in src:
            anchors.append(token)

    # CLI flags
    anchors.extend(_extract_flags_textually(src))

    anchors = _dedupe_keep_order(_prefer_stable(anchors))

    # Keep bounded
    if len(anchors) > MAX_ANCHORS_PER_FILE:
        anchors = anchors[:MAX_ANCHORS_PER_FILE]

    # Ensure at least one anchor
    if not anchors:
        anchors = ["<empty>"]

    return FileEntry(path=rel, anchors=anchors)

def _emit_yaml(entries: list[FileEntry]) -> str:
    # Minimal YAML emitter (no deps), stable ordering
    lines: list[str] = []
    lines.append("version: 1")
    lines.append("project: AudioMason")
    lines.append("")
    lines.append("rules:")
    lines.append("  authoritative: true")
    lines.append("  latest_wins: true")
    lines.append("  anchors_required: true")
    lines.append("  fail_fast_on_missing_anchor: true")
    lines.append("  fail_fast_on_missing_file: true")
    lines.append("")
    lines.append("repo_root_markers:")
    lines.append("  - pyproject.toml")
    if (ROOT / "src" / "audiomason" / "__init__.py").exists():
        lines.append("  - src/audiomason/__init__.py")
    lines.append("")
    lines.append("domains:")
    lines.append("  python:")
    lines.append('    description: "Auto-generated anchors for all src/audiomason Python files"')
    lines.append("    files:")
    for e in entries:
        lines.append(f"      - path: {e.path}")
        lines.append("        anchors:")
        for a in e.anchors:
            # quote always for safety
            a = a.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'          - "{a}"')
    lines.append("")
    lines.append("generated:")
    # include stable fingerprint of inputs to detect drift
    fp = hashlib.sha1()
    for e in entries:
        fp.update(e.path.encode("utf-8"))
        fp.update(b"\0")
        fp.update("\n".join(e.anchors).encode("utf-8"))
        fp.update(b"\0")
    lines.append(f'  fingerprint_sha1: "{fp.hexdigest()}"')
    return "\n".join(lines) + "\n"

def main() -> None:
    files = _py_files()
    entries = [_file_entry(p) for p in files]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(_emit_yaml(entries), encoding="utf-8")
    print(f"OK: wrote {OUT}")

if __name__ == "__main__":
    main()
