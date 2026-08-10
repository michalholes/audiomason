from __future__ import annotations

import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import TextIO

# Lightweight logging bus with contextual prefixes and optional per-source sink.
# Keeps stdout intact, supports interleaving with a global console lock.

_console_lock = threading.Lock()

_sink_var: ContextVar[TextIO | None] = ContextVar("audiomason_log_sink", default=None)
_src_var: ContextVar[str | None] = ContextVar("audiomason_log_src", default=None)
_book_var: ContextVar[str | None] = ContextVar("audiomason_log_book", default=None)
_phase_var: ContextVar[str | None] = ContextVar("audiomason_log_phase", default=None)


def _prefix() -> str:
    parts: list[str] = []
    src = _src_var.get()
    if src:
        parts.append(f"src={src}")
    book = _book_var.get()
    if book:
        parts.append(f"book={book}")
    phase = _phase_var.get()
    if phase:
        parts.append(f"phase={phase}")
    return ("[" + "][".join(parts) + "] ") if parts else ""


def emit(line: str) -> None:
    """Atomically write a single line to console and active sink (if any).

    Expects a single logical log message (line). Newline is appended for sink
    when missing to keep consistent formatting.
    """
    msg = str(line)
    sink = _sink_var.get()
    pfx = _prefix()

    # Console
    with _console_lock:
        try:
            # print() adds a newline; we add prefix only for console to make
            # interleaving readable. The message may already include [TRACE].
            sys.stdout.write(pfx + msg + "\n")
            sys.stdout.flush()
        except BrokenPipeError:
            # Respect pipelines
            return

    # Sink (no interleaving concern; each emit writes as one line)
    if sink is not None:
        try:
            sink.write(pfx + msg)
            if not msg.endswith("\n"):
                sink.write("\n")
            sink.flush()
        except Exception:
            # Never break the run due to logging sink failures.
            pass


@contextmanager
def register_sink(fh: TextIO) -> Generator[None, None, None]:
    """Activate a file-like sink for the current context."""
    token: Token[TextIO | None] = _sink_var.set(fh)
    try:
        yield None
    finally:
        _sink_var.reset(token)


@contextmanager
def push_context(
    *, source: str | None = None, book: str | None = None, phase: str | None = None
) -> Generator[None, None, None]:
    """Temporarily set logging context fields."""
    t_src: Token[str | None] | None = None
    t_book: Token[str | None] | None = None
    t_phase: Token[str | None] | None = None
    try:
        if source is not None:
            t_src = _src_var.set(source)
        if book is not None:
            t_book = _book_var.set(book)
        if phase is not None:
            t_phase = _phase_var.set(phase)
        yield None
    finally:
        if t_phase is not None:
            _phase_var.reset(t_phase)
        if t_book is not None:
            _book_var.reset(t_book)
        if t_src is not None:
            _src_var.reset(t_src)
