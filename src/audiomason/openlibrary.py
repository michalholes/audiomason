from __future__ import annotations

from pathlib import Path
import json
import time
import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "https://openlibrary.org"
UA = "AudioMason/1.0 (https://github.com/michalholes/audiomason)"



# Disk cache (deterministic): AUDIOMASON_ROOT/_state/openlibrary_cache.json
_CACHE: dict[str, dict] | None = None

def _cache_path() -> Path | None:
    try:
        import os
        root = os.environ.get("AUDIOMASON_ROOT")
        if not root:
            return None
        return Path(root) / "_state" / "openlibrary_cache.json"
    except Exception:
        return None

def _cache_load() -> dict[str, dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    cp = _cache_path()
    if not cp or not cp.exists():
        _CACHE = {}
        return _CACHE
    try:
        raw = cp.read_text(encoding="utf-8")
        data = json.loads(raw)
        _CACHE = data if isinstance(data, dict) else {}
        return _CACHE
    except Exception:
        _CACHE = {}
        return _CACHE

def _cache_get(key: str) -> dict | None:
    c = _cache_load()
    v = c.get(key)
    return v if isinstance(v, dict) else None

def _cache_put(key: str, payload: dict) -> None:
    # respect dry-run: no cache writes
    try:
        import audiomason.state as state
        if getattr(getattr(state, "OPTS", None), "dry_run", False):
            return
    except Exception:
        pass

    cp = _cache_path()
    if not cp:
        return
    cp.parent.mkdir(parents=True, exist_ok=True)

    c = _cache_load()
    c[key] = payload

    tmp = cp.with_suffix(cp.suffix + ".tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(cp)


@dataclass(frozen=True)
class OLResult:
    ok: bool
    status: str
    hits: int
    top: str | None = None


def _get_json(path: str, params: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    qs = urlencode(params)
    url = f"{BASE}{path}?{qs}"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def validate_author(name: str) -> OLResult:
    q = (name or "").strip()
    if not q:
        return OLResult(False, "author:empty", 0, None)

    ck = "author:" + q
    hit = _cache_get(ck)
    if hit is not None:
        return OLResult(bool(hit.get("ok")), str(hit.get("status")), int(hit.get("hits") or 0), hit.get("top"))

    try:
        data = _get_json("/search/authors.json", {"q": q, "limit": 5})
    except Exception as e:
        return OLResult(False, f"author:error:{type(e).__name__}", 0, None)

    hits = int(data.get("numFound") or 0)
    docs = data.get("docs") or []
    top = None
    if docs:
        top = str(docs[0].get("name") or "") or None

    if hits == 0:
        _cache_put(ck, {"ok": False, "status": "author:not_found", "hits": 0, "top": top})
        return OLResult(False, "author:not_found", 0, top)

    _cache_put(ck, {"ok": True, "status": "author:ok", "hits": hits, "top": top})
    return OLResult(True, "author:ok", hits, top)


def _norm_title(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _best_title_suggestion(entered: str, titles: list[str]) -> tuple[str | None, float, float]:
    n0 = _norm_title(entered)
    if not n0:
        return (None, 0.0, 0.0)
    scored: list[tuple[float, str]] = []
    seen = set()
    for t in titles:
        tt = (t or "").strip()
        if not tt:
            continue
        nt = _norm_title(tt)
        if not nt or nt in seen:
            continue
        seen.add(nt)
        scored.append((difflib.SequenceMatcher(None, n0, nt).ratio(), tt))
    if not scored:
        return (None, 0.0, 0.0)
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_title = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    return (best_title, float(best_score), float(second_score))


def validate_book(author: str, title: str) -> OLResult:
    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return OLResult(False, "book:empty", 0, None)

    ck = f"book:{a}|{t}"
    hit = _cache_get(ck)
    if hit is not None:
        return OLResult(bool(hit.get("ok")), str(hit.get("status")), int(hit.get("hits") or 0), hit.get("top"))

    # Explicit fields due to /search.json default field changes.
    params = {
        "title": t,
        "author": a,
        "limit": 5,
        "fields": "key,title,author_name,first_publish_year",
    }

    # Be polite (avoid bursts); deterministic delay.
    time.sleep(0.2)

    try:
        data = _get_json("/search.json", params)
    except Exception as e:
        return OLResult(False, f"book:error:{type(e).__name__}", 0, None)

    hits = int(data.get("numFound") or 0)
    docs = data.get("docs") or []
    top = None
    if docs:
        top = str(docs[0].get("title") or "") or None
    if hits == 0:
        # Guarded fuzzy suggestion: secondary search by title text (q) + author filter.
        # Deterministic + safe-by-default: require strong score and clear gap.
        if top is None:
            try:
                time.sleep(0.2)
                data2 = _get_json("/search.json", {"q": t, "limit": 50, "fields": "title,author_name"})
                docs2 = data2.get("docs") or []
                a_norm = _norm_title(a)
                titles: list[str] = []
                for d in docs2:
                    if not isinstance(d, dict):
                        continue
                    ans = d.get("author_name")
                    if isinstance(ans, list):
                        if a_norm and not any(_norm_title(str(x)) == a_norm for x in ans if x is not None):
                            continue
                    elif isinstance(ans, str):
                        if a_norm and _norm_title(ans) != a_norm:
                            continue
                    elif a_norm:
                        continue
                    titles.append(str(d.get("title") or ""))

                sug, best, second = _best_title_suggestion(t, titles)
                if sug and best >= 0.92 and (best - second) >= 0.03:
                    top = sug
            except Exception:
                pass

        _cache_put(ck, {"ok": False, "status": "book:not_found", "hits": 0, "top": top})
        return OLResult(False, "book:not_found", 0, top)

    _cache_put(ck, {"ok": True, "status": "book:ok", "hits": hits, "top": top})
    return OLResult(True, "book:ok", hits, top)
