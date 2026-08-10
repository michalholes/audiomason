from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import audiomason.state as state
from audiomason.import_engine_async import run_import_async
from audiomason.state import Opts


async def _run_async(coro: Awaitable[None]) -> None:
    await coro


def test_run_import_async_two_sources(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    # Prepare roots
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    # Two sources with a single mp3 each
    s1 = drop_root / "Src.One"
    s2 = drop_root / "Src.Two"
    s1.mkdir()
    s2.mkdir()
    (s1 / "01.mp3").write_bytes(b"x")
    (s2 / "01.mp3").write_bytes(b"x")

    # Monkeypatch import_flow environment
    import audiomason.import_flow as imp
    import audiomason.preflight_resolve as pr
    import audiomason.preflight_undo as pu

    def _dr(cfg: dict[str, object]) -> Path:
        return drop_root

    def _sr(cfg: dict[str, object]) -> Path:
        return stage_root

    def _ar(cfg: dict[str, object]) -> Path:
        return archive_root

    def _or(cfg: dict[str, object]) -> Path:
        return output_root

    monkeypatch.setattr(imp, "get_drop_root", _dr)
    monkeypatch.setattr(imp, "get_stage_root", _sr)
    monkeypatch.setattr(imp, "get_archive_root", _ar)
    monkeypatch.setattr(imp, "get_output_root", _or)

    # choose_source / choose_books -> 'a'
    def _pf_prompt_all(cfg: dict[str, object], key: str, msg: str, default: str = "1") -> str:
        return "a"

    monkeypatch.setattr(imp, "pf_prompt", _pf_prompt_all)

    # Disable yes/no prompts deterministically
    def _pf_yesno_all(cfg: dict[str, object], key: str, msg: str, default_no: bool = True) -> bool:
        return False

    monkeypatch.setattr(pr, "pf_prompt_yes_no", _pf_yesno_all)

    # Author prompt: return src_name
    def _prompt_author(cfg: dict[str, object], default_author: object = None, **kw: object) -> str:
        src_name = kw.get("src_name")
        return str(src_name or (default_author or "Author"))

    monkeypatch.setattr(pu, "prompt_author_with_undo", _prompt_author)

    # publish/wipe/clean decisions
    def _decide(*a: object, **k: object) -> tuple[bool, bool, bool]:
        return (False, False, False)

    monkeypatch.setattr(pu, "decide_publish_wipe_clean", _decide)

    # State options: disable lookup/ai, default limits
    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            yes=False,
            dry_run=False,
            quiet=False,
            publish=None,
            wipe_id3=None,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="no",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
            max_parallel_sources=2,
            max_parallel_books=2,
            max_parallel_ffmpeg=2,
            verify_parallel=1,
        )
        # Run async import
        asyncio.run(_run_async(run_import_async(cfg={}, src_path=None)))

        # Verify manifests show processed book for both sources
        from audiomason.manifest import load_manifest

        for src in (s1, s2):
            sr = stage_root / imp.slug(src.name)
            mf = load_manifest(sr)
            books_raw = mf.get("books")
            if isinstance(books_raw, dict):
                books_map2: dict[str, object] = books_raw  # type: ignore[assignment]
            else:
                books_map2 = {}
            proc_raw = books_map2.get("processed")
            if isinstance(proc_raw, list):
                processed_list2: list[object] = proc_raw  # type: ignore[assignment]
            else:
                processed_list2 = []
            processed_list = processed_list2
            assert len(processed_list) >= 1
    finally:
        state.OPTS = old_opts
