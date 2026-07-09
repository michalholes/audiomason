from __future__ import annotations

import re
import subprocess
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import IO


# ======================
# Controlled exits (Issue #41)
# ======================
class AmExitError(RuntimeError):
    """Expected termination (no traceback)."""

    exit_code: int = 2

    def __init__(self, msg: str, exit_code: int | None = None):
        super().__init__(msg)
        if exit_code is not None:
            self.exit_code = int(exit_code)


class AmConfigError(AmExitError):
    pass


class AmValidationError(AmExitError):
    pass


class AmExternalToolError(AmExitError):
    pass


class AmAbortError(AmExitError):
    exit_code = 130


def run_cmd(
    cmd: Sequence[str | Path],
    *,
    check: bool = True,
    stdout: int | IO[str] | None = None,
    tool: str | None = None,
    install: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """subprocess.run wrapper that turns expected failures into AmExitError."""
    try:
        return subprocess.run(cmd, check=check, stdout=stdout)
    except FileNotFoundError as e:
        name = tool or (cmd[0] if isinstance(cmd, (list, tuple)) and cmd else str(cmd))
        raise AmExternalToolError(
            f"Missing external tool: {name} (install {install or name})"
        ) from e
    except subprocess.CalledProcessError as e:
        name = tool or (cmd[0] if isinstance(cmd, (list, tuple)) and cmd else "external tool")
        raise AmExternalToolError(f"External tool failed: {name} (exit {e.returncode})") from e


def out(msg: str) -> None:
    try:
        import audiomason.state as state

        # --quiet => only errors
        opts = state.OPTS
        if opts is not None and opts.quiet:
            m = str(msg)
            if not m.lstrip().startswith(("[ERROR]", "ERROR:", "[FATAL]", "FATAL:")):
                return

        if state.DEBUG:
            print(f"[TRACE] {msg}", flush=True)
        else:
            print(msg, flush=True)
    except BrokenPipeError:
        return


def die(msg: str, code: int = 2) -> None:
    # Backward-compatible helper: raise a controlled exit instead of printing/traceback.
    m = str(msg)
    cls = AmExitError
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


def prompt(msg: str, default: str | None = None) -> str:
    try:
        import audiomason.state as state

        opts = state.OPTS
    except Exception:
        opts = None
    if opts is not None and opts.yes:
        return default or ""
    try:
        if default is not None and default != "":
            s = input(f"{msg} [{default}]: ")
        else:
            s = input(f"{msg}: ")
        # Ctrl+G (BEL, \x07) as inline-undo.
        # If the line consists only of BELs and/or whitespace, treat as undo.
        if s and s.replace("\x07", "").strip() == "":
            raise AmUndoError("undo")
        s = s.strip()
        if default is not None and default != "":
            return s if s else default
        return s
    except KeyboardInterrupt as e:
        raise AmAbortError("cancelled by user") from e
        raise
        return default or ""


def prompt_yes_no(msg: str, default_no: bool = True) -> bool:
    try:
        import audiomason.state as state

        opts = state.OPTS
    except Exception:
        opts = None
    if opts is not None and opts.yes:
        return not default_no
    d = "y/N" if default_no else "Y/n"
    try:
        raw = input(f"{msg} [{d}] ")
        # Ctrl+G (BEL) as inline-undo
        if raw and raw.replace("\x07", "").strip() == "":
            raise AmUndoError("undo")
        ans = raw.strip().lower()
    except KeyboardInterrupt as e:
        raise AmAbortError("cancelled by user") from e
    if not ans:
        return not default_no
    return ans in {"y", "yes"}


class AmUndoError(RuntimeError):
    """Raised by prompt/prompt_yes_no when the user presses Ctrl+G (BEL) and Enter.

    We rely on canonical input (Enter required) and do not modify TTY settings.
    Callers can catch this to step back one prompt.
    """

    pass


class AmUndoToChooseSourceError(AmUndoError):
    """Specialized undo meaning: jump back to Choose Source.

    Used by prompts where the previous logical section is the top-level
    source selection (for example, choose_books).
    """

    pass


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


def find_archive_match(
    archive_ro: str, author_hint: str, book_hint: str
) -> tuple[str | None, str | None]:
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

    hits: list[tuple[str, str, int]] = []

    for author_dir in root.iterdir():
        if not author_dir.is_dir():
            continue

        # if author hint exists, require author match
        if (
            a_slug
            and slug(author_dir.name).lower() != a_slug
            and a_slug not in slug(author_dir.name).lower()
        ):
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
    exact: list[tuple[str, str]] = [(a, b) for a, b, score in hits if score == 2]
    if len(exact) == 1:
        return exact[0]

    # if only one fuzzy hit overall, accept
    uniq: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for a, b, _ in hits:
        if (a, b) not in seen:
            seen.add((a, b))
            uniq.append((a, b))
    if len(uniq) == 1:
        return uniq[0]

    return (None, None)
