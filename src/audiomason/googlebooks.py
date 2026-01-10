from __future__ import annotations

import difflib
import json
import re
import time
import unicodedata
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.googleapis.com/books/v1"
UA = "AudioMason/1.0 (https://github.com/michalholes/audiomason)"


def _dry_run() -> bool:
    try:
        import audiomason.state as state
        return bool(getattr(getattr(state, "OPTS", None), "dry_run", False))
    except Exception:
        return False


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    # deterministic token normalization (helps minor CZ/SK preposition diffs)
    stop = {"a","i","v","vo","na","do","od","po","pri","ku","k","z","zo","s","so","u"}
    toks = [t for t in s.split(" ") if t and t not in stop]
    s = " ".join(toks).strip()
    return s


def _author_match(author: str, authors: object) -> bool:
    a = _norm(author)
    if not a:
        return False
    vals: list[str] = []
    if isinstance(authors, list):
        vals = [str(x) for x in authors if x is not None]
    elif isinstance(authors, str):
        vals = [authors]
    else:
        return False
    for v in vals:
        nv = _norm(v)
        if not nv:
            continue
        if nv == a or a in nv or nv in a:
            return True
    return False


def _get_json(path: str, params: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    qs = urlencode(params)
    url = f"{BASE}{path}?{qs}"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _pick_best(entered_title: str, author: str, items: list[dict[str, Any]]) -> str | None:
    t0 = _norm(entered_title)
    if not t0:
        return None

    cand: list[tuple[float, str]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        vi = it.get("volumeInfo") if isinstance(it.get("volumeInfo"), dict) else {}
        title = str(vi.get("title") or "").strip()
        if not title:
            continue
        if not _author_match(author, vi.get("authors")):
            continue
        sc = difflib.SequenceMatcher(None, t0, _norm(title)).ratio()
        cand.append((sc, title))

    if not cand:
        return None

    cand.sort(key=lambda x: (-x[0], x[1]))
    best_s, best_t = cand[0]
    second_s = cand[1][0] if len(cand) > 1 else 0.0

    # conservative guard (same as OL): strong + clear gap
    if best_s >= 0.92 and (best_s - second_s) >= 0.03:
        return best_t

    # Special-case: multiple perfect/near-perfect matches (often diacritics variants).
    # Still safe: require extremely high score, then deterministically prefer diacritics.
    if best_s >= 0.98:
        top = [t for (sc, t) in cand if sc >= 0.98]
        if len(top) >= 2:
            def _dia_score(x: str) -> tuple[int, int, str]:
                non_ascii = sum(1 for ch in x if ord(ch) > 127)
                return (non_ascii, len(x), x)
            top.sort(key=_dia_score, reverse=True)
            return top[0]

    return None


def suggest_title(author: str, title: str) -> str | None:
    # No network calls in --dry-run
    if _dry_run():
        return None

    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return None

    # deterministic, limited, language-restricted
    q = f'intitle:{t} inauthor:{a}'
    fields = "items(volumeInfo/title,volumeInfo/authors,volumeInfo/language)"

    for lang in ("cs", "sk"):
        # be polite; deterministic delay
        time.sleep(0.2)
        try:
            data = _get_json("/volumes", {
                "q": q,
                "maxResults": 20,
                "langRestrict": lang,
                "printType": "books",
                "fields": fields,
            })
        except Exception:
            continue
        items = data.get("items") or []
        if not isinstance(items, list):
            continue

        # keep only matching language (defensive; langRestrict should already do it)
        filtered: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            vi = it.get("volumeInfo") if isinstance(it.get("volumeInfo"), dict) else {}
            if str(vi.get("language") or "").strip().lower() != lang:
                continue
            filtered.append(it)

        best = _pick_best(t, a, filtered)
        if best:
            return best

    return None
