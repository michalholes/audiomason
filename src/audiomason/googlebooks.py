from __future__ import annotations

import asyncio
import difflib
import json
import re
import threading
import time
import unicodedata
from collections.abc import Mapping
from typing import cast

import httpx

BASE = "https://www.googleapis.com/books/v1"
UA = "AudioMason/1.0 (https://github.com/michalholes/audiomason)"


def _dry_run() -> bool:
    try:
        import audiomason.state as state

        return state.OPTS is not None and state.OPTS.dry_run
    except Exception:
        return False


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    stop = {
        "a",
        "i",
        "v",
        "vo",
        "na",
        "do",
        "od",
        "po",
        "pri",
        "ku",
        "k",
        "z",
        "zo",
        "s",
        "so",
        "u",
    }
    toks = [t for t in s.split(" ") if t and t not in stop]
    s = " ".join(toks).strip()
    return s


def _author_match(author: str, authors: object) -> bool:
    a = _norm(author)
    if not a:
        return False
    vals: list[str] = []
    if isinstance(authors, list):
        vals = [str(x) for x in cast(list[object], authors) if x is not None]
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


def _norm_params(params: Mapping[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in params.items():
        try:
            out[str(k)] = str(v)
        except Exception:
            out[str(k)] = ""
    return out


def _get_json(path: str, params: Mapping[str, object], timeout: float = 10.0) -> dict[str, object]:
    url = f"{BASE}{path}"
    headers = {"User-Agent": UA, "Accept": "application/json"}
    delay_s = max(0, int(_goog_host_delay_ms)) / 1000.0
    if delay_s:
        time.sleep(delay_s)
    with httpx.Client(headers=headers, timeout=timeout) as client:
        resp = client.get(url, params=_norm_params(params))
        resp.raise_for_status()
        raw = resp.text
    return cast(dict[str, object], json.loads(raw))


# Per-host guard shared across loops (limit 1 to avoid 429)
_goog_host_sem = threading.Semaphore(1)
_goog_host_delay_ms = 0


class _HostGuardAsync:
    def __init__(self, sem: threading.Semaphore):
        self._sem = sem

    async def __aenter__(self) -> None:
        await asyncio.to_thread(self._sem.acquire)

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self._sem.release()


def set_host_limit(n: int) -> None:  # noqa: N802
    global _goog_host_sem
    _goog_host_sem = threading.Semaphore(max(1, int(n)))


def set_host_delay_ms(n: int) -> None:  # noqa: N802
    global _goog_host_delay_ms
    _goog_host_delay_ms = max(0, int(n))


async def _get_json_async(
    path: str, params: Mapping[str, object], timeout: float = 10.0
) -> dict[str, object]:
    url = f"{BASE}{path}"
    headers = {"User-Agent": UA, "Accept": "application/json"}
    # Per-host guard (1 in-flight) to avoid 429
    _sem = _goog_host_sem
    delay_s = max(0, int(_goog_host_delay_ms)) / 1000.0
    if delay_s:
        await asyncio.sleep(delay_s)
    async with _HostGuardAsync(_sem), httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        resp = await client.get(url, params=_norm_params(params))
        resp.raise_for_status()
        raw = resp.text
    return cast(dict[str, object], json.loads(raw))


async def suggest_title_async(author: str, title: str) -> str | None:
    if _dry_run():
        return None

    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return None

    q = f"intitle:{t} inauthor:{a}"
    fields = "items(volumeInfo/title,volumeInfo/authors,volumeInfo/language)"

    for lang in ("cs", "sk"):
        try:
            data = await _get_json_async(
                "/volumes",
                {
                    "q": q,
                    "maxResults": 20,
                    "langRestrict": lang,
                    "printType": "books",
                    "fields": fields,
                },
            )
        except Exception:
            continue
        raw_items_obj = data.get("items")
        raw_items: list[object] = (
            cast(list[object], raw_items_obj) if isinstance(raw_items_obj, list) else []
        )

        filtered: list[dict[str, object]] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            it_dict = cast(dict[str, object], it)
            vi_raw = it_dict.get("volumeInfo")
            vi: dict[str, object] = (
                cast(dict[str, object], vi_raw) if isinstance(vi_raw, dict) else {}
            )
            if str(vi.get("language") or "").strip().lower() != lang:
                continue
            filtered.append(it_dict)

        best = _pick_best(t, a, filtered)
        if best:
            return best

    return None


def _sort_key(item: tuple[float, str]) -> tuple[float, str]:
    return (-item[0], item[1])


def _pick_best(entered_title: str, author: str, items: list[dict[str, object]]) -> str | None:
    t0 = _norm(entered_title)
    if not t0:
        return None

    cand: list[tuple[float, str]] = []
    for it in items:
        vi_raw = it.get("volumeInfo")
        vi: dict[str, object] = cast(dict[str, object], vi_raw) if isinstance(vi_raw, dict) else {}
        title = str(vi.get("title") or "").strip()
        if not title:
            continue
        if not _author_match(author, vi.get("authors")):
            continue
        sc = difflib.SequenceMatcher(None, t0, _norm(title)).ratio()
        cand.append((sc, title))

    if not cand:
        return None

    cand.sort(key=_sort_key)
    best_s, best_t = cand[0]
    second_s = cand[1][0] if len(cand) > 1 else 0.0

    if best_s >= 0.92 and (best_s - second_s) >= 0.03:
        return best_t

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
    if _dry_run():
        return None

    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return None

    q = f"intitle:{t} inauthor:{a}"
    fields = "items(volumeInfo/title,volumeInfo/authors,volumeInfo/language)"

    for lang in ("cs", "sk"):
        time.sleep(0.2)
        try:
            data = _get_json(
                "/volumes",
                {
                    "q": q,
                    "maxResults": 20,
                    "langRestrict": lang,
                    "printType": "books",
                    "fields": fields,
                },
            )
        except Exception:
            continue
        raw_items_obj = data.get("items")
        raw_items: list[object] = (
            cast(list[object], raw_items_obj) if isinstance(raw_items_obj, list) else []
        )

        filtered: list[dict[str, object]] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            it_dict = cast(dict[str, object], it)
            vi_raw = it_dict.get("volumeInfo")
            vi: dict[str, object] = (
                cast(dict[str, object], vi_raw) if isinstance(vi_raw, dict) else {}
            )
            if str(vi.get("language") or "").strip().lower() != lang:
                continue
            filtered.append(it_dict)

        best = _pick_best(t, a, filtered)
        if best:
            return best

    return None
