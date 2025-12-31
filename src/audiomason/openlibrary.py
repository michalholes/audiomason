from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "https://openlibrary.org"
UA = "AudioMason/1.0 (https://github.com/michalholes/audiomason)"


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
        return OLResult(False, "author:not_found", 0, top)
    return OLResult(True, "author:ok", hits, top)


def validate_book(author: str, title: str) -> OLResult:
    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return OLResult(False, "book:empty", 0, None)

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
        return OLResult(False, "book:not_found", 0, top)
    return OLResult(True, "book:ok", hits, top)
