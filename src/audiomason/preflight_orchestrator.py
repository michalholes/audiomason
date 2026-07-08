# Issue #93: Preflight Orchestrator
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import cast

from audiomason.preflight_registry import (
    MIN_CONTEXT_BOOKS,
    MIN_CONTEXT_NONE,
    MIN_CONTEXT_SOURCE,
    REGISTRY,
    default_steps,
    validate_steps_list,
)

_Cfg = Mapping[str, object]


def _empty_str_list() -> list[str]:
    return []


@dataclass
class PreflightContext:
    # Minimal deterministic context carrier.
    cfg: _Cfg
    context_level: str = MIN_CONTEXT_NONE  # none/source_selected/books_selected
    picked_sources: list[str] | None = None
    picked_books: list[str] | None = None


@dataclass
class PreflightPlan:
    order: list[str]
    pending: list[str] = field(default_factory=_empty_str_list)
    executed: list[str] = field(default_factory=_empty_str_list)


class PreflightOrchestrator:
    def __init__(self, cfg: _Cfg):
        self.cfg = cfg

    def resolve_order(self) -> list[str]:
        raw = self.cfg.get("preflight_steps")
        if raw is None:
            out: list[str] = default_steps()
            return list(out)
        if not isinstance(raw, list):
            raise ValueError("preflight_steps must be a list of step keys")
        out2 = validate_steps_list(cast(list[str], raw))
        return list(out2)

    def _eligible(self, ctx: PreflightContext, key: str) -> bool:
        meta = REGISTRY[key]
        need = meta.min_context
        if need == MIN_CONTEXT_NONE:
            return True
        if need == MIN_CONTEXT_SOURCE:
            return ctx.context_level in (MIN_CONTEXT_SOURCE, MIN_CONTEXT_BOOKS)
        if need == MIN_CONTEXT_BOOKS:
            return ctx.context_level == MIN_CONTEXT_BOOKS
        return False

    def plan(self, ctx: PreflightContext) -> PreflightPlan:
        order = self.resolve_order()
        pending: list[str] = []
        exec_now: list[str] = []
        for k in order:
            if self._eligible(ctx, k):
                exec_now.append(k)
            else:
                pending.append(k)
        return PreflightPlan(order=order, pending=pending, executed=exec_now)

    def materialize_pending(
        self,
        ctx: PreflightContext,
        plan: PreflightPlan,
        *,
        executor: Callable[[str], None],
    ) -> None:
        done: set[str] = set()
        pending2: list[str] = []
        for k in plan.order:
            if k in done:
                continue
            if self._eligible(ctx, k):
                executor(k)
                done.add(k)
            else:
                pending2.append(k)
        plan.pending = pending2
