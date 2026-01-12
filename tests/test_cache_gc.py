from __future__ import annotations

import os
import time
from pathlib import Path

from audiomason.cache_gc import cache_gc


def _touch(p: Path, *, mtime: float) -> None:
    os.utime(p, (mtime, mtime))


def test_cache_gc_dry_run_does_not_delete(tmp_path: Path):
    cache = tmp_path / "cache"
    cache.mkdir()
    cfg = {"paths": {"cache": str(cache)}}

    good = cache / ("a" * 40 + ".jpg")
    good.write_bytes(b"x" * 10)
    bad = cache / "not-a-cache.txt"
    bad.write_text("nope")

    now = time.time()
    _touch(good, mtime=now - 10 * 86400)

    cache_gc(cfg, days=7, dry_run=True)
    assert good.exists()
    assert bad.exists()


def test_cache_gc_max_mb_prunes_oldest(tmp_path: Path):
    cache = tmp_path / "cache"
    cache.mkdir()
    cfg = {"paths": {"cache": str(cache)}}

    p1 = cache / ("1" * 40 + ".jpg")
    p2 = cache / ("2" * 40 + ".png")
    p3 = cache / ("3" * 40 + ".webp")
    for p in (p1, p2, p3):
        p.write_bytes(b"x" * (1024 * 1024))

    now = time.time()
    _touch(p1, mtime=now - 300)
    _touch(p2, mtime=now - 200)
    _touch(p3, mtime=now - 100)

    cache_gc(cfg, max_mb=2, dry_run=False)
    assert not p1.exists()
    assert p2.exists()
    assert p3.exists()
