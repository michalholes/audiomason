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
from audiomason.util import strip_diacritics
from audiomason.googlebooks import suggest_title


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
        top = _sanitize_title_suggestion(t, top)

        _cache_put(ck, {"ok": False, "status": "author:not_found", "hits": 0, "top": top})
        return OLResult(False, "author:not_found", 0, top)

    top = _sanitize_title_suggestion(t, top)

    _cache_put(ck, {"ok": True, "status": "author:ok", "hits": hits, "top": top})
    return OLResult(True, "author:ok", hits, top)


def _norm_title(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _sanitize_title_suggestion(entered: str, suggested: str | None) -> str | None:
    """No-diacritics suggestion, and suppress suggestion if it matches entered."""
    if not suggested:
        return None
    ss = strip_diacritics(str(suggested)).strip()
    ss = re.sub(r"\s+", " ", ss).strip()
    if not ss:
        return None
    if _norm_title(ss) == _norm_title(entered):
        return None
    return ss

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


def _fallback_q(title: str) -> str:
    s = (title or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"\b\d+\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _author_match(author: str, author_name: object) -> bool:
    a = _norm_title(author)
    if not a:
        return False
    vals: list[str] = []
    if isinstance(author_name, list):
        vals = [str(x) for x in author_name if x is not None]
    elif isinstance(author_name, str):
        vals = [author_name]
    else:
        return False
    for v in vals:
        nv = _norm_title(v)
        if not nv:
            continue
        if nv == a or a in nv or nv in a:
            return True
    return False


def _lang_codes(lang_obj: object) -> set[str]:
    out: set[str] = set()
    items = lang_obj if isinstance(lang_obj, list) else [lang_obj]
    for it in items:
        if isinstance(it, dict):
            k = str(it.get("key") or "")
            if k.startswith("/languages/"):
                out.add(k.split("/languages/", 1)[1])
        elif isinstance(it, str) and it.startswith("/languages/"):
            out.add(it.split("/languages/", 1)[1])
    return out


def _pick_edition_title(work_key: str, prefer: list[str]) -> str | None:
    if not work_key.startswith("/works/"):
        return None
    try:
        time.sleep(0.2)
        data = _get_json(work_key + "/editions.json", {"limit": 50, "fields": "title,languages"})
        entries = data.get("entries") or []
        for code in prefer:
            for e in entries:
                if not isinstance(e, dict):
                    continue
                langs = _lang_codes(e.get("languages"))
                if code in langs:
                    t = str(e.get("title") or "").strip()
                    if t:
                        return t
    except Exception:
        return None
    return None


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
                q = _fallback_q(t)
                data2 = _get_json("/search.json", {"q": q, "limit": 50, "fields": "key,title,author_name"})
                docs2 = data2.get("docs") or []
                cand: list[tuple[float, str, str]] = []  # (score, title, key)
                for d in docs2:
                    if not isinstance(d, dict):
                        continue
                    if not _author_match(a, d.get("author_name")):
                        continue
                    key = str(d.get("key") or "").strip()
                    tt = str(d.get("title") or "").strip()
                    if not key or not tt:
                        continue
                    score = difflib.SequenceMatcher(None, _norm_title(t), _norm_title(tt)).ratio()
                    cand.append((score, tt, key))

                if cand:
                    # Prefer scoring against localized edition title (CZ/SK) when available.
                    cand.sort(key=lambda x: (-x[0], x[1], x[2]))
                    rescored: list[tuple[float, str]] = []
                    for _, tt, kk in cand[:5]:
                        loc = _pick_edition_title(kk, ["cze", "slo"])
                        sugg = loc or tt
                        score2 = difflib.SequenceMatcher(None, _norm_title(t), _norm_title(sugg)).ratio()
                        rescored.append((score2, sugg))
                    rescored.sort(key=lambda x: (-x[0], x[1]))
                    best_s, best_t = rescored[0]
                    second_s = rescored[1][0] if len(rescored) > 1 else 0.0
                    if best_t and best_s >= 0.92 and (best_s - second_s) >= 0.03:
                        top = best_t
            except Exception:
                pass

        # Fallback (CZ/SK): Google Books suggestion when OL has no safe suggestion.
        if top is None:
            try:
                g = suggest_title(a, t)
                if g:
                    top = g
            except Exception:
                pass

        top = _sanitize_title_suggestion(t, top)

        _cache_put(ck, {"ok": False, "status": "book:not_found", "hits": 0, "top": top})
        return OLResult(False, "book:not_found", 0, top)

    top = _sanitize_title_suggestion(t, top)

    _cache_put(ck, {"ok": True, "status": "book:ok", "hits": hits, "top": top})
    return OLResult(True, "book:ok", hits, top)
