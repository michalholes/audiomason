from __future__ import annotations
# ruff: noqa: I001
# mypy: ignore-errors

import json
from importlib import import_module
from pathlib import Path
from typing import cast

import audiomason.state as state
from audiomason.async_runner import run_parallel_async
from audiomason.source_lifecycle_async import run_source_lifecycle_async
from audiomason.util import die, ensure_dir, out


async def run_import_async(cfg: dict[str, object], src_path: Path | None = None) -> None:
    """Async import driver that reuses existing per-source logic and prompts.

    Behavior-parity goal: mirrors import_flow.run_import ordering and prompts,
    but uses native async parallelization for multi-source PROCESS.
    """
    imp = import_module("audiomason.import_flow")

    # Validate/resolve pipeline early (parity with sync flow)
    steps = imp._resolved_preflight_steps(cfg)
    if getattr(state, "DEBUG", False):
        out(f"[debug] pipeline order: {' -> '.join(steps)}")

    # Resolve clean_inbox mode
    clean_inbox_mode = str(
        getattr(getattr(state, "OPTS", None), "clean_inbox_mode", cfg.get("clean_inbox", "no"))
    )
    if clean_inbox_mode not in {"ask", "yes", "no"}:
        die(
            f"Invalid configuration: clean_inbox must be one of ask|yes|no,"
            f" got: {clean_inbox_mode!r}"
        )
    if (
        getattr(state, "OPTS", None) and getattr(state.OPTS, "yes", False)
    ) and clean_inbox_mode == "ask":
        die(
            "Non-interactive run requires an explicit inbox cleanup decision:"
            " set --clean-inbox yes|no (or config clean_inbox: yes|no)"
        )

    # Roots
    drop_root = imp.get_drop_root(cfg)
    stage_root = imp.get_stage_root(cfg)
    archive_root = imp.get_archive_root(cfg)
    output_root = imp.get_output_root(cfg)
    for d in (drop_root, stage_root, archive_root, output_root):
        ensure_dir(d)

    stage_runs_for_json: list[Path] = []

    # Apply network settings (limits/delays) if configured (parity)
    def _as_dict(val: object) -> dict[str, object]:
        return cast(dict[str, object], val) if isinstance(val, dict) else {}

    def _int_cfg(val: object, d: int) -> int:
        try:
            if isinstance(val, bool):
                return int(val)
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                return int(val.strip())
        except Exception:
            return d
        return d

    try:
        net = _as_dict(cfg.get("network"))
        hl = _as_dict(net.get("host_limits") or {})
        hd = _as_dict(net.get("host_delay_ms") or {})
        from audiomason import googlebooks as _gb
        from audiomason import openlibrary as _ol

        ol_limit = _int_cfg(hl.get("openlibrary", 1), 1)
        gb_limit = _int_cfg(hl.get("googlebooks", 1), 1)
        ol_delay = _int_cfg(hd.get("openlibrary", 0), 0)
        gb_delay = _int_cfg(hd.get("googlebooks", 0), 0)
        _ol.set_host_limit(ol_limit)
        _gb.set_host_limit(gb_limit)
        _ol.set_host_delay_ms(ol_delay)
        _gb.set_host_delay_ms(gb_delay)
        if getattr(state, "DEBUG", False):
            out(f"[TRACE] [net] openlibrary limit={ol_limit} delay_ms={ol_delay}")
            out(f"[TRACE] [net] googlebooks limit={gb_limit} delay_ms={gb_delay}")
    except Exception:
        pass

    # Forced flag if explicit src_path
    _forced_flag = False
    try:
        if src_path is not None:
            rp = imp._resolve_source_arg(drop_root, src_path)
            _forced_flag = rp.expanduser().resolve() != drop_root.expanduser().resolve()
    except Exception:
        _forced_flag = False

    # List and choose sources (reuse existing prompts)
    sources = imp._list_sources(drop_root)
    picked_sources = imp._choose_source(cfg, sources)

    # Decide run_clean_inbox once at run-level
    if clean_inbox_mode == "yes":
        run_clean_inbox = True
    elif clean_inbox_mode == "no":
        run_clean_inbox = False
    else:
        # ask
        run_clean_inbox = cast(
            bool,
            imp.pf_prompt_yes_no(cfg, "clean_inbox", "Clean inbox after successful import?", True),
        )

    # Phases: match import_flow semantics
    picked_all = len(picked_sources) == len(sources) and len(picked_sources) > 1
    phases = ["preflight", "process"] if picked_all else ["combined"]

    async def _run_one(src: Path, *, do_process: bool) -> None:
        await run_source_lifecycle_async(
            cfg,
            src=src,
            si=(picked_sources.index(src) + 1) if src in picked_sources else 1,
            total=len(picked_sources),
            phase=("process" if do_process and picked_all else "combined"),
            do_process=do_process,
            run_clean_inbox=(run_clean_inbox if do_process else False),
            drop_root=drop_root,
            stage_root=stage_root,
            archive_root=archive_root,
            output_root=output_root,
            stage_runs_for_json=stage_runs_for_json,
            steps=steps,
            forced_flag=_forced_flag,
        )

    for phase in phases:
        do_process = phase != "preflight"
        if do_process and len(picked_sources) > 1:
            # PROCESS multiple sources in parallel
            await run_parallel_async(
                picked_sources,
                lambda s: _run_one(s, do_process=True),
                max_concurrency=int(getattr(state.OPTS, "max_parallel_sources", 1)),
            )
        else:
            # PRE-FLIGHT or single source => serial order
            for s in picked_sources:
                await _run_one(s, do_process=do_process)

    # Machine-readable report
    if getattr(state, "OPTS", None) is not None and getattr(state.OPTS, "json", False):
        report = imp._build_json_report(stage_runs_for_json)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
