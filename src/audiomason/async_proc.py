from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from audiomason.log_bus import emit as _emit
from audiomason.util import AmExternalToolError


@dataclass
class AsyncCompleted:
    returncode: int
    stdout: bytes | None = None
    stderr: bytes | None = None


async def run_cmd_async(
    cmd: Sequence[str | Path],
    *,
    check: bool = True,
    capture_stdout: bool = False,
    capture_stderr: bool = False,
) -> AsyncCompleted:
    """Async subprocess runner with optional streaming to log bus.

    - If capture_stdout/stderr is False, streams are read line-by-line and emitted via log bus.
    - If capture_* is True, bytes are captured and returned.
    - On non-zero exit and check=True, raises AmExternalToolError.
    - Respects KeyboardInterrupt via asyncio cancellation.
    """
    try:
        import audiomason.state as state

        opts = state.OPTS
    except Exception:
        opts = None

    args = [str(x) for x in cmd]
    if opts is not None and opts.dry_run:
        _emit("[dry-run] " + " ".join(args))
        return AsyncCompleted(
            returncode=0,
            stdout=b"" if capture_stdout else None,
            stderr=b"" if capture_stderr else None,
        )

    stdout_opt = asyncio.subprocess.PIPE
    stderr_opt = asyncio.subprocess.PIPE
    proc = await asyncio.create_subprocess_exec(*args, stdout=stdout_opt, stderr=stderr_opt)

    captured_out: bytearray | None = bytearray() if capture_stdout else None
    captured_err: bytearray | None = bytearray() if capture_stderr else None

    async def _pump(stream: asyncio.StreamReader, cap: bytearray | None) -> None:
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                if cap is not None:
                    cap.extend(line)
                else:
                    with contextlib.suppress(Exception):
                        _emit(line.decode("utf-8", errors="replace").rstrip("\n"))
        except Exception:
            # Never crash the runner due to stream errors
            pass

    pump_out = asyncio.create_task(
        _pump(proc.stdout, captured_out) if proc.stdout else asyncio.sleep(0)
    )
    pump_err = asyncio.create_task(
        _pump(proc.stderr, captured_err) if proc.stderr else asyncio.sleep(0)
    )

    try:
        rc = await proc.wait()
    finally:
        with contextlib.suppress(Exception):
            await asyncio.gather(pump_out, pump_err)

    if check and rc != 0:
        raise AmExternalToolError(f"External tool failed: {args[0]} (exit {rc})")

    return AsyncCompleted(
        returncode=rc,
        stdout=bytes(captured_out) if captured_out is not None else None,
        stderr=bytes(captured_err) if captured_err is not None else None,
    )
