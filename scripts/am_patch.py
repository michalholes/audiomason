#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd):
    return subprocess.run(cmd, cwd=REPO_ROOT)


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    print("AM_PATCH_RESULT=FAIL_PRECHECK")
    sys.exit(code)


def ensure_dirty():
    r = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True, capture_output=True)
    if r.returncode != 0 or not r.stdout.strip():
        fail("Dirty tree required for finalize mode")


def run_tests():
    cmds = [
        ["bash", "-c", "source .venv/bin/activate && ruff check ."],
        ["bash", "-c", "source .venv/bin/activate && pytest"],
        ["bash", "-c", "source .venv/bin/activate && mypy src"],
    ]
    for c in cmds:
        r = run(c)
        if r.returncode != 0:
            print("AM_PATCH_RESULT=FAIL_TESTS")
            sys.exit(r.returncode)


def finalize(message):
    ensure_dirty()
    run_tests()
    run(["git", "add", "-A"])
    r = run(["git", "commit", "-m", message])
    if r.returncode != 0:
        print("AM_PATCH_RESULT=FAIL_GIT")
        sys.exit(r.returncode)
    run(["git", "push"])
    print("AM_PATCH_RESULT=SUCCESS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--finalize", metavar="MSG", help="Finalize dirty tree with tests and commit")
    ap.add_argument("issue", nargs="?", help="Issue number")
    ap.add_argument("message", nargs="?", help="Commit message")
    ap.add_argument("patch", nargs="?", help="Patch filename")
    args = ap.parse_args()

    if args.finalize:
        if args.issue or args.patch:
            fail("Finalize mode cannot be combined with patch mode")
        finalize(args.finalize)
        return

    fail("Patch mode not implemented in this stub")


if __name__ == "__main__":
    main()
