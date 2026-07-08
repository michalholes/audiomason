# mypy: ignore-errors
# pyright: reportConstantRedefinition=false, reportCallIssue=false, reportArgumentType=false
# ruff: noqa: ANN401
"""Monkey-patching trace wrappers for subprocess/shutil/os.

This module is inherently untyped because it wraps stdlib functions
with *args/**kwargs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from typing import Any, cast

_TRACE_ENABLED = False


def enable_trace() -> None:
    """
    ISSUE #9: Full TRACE mode.
    When enabled, prints every low-level action (subprocess/shutil/os) as [TRACE-OP] ...
    Deterministic: no behavior change, logging only.
    """
    global _TRACE_ENABLED
    if _TRACE_ENABLED:
        return
    _TRACE_ENABLED = True

    def _t(msg: str) -> None:
        try:
            import audiomason.state as state

            if state.OPTS is not None and state.OPTS.quiet:
                return
        except Exception:
            pass
        print(f"[TRACE-OP] {msg}", flush=True)

    # --- subprocess ---
    _sub_run = subprocess.run
    _sub_cc = subprocess.check_call
    _sub_co = subprocess.check_output
    _sub_popen = subprocess.Popen

    def run(*args: Any, **kwargs: Any) -> Any:
        _t(f"subprocess.run args={args!r} kwargs={kwargs!r}")
        return cast(Callable[..., object], _sub_run)(*args, **kwargs)

    def check_call(*args: Any, **kwargs: Any) -> Any:
        _t(f"subprocess.check_call args={args!r} kwargs={kwargs!r}")
        return cast(Callable[..., object], _sub_cc)(*args, **kwargs)

    def check_output(*args: Any, **kwargs: Any) -> Any:
        _t(f"subprocess.check_output args={args!r} kwargs={kwargs!r}")
        return cast(Callable[..., object], _sub_co)(*args, **kwargs)

    class TracePopen(subprocess.Popen[bytes]):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _t(f"subprocess.Popen args={args!r} kwargs={kwargs!r}")
            super().__init__(*args, **kwargs)

    subprocess.run = run  # type: ignore[assignment]
    subprocess.check_call = check_call  # type: ignore[assignment]
    subprocess.check_output = check_output  # type: ignore[assignment]
    subprocess.Popen = TracePopen  # type: ignore[assignment]

    # --- shutil ---
    for name in [
        "copy2",
        "copytree",
        "rmtree",
        "move",
        "copyfile",
        "copymode",
        "copystat",
        "make_archive",
        "unpack_archive",
    ]:
        if hasattr(shutil, name):
            fn = getattr(shutil, name)

            def _wrap(fn: object, nm: str) -> object:
                def w(*args: Any, **kwargs: Any) -> Any:
                    _t(f"shutil.{nm} args={args!r} kwargs={kwargs!r}")
                    return cast(Callable[..., object], fn)(*args, **kwargs)

                return w

            setattr(shutil, name, _wrap(fn, name))

    # --- os (covers Path ops internally: rename/unlink/mkdir/etc.) ---
    for name in [
        "rename",
        "replace",
        "remove",
        "unlink",
        "mkdir",
        "rmdir",
        "makedirs",
        "chmod",
        "chown",
        "utime",
    ]:
        if hasattr(os, name):
            fn = getattr(os, name)

            def _wrap(fn: object, nm: str) -> object:
                def w(*args: Any, **kwargs: Any) -> Any:
                    _t(f"os.{nm} args={args!r} kwargs={kwargs!r}")
                    return cast(Callable[..., object], fn)(*args, **kwargs)

                return w

            setattr(os, name, _wrap(fn, name))
