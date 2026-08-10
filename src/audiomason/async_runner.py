from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


async def run_parallel(
    items: Sequence[T], worker: Callable[[T], None], *, max_concurrency: int
) -> None:
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))

    async def _one(it: T) -> None:
        async with sem:
            await asyncio.to_thread(worker, it)

    tasks = [asyncio.create_task(_one(it)) for it in items]
    err: BaseException | None = None
    for t in tasks:
        try:
            await t
        except BaseException as e:  # noqa: BLE001
            err = e
            # Cancel outstanding tasks
            for tt in tasks:
                if tt is not t:
                    tt.cancel()
            break
    if err is not None:
        raise err


async def run_parallel_async(
    items: Sequence[T], worker: Callable[[T], Awaitable[None]], *, max_concurrency: int
) -> None:
    """Run an async worker over items with a concurrency limit.

    - Uses an asyncio.Semaphore to bound in-flight tasks.
    - Cancels outstanding tasks on the first error and re-raises it.
    - Deterministic semantics mirror the sync variant above.
    """
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))

    async def _one(it: T) -> None:
        async with sem:
            await worker(it)

    tasks = [asyncio.create_task(_one(it)) for it in items]
    err: BaseException | None = None
    for t in tasks:
        try:
            await t
        except BaseException as e:  # noqa: BLE001
            err = e
            for tt in tasks:
                if tt is not t:
                    tt.cancel()
            break
    if err is not None:
        raise err
