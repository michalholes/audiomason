from __future__ import annotations

import shutil
from pathlib import Path

from audiomason.util import die, ensure_dir, run_cmd


def _require_tool(name: str) -> None:
    if not shutil.which(name):
        die(f"Missing external tool: {name} (install {name})")


def unpack(archive: Path, outdir: Path) -> None:
    ensure_dir(outdir)
    ext = archive.suffix.lower()

    if ext == ".zip":
        _require_tool("unzip")
        run_cmd(["unzip", "-q", "-o", str(archive), "-d", str(outdir)], check=True)
        return

    if ext == ".rar":
        if shutil.which("unrar"):
            _require_tool("unrar")
            run_cmd(["unrar", "x", "-o+", "-idq", str(archive), str(outdir)], check=True)
        else:
            _require_tool("7z")
            run_cmd(["7z", "x", "-y", f"-o{outdir}", str(archive)], check=True)
        return

    if ext == ".7z":
        _require_tool("7z")
        run_cmd(["7z", "x", "-y", f"-o{outdir}", str(archive)], check=True)
        return

    die(f"Unsupported archive: {archive}")
