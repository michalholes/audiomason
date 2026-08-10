from __future__ import annotations
# ruff: noqa: I001
# mypy: ignore-errors

import json
import shutil
import threading
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import audiomason.metadata_lookup as metadata_lookup
import audiomason.openlibrary as openlibrary
import audiomason.state as state
from audiomason.concurrency import set_ffmpeg_limit
from audiomason.guess import (
    guess_book_title_default,
    guess_series_numbering_style,
    normalize_series_numbering,
)
from audiomason.ignore import add_ignore, load_ignore
from audiomason.logging_integration import start_source_logging
from audiomason.log_bus import push_context
from audiomason.manifest import load_manifest, source_fingerprint, update_manifest
from audiomason.preflight_orchestrator import PreflightContext, PreflightOrchestrator
from audiomason.preflight_resolve import pf_prompt, pf_prompt_yes_no
import audiomason.preflight_undo as pu
from audiomason.util import AmUndoError
from audiomason.tags import summarize_id3_files
from audiomason.util import die, ensure_dir, out, slug


def run_source_lifecycle_sync(
    cfg: dict[str, object],
    *,
    src: Path,
    si: int,
    total: int,
    phase: str,
    do_process: bool,
    run_clean_inbox: bool,
    drop_root: Path,
    stage_root: Path,
    archive_root: Path,
    output_root: Path,
    stage_runs_for_json: list[Path],
    steps: list[str],
    forced_flag: bool,
) -> None:
    """Run full per-source lifecycle (PREPARE -> PROCESS -> FINALIZE).

    This is a direct extraction of the original import_flow._process_one_source
    with no behavior changes. Helpers previously local to import_flow are
    accessed via dynamic import to avoid cyclic imports at module import time.
    """
    # Late import to avoid import-time cycle with import_flow
    _iflow = import_module("audiomason.import_flow")

    stage_run = stage_root / slug(src.name)

    # Per-source logging sink and context prefixing
    with start_source_logging(cfg, stage_run=stage_run, src=src, explicit_target=None):
        out(f"[source] {si}/{total}: {src.name}")
        # Keep test-visible source prefix identical to original flow
        _iflow._SOURCE_PREFIX = src.name  # type: ignore[attr-defined]

        # Normalize ignore candidate keys
        def _norm(s: str) -> str:
            import unicodedata as _ud

            return _ud.normalize("NFKC", s).strip().casefold()

        ignore_raw = load_ignore(drop_root, source_list=True)
        ignore_norm = _iflow._ignore_norms(ignore_raw)

        candidates = {
            _norm(src.name),
            _norm(src.stem),
            _norm(slug(src.name)),
            _norm(slug(src.stem)),
        }

        if (not forced_flag) and (candidates & ignore_norm):
            out("[source] skipped (ignored)")
            return

        stage_runs_for_json.append(stage_run)
        stage_src = stage_run / "src"

        fp = source_fingerprint(src)
        update_manifest(stage_run, {"source": {"fingerprint": fp}})
        mf = load_manifest(stage_run)
        dec = cast(
            dict[str, object],
            mf.get("decisions") if isinstance(mf.get("decisions"), dict) else {},
        )
        bm = cast(
            dict[str, object],
            mf.get("book_meta") if isinstance(mf.get("book_meta"), dict) else {},
        )
        src_meta = cast(
            dict[str, object],
            mf.get("source") if isinstance(mf.get("source"), dict) else {},
        )

        reuse_possible = bool(stage_src.exists() and src_meta.get("fingerprint") == fp)
        reuse_stage = False
        use_manifest_answers = False
        if phase == "process":
            if not reuse_possible:
                die("Internal error: process phase requires staged source from preflight phase")
            reuse_stage = True
            use_manifest_answers = True
        else:
            if reuse_possible:
                reuse_stage = pf_prompt_yes_no(
                    cfg,
                    "reuse_stage",
                    "[stage] Reuse existing staged source?",
                    default_no=False,
                )

            if reuse_stage:
                out("[stage] reuse")
                try:
                    use_manifest_answers = pf_prompt_yes_no(
                        cfg,
                        "use_manifest_answers",
                        "[manifest] Use saved answers (skip prompts)?",
                        default_no=False,
                    )
                except AmUndoError:
                    reuse_stage = pf_prompt_yes_no(
                        cfg,
                        "reuse_stage",
                        "[stage] Reuse existing staged source?",
                        default_no=False,
                    )
                    if not reuse_stage:
                        use_manifest_answers = False
            else:
                if reuse_possible:
                    out("[stage] delete")
                    shutil.rmtree(stage_run, ignore_errors=True)
                    mf = {}
                    dec = {}
                    bm = {}

            ensure_dir(stage_run)
            update_manifest(
                stage_run,
                {
                    "source": {
                        "name": src.name,
                        "stem": src.stem,
                        "is_dir": bool(src.is_dir()),
                        "is_file": bool(src.is_file()),
                        "path": str(src),
                        "fingerprint": fp,
                    },
                },
            )
            out(f"[stage] copying source into stage: {src} -> {stage_src}")
            _iflow._stage_source(src, stage_src)

        # Detect books and apply source-level ignore
        all_books = _iflow._detect_books(stage_src)
        book_ignore_raw = load_ignore(src)
        book_ignore_norm = _iflow._ignore_norms(book_ignore_raw)
        books = [b for b in all_books if not _iflow._matches_ignore(b.label, book_ignore_norm)]
        if len(books) != len(all_books):
            out(f"[books] skipped ignored: {len(all_books) - len(books)}")
        if not books:
            out("[books] skipped (ignored)")
            return

        # Picked books
        picked_books: list[Any] = []
        books_meta = cast(
            dict[str, object], mf.get("books") if isinstance(mf.get("books"), dict) else {}
        )
        picked = cast(
            list[str],
            books_meta.get("picked") if isinstance(books_meta.get("picked"), list) else [],
        )
        if reuse_stage and use_manifest_answers and picked:
            by_label = {b.label: b for b in books}
            picked_books = [by_label[lbl] for lbl in picked if lbl in by_label]

        default_ans = "1"
        if (not picked_books) and picked:
            if len(picked) == len(books):
                default_ans = "a"
            else:
                first = picked[0]
                try:
                    idx = [b.label for b in books].index(first) + 1
                    default_ans = str(idx)
                except Exception:
                    default_ans = "1"

        if not picked_books:
            picked_books = _iflow._choose_books(cfg, books, default_ans=default_ans)

        update_manifest(
            stage_run,
            {
                "books": {
                    "detected": [b.label for b in books],
                    "picked": [b.label for b in picked_books],
                },
            },
        )

        # Resume skip processed
        processed = cast(
            list[str],
            books_meta.get("processed") if isinstance(books_meta.get("processed"), list) else [],
        )
        if reuse_stage and use_manifest_answers and processed:
            done = set(processed)
            before = [b.label for b in picked_books]
            already = [x for x in before if x in done]
            if already:
                out(f"[books] resume: already processed: {', '.join(already)}")
                if pf_prompt_yes_no(
                    cfg, "skip_processed_books", "Skip already processed books?", default_no=True
                ):
                    picked_books = [b for b in picked_books if b.label not in done]
                    if not picked_books:
                        out("[books] resume: nothing left to process")
                        return

        # Preflight decisions
        _iflow._resolved_preflight_steps(cfg)

        publish: bool | None = None
        wipe: bool | None = None
        clean_stage: bool | None = None

        orchestrator = PreflightOrchestrator(cfg)
        ctx = PreflightContext(cfg=cfg)
        ctx.context_level = "books_selected"
        plan = orchestrator.plan(ctx)

        def _exec_step(step_key: str) -> None:
            nonlocal publish, wipe, clean_stage
            if step_key in {"publish", "wipe_id3", "clean_stage"} and (
                publish is None or wipe is None or clean_stage is None
            ):
                publish, wipe, clean_stage = pu.decide_publish_wipe_clean(
                    cfg,
                    stage_run=stage_run,
                    decisions=dec,
                    reuse_stage=reuse_stage,
                    use_manifest_answers=use_manifest_answers,
                )

        orchestrator.materialize_pending(ctx, plan, executor=_exec_step)

        if publish is None or wipe is None or clean_stage is None:
            publish, wipe, clean_stage = pu.decide_publish_wipe_clean(
                cfg,
                stage_run=stage_run,
                decisions=dec,
                reuse_stage=reuse_stage,
                use_manifest_answers=use_manifest_answers,
            )
        assert publish is not None and wipe is not None and clean_stage is not None
        publish_b = bool(publish)
        wipe_b = bool(wipe)

        batch_books: list[dict[str, object]] = []
        mp3s_by_label: dict[str, list[Path]] = {}
        id3_by_label: dict[str, list[dict[str, str]]] = {}
        source_id3_context: list[dict[str, str]] = []
        for b in picked_books:
            mp3s = _iflow._collect_audio_files(b.group_root)
            mp3s_by_label[b.label] = mp3s
            id3_context = summarize_id3_files(mp3s, limit=3)
            id3_by_label[b.label] = id3_context
            if b.label == "__ROOT_AUDIO__" and not source_id3_context:
                source_id3_context = id3_context
            batch_books.append(
                {
                    "label": b.label,
                    "default_title": guess_book_title_default(b.label),
                    "group_root": b.group_root.name,
                    "root_audio": b.label == "__ROOT_AUDIO__",
                    "audio_files": [p.name for p in mp3s[:8]],
                    "id3": id3_context,
                }
            )

        batch_defaults = metadata_lookup.suggest_batch_defaults(
            src.name,
            batch_books,
            cfg,
            artifact_dir=stage_run,
        )
        series_style = guess_series_numbering_style(
            [
                {
                    "default_title": (
                        batch_defaults.book_titles.get(b.label)
                        if batch_defaults is not None and b.label in batch_defaults.book_titles
                        else guess_book_title_default(b.label)
                    ),
                    "root_audio": b.label == "__ROOT_AUDIO__",
                }
                for b in picked_books
            ]
        )

        # Resolve author
        default_author = str(dec.get("author") or "").strip()
        if reuse_stage and use_manifest_answers and default_author:
            author = default_author
        else:
            try:
                author = pu.prompt_author_with_undo(
                    cfg,
                    default_author=default_author,
                    batch_defaults=batch_defaults,
                    src_name=src.name,
                    source_id3_context=source_id3_context,
                    stage_run=stage_run,
                )
            except AmUndoError:
                publish, wipe, clean_stage = pu.decide_publish_wipe_clean(
                    cfg,
                    stage_run=stage_run,
                    decisions=dec,
                    reuse_stage=reuse_stage,
                    use_manifest_answers=use_manifest_answers,
                )
                author = pu.prompt_author_with_undo(
                    cfg,
                    default_author=default_author,
                    batch_defaults=batch_defaults,
                    src_name=src.name,
                    source_id3_context=source_id3_context,
                    stage_run=stage_run,
                )
        if not author:
            die("Author is required")
        update_manifest(stage_run, {"decisions": {"author": author}})

        out("[phase] PREPARE")

        # Resolve roots
        _work_root_default: Path | None = output_root if publish_b else None

        # Preflight per-book metadata (title/cover decisions)
        meta: list[tuple[Any, str, str, Path, str, bool, Path]] = []
        for bi, b in enumerate(picked_books, 1):
            # title
            bm_entry2 = cast(
                dict[str, object],
                bm.get(b.label) if isinstance(bm.get(b.label), dict) else {},
            )
            default_title = str(bm_entry2.get("out_title") or bm_entry2.get("title") or "").strip()
            if not default_title:
                default_title = (
                    batch_defaults.book_titles.get(b.label) if batch_defaults is not None else None
                ) or guess_book_title_default(b.label)
            default_title = normalize_series_numbering(default_title, series_style)

            if reuse_stage and use_manifest_answers and default_title:
                title = default_title
            else:
                if state.OPTS is not None and state.OPTS.dry_run:
                    title = default_title or b.label
                else:
                    while True:
                        try:
                            title = _iflow._preflight_book(
                                cfg, bi, len(picked_books), b, default_title=default_title
                            )
                            break
                        except AmUndoError:
                            try:
                                author = pu.prompt_author_with_undo(
                                    cfg,
                                    default_author=default_author,
                                    batch_defaults=batch_defaults,
                                    src_name=src.name,
                                    source_id3_context=source_id3_context,
                                    stage_run=stage_run,
                                )
                            except AmUndoError:
                                publish, wipe, clean_stage = pu.decide_publish_wipe_clean(
                                    cfg,
                                    stage_run=stage_run,
                                    decisions=dec,
                                    reuse_stage=reuse_stage,
                                    use_manifest_answers=use_manifest_answers,
                                )
                                author = pu.prompt_author_with_undo(
                                    cfg,
                                    default_author=default_author,
                                    batch_defaults=batch_defaults,
                                    src_name=src.name,
                                    source_id3_context=source_id3_context,
                                    stage_run=stage_run,
                                )

                # Metadata suggestion (book title)
                if metadata_lookup.is_enabled(cfg):
                    if getattr(state, "DEBUG", False):
                        out(f"[ol] validate book: author='{author}' title='{title}'")
                    book_context = f"source={src.name}; book_label={b.label}"
                    if id3_by_label.get(b.label):
                        book_context += "; id3=" + json.dumps(
                            id3_by_label[b.label], ensure_ascii=False, sort_keys=True
                        )
                    if batch_defaults is not None:
                        br = openlibrary.validate_book(author, title)
                    else:
                        br = metadata_lookup.validate_book(
                            author,
                            title,
                            cfg,
                            context=book_context,
                            artifact_dir=stage_run,
                        )
                    if (not br.ok) and (not br.top):
                        out(f"[ol] book not found: author='{author}' title='{title}'")
                    if getattr(state, "DEBUG", False):
                        out(
                            f"[ol] book result: ok={br.ok}"
                            f" status={br.status!r}"
                            f" hits={br.hits}"
                            f" top={br.top!r}"
                        )
                    title = _iflow._ol_offer_top(
                        "book title", title, br, cfg=cfg, key="normalize_book_title"
                    )

            # cover decision
            bm_entry = cast(
                dict[str, object],
                bm.get(b.label) if isinstance(bm.get(b.label), dict) else {},
            )
            default_cover_mode = (
                str(bm_entry.get("cover_mode") or "").strip()
                if (reuse_stage and use_manifest_answers)
                else ""
            )
            default_cover_src = (
                str(bm_entry.get("cover_src") or "").strip()
                if (reuse_stage and use_manifest_answers)
                else ""
            )

            # Replicate the same interactive logic from import_flow via helper
            # The helper _preflight_book already handled title; cover logic remains inside
            # import_flow because it depends on multiple local helpers. We persist chosen
            # values via manifest below.

            # Use the exact cover meta block from import_flow by delegating to its logic
            # We will reconstruct the same variables used there.
            # For minimal change in this extraction step, reuse import_flow's implementation by
            # invoking the same code paths in-place here.

            # The original code computes file_cover/embedded and runs prompts; reuse that code by
            # calling into import_flow helper that stages cover and returns mode/src when needed.
            # To avoid duplicating that logic here, we keep the same flow but inline minimal parts.

            # Derive detected file cover and embedded cover
            file_cover = _iflow.find_file_cover(b.stage_root, b.group_root)
            embedded = (
                _iflow.extract_embedded_cover_from_mp3(mp3s_by_label[b.label][0])
                if mp3s_by_label.get(b.label)
                else None
            )

            cover_mode = ""
            cover_src = ""
            if reuse_stage and use_manifest_answers and default_cover_mode:
                cover_mode = default_cover_mode
                cover_src = default_cover_src
            else:
                out(f"[cover-meta] {bi}/{len(picked_books)}: {author} / {title}")
                try:
                    # For exact behavior (including non-interactive), reuse the same
                    # interactive guard as import_flow._is_interactive().
                    if not _iflow._is_interactive():
                        # Non-interactive: deterministic, no prompts
                        if file_cover:
                            cover_mode, cover_src = "file", str(file_cover.name)
                        elif embedded:
                            cover_mode, cover_src = "embedded", "embedded"
                        else:
                            cover_mode, cover_src = "skip", "skip"
                    else:
                        # Keep the same prompting logic as original
                        if file_cover or embedded:
                            if file_cover and embedded:
                                out("Cover detected:")
                                out("  1) embedded cover from audio")
                                out(f"  2) {file_cover.name} (preferred)")
                                out("  s) skip")
                                out("  u) URL/path override")
                                d = "2"
                                if default_cover_mode == "embedded":
                                    d = "1"
                                elif default_cover_mode == "skip":
                                    d = "s"
                                ans = (
                                    pf_prompt(cfg, "cover", "Choose cover [1/2/s/u]", d)
                                    .strip()
                                    .lower()
                                )
                                if ans == "1":
                                    cover_mode, cover_src = "embedded", "embedded"
                                elif ans == "s":
                                    cover_mode, cover_src = "skip", "skip"
                                elif ans == "u":
                                    raw = pf_prompt(
                                        cfg, "cover", "Cover URL or file path (Enter=skip)", ""
                                    ).strip()
                                    if not raw:
                                        cover_mode, cover_src = "skip", "skip"
                                    else:
                                        staged = _iflow._stage_cover_from_raw(
                                            cfg, raw, b.group_root
                                        )
                                        if staged is None:
                                            cover_mode, cover_src = "skip", "skip"
                                        else:
                                            cover_mode, cover_src = "file", raw
                                else:
                                    cover_mode, cover_src = "file", str(file_cover.name)
                            else:
                                if file_cover:
                                    out(f"Cover detected: {file_cover.name}")
                                    keep = pf_prompt_yes_no(
                                        cfg, "cover", "Use detected cover?", default_no=False
                                    )
                                    if keep:
                                        cover_mode, cover_src = "file", str(file_cover.name)
                                    else:
                                        raw = pf_prompt(
                                            cfg,
                                            "cover",
                                            "Cover URL or file path (Enter=skip)",
                                            "",
                                        ).strip()
                                        if not raw:
                                            cover_mode, cover_src = "skip", "skip"
                                        else:
                                            staged = _iflow._stage_cover_from_raw(
                                                cfg, raw, b.group_root
                                            )
                                            if staged is None:
                                                cover_mode, cover_src = "skip", "skip"
                                            else:
                                                cover_mode, cover_src = "file", raw
                                else:
                                    out("Cover detected: embedded")
                                    keep = pf_prompt_yes_no(
                                        cfg, "cover", "Use embedded cover?", default_no=False
                                    )
                                    if keep:
                                        cover_mode, cover_src = "embedded", "embedded"
                                    else:
                                        raw = pf_prompt(
                                            cfg,
                                            "cover",
                                            "Cover URL or file path (Enter=skip)",
                                            "",
                                        ).strip()
                                        if not raw:
                                            cover_mode, cover_src = "skip", "skip"
                                        else:
                                            staged = _iflow._stage_cover_from_raw(
                                                cfg, raw, b.group_root
                                            )
                                            if staged is None:
                                                cover_mode, cover_src = "skip", "skip"
                                            else:
                                                cover_mode, cover_src = "file", raw
                        else:
                            if state.OPTS and state.OPTS.dry_run:
                                cover_mode, cover_src = "skip", "skip"
                            else:
                                raw = pf_prompt(
                                    cfg,
                                    "cover",
                                    "No cover found. URL or file path (Enter=skip)",
                                    "",
                                ).strip()
                                if not raw:
                                    cover_mode, cover_src = "skip", "skip"
                                else:
                                    staged = _iflow._stage_cover_from_raw(cfg, raw, b.group_root)
                                    if staged is None:
                                        cover_mode, cover_src = "skip", "skip"
                                    else:
                                        cover_mode, cover_src = "file", raw
                except AmUndoError:
                    try:
                        title = _iflow._preflight_book(
                            cfg, bi, len(picked_books), b, default_title=default_title
                        )
                    except AmUndoError:
                        publish, wipe, clean_stage = pu.decide_publish_wipe_clean(
                            cfg,
                            stage_run=stage_run,
                            decisions=dec,
                            reuse_stage=reuse_stage,
                            use_manifest_answers=use_manifest_answers,
                        )

            # Destination resolve
            if reuse_stage and use_manifest_answers:
                m_overwrite = bool(bm_entry.get("overwrite") is True)
                m_dest_kind = str(bm_entry.get("dest_kind") or "")
                m_out_title = str(bm_entry.get("out_title") or "").strip()
            else:
                m_overwrite = False
                m_dest_kind = ""
                m_out_title = ""

            final_root2 = archive_root
            if m_dest_kind == "output":
                final_root2 = output_root
            elif m_dest_kind == "archive":
                final_root2 = archive_root

            dest_root2 = (
                _work_root_default if publish_b and _work_root_default is not None else final_root2
            )

            out_title = m_out_title or title
            overwrite = m_overwrite

            outdir = _iflow._output_dir(dest_root2, author, out_title)
            if _iflow._is_dir_nonempty(outdir) and not (reuse_stage and use_manifest_answers):
                if not (state.OPTS and state.OPTS.yes):
                    out(f"[dest] exists: {outdir}")
                    overwrite = pf_prompt_yes_no(
                        cfg,
                        "overwrite_destination",
                        "Destination exists. Overwrite?",
                        default_no=True,
                    )
                else:
                    overwrite = False

                if not overwrite:
                    if dest_root2 != output_root:
                        dest_root2 = output_root
                        outdir = _iflow._output_dir(dest_root2, author, out_title)
                    if _iflow._is_dir_nonempty(outdir):
                        die(f"Conflict: output already exists and is not empty: {outdir}")

            dest_kind = "archive" if dest_root2 == archive_root else "output"
            meta.append((b, title, cover_mode, dest_root2, out_title, overwrite, final_root2))
            update_manifest(
                stage_run,
                {
                    "book_meta": {
                        b.label: {
                            "title": title,
                            "cover_mode": cover_mode,
                            "cover_src": cover_src,
                            "dest_kind": dest_kind,
                            "out_title": out_title,
                            "overwrite": bool(overwrite),
                        }
                    }
                },
            )

        if not do_process:
            return

        out("[phase] PROCESS")
        processed_labels = cast(
            list[str],
            books_meta.get("processed") if isinstance(books_meta.get("processed"), list) else [],
        )

        _mf_lock = threading.Lock()

        def _book_worker(entry: tuple[Any, str, str, Path, str, bool, Path]) -> None:
            b, title, cover_mode, dest_root2, out_title, overwrite, final_root2 = entry
            bi = [x[0] for x in enumerate([m[0] for m in meta], 1) if x[1] == b][0]
            with push_context(source=slug(src.name), book=b.label, phase="PROCESS"):
                _iflow._process_book(
                    i=bi,
                    n=len(meta),
                    b=b,
                    stage_run=stage_run,
                    dest_root=dest_root2,
                    author=author,
                    title=title,
                    out_title=out_title,
                    wipe=wipe_b,
                    cover_mode=cover_mode,
                    overwrite=overwrite,
                    cfg=cfg,
                    final_root=final_root2,
                    steps=steps,
                )
            with _mf_lock:
                processed_labels.append(b.label)
                update_manifest(stage_run, {"books": {"processed": processed_labels}})

        _opts = state.OPTS
        max_books = int(_opts.max_parallel_books) if _opts is not None else 2
        max_ff = int(_opts.max_parallel_ffmpeg) if _opts is not None else 2
        set_ffmpeg_limit(max_ff)
        import asyncio as _asyncio
        from audiomason.async_runner import run_parallel as _run_parallel

        _asyncio.run(_run_parallel(meta, _book_worker, max_concurrency=max_books))

        out("[phase] FINALIZE")

        if not (state.OPTS and state.OPTS.dry_run):
            for label in processed_labels:
                add_ignore(src, label)
            book_ignore_after = _iflow._ignore_norms(load_ignore(src))
            if all(_iflow._matches_ignore(b.label, book_ignore_after) for b in all_books):
                add_ignore(drop_root, src.name, source_list=True)
                out(f"[ignore] added: {src.name}")

        do_clean_inbox = bool(run_clean_inbox)
        if do_clean_inbox:
            if state.OPTS and state.OPTS.dry_run:
                out(f"[inbox] would clean: {src}")
            else:
                if src.is_dir():
                    shutil.rmtree(src, ignore_errors=True)
                else:
                    src.unlink(missing_ok=True)
                out(f"[inbox] cleaned: {src}")

        dec2 = cast(
            dict[str, object],
            load_manifest(stage_run).get("decisions")
            if isinstance(load_manifest(stage_run).get("decisions"), dict)
            else {},
        )
        do_clean = bool(dec2.get("clean_stage"))
        if do_clean:
            if state.OPTS is not None and state.OPTS.dry_run:
                out(f"[stage] would clean: {stage_run}")
            else:
                shutil.rmtree(stage_run, ignore_errors=True)
                out(f"[stage] cleaned: {stage_run}")
