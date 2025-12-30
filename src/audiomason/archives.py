from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from audiomason.util import die, ensure_dir


def unpack(archive: Path, outdir: Path) -> None:
    ensure_dir(outdir)
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

    die(f"Unsupported archive: {archive}")
