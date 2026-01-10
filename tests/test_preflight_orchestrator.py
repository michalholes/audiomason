# Issue #93: Preflight Orchestrator Tests
from __future__ import annotations

from audiomason.preflight_orchestrator import PreflightContext, PreflightOrchestrator
from audiomason.preflight_registry import MIN_CONTEXT_BOOKS, MIN_CONTEXT_NONE, MIN_CONTEXT_SOURCE


def test_orchestrator_pending_when_too_early():
    cfg = {}
    o = PreflightOrchestrator(cfg)

    ctx = PreflightContext(cfg=cfg, context_level=MIN_CONTEXT_NONE)
    plan = o.plan(ctx)

    assert "choose_source" in plan.executed
    assert "choose_books" in plan.pending
    assert "book_title" in plan.pending


def test_orchestrator_materialize_after_context_progression():
    cfg = {}
    o = PreflightOrchestrator(cfg)

    executed: list[str] = []

    def _exec(k: str) -> None:
        executed.append(k)

    ctx = PreflightContext(cfg=cfg, context_level=MIN_CONTEXT_NONE)
    plan = o.plan(ctx)

    ctx.context_level = MIN_CONTEXT_SOURCE
    o.materialize_pending(ctx, plan, executor=_exec)
    assert "choose_books" in executed

    ctx.context_level = MIN_CONTEXT_BOOKS
    o.materialize_pending(ctx, plan, executor=_exec)
    assert "book_title" in executed
