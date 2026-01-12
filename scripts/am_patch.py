#!/usr/bin/env python3
"""AudioMason canonical patch runner (Python core).

This is the canonical execution engine invoked by:
  scripts/am_patch.sh

Patch scripts are staged under:
  /home/pi/apps/patches/

Key properties:
- deterministic, auditable, failure-friendly
- exclusive lock (no concurrent runs)
- per-run logs under /home/pi/apps/patches/logs/ with retention + stable symlink
- repo root discovery independent of CWD (based on this file location)
- patch mode: run patch script, always delete it, forensics on failure
- verify-only mode: patch + tests, but no commit/push
- finalize mode: for already-dirty working tree (manual edits), tests then commit/push
- test policy switches: safe-by-default (all) with opt-outs

Exit/summary markers:
- AM_PATCH_RESULT=SUCCESS | FAIL_PRECHECK | FAIL_PATCH | FAIL_TESTS | FAIL_GIT
- READY_TO_COMMIT=YES | NO (verify-only / test outcomes)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn, Sequence

PATCH_DIR = Path("/home/pi/apps/patches")
LOG_DIR = PATCH_DIR / "logs"
LAST_LOG_SYMLINK = PATCH_DIR / "am_patch.log"

LOCK_PRIMARY_DIR = Path("/run/audiomason")
LOCK_FALLBACK_DIR = Path("/tmp/audiomason")
LOCK_NAME = "am_patch.lock"

RETENTION_MAX_LOGS = 20


def _die(msg: str, *, result: str = "FAIL_PRECHECK", code: int = 1) -> NoReturn:
    print(f"ERROR: {msg}", file=sys.stderr)
    print(f"AM_PATCH_RESULT={result}")
    if result != "SUCCESS":
        print("READY_TO_COMMIT=NO")
    raise SystemExit(code)


def _repo_root() -> Path:
    # scripts/am_patch.py lives under <repo_root>/scripts/
    return Path(__file__).resolve().parent.parent


def _run(cmd: Sequence[str], *, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), text=True, capture_output=capture)


def _ensure_filename_only(name: str) -> None:
    if "/" in name or "\\" in name or ".." in name:
        _die(f"patch filename must be filename-only (no paths): {name}")


def _git(root: Path, args: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return _run(["git", *args], cwd=root, capture=capture)


def _git_porcelain(root: Path) -> str:
    r = _git(root, ["status", "--porcelain"], capture=True)
    if r.returncode != 0:
        return ""
    return r.stdout.strip("\n")


def _ensure_git_repo(root: Path) -> None:
    r = _git(root, ["rev-parse", "--is-inside-work-tree"], capture=True)
    if r.returncode != 0 or r.stdout.strip() != "true":
        _die(f"not a git repository: {root}")


def _ensure_not_detached_head(root: Path) -> None:
    r = _git(root, ["rev-parse", "--abbrev-ref", "HEAD"], capture=True)
    if r.returncode != 0:
        _die("unable to determine current branch (git rev-parse failed)")
    if r.stdout.strip() == "HEAD":
        _die("detached HEAD is not allowed for commit/push")


def _ensure_has_upstream(root: Path) -> None:
    r = _git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], capture=True)
    if r.returncode != 0:
        _die("current branch has no upstream configured (refusing to push)")


def _tool_paths(root: Path) -> dict[str, Path]:
    venv = root / ".venv" / "bin"
    return {
        "python": venv / "python",
        "ruff": venv / "ruff",
        "mypy": venv / "mypy",
    }


def _ensure_venv_tools(root: Path, want_ruff: bool, want_mypy: bool) -> dict[str, Path]:
    tools = _tool_paths(root)
    if not tools["python"].exists():
        _die(f"venv python not found: {tools['python']}")
    if want_ruff and not tools["ruff"].exists():
        _die(f"venv ruff not found: {tools['ruff']}")
    if want_mypy and not tools["mypy"].exists():
        _die(f"venv mypy not found: {tools['mypy']}")
    return tools


def _make_log_path(issue_tag: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"am_patch_{issue_tag}_{ts}.log"


def _prune_logs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logs = [p for p in LOG_DIR.iterdir() if p.is_file() and re.fullmatch(r"am_patch_.+_\d{{8}}_\d{{6}}\.log", p.name)]
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
        _die(f"another am_patch is already running (lock: {p})")
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
        _die(f"unable to read patch script: {path}", result="FAIL_PRECHECK")

    # Minimal structural requirements (cheap and robust)
    required = ["FILE MANIFEST", "repo-relative"]
    for s in required:
        if s not in text:
            _die(f"patch script missing required marker: {s!r}", result="FAIL_PRECHECK")

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
            _die(f"patch script contains forbidden pattern: {pat}", result="FAIL_PRECHECK")


def _run_tests(root: Path, *, tests: str, no_ruff: bool, no_mypy: bool) -> None:
    want_ruff = (tests == "all") and (not no_ruff)
    want_mypy = (tests == "all") and (not no_mypy)

    tools = _ensure_venv_tools(root, want_ruff=want_ruff, want_mypy=want_mypy)

    if want_ruff:
        print("[am_patch] running ruff in venv")
        r = _run([str(tools["ruff"]), "check", "."], cwd=root)
        if r.returncode != 0:
            print("AM_PATCH_RESULT=FAIL_TESTS")
            print("READY_TO_COMMIT=NO")
            raise SystemExit(r.returncode)

    print("[am_patch] running pytest in venv")
    r = _run([str(tools["python"]), "-m", "pytest", "-q"], cwd=root)
    if r.returncode != 0:
        print("AM_PATCH_RESULT=FAIL_TESTS")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(r.returncode)

    if want_mypy:
        print("[am_patch] running mypy in venv")
        r = _run([str(tools["mypy"]), "src"], cwd=root)
        if r.returncode != 0:
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
        _die("no staged changes; refusing to create empty commit", result="FAIL_GIT")

    print(f"[am_patch] committing: {msg}")
    r = _git(root, ["commit", "-m", msg])
    if r.returncode != 0:
        print("AM_PATCH_RESULT=FAIL_GIT")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(r.returncode)

    print("[am_patch] pushing")
    r = _git(root, ["push"])
    if r.returncode != 0:
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


def _patch_mode(
    *,
    root: Path,
    issue: str,
    commit_msg: str,
    patch_filename: str,
    verify_only: bool,
    tests: str,
    no_ruff: bool,
    no_mypy: bool,
) -> None:
    _ensure_filename_only(patch_filename)
    patch_path = PATCH_DIR / patch_filename
    if not patch_path.is_file():
        _die(f"missing patch script: {patch_path}")

    _static_validate_patch_script(patch_path)

    print(f"[am_patch] repo_root={root}")
    print(f"[am_patch] patch={patch_path}")
    print(f"[am_patch] log_dir={LOG_DIR}")
    print(f"[am_patch] lock={_lock_path()}")
    print(f"[am_patch] verify_only={verify_only} tests={tests} no_ruff={no_ruff} no_mypy={no_mypy}")

    os.chdir(root)

    before = _snapshot_files(root)

    print("[am_patch] running patch...")
    rc = _run(["python3", str(patch_path)], cwd=root).returncode

    print(f"[am_patch] deleting patch script (always): {patch_path}")
    try:
        patch_path.unlink(missing_ok=True)
    except Exception:
        pass

    if rc != 0:
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

        print("[am_patch] NEXT STEPS (choose one):")
        print("  A) Upload changed files (listed above) + the log file:")
        print(f"     {LAST_LOG_SYMLINK}  (symlink to latest run log)")
        print("  B) Discard local changes (optional):")
        if porcelain:
            _print_discard_commands_from_porcelain(porcelain)
        else:
            print("     (nothing to discard according to git)")

        print("AM_PATCH_RESULT=FAIL_PATCH")
        print("READY_TO_COMMIT=NO")
        raise SystemExit(1)

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
    commit_msg: str,
    verify_only: bool,
    tests: str,
    no_ruff: bool,
    no_mypy: bool,
) -> None:
    print(f"[am_patch] repo_root={root}")
    print(f"[am_patch] log_dir={LOG_DIR}")
    print(f"[am_patch] lock={_lock_path()}")
    print(f"[am_patch] verify_only={verify_only} tests={tests} no_ruff={no_ruff} no_mypy={no_mypy}")

    os.chdir(root)

    porcelain = _git_porcelain(root)
    if not porcelain:
        _die("dirty tree required for finalize mode (no changes detected)", result="FAIL_PRECHECK")

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

    ap.add_argument("issue", nargs="?", help="Issue number (patch mode)")
    ap.add_argument("message", nargs="?", help="Commit message (patch mode)")
    ap.add_argument("patch", nargs="?", help="Patch filename (patch mode; filename-only under /home/pi/apps/patches/)")

    args = ap.parse_args(argv)

    root = _repo_root()
    _ensure_git_repo(root)

    # prepare logs + lock (for all modes)
    _prune_logs()

    issue_tag = args.issue if args.issue else ("finalize" if args.finalize else "unknown")
    log_path = _make_log_path(issue_tag)
    _set_last_log_symlink(log_path)
    _redirect_stdio_to_log(log_path)

    lock_fd = _acquire_lock()
    try:
        if args.finalize:
            if args.issue or args.message or args.patch:
                _die("Finalize mode cannot be combined with patch mode arguments", result="FAIL_PRECHECK")
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
            _die('usage: am_patch.sh <ISSUE> "<COMMIT MESSAGE>" [<PATCH_FILENAME>]', result="FAIL_PRECHECK")

        patch_filename = args.patch or f"issue_{args.issue}.py"

        _patch_mode(
            root=root,
            issue=args.issue,
            commit_msg=args.message,
            patch_filename=patch_filename,
            verify_only=args.verify_only,
            tests=args.tests,
            no_ruff=args.no_ruff,
            no_mypy=args.no_mypy,
        )
    finally:
        _release_lock(lock_fd)


if __name__ == "__main__":
    main()
