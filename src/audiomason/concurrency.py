from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

_ffmpeg_sem_lock = threading.Lock()
_ffmpeg_sem: threading.Semaphore | None = None


def set_ffmpeg_limit(n: int) -> None:
    """Set maximum concurrent ffmpeg processes.

    n <= 0 means unlimited (no semaphore gating).
    """
    global _ffmpeg_sem
    with _ffmpeg_sem_lock:
        # Recreate semaphore with new capacity.
        _ffmpeg_sem = None if n <= 0 else threading.Semaphore(int(n))


@contextmanager
def ffmpeg_slot() -> Generator[None, None, None]:
    sem = _ffmpeg_sem
    if sem is None:
        yield None
        return
    sem.acquire()
    try:
        yield None
    finally:
        sem.release()


@asynccontextmanager
async def async_ffmpeg_slot() -> AsyncGenerator[None, None]:
    """Async wrapper around the global ffmpeg threading semaphore.

    Works across threads and event loops by acquiring the semaphore in a worker thread.
    """
    sem = _ffmpeg_sem
    if sem is None:
        yield None
        return
    await asyncio.to_thread(sem.acquire)
    try:
        yield None
    finally:
        sem.release()
