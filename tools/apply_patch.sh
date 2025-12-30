#!/usr/bin/env bash
set -euo pipefail
patch_file="${1:-}"
if [[ -z "${patch_file}" || ! -f "${patch_file}" ]]; then
  echo "usage: tools/apply_patch.sh /path/to/patch.diff" >&2
  exit 2
fi
git apply --verbose "${patch_file}"
echo "[ok] applied: ${patch_file}"
