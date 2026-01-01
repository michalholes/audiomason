from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import audiomason.state as state
from audiomason.paths import get_cache_root
from audiomason.util import out, ensure_dir


KNOWN_EXTS = {".jpg", ".png", ".webp", ".img"}


def _is_known_cache_file(p: Path) -> bool:
    if p.suffix.lower() not in KNOWN_EXTS:
        return False
    stem = p.stem
    if len(stem) != 40:
        return False
    # sha1 hex
    for ch in stem:
        if ch not in "0123456789abcdef":
            return False
    return True


@dataclass(frozen=True)
class CacheEntry:
    path: Path
    size: int
    mtime: float


def _iter_entries(cache_root: Path) -> list[CacheEntry]:
    if not cache_root.exists() or not cache_root.is_dir():
        return []
    out_entries: list[CacheEntry] = []
    for p in cache_root.iterdir():
        if not p.is_file():
            continue
        if not _is_known_cache_file(p):
            continue
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        out_entries.append(CacheEntry(path=p, size=int(st.st_size), mtime=float(st.st_mtime)))
    return out_entries


def cache_gc(cfg: dict, *, days: int | None = None, max_mb: int | None = None, dry_run: bool = False) -> int:
    cache_root = get_cache_root(cfg).expanduser().resolve()
    ensure_dir(cache_root)

    entries = _iter_entries(cache_root)
    total = sum(e.size for e in entries)
    total_mb = total / (1024 * 1024) if total else 0.0
    out(f"[cache-gc] root={cache_root} files={len(entries)} total_mb={total_mb:.1f}")

    now = time.time()
    cutoff = None
    if days is not None and days >= 0:
        cutoff = now - (days * 86400)

    to_remove: dict[Path, str] = {}

    if cutoff is not None:
        for e in entries:
            if e.mtime < cutoff:
                age_days = int((now - e.mtime) // 86400)
                to_remove[e.path] = f"age>{days}d (age={age_days}d)"

    if max_mb is not None and max_mb >= 0:
        limit = int(max_mb) * 1024 * 1024
        remaining = [e for e in entries if e.path not in to_remove]
        remaining_total = sum(e.size for e in remaining)
        if remaining_total > limit:
            remaining.sort(key=lambda e: (e.mtime, e.path.name))
            cur = remaining_total
            for e in remaining:
                if cur <= limit:
                    break
                to_remove[e.path] = f"size>={max_mb}MB (prune-oldest)"
                cur -= e.size

    removed = 0
    reclaimed = 0
    for pth, why in sorted(to_remove.items(), key=lambda kv: kv[0].name):
        rp = pth.resolve()
        try:
            if not rp.is_relative_to(cache_root):
                out(f"[cache-gc] SKIP outside-root: {rp}")
                continue
        except Exception:
            # best-effort fallback
            if str(cache_root) not in str(rp):
                out(f"[cache-gc] SKIP outside-root: {rp}")
                continue

        try:
            sz = rp.stat().st_size
        except FileNotFoundError:
            continue

        if getattr(state, "DEBUG", False):
            out(f"[cache-gc][debug] rm {rp.name} bytes={sz} why={why}")

        if dry_run or (state.OPTS and getattr(state.OPTS, "dry_run", False)):
            out(f"[cache-gc] would remove: {rp.name}")
            continue

        try:
            rp.unlink()
            removed += 1
            reclaimed += int(sz)
            out(f"[cache-gc] removed: {rp.name}")
        except FileNotFoundError:
            continue
        except Exception as e:
            out(f"[cache-gc] failed: {rp.name}: {e}")

    rec_mb = reclaimed / (1024 * 1024) if reclaimed else 0.0
    out(f"[cache-gc] done removed={removed} reclaimed_mb={rec_mb:.1f}")
    return 0
