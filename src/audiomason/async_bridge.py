from __future__ import annotations

import asyncio
import atexit
import contextlib
from collections.abc import Coroutine
from threading import Event, Thread
from typing import TypeVar

_loop: asyncio.AbstractEventLoop | None = None
_thread: Thread | None = None
_stopped = Event()

T = TypeVar("T")


def _runner(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()
    _stopped.set()


def start_global_loop() -> None:
    global _loop, _thread
    if _loop is not None:
        return
    loop = asyncio.new_event_loop()
    t = Thread(target=_runner, args=(loop,), name="am-async-loop", daemon=True)
    t.start()
    _loop = loop
    _thread = t


def stop_global_loop() -> None:
    global _loop, _thread
    if _loop is None:
        return
    with contextlib.suppress(Exception):
        _loop.call_soon_threadsafe(_loop.stop)
    if _thread is not None:
        _thread.join(timeout=1.0)
    _thread = None
    _loop = None


def register_atexit_stop() -> None:
    atexit.register(stop_global_loop)


def run_coro(awaitable: Coroutine[object, object, T]) -> T:
    """Run a coroutine on the global loop if present, else create a temporary loop.

    Keeps import_flow/preflight code simple while unifying loop usage across the process.
    """
    if _loop is None:
        return asyncio.run(awaitable)
    fut = asyncio.run_coroutine_threadsafe(awaitable, _loop)
    return fut.result()
