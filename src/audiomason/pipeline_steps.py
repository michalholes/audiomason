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

# Ordering constraints (fail fast for impossible pipelines in current implementation):
# - stage steps must happen before PROCESS steps (need mp3s + output dir)
# - chapters/split are stage-level (even if currently no-op)
ORDER_CONSTRAINTS: list[tuple[str, str]] = [
    ("unpack", "convert"),
    ("convert", "chapters"),
    ("chapters", "split"),
    ("convert", "rename"),
    ("convert", "tags"),
    ("convert", "cover"),
    ("convert", "publish"),
    ("split", "rename"),
    ("split", "tags"),
    ("split", "cover"),
    ("split", "publish"),
]


def _validate_step_order(steps: list[str]) -> None:
    idx = {name: i for i, name in enumerate(steps)}
    for a, b in ORDER_CONSTRAINTS:
        if a in idx and b in idx and idx[a] > idx[b]:
            raise AmConfigError(f"invalid pipeline_steps order: '{a}' must come before '{b}'")


def resolve_pipeline_steps(cfg: dict) -> list[str]:
    steps = cfg.get("pipeline_steps")
    if steps is None:
        resolved = list(DEFAULT_ORDER)
        _validate_step_order(resolved)
        return resolved

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

    _validate_step_order(list(steps))
    return list(steps)
