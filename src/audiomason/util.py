from __future__ import annotations

import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Optional


# ======================
# Controlled exits (Issue #41)
# ======================
class AmExit(RuntimeError):
    """Expected termination (no traceback)."""
    exit_code: int = 2

    def __init__(self, msg: str, exit_code: int | None = None):
        super().__init__(msg)
        if exit_code is not None:
            self.exit_code = int(exit_code)


class AmConfigError(AmExit):
    pass


class AmValidationError(AmExit):
    pass


class AmExternalToolError(AmExit):
    pass


class AmAbort(AmExit):
    exit_code = 130


def run_cmd(cmd, *, tool: str | None = None, install: str | None = None, **kwargs):
    """subprocess.run wrapper that turns expected failures into AmExit."""
    try:
        kwargs.pop("check", None)
        return subprocess.run(cmd, check=True, **kwargs)
    except FileNotFoundError as e:
        name = tool or (cmd[0] if isinstance(cmd, (list, tuple)) and cmd else str(cmd))
        raise AmExternalToolError(f"Missing external tool: {name} (install {install or name})") from e
    except subprocess.CalledProcessError as e:
        name = tool or (cmd[0] if isinstance(cmd, (list, tuple)) and cmd else "external tool")
        raise AmExternalToolError(f"External tool failed: {name} (exit {e.returncode})") from e



def out(msg: str) -> None:
    try:
        import audiomason.state as state

        # --quiet => only errors
        if bool(getattr(getattr(state, "OPTS", None), "quiet", False)):
            m = str(msg)
            if not m.lstrip().startswith(("[ERROR]", "ERROR:", "[FATAL]", "FATAL:")):
                return

        if bool(getattr(state, "DEBUG", False)):
            print(f"[TRACE] {msg}", flush=True)
        else:
            print(msg, flush=True)
    except BrokenPipeError:
        return
def die(msg: str, code: int = 2) -> None:
    # Backward-compatible helper: raise a controlled exit instead of printing/traceback.
    m = str(msg)
    cls = AmExit
    if m.startswith("Missing external tool:"):
        cls = AmExternalToolError
    elif m.startswith("Invalid configuration"):
        cls = AmConfigError
    raise cls(m, exit_code=code)


def strip_diacritics(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def clean_text(s: str) -> str:
    s = strip_diacritics(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def slug(s: str) -> str:
    s = strip_diacritics(s)
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "Unknown"


def two(n: int) -> str:
    return f"{n:02d}"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def unique_path(p: Path) -> Path:
    outp = p
    i = 2
    while outp.exists():
        outp = Path(str(p) + f"__{i}")
        i += 1
    return outp


def prompt(msg: str, default: Optional[str] = None) -> str:
    try:
        import audiomason.state as state
        _opts = getattr(state, 'OPTS', None)
    except Exception:
        _opts = None
    if _opts is not None and getattr(_opts, 'yes', False):
        return default or ""
    try:
        if default is not None and default != "":
            s = input(f"{msg} [{default}]: ").strip()
            return s if s else default
        s = input(f"{msg}: ").strip()
        return s
    except KeyboardInterrupt as e:
        raise AmAbort("cancelled by user") from e
        raise
        return default or ""


def prompt_yes_no(msg: str, default_no: bool = True) -> bool:
    try:
        import audiomason.state as state
        _opts = getattr(state, 'OPTS', None)
    except Exception:
        _opts = None
    if _opts is not None and getattr(_opts, 'yes', False):
        return False if default_no else True
    d = "y/N" if default_no else "Y/n"
    try:
        ans = input(f"{msg} [{d}] ").strip().lower()
    except KeyboardInterrupt as e:
        raise AmAbort("cancelled by user") from e
    if not ans:
        return False if default_no else True
    return ans in {"y", "yes"}


def prune_empty_dirs(start: Path, stop_at: Path) -> None:
    try:
        p = start
        while p != stop_at and p.exists():
            if any(p.iterdir()):
                break
            p.rmdir()
            p = p.parent
    except Exception:
        pass


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), flags=re.I))


def find_archive_match(archive_ro: str, author_hint: str, book_hint: str):
    """
    Best-effort lookup in archive_ro for an existing book.
    Returns (author_dirname, book_dirname) if exactly one strong match is found,
    otherwise (None, None).

    Matching is conservative: ignore very short hints to avoid false positives.
    """
    from pathlib import Path

    if not archive_ro:
        return (None, None)

    root = Path(archive_ro)
    if not root.exists():
        return (None, None)

    a = (author_hint or "").strip()
    b = (book_hint or "").strip()

    # Too short hints are ambiguous (e.g. "sp")
    if len(b) < 4 and len(a) < 4:
        return (None, None)

    a_slug = slug(a).lower() if a else ""
    b_slug = slug(b).lower() if b else ""

    hits = []

    for author_dir in root.iterdir():
        if not author_dir.is_dir():
            continue

        # if author hint exists, require author match
        if a_slug and slug(author_dir.name).lower() != a_slug and a_slug not in slug(author_dir.name).lower():
            continue

        for book_dir in author_dir.iterdir():
            if not book_dir.is_dir():
                continue
            bd = book_dir.name
            bd_slug = slug(bd).lower()

            if b_slug:
                if bd_slug == b_slug:
                    hits.append((author_dir.name, book_dir.name, 2))
                elif b_slug in bd_slug:
                    hits.append((author_dir.name, book_dir.name, 1))
            else:
                # no book hint: don't guess
                continue

    # prefer exact match
    exact = [(a,b) for a,b,score in hits if score == 2]
    if len(exact) == 1:
        return exact[0]

    # if only one fuzzy hit overall, accept
    uniq = []
    seen = set()
    for a,b,_ in hits:
        if (a,b) not in seen:
            seen.add((a,b))
            uniq.append((a,b))
    if len(uniq) == 1:
        return uniq[0]

    return (None, None)

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
        # Respect --quiet (runtime state, not a stale imported name)
        try:
            import audiomason.state as state
            if getattr(getattr(state, "OPTS", None), "quiet", False):
                return
        except Exception:
            pass
        print(f"[TRACE-OP] {msg}", flush=True)

    # --- subprocess ---
    _sub_run = subprocess.run
    _sub_cc = subprocess.check_call
    _sub_co = subprocess.check_output
    _sub_popen = subprocess.Popen

    def run(*args, **kwargs):
        _t(f"subprocess.run args={args!r} kwargs={kwargs!r}")
        return _sub_run(*args, **kwargs)

    def check_call(*args, **kwargs):
        _t(f"subprocess.check_call args={args!r} kwargs={kwargs!r}")
        return _sub_cc(*args, **kwargs)

    def check_output(*args, **kwargs):
        _t(f"subprocess.check_output args={args!r} kwargs={kwargs!r}")
        return _sub_co(*args, **kwargs)

    class Popen(_sub_popen):
        def __init__(self, *args, **kwargs):
            _t(f"subprocess.Popen args={args!r} kwargs={kwargs!r}")
            super().__init__(*args, **kwargs)

    subprocess.run = run
    subprocess.check_call = check_call
    subprocess.check_output = check_output
    subprocess.Popen = Popen

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
            def _wrap(fn, nm):
                def w(*args, **kwargs):
                    _t(f"shutil.{nm} args={args!r} kwargs={kwargs!r}")
                    return fn(*args, **kwargs)
                return w
            setattr(shutil, name, _wrap(fn, name))

    # --- os (covers Path ops internally: rename/unlink/mkdir/etc.) ---
    for name in ["rename", "replace", "remove", "unlink", "mkdir", "rmdir", "makedirs", "chmod", "chown", "utime"]:
        if hasattr(os, name):
            fn = getattr(os, name)
            def _wrap(fn, nm):
                def w(*args, **kwargs):
                    _t(f"os.{nm} args={args!r} kwargs={kwargs!r}")
                    return fn(*args, **kwargs)
                return w
            setattr(os, name, _wrap(fn, name))

