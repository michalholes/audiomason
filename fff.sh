#!/usr/bin/env bash
set -euo pipefail

# Ensure the installed console entrypoint is `audiomason` (Debian-friendly).
# Keeps `am` as a backward-compatible alias if it already existed or if you want it.
# Run from AudioMason repo root.

if [ ! -f "pyproject.toml" ]; then
  echo "ERROR: run from AudioMason repo root (pyproject.toml not found)"
  exit 1
fi

python3 - <<'PY'
from __future__ import annotations
from pathlib import Path
import re

p = Path("pyproject.toml")
s = p.read_text(encoding="utf-8")

# We want:
# [project.scripts]
# audiomason = "audiomason.cli:main"
# am = "audiomason.cli:main"   (optional alias; safe)

target_block = (
    "[project.scripts]\n"
    'audiomason = "audiomason.cli:main"\n'
    'am = "audiomason.cli:main"\n'
)

def upsert_scripts_block(text: str) -> str:
    # If [project.scripts] exists, update/insert keys inside it.
    m = re.search(r"(?ms)^\[project\.scripts\]\n(.*?)(?=^\[|\Z)", text)
    if not m:
        # Insert after [project] block if present, else append.
        mp = re.search(r"(?ms)^\[project\]\n.*?(?=^\[|\Z)", text)
        if mp:
            insert_at = mp.end()
            return text[:insert_at].rstrip() + "\n\n" + target_block + "\n" + text[insert_at:].lstrip()
        return text.rstrip() + "\n\n" + target_block + "\n"

    body = m.group(1)

    def set_k(body: str, key: str, val: str) -> str:
        # Replace existing key, else append.
        if re.search(rf'(?m)^\s*{re.escape(key)}\s*=', body):
            body = re.sub(rf'(?m)^\s*{re.escape(key)}\s*=\s*(".*?"|\'.*?\'|[^\n#]+)\s*$',
                          f'{key} = "{val}"', body)
        else:
            # append with newline
            body = body.rstrip() + f'\n{key} = "{val}"\n'
        return body

    body2 = body
    body2 = set_k(body2, "audiomason", "audiomason.cli:main")
    body2 = set_k(body2, "am", "audiomason.cli:main")

    new = text[:m.start()] + "[project.scripts]\n" + body2.lstrip("\n") + text[m.end():]
    return new

s2 = upsert_scripts_block(s)

# Also: if there is an old script key pointing elsewhere, we overwrite it above.
p.write_text(s2, encoding="utf-8")
print("OK: ensured [project.scripts] provides `audiomason` (and `am` alias)")
PY

. .venv/bin/activate && \
python -m pytest -q && \
git add pyproject.toml && \
git commit -m "Pack: ensure console entrypoint is audiomason (keep am alias)" && \
git push && \
deactivate

