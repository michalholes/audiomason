"""
Preflight undo helpers for interactive import flow.

Provides small drivers that catch AmUndoError (Ctrl+G) and step back across
adjacent prompts without growing import_flow.py further.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import audiomason.metadata_lookup as metadata_lookup
import audiomason.openlibrary as openlibrary
import audiomason.state as state
from audiomason.guess import guess_source_author_default
from audiomason.manifest import update_manifest
from audiomason.naming import normalize_name
from audiomason.preflight_resolve import pf_prompt, pf_prompt_yes_no, resolve_bool_config
from audiomason.util import AmUndoError, out


def decide_publish_wipe_clean(
    cfg: dict[str, object],
    *,
    stage_run: Path,
    decisions: dict[str, object],
    reuse_stage: bool,
    use_manifest_answers: bool,
) -> tuple[bool, bool, bool]:
    """Resolve publish, wipe_id3, and clean_stage with Ctrl+G undo.

    Persists decisions into manifest at stage_run as they are confirmed.
    """

    publish: bool | None = None
    wipe: bool | None = None
    clean_stage: bool | None = None

    default_publish = bool(decisions.get("publish")) if "publish" in decisions else False
    default_wipe = bool(decisions.get("wipe_id3")) if "wipe_id3" in decisions else False
    default_clean = bool(decisions.get("clean_stage")) if "clean_stage" in decisions else False

    # Fast path: reuse cached answers from manifest when allowed
    if (
        reuse_stage
        and use_manifest_answers
        and ("publish" in decisions)
        and ("wipe_id3" in decisions)
    ):
        publish = bool(decisions.get("publish"))
        wipe = bool(decisions.get("wipe_id3"))
    else:
        # Two-step loop with undo across publish -> wipe
        step_i = 0
        while step_i < 2:
            try:
                opts = state.OPTS
                if step_i == 0:
                    if opts is None or opts.publish is None:
                        publish = pf_prompt_yes_no(
                            cfg,
                            "publish",
                            "Publish after import?",
                            default_no=(not default_publish),
                        )
                    else:
                        publish = bool(opts.publish)
                else:
                    if opts is None or opts.wipe_id3 is None:
                        wipe = pf_prompt_yes_no(
                            cfg,
                            "wipe_id3",
                            "Full wipe ID3 tags before tagging?",
                            default_no=(not default_wipe),
                        )
                    else:
                        wipe = bool(opts.wipe_id3)
                step_i += 1
            except AmUndoError:
                step_i = max(0, step_i - 1)
        publish = bool(publish)
        wipe = bool(wipe)
        update_manifest(stage_run, {"decisions": {"publish": publish, "wipe_id3": wipe}})

    # Clean stage decision, with inline undo back to publish/wipe
    if reuse_stage and use_manifest_answers and ("clean_stage" in decisions):
        clean_stage = bool(decisions.get("clean_stage"))
    else:
        cfg_clean = resolve_bool_config(cfg, "clean_stage")
        if cfg_clean is not None:
            clean_stage = cfg_clean
        else:
            while True:
                try:
                    clean_stage = pf_prompt_yes_no(
                        cfg,
                        "clean_stage",
                        "Clean stage after successful import?",
                        default_no=(not default_clean),
                    )
                    break
                except AmUndoError:
                    # Go back and re-ask publish/wipe if requested
                    publish, wipe, _ = decide_publish_wipe_clean(
                        cfg,
                        stage_run=stage_run,
                        decisions=decisions,
                        reuse_stage=reuse_stage,
                        use_manifest_answers=use_manifest_answers,
                    )
        clean_stage = bool(clean_stage)
        update_manifest(stage_run, {"decisions": {"clean_stage": clean_stage}})

    assert publish is not None and wipe is not None and clean_stage is not None
    return bool(publish), bool(wipe), bool(clean_stage)


def prompt_author_with_undo(
    cfg: dict[str, object],
    *,
    default_author: str,
    batch_defaults: object | None,
    src_name: str,
    source_id3_context: list[dict[str, str]] | None,
    stage_run: Path,
) -> str:
    """Prompt for author with Ctrl+G undo support.

    Applies normalization and optional OpenLibrary/AI suggestion offering.
    """
    while True:
        try:
            bd_source_author: str | None = None
            if batch_defaults is not None:
                val_obj = cast(object | None, getattr(batch_defaults, "source_author", None))
                bd_source_author = val_obj if isinstance(val_obj, str) else None
            dflt_author = (
                default_author or bd_source_author or guess_source_author_default(src_name)
            )
            author = pf_prompt(
                cfg, "source_author", "[source] Author", str(dflt_author or "")
            ).strip()
            na = normalize_name(author)
            if na != author:
                out(f"[name] author suggestion: '{author}' -> '{na}'")
                # Ask whether to apply normalization (undo can backtrack here as well)
                if pf_prompt_yes_no(
                    cfg, "normalize_author", "Apply suggested author?", default_no=True
                ):
                    author = na

            if metadata_lookup.is_enabled(cfg):
                from json import dumps

                if state.DEBUG:
                    out(f"[ol] validate author: author='{author}'")
                author_context = f"source={src_name}"
                if source_id3_context:
                    author_context += "; id3=" + dumps(
                        source_id3_context, ensure_ascii=False, sort_keys=True
                    )
                # If batch_defaults exists, prefer OpenLibrary direct call for determinism here
                ar = (
                    openlibrary.validate_author(author)
                    if batch_defaults is not None
                    else metadata_lookup.validate_author(
                        author, cfg, context=author_context, artifact_dir=stage_run
                    )
                )
                if state.DEBUG:
                    out(
                        f"[ol] author result: ok={ar.ok}"
                        f" status={ar.status!r}"
                        f" hits={ar.hits}"
                        f" top={ar.top!r}"
                    )
                # Offer top suggestion if different
                top_raw: object | None = getattr(ar, "top", None)
                top = top_raw.strip() if isinstance(top_raw, str) else ""
                if top and top.casefold() != author.strip().casefold():
                    out(
                        f"{'[ai]' if ar.source == 'ai' else '[ol]'} author suggestion: "
                        f"'{author}' -> '{top}'"
                    )
                    if pf_prompt_yes_no(
                        cfg,
                        "normalize_author",
                        f"Use suggested author '{top}'?",
                        default_no=True,
                    ):
                        author = top

            if not author:
                # Enforce non-empty author; let undo happen if desired
                continue
            return author
        except AmUndoError:
            # Let caller step back further (publish/wipe) as needed by re-raising
            raise


def drive_top_level(
    cfg: dict[str, object],
    *,
    src_path: Path | None,
    drop_root: Path,
    clean_inbox_mode: str,
    list_sources: Callable[[], list[Path]],
    choose_sources: Callable[[list[Path]], list[Path]],
    run_for: Callable[[list[Path], bool, bool], None],
    ask_clean_inbox: Callable[[dict[str, object], bool], bool],
) -> None:
    """Top-level interactive driver: choose source -> clean_inbox -> run.

    - Catches AmUndoError from deeper flows and returns to choose source.
    - If clean_inbox_mode == 'ask', undo from deeper flows first returns to clean_inbox
      and ďalšie undo vráti na choose source.

    Callbacks:
      - list_sources() -> list[Path]
      - choose_sources(sources: list[Path]) -> list[Path]
      - run_for(picked_sources: list[Path], picked_all: bool, run_clean_inbox: bool) -> None
    """
    while True:
        # Step 0: choose sources
        if src_path is not None:
            sp = src_path.expanduser().resolve()
            dr = drop_root.expanduser().resolve()
            if sp == dr:
                sources: list[Path] = list_sources()
                try:
                    picked_sources: list[Path] = choose_sources(sources)
                except AmUndoError:
                    # nothing before, re-ask
                    continue
                picked_all = len(picked_sources) == len(sources) and all(
                    p in picked_sources for p in sources
                )
            else:
                picked_sources = [sp]
                picked_all = False
        else:
            sources = list_sources()
            try:
                picked_sources = choose_sources(sources)
            except AmUndoError:
                continue
            picked_all = len(picked_sources) == len(sources) and all(
                p in picked_sources for p in sources
            )

        # Step 1: inbox cleanup decision
        if clean_inbox_mode == "yes":
            run_clean_inbox = True
        elif clean_inbox_mode == "no":
            run_clean_inbox = False
        else:
            try:
                run_clean_inbox = ask_clean_inbox(cfg, False)
            except AmUndoError:
                # Back to choose sources
                continue

        # Step 2: run for picked sources
        try:
            run_for(picked_sources, picked_all, run_clean_inbox)
            return
        except AmUndoError:
            # If asking clean_inbox, return there first; otherwise go to choose sources
            if clean_inbox_mode == "ask":
                from contextlib import suppress

                with suppress(AmUndoError):
                    _ = ask_clean_inbox(cfg, False)
                continue
            else:
                continue
