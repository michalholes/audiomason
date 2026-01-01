from __future__ import annotations

from audiomason.util import AmConfigError

DEFAULT_ORDER = [
    "unpack",
    "convert",
    "chapters",
    "split",
    "rename",
    "tags",
    "cover",
    "publish",
]

REQUIRED = {
    "unpack",
    "convert",
    "rename",
    "tags",
    "cover",
}

def resolve_pipeline_steps(cfg: dict) -> list[str]:
    steps = cfg.get("pipeline_steps")
    if steps is None:
        return list(DEFAULT_ORDER)

    if not isinstance(steps, list) or not all(isinstance(s, str) for s in steps):
        raise AmConfigError("pipeline_steps must be a list of strings")

    unknown = [s for s in steps if s not in DEFAULT_ORDER]
    if unknown:
        raise AmConfigError(f"unknown pipeline step(s): {', '.join(unknown)}")

    if len(steps) != len(set(steps)):
        raise AmConfigError("duplicate pipeline step in pipeline_steps")

    missing = REQUIRED - set(steps)
    if missing:
        raise AmConfigError(f"missing required pipeline step(s): {', '.join(sorted(missing))}")

    return list(steps)
