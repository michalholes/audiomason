#!/usr/bin/env bash
set -euo pipefail

# Canonical AudioMason patch runner (repo-backed)
#
# Usage:
#   /home/pi/apps/audiomason/scripts/am_patch.sh <ISSUE_NUMBER> "<COMMIT MESSAGE>" [<PATCH_FILENAME>]
#
# Patch location rules:
# - Patch scripts MUST be stored under: /home/pi/apps/patches/
# - Default patch filename (if <PATCH_FILENAME> omitted): issue_<ISSUE_NUMBER>.py
# - If <PATCH_FILENAME> is provided, it must be a FILENAME only (no path separators),
#   and the patch will be executed from: /home/pi/apps/patches/<PATCH_FILENAME>
#
# Runner guarantees:
# - Runs patch (python3).
# - ALWAYS deletes the patch script afterwards (success or failure).
# - Runs tests in venv: <repo_root>/.venv/bin/python -m pytest -q
# - Prints patched files AFTER tests (captured before tests), even if tests fail.
# - Commits and pushes ONLY if tests pass.

die() {
  echo "ERROR: $*" >&2
  exit 1
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
  die "usage: $0 <ISSUE_NUMBER> "<COMMIT MESSAGE>" [<PATCH_FILENAME>]"
fi

ISSUE="$1"
COMMIT_MSG="$2"
PATCH_FILENAME="${3:-issue_${ISSUE}.py}"

PATCH_DIR="/home/pi/apps/patches"

# Reject paths and path traversal: filename only
if [[ "${PATCH_FILENAME}" == */* || "${PATCH_FILENAME}" == *".."* ]]; then
  die "patch filename must be a filename only (no path separators): ${PATCH_FILENAME}"
fi

PATCH_PATH="${PATCH_DIR}/${PATCH_FILENAME}"

[[ -f "${PATCH_PATH}" ]] || die "missing patch script: ${PATCH_PATH}"

# ------------------------------------------------------------------
# Discover repo root (walk up until pyproject.toml is found)
# ------------------------------------------------------------------
find_repo_root() {
  local d
  d="$(pwd)"
  while true; do
    if [[ -f "${d}/pyproject.toml" ]]; then
      echo "${d}"
      return 0
    fi
    [[ "${d}" == "/" ]] && return 1
    d="$(dirname "${d}")"
  done
}

REPO_ROOT="$(find_repo_root)" || die "could not find repo root (pyproject.toml not found)"
echo "[am_patch] repo_root=${REPO_ROOT}"

# ------------------------------------------------------------------
# Enforce venv
# ------------------------------------------------------------------
VENV_PY="${REPO_ROOT}/.venv/bin/python"
[[ -x "${VENV_PY}" ]] || die "venv python not found/executable: ${VENV_PY}"

# ------------------------------------------------------------------
# Run patch (patch script is ALWAYS deleted)
# ------------------------------------------------------------------
PATCH_RC=0
echo "[am_patch] running patch: ${PATCH_PATH}"
set +e
python3 "${PATCH_PATH}"
PATCH_RC=$?
set -e

echo "[am_patch] deleting patch script: ${PATCH_PATH}"
rm -f "${PATCH_PATH}" || true

if [[ "${PATCH_RC}" -ne 0 ]]; then
  die "patch failed (exit=${PATCH_RC}). Patch script was deleted as required."
fi

# ------------------------------------------------------------------
# Capture patched files BEFORE tests (needed even if tests fail)
# ------------------------------------------------------------------
cd "${REPO_ROOT}"

PATCHED_STATUS="$(git status --porcelain)"
# Keep both status and filenames; print status later for auditability.
# Note: repo paths are expected to not include spaces.
PATCHED_FILES="$(printf "%s
" "${PATCHED_STATUS}" | awk '{print $2}' | sed '/^$/d' | sort -u)"

# ------------------------------------------------------------------
# Run tests in venv
# ------------------------------------------------------------------
echo "[am_patch] running tests in venv: ${VENV_PY} -m pytest -q"
set +e
"${VENV_PY}" -m pytest -q
TEST_RC=$?
set -e

echo "[am_patch] patched files (captured before tests):"
if [[ -n "${PATCHED_STATUS}" ]]; then
  printf "%s
" "${PATCHED_STATUS}" | sed 's/^/ - /'
else
  echo " - (none)"
fi

if [[ "${TEST_RC}" -ne 0 ]]; then
  die "tests failed (exit=${TEST_RC}). No commit/push performed."
fi

# ------------------------------------------------------------------
# Commit + push
# ------------------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null 2>&1   || die "not a git repository: ${REPO_ROOT}"

echo "[am_patch] staging changes"
git add -A

if git diff --cached --quiet; then
  die "no staged changes after patch; refusing to create empty commit"
fi

echo "[am_patch] committing: ${COMMIT_MSG}"
git commit -m "${COMMIT_MSG}"

echo "[am_patch] pushing"
git push

echo "[am_patch] DONE"
