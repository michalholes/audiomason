from __future__ import annotations

import asyncio
import shutil
from pathlib import Path


async def copy2_async(src: Path, dst: Path) -> None:
    await asyncio.to_thread(shutil.copy2, src, dst)


async def copytree_async(src: Path, dst: Path, *, dirs_exist_ok: bool = False) -> None:
    await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=dirs_exist_ok)


async def rmtree_async(path: Path) -> None:
    await asyncio.to_thread(shutil.rmtree, path, True)


async def unlink_async(path: Path) -> None:
    await asyncio.to_thread(path.unlink, True)
