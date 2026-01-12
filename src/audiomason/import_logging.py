from __future__ import annotations

import sys
from contextlib import contextmanager


@contextmanager
def tee_stdout(to):
    orig = sys.stdout
    try:
        sys.stdout = to
        yield
    finally:
        sys.stdout = orig


@contextmanager
def tee_stderr(to):
    orig = sys.stderr
    try:
        sys.stderr = to
        yield
    finally:
        sys.stderr = orig
