from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ARCHIVE_EXTS = {".zip", ".rar", ".7z"}


def is_archive(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in ARCHIVE_EXTS


def unpack(archive: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    ext = archive.suffix.lower()

    if ext == ".zip":
        subprocess.run(["unzip", "-q", "-o", str(archive), "-d", str(outdir)], check=True)
        return

    if ext == ".rar":
        if shutil.which("unrar"):
            subprocess.run(["unrar", "x", "-o+", "-idq", str(archive), str(outdir)], check=True)
        else:
            subprocess.run(["7z", "x", "-y", f"-o{outdir}", str(archive)], check=True)
        return

    if ext == ".7z":
        subprocess.run(["7z", "x", "-y", f"-o{outdir}", str(archive)], check=True)
        return

    raise ValueError(f"Unsupported archive: {archive}")
