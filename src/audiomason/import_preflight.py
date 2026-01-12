from __future__ import annotations

from typing import Iterable, Tuple

import audiomason.state as state
from audiomason.preflight import run_preflight as _run_preflight_impl
from audiomason.preflight_registry import DEFAULT_PREFLIGHT_STEPS


def run_preflight(
    *,
    cfg: dict,
    steps: Iterable[str] | None,
) -> Tuple[bool, bool]:
    if steps is None:
        steps = DEFAULT_PREFLIGHT_STEPS

    _run_preflight_impl(cfg=cfg, steps=list(steps))

    opts = state.OPTS
    if opts is None:
        raise RuntimeError("preflight did not initialize state.OPTS")

    return bool(opts.publish), bool(opts.wipe_id3)
