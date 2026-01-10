\
#!/usr/bin/env bash
set -euo pipefail

# Canonical AudioMason patch runner (repo-backed)
#
# Usage:
#   /home/pi/apps/audiomason/scripts/am_patch.sh <ISSUE> "<COMMIT MESSAGE>" [<PATCH_FILENAME>]
#
# Patch location rules:
# - Patch scripts MUST be stored under: /home/pi/apps/patches/
# - Default patch filename (if <PATCH_FILENAME> omitted): issue_<ISSUE>.py
# - If <PATCH_FILENAME> is provided, it must be a FILENAME only (no path separators),
#   and the patch will be executed from: /home/pi/apps/patches/<PATCH_FILENAME>
#
# Behavior summary:
# - Runs patch (python3) and ALWAYS deletes the patch script afterwards (success or failure).
# - Runs tests in venv: <repo_root>/.venv/bin/python -m pytest -q
# - Prints forensic info on failures (no automatic cleanup/rollback).
# - Writes a SINGLE log file which is overwritten on each run:
#     /home/pi/apps/patches/am_patch.log
#   Concurrency is prevented using a lock:
#     /home/pi/apps/patches/am_patch.lock

die() {
  echo "ERROR: $*" >&2
  exit 1
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
  die "usage: $0 <ISSUE_NUMBER> \"<COMMIT MESSAGE>\" [<PATCH_FILENAME>]"
fi

ISSUE="$1"
COMMIT_MSG="$2"
PATCH_FILENAME="${3:-issue_${ISSUE}.py}"

PATCH_DIR="/home/pi/apps/patches"
LOG_PATH="${PATCH_DIR}/am_patch.log"
LOCK_PATH="${PATCH_DIR}/am_patch.lock"

mkdir -p "${PATCH_DIR}"

# ------------------------------------------------------------------
# Acquire lock (no concurrent runs)
# ------------------------------------------------------------------
exec 9>"${LOCK_PATH}"
if ! flock -n 9; then
  die "another am_patch.sh is already running (lock: ${LOCK_PATH})"
fi

# Overwrite log each run, and tee all stdout+stderr into it.
: > "${LOG_PATH}"
exec > >(tee -a "${LOG_PATH}") 2>&1

echo "[am_patch] log=${LOG_PATH}"
echo "[am_patch] lock=${LOCK_PATH}"

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
VENV_PY="${REPO_ROOT}/.venv/bin/python"
[[ -x "${VENV_PY}" ]] || die "venv python not found/executable: ${VENV_PY}"

echo "[am_patch] repo_root=${REPO_ROOT}"
echo "[am_patch] patch=${PATCH_PATH}"

cd "${REPO_ROOT}"

# ------------------------------------------------------------------
# Helper: print discard commands for a given git porcelain snapshot
# (purely advisory; no automatic cleanup is performed)
# ------------------------------------------------------------------
print_discard_commands_from_porcelain() {
  local status="$1"
  local tracked_paths=()
  local untracked_paths=()

  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue

    if [[ "${line}" == "?? "* ]]; then
      untracked_paths+=("${line:3}")
      continue
    fi

    local rest="${line:3}"
    if [[ "${rest}" == *" -> "* ]]; then
      rest="${rest##* -> }"
    fi
    tracked_paths+=("${rest}")
  done <<< "${status}"

  echo "[am_patch] OPTIONAL cleanup commands (run from repo root) to discard ONLY the paths above:"
  if [[ "${#tracked_paths[@]}" -gt 0 ]]; then
    printf "git restore --staged --worktree --"
    for p in "${tracked_paths[@]}"; do
      printf " %q" "${p}"
    done
    printf "\n"
  fi
  if [[ "${#untracked_paths[@]}" -gt 0 ]]; then
    printf "git clean -f --"
    for p in "${untracked_paths[@]}"; do
      printf " %q" "${p}"
    done
    printf "\n"
  fi
  if [[ "${#tracked_paths[@]}" -eq 0 && "${#untracked_paths[@]}" -eq 0 ]]; then
    echo "(nothing to discard)"
  fi
}

# ------------------------------------------------------------------
# Snapshot BEFORE patch (best-effort filesystem diff for patch FAIL)
# ------------------------------------------------------------------
PRE_PATCH_SNAPSHOT="$(mktemp)"
find . -type f | sort > "${PRE_PATCH_SNAPSHOT}"

# ------------------------------------------------------------------
# Run patch (ALWAYS delete patch)
# ------------------------------------------------------------------
PATCH_RC=0
echo "[am_patch] running patch..."
set +e
python3 "${PATCH_PATH}"
PATCH_RC=$?
set -e

echo "[am_patch] deleting patch script (always): ${PATCH_PATH}"
rm -f "${PATCH_PATH}" || true

# ------------------------------------------------------------------
# Patch FAILED → forensic output + "what to do next"
# ------------------------------------------------------------------
if [[ "${PATCH_RC}" -ne 0 ]]; then
  POST_PATCH_SNAPSHOT="$(mktemp)"
  find . -type f | sort > "${POST_PATCH_SNAPSHOT}"

  echo "[am_patch] PATCH FAILED (exit=${PATCH_RC})"
  echo "[am_patch] files touched before patch failure (best-effort filesystem diff):"
  comm -3 "${PRE_PATCH_SNAPSHOT}" "${POST_PATCH_SNAPSHOT}" | sed 's/^/ - /'

  PATCHED_STATUS_ON_FAIL="$(git status --porcelain || true)"
  if [[ -n "${PATCHED_STATUS_ON_FAIL}" ]]; then
    echo "[am_patch] git status snapshot (porcelain):"
    printf "%s\n" "${PATCHED_STATUS_ON_FAIL}" | sed 's/^/ - /'
  else
    echo "[am_patch] git shows no changes (tracked/untracked) to discard."
  fi

  echo "[am_patch] NEXT STEPS (choose one):"
  echo "  A) Continue with IC: upload the changed files (listed above) + the log file:"
  echo "     ${LOG_PATH}"
  echo "  B) Discard local changes (optional):"
  if [[ -n "${PATCHED_STATUS_ON_FAIL}" ]]; then
    print_discard_commands_from_porcelain "${PATCHED_STATUS_ON_FAIL}"
  else
    echo "     (nothing to discard according to git)"
  fi

  rm -f "${PRE_PATCH_SNAPSHOT}" "${POST_PATCH_SNAPSHOT}"
  exit 1
fi

rm -f "${PRE_PATCH_SNAPSHOT}"

# ------------------------------------------------------------------
# Capture patched files BEFORE tests (git-based)
# ------------------------------------------------------------------
PATCHED_STATUS="$(git status --porcelain)"

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
  printf "%s\n" "${PATCHED_STATUS}" | sed 's/^/ - /'
else
  echo " - (none)"
fi

if [[ "${TEST_RC}" -ne 0 ]]; then
  echo "[am_patch] TESTS FAILED (exit=${TEST_RC})"
  echo "[am_patch] NEXT STEPS:"
  echo "  - Upload the patched files (listed above) and the log file to IC:"
  echo "    ${LOG_PATH}"
  echo "  - Decide manually whether to discard local changes or keep them for follow-up."
  exit 1
fi

# ------------------------------------------------------------------
# Commit + push
# ------------------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "not a git repository: ${REPO_ROOT}"

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
