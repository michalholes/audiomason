from __future__ import annotations

import re
import unicodedata

# Read-only normalization helper (NO FS changes)

def normalize_name(s: str) -> str:
    if not s:
        return s

    # Unicode normalize
    s = unicodedata.normalize("NFKC", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # Fix common separators
    s = s.replace("_", " ")

    # Title case but keep acronyms/numbers
    parts = []
    for w in s.split(" "):
        if w.isupper() or any(c.isdigit() for c in w):
            parts.append(w)
        else:
            parts.append(w.capitalize())
    s = " ".join(parts)

    return s
