#!/usr/bin/env python3
"""AudioMason canonical patch runner (Python core).

This is the canonical execution engine.

Patch scripts are staged under:
  /home/pi/apps/patches/

Key properties:
- deterministic, auditable, failure-friendly
- exclusive lock (no concurrent runs)
- per-run logs under /home/pi/apps/patches/logs/ with retention + stable symlink
- repo root discovery independent of CWD (based on this file location)
- patch mode: run patch script with pre-flight compatibility checks, forensics on failure
- verify-only mode: patch + tests, but no commit/push
- finalize mode: for already-dirty working tree (manual edits), tests then commit/push
- test policy switches: safe-by-default (all) with opt-outs

Exit/summary markers:
- AM_PATCH_RESULT=SUCCESS | FAIL_PRECHECK | FAIL_PATCH | FAIL_TESTS | FAIL_GIT
- READY_TO_COMMIT=YES | NO (verify-only / test outcomes)

Failure fingerprint (always appended on FAIL):
- AM_PATCH_FAILURE_FINGERPRINT: ... (compact diagnostics block)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import NoReturn, Sequence

RUNNER_VERSION = "2.0"

PATCH_DIR = Path("/home/pi/apps/patches")


def _resolve_patch_arg(patch_arg: str) -> Path:
    """Resolve patch script argument to an absolute path inside PATCH_DIR.

    Accepts:
      - filename-only (looked up under PATCH_DIR)
      - relative/absolute paths (e.g. ../patches/issue_13.py)

    Safety:
      The resolved path MUST reside inside PATCH_DIR to preserve deterministic
      behavior (archival, log references).
    """
    p = Path(patch_arg).expanduser()
    if p.is_absolute():
        p = p.resolve()
    else:
        # If caller gave filename-only, interpret it under PATCH_DIR first.
        if p.parent == Path("."):
            p1 = (PATCH_DIR / p).resolve()
            p = p1 if p1.exists() else (Path.cwd() / p).resolve()
        else:
            p = (Path.cwd() / p).resolve()

    patch_dir_resolved = PATCH_DIR.resolve()
    try:
        p.relative_to(patch_dir_resolved)
    except Exception:
        _die(
            f"patch script must reside in canonical patch directory: {patch_dir_resolved} (got {p})",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_PATCH_OUTSIDE_PATCH_DIR",
            next_action="MOVE_PATCH_INTO_PATCH_DIR",
        )
    return p

FAILED_DIR = PATCH_DIR / "failed"
LOG_DIR = PATCH_DIR / "logs"
LAST_LOG_SYMLINK = PATCH_DIR / "am_patch.log"

LOCK_PRIMARY_DIR = Path("/run/audiomason")
LOCK_FALLBACK_DIR = Path("/tmp/audiomason")
LOCK_NAME = "am_patch.lock"

RETENTION_MAX_LOGS = 20
PATCH_OUTPUT_TAIL_LINES = 60


def _single_line(s: str) -> str:
    return " ".join(s.strip().split())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _emit_failure_fingerprint(
    *,
    stage: str,
    exit_code: int,
    exception_type: str,
    message: str,
    first_traceback_line: str,
    category: str,
    next_action: str,
) -> None:
    # Keep this block compact and stable; it must be usable without reading the full log.
    print()
    print("AM_PATCH_FAILURE_FINGERPRINT:")
    print(f"- stage: {stage}")
    print(f"- exit_code: {exit_code}")
    print(f"- exception_type: {exception_type}")
    print(f"- message: {_single_line(message) if message else 'NONE'}")
    print(f"- first_traceback_line: {_single_line(first_traceback_line) if first_traceback_line else 'NONE'}")
    print(f"- category: {category}")
    print(f"- next_action: {next_action}")


def _die(
    msg: str,
    *,
    result: str = "FAIL_PRECHECK",
    code: int = 1,
    stage: str = "PRE_FLIGHT",
    category: str = "PRE_FLIGHT_ERROR",
    next_action: str = "UPLOAD_LOG",
) -> NoReturn:
    print(f"ERROR: {msg}", file=sys.stderr)
    # Ensure the fingerprint is printed *after* error context.
    _emit_failure_fingerprint(
        stage=stage,
        exit_code=code,
        exception_type="NONE",
        message=msg,
        first_traceback_line="NONE",
        category=category,
        next_action=next_action,
    )
    print(f"AM_PATCH_RESULT={result}")
    if result != "SUCCESS":
        print("READY_TO_COMMIT=NO")
    raise SystemExit(code)


def _repo_root() -> Path:
    # scripts/am_patch.py lives under <repo_root>/scripts/
    return Path(__file__).resolve().parent.parent


def _run(cmd: Sequence[str], *, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), text=True, capture_output=capture)


def _run_logged(cmd: Sequence[str], *, cwd: Path, label: str) -> subprocess.CompletedProcess:
    """Run a subprocess with capture_output=True and echo stdout/stderr into the main log.

    Rationale: The runner redirects Python stdout/stderr via a Tee implementation.
    Subprocesses write to OS-level fds, so relying on Python stream replacement is insufficient.
    Capturing and replaying guarantees that ALL subprocess output ends up in the single run log.
    """
    r = subprocess.run(list(cmd), cwd=str(cwd), text=True, capture_output=True)
    if r.stdout:
        print(f"[am_patch] {label} stdout (full):")
        for ln in r.stdout.splitlines():
            print(ln)
    if r.stderr:
        print(f"[am_patch] {label} stderr (full):", file=sys.stderr)
        for ln in r.stderr.splitlines():
            print(ln, file=sys.stderr)
    return r


def _ensure_filename_only(name: str) -> None:
    if "/" in name or "\\" in name or ".." in name:
        _die(
            f"patch filename must be filename-only (no paths): {name}",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_INVALID_PATCH_NAME",
            next_action="FIX_PATCH_FILENAME",
        )


def _git(root: Path, args: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    if capture:
        return _run(cmd, cwd=root, capture=True)
    return _run_logged(cmd, cwd=root, label=f"git {' '.join(args)}")


def _git_porcelain(root: Path) -> str:
    r = _git(root, ["status", "--porcelain"], capture=True)
    if r.returncode != 0:
        return ""
    return r.stdout.strip("\n")


def _ensure_git_repo(root: Path) -> None:
    r = _git(root, ["rev-parse", "--is-inside-work-tree"], capture=True)
    if r.returncode != 0 or r.stdout.strip() != "true":
        _die(
            f"not a git repository: {root}",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_NOT_GIT_REPO",
            next_action="RUN_FROM_REPO",
        )


def _git_head_sha(root: Path) -> str:
    r = _git(root, ["rev-parse", "HEAD"], capture=True)
    return r.stdout.strip() if r.returncode == 0 else "UNKNOWN"


def _git_branch(root: Path) -> str:
    r = _git(root, ["rev-parse", "--abbrev-ref", "HEAD"], capture=True)
    return r.stdout.strip() if r.returncode == 0 else "UNKNOWN"


def _ensure_not_detached_head(root: Path) -> None:
    if _git_branch(root) == "HEAD":
        _die(
            "detached HEAD is not allowed for commit/push",
            stage="GIT",
            category="GIT_DETACHED_HEAD",
            next_action="CHECKOUT_BRANCH",
        )


def _ensure_has_upstream(root: Path) -> None:
    r = _git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], capture=True)
    if r.returncode != 0:
        _die(
            "current branch has no upstream configured (refusing to push)",
            stage="GIT",
            category="GIT_NO_UPSTREAM",
            next_action="SET_UPSTREAM_OR_PUSH_MANUALLY",
        )


def _tool_paths(root: Path) -> dict[str, Path]:
    venv = root / ".venv" / "bin"
    return {
        "python": venv / "python",
        "ruff": venv / "ruff",
        "mypy": venv / "mypy",
    }


def _select_patch_python(root: Path) -> Path | None:
    py = _tool_paths(root)["python"]
    if py.exists():
        return py
    return None


def _ensure_venv_tools(root: Path, want_ruff: bool, want_mypy: bool) -> dict[str, Path]:
    tools = _tool_paths(root)
    if not tools["python"].exists():
        _die(
            f"venv python not found: {tools['python']}",
            stage="TESTS",
            category="TESTS_NO_VENV",
            next_action="CREATE_VENV",
        )
    if want_ruff and not tools["ruff"].exists():
        _die(
            f"venv ruff not found: {tools['ruff']}",
            stage="TESTS",
            category="TESTS_MISSING_RUFF",
            next_action="INSTALL_RUFF_IN_VENV",
        )
    if want_mypy and not tools["mypy"].exists():
        _die(
            f"venv mypy not found: {tools['mypy']}",
            stage="TESTS",
            category="TESTS_MISSING_MYPY",
            next_action="INSTALL_MYPY_IN_VENV",
        )
    return tools


def _make_log_path(issue_tag: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"am_patch_{issue_tag}_{ts}.log"


def _prune_logs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logs = [
        p
        for p in LOG_DIR.iterdir()
        if p.is_file() and re.fullmatch(r"am_patch_.+_\d{{8}}_\d{{6}}\.log", p.name)
    ]
    logs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in logs[RETENTION_MAX_LOGS:]:
        try:
            p.unlink()
        except Exception:
            pass


def _set_last_log_symlink(log_path: Path) -> None:
    try:
        if LAST_LOG_SYMLINK.is_symlink() or LAST_LOG_SYMLINK.exists():
            LAST_LOG_SYMLINK.unlink()
    except Exception:
        pass
    try:
        LAST_LOG_SYMLINK.symlink_to(log_path)
    except Exception:
        # best-effort: symlink may fail on some fs; do not fail the run
        pass


def _redirect_stdio_to_log(log_path: Path) -> None:
    log_f = log_path.open("a", encoding="utf-8")

    class Tee:
        def __init__(self, stream):
            self._stream = stream

        def write(self, data):
            self._stream.write(data)
            self._stream.flush()
            log_f.write(data)
            log_f.flush()

        def flush(self):
            self._stream.flush()
            log_f.flush()

    sys.stdout = Tee(sys.__stdout__)  # type: ignore[assignment]
    sys.stderr = Tee(sys.__stderr__)  # type: ignore[assignment]


def _lock_path() -> Path:
    # Prefer /run (tmpfs), fallback to /tmp.
    try:
        LOCK_PRIMARY_DIR.mkdir(parents=True, exist_ok=True)
        test = LOCK_PRIMARY_DIR / ".write_test"
        test.write_text("x", encoding="utf-8")
        test.unlink(missing_ok=True)
        return LOCK_PRIMARY_DIR / LOCK_NAME
    except Exception:
        LOCK_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        return LOCK_FALLBACK_DIR / LOCK_NAME


def _acquire_lock() -> int:
    p = _lock_path()
    fd = os.open(str(p), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        import fcntl  # Linux/Pi

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        _die(
            f"another am_patch is already running (lock: {p})",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_LOCK_HELD",
            next_action="WAIT_OR_KILL_OTHER_RUN",
        )
    return fd


def _release_lock(fd: int) -> None:
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        os.close(fd)
    except Exception:
        pass


def _snapshot_files(root: Path) -> list[str]:
    files: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                rel = p.relative_to(root).as_posix()
            except Exception:
                continue
            files.append(rel)
    files.sort()
    return files


def _print_fs_diff(before: list[str], after: list[str]) -> None:
    before_set = set(before)
    after_set = set(after)
    touched = sorted(before_set.symmetric_difference(after_set))
    for p in touched:
        print(f" - {p}")


def _print_git_diff_outputs(root: Path) -> None:
    print("[am_patch] git diff --name-status:")
    r1 = _git(root, ["diff", "--name-status"])
    if r1.returncode != 0:
        print("(git diff --name-status failed)")
    print("[am_patch] git diff --stat:")
    r2 = _git(root, ["diff", "--stat"])
    if r2.returncode != 0:
        print("(git diff --stat failed)")


def _static_validate_patch_script(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        _die(
            f"unable to read patch script: {path}",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_PATCH_UNREADABLE",
            next_action="FIX_PATCH_FILE",
        )

    # Minimal structural requirements (cheap and robust)
    required = ["FILE MANIFEST", "repo-relative"]
    for s in required:
        if s not in text:
            _die(
                f"patch script missing required marker: {s!r}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_MISSING_MARKER",
                next_action="REGENERATE_PATCH_WITH_REQUIRED_MARKERS",
            )

    # Denylist (keep permissive enough for normal patch scripts)
    forbidden_patterns = [
        r"\bos\.system\s*\(",
        r"subprocess\.Popen",
        r"shell\s*=\s*True",
        r"\brequests\b",
        r"urllib\.request",
        r"\bsocket\b",
        r"rm\s+-rf",
        r"\bcurl\b\s+http",
        r"\bwget\b\s+http",
    ]
    for pat in forbidden_patterns:
        if re.search(pat, text):
            _die(
                f"patch script contains forbidden pattern: {pat}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_FORBIDDEN_PATTERN",
                next_action="REGENERATE_PATCH_WITHOUT_FORBIDDEN_CALLS",
            )


# Header formats supported (top of patch script; scanned in the first N lines):
#  1) Comment header (recommended; robust):
#       # TARGET_BRANCH: <branch>
#       # PROOF_ANCHOR: <path> :: <snippet>
#  2) Simple Python assignment header (supported for compatibility):
#       TARGET_BRANCH = "<branch>"
#       PROOF_ANCHOR = "<path> :: <snippet>"
#
# Notes:
# - Multiple PROOF_ANCHOR entries are allowed (repeat the line).
# - Header scanning is tolerant to shebang, encoding cookies, blank lines, and comments.
# - The runner does NOT import/execute the patch script during preflight.
_HEADER_COMMENT_RE = re.compile(r"^#\s*([A-Z_]+)\s*:\s*(.+?)\s*$")
_HEADER_ASSIGN_RE = re.compile(r"^\s*([A-Z_]+)\s*=\s*([\"'])(.+?)\2\s*$")


def _parse_patch_header(patch_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Parse compatibility header from patch script.

    Returns:
      (meta, parse_notes)

    parse_notes is a short list of human-readable observations used to improve
    preflight error messages (e.g. "found TARGET_BRANCH (optional) but in unsupported format").
    """
    try:
        raw = patch_path.read_bytes()
    except Exception:
        return {}, ["unable to read patch bytes"]

    # Be tolerant to UTF-8 BOM.
    notes: list[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
        notes.append("stripped UTF-8 BOM")

    try:
        lines = raw.decode("utf-8").splitlines()
    except Exception:
        lines = raw.decode("utf-8", errors="replace").splitlines()
        notes.append("decoded with replacement (non-utf8 bytes present)")

    meta: dict[str, list[str]] = {}

    scan_limit = 200
    for i, line in enumerate(lines[:scan_limit], start=1):
        # Allow shebang and blank/comment lines in the header region.
        if i == 1 and line.startswith("#!"):
            continue
        if re.match(r"^#.*coding[:=]\s*[-\w.]+", line):
            continue
        if line.strip() == "":
            continue

        # Preferred form: comment header.
        if line.lstrip().startswith("#"):
            m = _HEADER_COMMENT_RE.match(line)
            if m:
                k, v = m.group(1), m.group(2)
                meta.setdefault(k, []).append(v)
            continue

        # Compatibility form: simple assignments.
        m2 = _HEADER_ASSIGN_RE.match(line)
        if m2:
            k, v = m2.group(1), m2.group(3)
            meta.setdefault(k, []).append(v)
            continue

        # Stop early once we reach clear "real code".
        if re.match(r"^\s*(def|class)\s+\w+", line):
            break

    # Near-miss notes for better diagnostics.
    wanted = {"TARGET_BRANCH", "PROOF_ANCHOR"}
    if not (meta.get("TARGET_BRANCH (optional)") or meta.get("TARGET_BRANCH") or meta.get("PROOF_ANCHOR")):
        for i, line in enumerate(lines[:scan_limit], start=1):
            if any(k in line for k in wanted):
                notes.append(f"found potential header token on line {i} but in unsupported format")
                if len(notes) >= 4:
                    break

    return meta, notes


def _preflight_check_patch_compatibility(root: Path, patch_path: Path) -> None:
    """Preflight compatibility checks.

    Policy (v2.16+):
    - TARGET_BRANCH (optional) is NOT supported and is ignored if present in patch scripts.
    - TARGET_BRANCH is optional (warn-only if it mismatches).
    - PROOF_ANCHOR is REQUIRED and is the primary compatibility contract.
    """
    meta, parse_notes = _parse_patch_header(patch_path)

    target_branches = meta.get("TARGET_BRANCH", [])
    proof_anchors = meta.get("PROOF_ANCHOR", [])

    if not proof_anchors:
        note = ("; " + "; ".join(parse_notes)) if parse_notes else ""
        _die(
            "patch script missing required compatibility header field: PROOF_ANCHOR" + note,
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_MISSING_ANCHOR",
            next_action="REGENERATE_PATCH_WITH_HEADER",
        )

    branch = _git_branch(root)

    # TARGET_BRANCH is a soft hint. Mismatch does NOT block execution.
    if target_branches and branch not in [t.strip() for t in target_branches]:
        print(
            f"[am_patch] WARN: TARGET_BRANCH mismatch (expected one of {target_branches}, got {branch}); proceeding"
        )

    for raw in proof_anchors:
        if "::" not in raw:
            _die(
                f"invalid PROOF_ANCHOR format (expected '<path> :: <snippet>'): {raw}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_INVALID_ANCHOR_FORMAT",
                next_action="REGENERATE_PATCH_WITH_VALID_ANCHOR",
            )
        rel_s, snippet = [p.strip() for p in raw.split("::", 1)]
        if not rel_s or not snippet:
            _die(
                f"invalid PROOF_ANCHOR format (empty path or snippet): {raw}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_INVALID_ANCHOR_FORMAT",
                next_action="REGENERATE_PATCH_WITH_VALID_ANCHOR",
            )

        target_file = root / rel_s
        if not target_file.is_file():
            _die(
                f"PROOF_ANCHOR target file not found: {rel_s}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_ANCHOR_FILE_MISSING",
                next_action="REGENERATE_PATCH_WITH_EXISTING_ANCHOR",
            )

        try:
            text = target_file.read_text(encoding="utf-8")
        except Exception:
            _die(
                f"unable to read PROOF_ANCHOR target file: {rel_s}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_ANCHOR_FILE_UNREADABLE",
                next_action="FIX_FILE_PERMISSIONS_OR_REGENERATE_PATCH",
            )

        if snippet not in text:
            _die(
                f"PROOF_ANCHOR snippet not found in {rel_s}: {snippet!r}",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_ANCHOR_NOT_FOUND",
                next_action="REGENERATE_PATCH_FOR_CURRENT_TREE",
            )


def _run_tests(root: Path, *, tests: str, no_ruff: bool, no_mypy: bool) -> None:
    want_ruff = (tests == "all") and (not no_ruff)
    want_mypy = (tests == "all") and (not no_mypy)

    tools = _ensure_venv_tools(root, want_ruff=want_ruff, want_mypy=want_mypy)

    if want_ruff:
        print("[am_patch] running ruff in venv")
        r = _run_logged([str(tools["ruff"]), "check", "."], cwd=root, label="ruff check .")
        if r.returncode != 0:
            _emit_failure_fingerprint(
                stage="TESTS",
                exit_code=r.returncode,
                exception_type="NONE",
                message="ruff check failed",
                first_traceback_line="NONE",
                category="TESTS_RUFF_FAILED",
                next_action="OPEN_LOG_AND_FIX_RUFF",
            )
            print("AM_PATCH_RESULT=FAIL_TESTS")
            print("READY_TO_COMMIT=NO")
            raise SystemExit(r.returncode)

    print("[am_patch] running pytest in venv")
    r = _run_logged([str(tools["python"]), "-m", "pytest", "-q"], cwd=root, label="pytest -q")
    if r.returncode != 0:
        _emit_failure_fingerprint(
            stage="TESTS",
            exit_code=r.returncode,
            exception_type="NONE",
            message="pytest failed",
            first_traceback_line="NONE",
            category="TESTS_PYTEST_FAILED",
            next_action="OPEN_LOG_AND_FIX_TESTS",
        )
        print("AM_PATCH_RESULT=FAIL_TESTS")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(r.returncode)

    if want_mypy:
        print("[am_patch] running mypy in venv")
        r = _run_logged([str(tools["mypy"]), "src"], cwd=root, label="mypy src")
        if r.returncode != 0:
            _emit_failure_fingerprint(
                stage="TESTS",
                exit_code=r.returncode,
                exception_type="NONE",
                message="mypy failed",
                first_traceback_line="NONE",
                category="TESTS_MYPY_FAILED",
                next_action="OPEN_LOG_AND_FIX_MYPY",
            )
            print("AM_PATCH_RESULT=FAIL_TESTS")
            print("READY_TO_COMMIT=NO")
            raise SystemExit(r.returncode)


def _commit_push(root: Path, msg: str) -> None:
    _ensure_not_detached_head(root)
    _ensure_has_upstream(root)

    print("[am_patch] staging changes")
    _git(root, ["add", "-A"])

    r = _git(root, ["diff", "--cached", "--quiet"])
    if r.returncode == 0:
        _die(
            "no staged changes; refusing to create empty commit",
            result="FAIL_GIT",
            stage="GIT",
            category="GIT_EMPTY_COMMIT",
            next_action="VERIFY_CHANGES_OR_ABORT",
        )

    print(f"[am_patch] committing: {msg}")
    r = _git(root, ["commit", "-m", msg])
    if r.returncode != 0:
        _emit_failure_fingerprint(
            stage="GIT",
            exit_code=r.returncode,
            exception_type="NONE",
            message="git commit failed",
            first_traceback_line="NONE",
            category="GIT_COMMIT_FAILED",
            next_action="OPEN_LOG_AND_FIX_GIT",
        )
        print("AM_PATCH_RESULT=FAIL_GIT")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(r.returncode)

    print("[am_patch] pushing")
    r = _git(root, ["push"])
    if r.returncode != 0:
        _emit_failure_fingerprint(
            stage="GIT",
            exit_code=r.returncode,
            exception_type="NONE",
            message="git push failed",
            first_traceback_line="NONE",
            category="GIT_PUSH_FAILED",
            next_action="OPEN_LOG_AND_FIX_GIT",
        )
        print("AM_PATCH_RESULT=FAIL_GIT")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(r.returncode)


def _print_discard_commands_from_porcelain(porcelain: str) -> None:
    tracked: list[str] = []
    untracked: list[str] = []

    for line in porcelain.splitlines():
        if not line:
            continue
        if line.startswith("?? "):
            untracked.append(line[3:])
            continue

        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        tracked.append(rest)

    print("[am_patch] OPTIONAL cleanup commands (run from repo root) to discard ONLY the paths above:")
    if tracked:
        cmd = "git restore --staged --worktree --" + "".join(f" {_sh_quote(p)}" for p in tracked)
        print(cmd)
    if untracked:
        cmd = "git clean -f --" + "".join(f" {_sh_quote(p)}" for p in untracked)
        print(cmd)
    if not tracked and not untracked:
        print("(nothing to discard)")


def _sh_quote(s: str) -> str:
    if s == "":
        return "''"
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/:@"
    if all(c in safe for c in s) and " " not in s and "\t" not in s and "\n" not in s:
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _archive_failed_patch(patch_path: Path, *, reason_tag: str) -> Path | None:
    try:
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = FAILED_DIR / f"{patch_path.stem}_{reason_tag}_{ts}{patch_path.suffix}"
        patch_path.replace(dst)
        return dst
    except Exception:
        return None


def _print_patch_output_tail(label: str, text: str) -> None:
    """Print full captured output into the main run log.

    NOTE: Despite the historical name, this function prints the FULL output.
    The project contract requires a single per-run log containing everything.
    """
    print(f"[am_patch] {label} (full):")
    # Print verbatim; do not re-wrap or truncate.
    for ln in text.splitlines():
        print(ln)


def _run_patch_subprocess(root: Path, patch_path: Path) -> tuple[int, str, str, list[str], str]:
    """Run patch with captured stdout/stderr.

    Returns:
      (returncode, stdout, stderr, patch_cmd, interpreter_used)
    """
    venv_python = _select_patch_python(root)
    if venv_python is not None:
        patch_cmd = [str(venv_python), str(patch_path)]
        interpreter_used = str(venv_python)
    else:
        # Fallback to the current interpreter if possible; otherwise, plain python3.
        interpreter_used = sys.executable if sys.executable else "python3"
        patch_cmd = [interpreter_used, str(patch_path)]

    print(f"[am_patch] PATCH_CMD={' '.join(_sh_quote(p) for p in patch_cmd)}")
    print(f"[am_patch] patch_interpreter={interpreter_used}")

    r = _run(patch_cmd, cwd=root, capture=True)
    return r.returncode, r.stdout, r.stderr, patch_cmd, interpreter_used


def _patch_mode(
    *,
    root: Path,
    log_path: Path,
    issue: str,
    commit_msg: str,
    patch_filename: str,
    verify_only: bool,
    tests: str,
    no_ruff: bool,
    no_mypy: bool,
) -> None:
    patch_path = _resolve_patch_arg(patch_filename)
    if not patch_path.is_file():
        _die(
            f"missing patch script: {patch_path}",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_PATCH_MISSING",
            next_action="ENSURE_PATCH_EXISTS_IN_PATCH_DIR",
        )

    _static_validate_patch_script(patch_path)
    _preflight_check_patch_compatibility(root, patch_path)

    print(f"[am_patch] runner_version={RUNNER_VERSION}")
    print(f"[am_patch] repo_root={root}")
    print(f"[am_patch] patch={patch_path}")
    print(f"[am_patch] patch_sha256={_sha256_file(patch_path)}")
    print(f"[am_patch] log_dir={LOG_DIR}")
    print(f"[am_patch] lock={_lock_path()}")
    print(f"[am_patch] verify_only={verify_only} tests={tests} no_ruff={no_ruff} no_mypy={no_mypy}")

    os.chdir(root)

    before = _snapshot_files(root)

    print("[am_patch] running patch...")
    rc, out, err, patch_cmd, interpreter_used = _run_patch_subprocess(root, patch_path)

    # Avoid bloating the main log/console with huge patch output.
    # Write full stdout/stderr to sidecar files next to the log, and print only a tail.
    if out:
        stdout_path = log_path.parent / f"{log_path.stem}.patch_stdout.txt"
        stdout_path.write_text(out, encoding="utf-8")
        print(f"[am_patch] patch stdout saved: {stdout_path}")
        _print_patch_output_tail("patch stdout", out)

    if err:
        stderr_path = log_path.parent / f"{log_path.stem}.patch_stderr.txt"
        stderr_path.write_text(err, encoding="utf-8")
        print(f"[am_patch] patch stderr saved: {stderr_path}")
        _print_patch_output_tail("patch stderr", err)

    if rc != 0:
        archived = _archive_failed_patch(patch_path, reason_tag="FAIL")
        if archived is not None:
            print(f"[am_patch] archived failed patch script: {archived}")
        else:
            print(f"[am_patch] WARNING: failed to archive patch script (leaving as-is): {patch_path}")

        after = _snapshot_files(root)
        print(f"[am_patch] PATCH FAILED (exit={rc})")
        print("[am_patch] files touched before patch failure (best-effort filesystem diff):")
        _print_fs_diff(before, after)

        _print_git_diff_outputs(root)

        porcelain = _git_porcelain(root)
        if porcelain:
            print("[am_patch] git status snapshot (porcelain):")
            for line in porcelain.splitlines():
                print(f" - {line}")
        else:
            print("[am_patch] git shows no changes (tracked/untracked) to discard.")

        # Try to extract a likely exception type / first traceback line from stderr.
        exc_type = "NONE"
        first_tb = "NONE"
        for ln in err.splitlines():
            if ln.startswith("Traceback (most recent call last):"):
                first_tb = ln
                break
        m = re.search(r"^([A-Za-z_][A-Za-z0-9_]*Error|AssertionError):", err, flags=re.M)
        if m:
            exc_type = m.group(1)

        _emit_failure_fingerprint(
            stage="PATCH_EXEC",
            exit_code=rc,
            exception_type=exc_type,
            message=f"patch exited non-zero (exit={rc})",
            first_traceback_line=first_tb,
            category="PATCH_EXEC_NONZERO_EXIT",
            next_action="UPLOAD_LOG_AND_ARCHIVED_PATCH",
        )

        print("[am_patch] NEXT STEPS (choose one):")
        print("  A) Upload changed files (listed above) + the log file + archived patch script:")
        print(f"     {LAST_LOG_SYMLINK}  (symlink to latest run log)")
        if archived is not None:
            print(f"     {archived}")
        print("  B) Discard local changes (optional):")
        if porcelain:
            _print_discard_commands_from_porcelain(porcelain)
        else:
            print("     (nothing to discard according to git)")

        print("AM_PATCH_RESULT=FAIL_PATCH")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(1)

    print(f"[am_patch] deleting patch script (success): {patch_path}")
    try:
        patch_path.unlink(missing_ok=True)
    except Exception:
        pass

    patched_status = _git_porcelain(root)

    _print_git_diff_outputs(root)

    _run_tests(root, tests=tests, no_ruff=no_ruff, no_mypy=no_mypy)

    print("[am_patch] patched files (captured before tests):")
    if patched_status:
        for line in patched_status.splitlines():
            print(f" - {line}")
    else:
        print(" - (none)")

    if verify_only:
        print("AM_PATCH_RESULT=SUCCESS")
        print("READY_TO_COMMIT=YES")
        return

    _commit_push(root, commit_msg)
    print("AM_PATCH_RESULT=SUCCESS")
    print("READY_TO_COMMIT=YES")


def _finalize_mode(
    *,
    root: Path,
    log_path: Path,
    commit_msg: str,
    verify_only: bool,
    tests: str,
    no_ruff: bool,
    no_mypy: bool,
) -> None:
    print(f"[am_patch] runner_version={RUNNER_VERSION}")
    print(f"[am_patch] repo_root={root}")
    print(f"[am_patch] log_dir={LOG_DIR}")
    print(f"[am_patch] lock={_lock_path()}")
    print(f"[am_patch] verify_only={verify_only} tests={tests} no_ruff={no_ruff} no_mypy={no_mypy}")

    os.chdir(root)

    porcelain = _git_porcelain(root)
    if not porcelain:
        _die(
            "dirty tree required for finalize mode (no changes detected)",
            result="FAIL_PRECHECK",
            stage="PRE_FLIGHT",
            category="PRE_FLIGHT_FINALIZE_CLEAN_TREE",
            next_action="MAKE_CHANGES_OR_USE_PATCH_MODE",
        )

    _print_git_diff_outputs(root)

    _run_tests(root, tests=tests, no_ruff=no_ruff, no_mypy=no_mypy)

    print("[am_patch] patched files (captured before tests):")
    for line in porcelain.splitlines():
        print(f" - {line}")

    if verify_only:
        print("AM_PATCH_RESULT=SUCCESS")
        print("READY_TO_COMMIT=YES")
        return

    _commit_push(root, commit_msg)
    print("AM_PATCH_RESULT=SUCCESS")
    print("READY_TO_COMMIT=YES")


def _print_context(root: Path, *, patch_filename: str | None) -> None:
    branch = _git_branch(root)
    head = _git_head_sha(root)
    porcelain = _git_porcelain(root)
    clean = "clean" if not porcelain else "dirty"
    print("AM_PATCH_CONTEXT:")
    print(f"- branch: {branch}")
    print(f"- head: {head}")
    print(f"- status: {clean}")
    print(f"- runner_version: {RUNNER_VERSION}")
    print(f"- log_dir: {LOG_DIR}")
    if patch_filename:
        patch_path = _resolve_patch_arg(patch_filename)
        if patch_path.exists():
            print(f"- patch: {patch_path.name}")
            print(f"- patch_sha256: {_sha256_file(patch_path)}")
        else:
            print(f"- patch: {patch_path.name} (MISSING)")
    else:
        print("- patch: NONE")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="am_patch.py", allow_abbrev=False)

    ap.add_argument(
        "-f",
        "--finalize",
        metavar="MSG",
        help="Finalize an already-dirty working tree: run tests then commit+push with MSG.",
    )
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="Run patch/finalize + tests, but do not commit/push.",
    )
    ap.add_argument(
        "--tests",
        choices=["all", "pytest"],
        default="all",
        help="Test policy (default: all). 'pytest' runs only pytest -q.",
    )
    ap.add_argument("--no-mypy", action="store_true", help="Skip mypy (only relevant with --tests all).")
    ap.add_argument("--no-ruff", action="store_true", help="Skip ruff (only relevant with --tests all).")

    ap.add_argument(
        "--print-context",
        action="store_true",
        help="Print compact context block (branch/SHA/status/log dir/patch sha256) and exit.",
    )

    ap.add_argument("issue", nargs="?", help="Issue number (patch mode)")
    ap.add_argument("message", nargs="?", help="Commit message (patch mode)")
    ap.add_argument("patch", nargs="?", help="Patch script path (patch mode; must resolve under /home/pi/apps/patches/)")

    args = ap.parse_args(argv)

    root = _repo_root()
    _ensure_git_repo(root)

    # Context printer is intentionally lightweight; no lock/log required.
    if args.print_context:
        patch_filename = args.patch or (f"issue_{args.issue}.py" if args.issue else None)
        _print_context(root, patch_filename=patch_filename)
        return

    # prepare logs + lock (for all normal modes)
    _prune_logs()

    issue_tag = args.issue if args.issue else ("finalize" if args.finalize else "unknown")
    log_path = _make_log_path(issue_tag)
    _set_last_log_symlink(log_path)
    _redirect_stdio_to_log(log_path)

    lock_fd = _acquire_lock()
    try:
        if args.finalize:
            if args.issue or args.message or args.patch:
                _die(
                    "Finalize mode cannot be combined with patch mode arguments",
                    result="FAIL_PRECHECK",
                    stage="PRE_FLIGHT",
                    category="PRE_FLIGHT_INVALID_ARGS",
                    next_action="FIX_COMMAND_LINE",
                )
            _finalize_mode(
                root=root,
                commit_msg=args.finalize,
                verify_only=args.verify_only,
                tests=args.tests,
                no_ruff=args.no_ruff,
                no_mypy=args.no_mypy,
            )
            return

        if not args.issue or not args.message:
            _die(
                'usage: am_patch.py <ISSUE> "<COMMIT MESSAGE>" [<PATCH_FILENAME>]',
                result="FAIL_PRECHECK",
                stage="PRE_FLIGHT",
                category="PRE_FLIGHT_MISSING_ARGS",
                next_action="FIX_COMMAND_LINE",
            )

        patch_filename = args.patch or f"issue_{args.issue}.py"

        _patch_mode(
            root=root,
            log_path=log_path,
            issue=args.issue,
            commit_msg=args.message,
            patch_filename=patch_filename,
            verify_only=args.verify_only,
            tests=args.tests,
            no_ruff=args.no_ruff,
            no_mypy=args.no_mypy,
        )
    except SystemExit:
        # Ensure we do not double-print anything; _die/_emit_failure_fingerprint already handled it.
        raise
    except Exception as e:  # unexpected runner failure
        tb = traceback.format_exc()
        first_line = tb.splitlines()[0] if tb.splitlines() else "NONE"
        print(tb, file=sys.stderr)
        _emit_failure_fingerprint(
            stage="GIT" if "git" in str(e).lower() else "PATCH_EXEC",
            exit_code=1,
            exception_type=type(e).__name__,
            message=str(e) or repr(e),
            first_traceback_line=first_line,
            category="RUNNER_EXCEPTION",
            next_action="UPLOAD_LOG",
        )
        print("AM_PATCH_RESULT=FAIL_GIT")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(1)
    finally:
        _release_lock(lock_fd)


if __name__ == "__main__":
    main()
