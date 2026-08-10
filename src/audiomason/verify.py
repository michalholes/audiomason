from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError

import audiomason.metadata_lookup as metadata_lookup
from audiomason.log_bus import push_context
from audiomason.naming import normalize_name
from audiomason.paths import COVER_NAME
from audiomason.util import out

READ_ONLY_VERIFY = True


async def verify_library_async(root: Path, cfg: dict[str, object] | None = None) -> None:
    """Async metadátová časť verify – beží s konfigurovateľnou paralelizáciou.

    Zodpovedá vnútornému async bloku v pôvodnom verify_library(); ponechané
    sem kvôli čistejšiemu orchestru a budúcej plnej async migrácii.
    """
    # Configure per-host limits from config
    from typing import cast as _cast

    def _as_dict(val: object) -> dict[str, object]:
        return _cast(dict[str, object], val) if isinstance(val, dict) else {}

    def _int_cfg(val: object, default: int) -> int:
        try:
            if isinstance(val, bool):
                return int(val)
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                return int(val.strip())
        except Exception:
            return default
        return default

    net = _as_dict(cfg.get("network")) if isinstance(cfg, dict) else {}
    host_limits = _as_dict(net.get("host_limits"))
    host_delays = _as_dict(net.get("host_delay_ms"))
    from audiomason import googlebooks as _gb
    from audiomason import openlibrary as _ol

    ol_limit = _int_cfg(host_limits.get("openlibrary"), 1)
    gb_limit = _int_cfg(host_limits.get("googlebooks"), 1)
    _ol.set_host_limit(ol_limit)
    _gb.set_host_limit(gb_limit)
    ol_delay = _int_cfg(host_delays.get("openlibrary"), 0)
    gb_delay = _int_cfg(host_delays.get("googlebooks"), 0)
    _ol.set_host_delay_ms(ol_delay)
    _gb.set_host_delay_ms(gb_delay)
    # TRACE logs for network settings
    if metadata_lookup.is_enabled(cfg):
        try:
            import audiomason.state as state

            if state.DEBUG:
                out(f"[TRACE] [net] openlibrary limit={ol_limit} delay_ms={ol_delay}")
                out(f"[TRACE] [net] googlebooks limit={gb_limit} delay_ms={gb_delay}")
        except Exception:
            pass

    # Expect layout: root/Author/Book
    authors = [p for p in sorted(root.iterdir()) if p.is_dir()]
    out(f"[verify] metadata: authors={len(authors)}")

    try:
        import audiomason.state as state

        _opts = state.OPTS
        parallel = int(_opts.verify_parallel) if _opts is not None else 1
    except Exception:
        parallel = 1
    parallel = max(1, parallel)

    sem = asyncio.Semaphore(parallel)

    async def _verify_one_author(a: Path) -> None:
        async with sem:
            with push_context(source=f"verify:{a.name}", phase="VERIFY"):
                ar = await metadata_lookup.validate_author_async(a.name, cfg)
                out(
                    f"[ol] {a.name}: {ar.status} hits={ar.hits}"
                    + (f" top='{ar.top}'" if ar.top else "")
                )
                books = [p for p in sorted(a.iterdir()) if p.is_dir()]
                for b in books:
                    with push_context(source=f"verify:{a.name}", book=b.name, phase="VERIFY"):
                        br = await metadata_lookup.validate_book_async(a.name, b.name, cfg)
                        out(
                            f"[ol]   {b.name}: {br.status} hits={br.hits}"
                            + (f" top='{br.top}'" if br.top else "")
                        )

    tasks = [asyncio.create_task(_verify_one_author(a)) for a in authors]
    for t in tasks:
        with contextlib.suppress(Exception):
            await t


def verify_library(root: Path, cfg: dict[str, object] | None = None) -> None:
    """
    Verify audiobook library:
    - each book dir has cover.jpg
    - mp3 files have ID3 tags
    """
    authors: list[Path] = [p for p in sorted(root.iterdir()) if p.is_dir()]
    books: list[Path] = []
    for a in authors:
        books.extend([p for p in sorted(a.iterdir()) if p.is_dir()])
    out(f"[verify] scanning {len(books)} book(s) under {root}")

    # Name normalization report (read-only)
    for a in [p for p in sorted(root.iterdir()) if p.is_dir()]:
        na = normalize_name(a.name)
        if na != a.name:
            out(f"[name] author: '{a.name}' -> '{na}'")
        for b in [p for p in sorted(a.iterdir()) if p.is_dir()]:
            nb = normalize_name(b.name)
            if nb != b.name:
                out(f"[name]   book: '{b.name}' -> '{nb}'")

    # Metadata validation (read-only)
    if metadata_lookup.is_enabled(cfg) and root.exists():
        # Prefer native asyncio runner instead of async_bridge
        asyncio.run(verify_library_async(root, cfg))

    missing_cover = 0
    missing_tags = 0

    for book in books:
        cover = book / COVER_NAME
        if not cover.exists():
            out(f"[verify] missing cover: {book.name}")
            missing_cover += 1

        mp3s = sorted(book.glob("*.mp3"))
        for mp3 in mp3s:
            try:
                ID3(mp3)  # type: ignore[no-untyped-call]
            except ID3NoHeaderError:
                out(f"[verify] missing ID3 tags: {book.name}/{mp3.name}")
                missing_tags += 1

    with push_context(source="verify:summary", phase="VERIFY"):
        out(
            f"[verify] done: "
            f"books={len(books)}, "
            f"missing_cover={missing_cover}, "
            f"missing_tags={missing_tags}"
        )
