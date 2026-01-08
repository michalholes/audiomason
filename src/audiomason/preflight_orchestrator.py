# Issue #93: Preflight Orchestrator
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from audiomason.preflight_registry import (
    MIN_CONTEXT_NONE,
    default_steps,
)


@dataclass
class PreflightContext:
    # RUN1 scaffolding for future dispatcher + pending decisions.
    cfg: dict
    context_level: str = MIN_CONTEXT_NONE
    picked_sources: Optional[list[Any]] = None
    picked_books: Optional[list[Any]] = None

    decisions_run: dict = field(default_factory=dict)
    decisions_source: dict = field(default_factory=dict)
    decisions_book: dict = field(default_factory=dict)


class PreflightOrchestrator:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def resolve_order(self) -> list[str]:
        # RUN1: keep behavior unchanged — if config absent, use default registry ordering.
        raw = self.cfg.get("preflight_steps", None)
        if raw is None:
            out = default_steps()
            self.cfg["_preflight_steps_list"] = list(out)
            return list(out)

        # Validation and dispatcher execution are introduced in later runs.
        if not isinstance(raw, list):
            raise ValueError("preflight_steps must be a list of step keys")
        out2: list[str] = [str(x).strip() for x in raw if str(x).strip()]
        self.cfg["_preflight_steps_list"] = list(out2)
        return list(out2)
