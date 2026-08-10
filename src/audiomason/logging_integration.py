from __future__ import annotations

import contextlib
from collections.abc import Generator
from pathlib import Path
from typing import Protocol, TextIO, cast

import audiomason.state as state
from audiomason.log_bus import push_context, register_sink
from audiomason.util import ensure_dir, slug


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _resolve_processing_log_target(
    cfg: dict[str, object], stage_run: Path, src: Path
) -> Path | None:
    """Mirror of import_flow._pl_resolve_target, kept here to avoid import_flow bloat."""
    spec = _as_dict(cfg.get("processing_log"))
    enabled = bool(spec.get("enabled", False))
    if not enabled:
        return None
    raw = spec.get("path")
    if raw is None or str(raw).strip() == "":
        return stage_run / "processing.log"
    p = Path(str(raw)).expanduser()
    if str(raw).endswith("/") or (p.exists() and p.is_dir()):
        fname = f"{slug(src.name)}.log"
        return p / fname
    if p.suffix.lower() != ".log":
        p = p.with_suffix(".log")
    return p


@contextlib.contextmanager
def start_source_logging(
    cfg: dict[str, object], *, stage_run: Path, src: Path, explicit_target: Path | None = None
) -> Generator[None, None, None]:
    """Per-source logging context.

    - Registers a per-source sink if processing_log is enabled.
    - Pushes source context for prefixed interleaved logs.
    - Wraps prompt() and prompt_yes_no() to log questions/answers into the sink when present.
    """
    # Determine sink path
    target = (
        explicit_target
        if explicit_target is not None
        else _resolve_processing_log_target(cfg, stage_run, src)
    )
    fh: TextIO | None = None
    if target is not None and not (state.OPTS and state.OPTS.dry_run):
        ensure_dir(stage_run)
        ensure_dir(target.parent)
        fh = target.open("w", encoding="utf-8", buffering=1)

    # Wrap prompts to log into sink (if any)
    class _PromptFn(Protocol):
        def __call__(self, msg: str, default: str | None = None) -> str: ...

    class _PromptYesNoFn(Protocol):
        def __call__(self, msg: str, default_no: bool = True) -> bool: ...

    def _wrap_prompt(orig: _PromptFn) -> _PromptFn:
        def _p(msg: str, default: str | None = None) -> str:
            if fh is not None:
                with contextlib.suppress(Exception):
                    fh.write(f"[prompt] {msg} [default={default or ''}]\n")
            ans = orig(msg, default)
            if fh is not None:
                with contextlib.suppress(Exception):
                    fh.write(f"[answer] {ans}\n")
                    fh.flush()
            return ans

        return _p

    def _wrap_prompt_yes_no(orig: _PromptYesNoFn) -> _PromptYesNoFn:
        def _p(msg: str, default_no: bool = True) -> bool:
            if fh is not None:
                with contextlib.suppress(Exception):
                    fh.write(f"[prompt_yes_no] {msg} [default={'no' if default_no else 'yes'}]\n")
            ansb = orig(msg, default_no=default_no)
            if fh is not None:
                with contextlib.suppress(Exception):
                    fh.write(f"[answer] {'yes' if ansb else 'no'}\n")
                    fh.flush()
            return ansb

        return _p

    # Apply wrappers
    import audiomason.util as _util_mod  # late import to avoid cycles at module import time

    _orig_prompt = _util_mod.prompt
    _orig_prompt_yes_no = _util_mod.prompt_yes_no
    try:
        _util_mod.prompt = _wrap_prompt(_orig_prompt)
        _util_mod.prompt_yes_no = _wrap_prompt_yes_no(_orig_prompt_yes_no)
        ctx_sink = register_sink(fh) if fh is not None else contextlib.nullcontext()
        with ctx_sink, push_context(source=slug(src.name)):
            yield None
    finally:
        try:
            _util_mod.prompt = _orig_prompt
            _util_mod.prompt_yes_no = _orig_prompt_yes_no
        except Exception:
            pass
        if fh is not None:
            with contextlib.suppress(Exception):
                fh.flush()
                fh.close()


@contextlib.contextmanager
def book_phase_context(
    *, book: str | None = None, phase: str | None = None
) -> Generator[None, None, None]:
    """Context helper to tag logs with current book/phase."""
    with push_context(book=book, phase=phase):
        yield None
