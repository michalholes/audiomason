from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from audiomason.util import out, strip_diacritics

DEFAULT_AI_CFG: dict[str, object] = {
    "enabled": False,
    "provider": "openai_compatible",
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o-mini",
    "api_key_env": "OPENAI_API_KEY",
    "timeout_s": 20,
    "temperature": 0,
    "max_completion_tokens": 80,
}

MAX_AI_ATTEMPTS = 4
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class BatchMetadataSuggestions:
    source_author: str | None
    book_titles: dict[str, str]


_cache: dict[str, str | None] | None = None


class _ReadableResponse(Protocol):
    def __enter__(self) -> _ReadableResponse: ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None: ...

    def read(self) -> bytes: ...


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _json_load_object(raw: str) -> object:
    return cast(object, json.loads(raw))


def _request_text(req: Request, timeout: float) -> str:
    response = cast(_ReadableResponse, urlopen(req, timeout=timeout))
    with response as r:
        raw_bytes = r.read()
    return raw_bytes.decode("utf-8", errors="replace")


def _retry_after_seconds(exc: HTTPError, attempt: int) -> float:
    delay = 1.0
    for _ in range(max(attempt - 1, 0)):
        delay *= 2.0
    return delay


def _request_text_with_retries(req: Request, timeout: float) -> str:
    for attempt in range(1, MAX_AI_ATTEMPTS + 1):
        try:
            return _request_text(req, timeout)
        except HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_STATUSES or attempt >= MAX_AI_ATTEMPTS:
                raise
            delay = _retry_after_seconds(exc, attempt)
            out(f"[ai] retry {attempt + 1}/{MAX_AI_ATTEMPTS} after {delay:.1f}s (HTTP {exc.code})")
            time.sleep(delay)
    raise RuntimeError("unreachable")


def _cfg_path() -> Path | None:
    try:
        root = os.environ.get("AUDIOMASON_ROOT")
        if not root:
            return None
        return Path(root) / "_state" / "ai_lookup_cache.json"
    except Exception:
        return None


def _cache_load() -> dict[str, str | None]:
    global _cache
    if _cache is not None:
        return _cache
    cp = _cfg_path()
    if not cp or not cp.exists():
        _cache = {}
        return _cache
    try:
        raw = cp.read_text(encoding="utf-8")
        data_obj = _json_load_object(raw)
        if not isinstance(data_obj, dict):
            _cache = {}
            return _cache
        data = cast(dict[str, object], data_obj)
        out: dict[str, str | None] = {}
        for k, v in data.items():
            out[str(k)] = str(v) if isinstance(v, str) else None
        _cache = out
        return _cache
    except Exception:
        _cache = {}
        return _cache


def _cache_get(key: str) -> str | None:
    return _cache_load().get(key)


def _cache_put(key: str, suggestion: str | None) -> None:
    try:
        import audiomason.state as state

        if state.OPTS is not None and state.OPTS.dry_run:
            return
    except Exception:
        pass

    cp = _cfg_path()
    if not cp:
        return
    cp.parent.mkdir(parents=True, exist_ok=True)
    c = _cache_load()
    c[key] = suggestion
    tmp = cp.with_suffix(cp.suffix + ".tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(cp)


def _artifact_path(artifact_dir: Path | None, kind: str, cache_key: str) -> Path | None:
    if artifact_dir is None:
        return None
    return artifact_dir / "_ai" / f"{kind}-{cache_key}.raw.json"


def _write_artifact(artifact_dir: Path | None, kind: str, cache_key: str, raw: str) -> None:
    path = _artifact_path(artifact_dir, kind, cache_key)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
    except Exception:
        pass


def _dry_run() -> bool:
    try:
        import audiomason.state as state

        return state.OPTS is not None and state.OPTS.dry_run
    except Exception:
        return False


def _normalize(s: str) -> str:
    s = strip_diacritics((s or "").strip())
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def _sanitize_suggestion(entered: str, suggested: str | None) -> str | None:
    if not suggested:
        return None
    out = strip_diacritics(str(suggested)).strip()
    out = re.sub(r"\s+", " ", out).strip()
    if not out:
        return None
    if _normalize(out) == _normalize(entered):
        return None
    return out


def _clean_ascii_text(s: str) -> str | None:
    out = strip_diacritics((s or "").strip())
    out = re.sub(r"\s+", " ", out).strip()
    return out or None


def _float_value(value: object, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return default
    return default


def _int_value(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except Exception:
            return default
    return default


def _effective_cfg(cfg: Mapping[str, object] | None) -> dict[str, object]:
    out = dict(DEFAULT_AI_CFG)
    if cfg is None:
        return out
    raw = _as_dict(cfg.get("ai"))
    out.update(raw)
    return out


def _enabled(cfg: Mapping[str, object] | None) -> bool:
    if cfg is None:
        try:
            import audiomason.state as state

            return bool(state.OPTS is not None and state.OPTS.ai_lookup)
        except Exception:
            return False
    if "_ai_enabled" in cfg:
        return bool(cfg.get("_ai_enabled"))
    raw = _as_dict(cfg.get("ai"))
    return bool(raw.get("enabled", False))


def _api_key(cfg: Mapping[str, object] | None) -> str | None:
    raw = _effective_cfg(cfg)
    api_key_env = str(raw.get("api_key_env") or "OPENAI_API_KEY")
    direct = raw.get("api_key")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    env_val = os.environ.get(api_key_env)
    return env_val.strip() if isinstance(env_val, str) and env_val.strip() else None


def _cache_key(kind: str, cfg: Mapping[str, object] | None, *parts: str) -> str:
    eff = _effective_cfg(cfg)
    payload = {
        "kind": kind,
        "provider": str(eff.get("provider") or "openai_compatible"),
        "endpoint": str(eff.get("endpoint") or ""),
        "model": str(eff.get("model") or ""),
        "parts": list(parts),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _extract_content(raw: object) -> str | None:
    if not isinstance(raw, dict):
        return None
    raw = cast(dict[str, object], raw)
    choices_obj = raw.get("choices")
    if not isinstance(choices_obj, list) or not choices_obj:
        return None
    choices = cast(list[object], choices_obj)
    first_obj = choices[0]
    if not isinstance(first_obj, dict):
        return None
    first = cast(dict[str, object], first_obj)
    msg = first.get("message")
    if not isinstance(msg, dict):
        return None
    msg = cast(dict[str, object], msg)
    content = msg.get("content")
    return str(content) if isinstance(content, str) else None


def _parse_json_suggestion(content: str) -> tuple[str | None, float]:
    txt = content.strip()
    if not txt:
        return (None, 0.0)
    if txt.startswith("```"):
        txt = re.sub(r"^```(?:json)?\s*", "", txt, flags=re.I)
        txt = re.sub(r"\s*```$", "", txt)
    try:
        data: object = json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if m is None:
            return (txt, 0.0)
        try:
            data = json.loads(m.group(0))
        except Exception:
            return (txt, 0.0)

    if isinstance(data, str):
        return (data.strip() or None, 1.0)
    if not isinstance(data, dict):
        return (None, 0.0)
    data = cast(dict[str, object], data)

    suggestion = data.get("suggestion") or data.get("title") or data.get("author")
    if not isinstance(suggestion, str):
        confidence_raw = data.get("confidence")
        return (
            None,
            float(confidence_raw) if isinstance(confidence_raw, (int, float)) else 0.0,
        )

    confidence = data.get("confidence")
    if isinstance(confidence, (int, float)):
        return (suggestion.strip() or None, float(confidence))
    return (suggestion.strip() or None, 1.0)


def _call_ai(
    kind: str,
    prompt: str,
    entered: str,
    cfg: Mapping[str, object] | None,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> str | None:
    if not _enabled(cfg):
        return None
    if _dry_run():
        return _cache_get(_cache_key(kind, cfg, entered, context or ""))

    eff = _effective_cfg(cfg)
    endpoint = str(eff.get("endpoint") or DEFAULT_AI_CFG["endpoint"])
    model = str(eff.get("model") or DEFAULT_AI_CFG["model"])
    timeout_raw = eff.get("timeout_s")
    timeout = _float_value(timeout_raw, 20.0)
    api_key = _api_key(cfg)
    if not api_key:
        return _cache_get(_cache_key(kind, cfg, entered, context or ""))

    cache_key = _cache_key(kind, cfg, entered, context or "")
    hit = _cache_get(cache_key)
    if hit is not None:
        return hit or None

    user_prompt = prompt
    if context:
        user_prompt = prompt + "\n\nContext:\n" + context.strip()

    body = {
        "model": model,
        "temperature": _float_value(eff.get("temperature"), 0.0),
        "max_completion_tokens": _int_value(
            eff.get("max_completion_tokens"),
            _int_value(eff.get("max_tokens"), 80),
        ),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON with keys suggestion and confidence. "
                    "Suggestion must be ASCII-only and concise. "
                    "If unsure, return an empty suggestion."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
    }
    req = Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        out(f"[ai] ask {kind}: '{entered}'")
        time.sleep(0.2)
        raw = _request_text_with_retries(req, timeout)
        _write_artifact(artifact_dir, kind, cache_key, raw)
        data: object = _json_load_object(raw)
        content = _extract_content(data)
        if not content:
            _cache_put(cache_key, None)
            return None
        suggestion, confidence = _parse_json_suggestion(content)
        if suggestion is None:
            _cache_put(cache_key, None)
            return None
        if confidence and confidence < 0.8:
            _cache_put(cache_key, None)
            return None
        suggestion = _sanitize_suggestion(entered, suggestion)
        _cache_put(cache_key, suggestion)
        return suggestion
    except HTTPError as exc:
        out(f"[ai] failed {kind}: HTTP {exc.code}")
        return _cache_get(cache_key)
    except Exception:
        out(f"[ai] failed {kind}: unavailable")
        return _cache_get(cache_key)


def suggest_author(
    name: str,
    cfg: Mapping[str, object] | None = None,
    *,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> str | None:
    q = (name or "").strip()
    if not q:
        return None
    prompt = (
        "Normalize this audiobook author name to an ASCII-only canonical form. "
        'Return JSON: {"suggestion": "...", "confidence": 0.0-1.0}. '
        f"Author: {q}"
    )
    return _call_ai("author", prompt, q, cfg, context=context, artifact_dir=artifact_dir)


def suggest_title(
    author: str,
    title: str,
    cfg: Mapping[str, object] | None = None,
    *,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> str | None:
    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return None
    prompt = (
        "Normalize this audiobook title to an ASCII-only canonical form. "
        "Keep the meaning and language of the original title. "
        'Return JSON: {"suggestion": "...", "confidence": 0.0-1.0}. '
        f"Author: {a}\nTitle: {t}"
    )
    return _call_ai("title", prompt, t, cfg, context=context, artifact_dir=artifact_dir)


def _parse_batch_payload(content: str) -> dict[str, object] | None:
    txt = content.strip()
    if not txt:
        return None
    if txt.startswith("```"):
        txt = re.sub(r"^```(?:json)?\s*", "", txt, flags=re.I)
        txt = re.sub(r"\s*```$", "", txt)
    data_obj: object
    try:
        data_obj = json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if m is None:
            return None
        try:
            data_obj = json.loads(m.group(0))
        except Exception:
            return None
    if not isinstance(data_obj, dict):
        return None
    return cast(dict[str, object], data_obj)


def _batch_suggestions_from_payload(payload: object) -> BatchMetadataSuggestions | None:
    if not isinstance(payload, dict):
        return None
    data = cast(dict[str, object], payload)

    source_author_raw = data.get("source_author")
    source_author = (
        _clean_ascii_text(source_author_raw) if isinstance(source_author_raw, str) else None
    )

    book_titles: dict[str, str] = {}
    books_raw = data.get("books")
    if isinstance(books_raw, list):
        for item_obj in cast(list[object], books_raw):
            if not isinstance(item_obj, dict):
                continue
            item = cast(dict[str, object], item_obj)
            label = str(item.get("label") or "").strip()
            title_raw = item.get("title")
            if not label or not isinstance(title_raw, str):
                continue
            title = _clean_ascii_text(title_raw)
            if title:
                book_titles[label] = title

    return BatchMetadataSuggestions(source_author=source_author, book_titles=book_titles)


def suggest_batch_defaults(
    source_name: str,
    books: Sequence[Mapping[str, object]],
    cfg: Mapping[str, object] | None = None,
    *,
    artifact_dir: Path | None = None,
) -> BatchMetadataSuggestions | None:
    if not _enabled(cfg):
        return None

    source = _clean_ascii_text(source_name)
    if not source:
        return None

    batch_books: list[dict[str, object]] = []
    for b in books:
        label = str(b.get("label") or "").strip()
        if not label:
            continue
        default_title = str(b.get("default_title") or "").strip()
        group_root = str(b.get("group_root") or "").strip()
        root_audio = bool(b.get("root_audio"))
        audio_files: list[str] = []
        raw_files = b.get("audio_files")
        if isinstance(raw_files, list):
            for item in cast(list[object], raw_files):
                if isinstance(item, str) and item.strip():
                    audio_files.append(item.strip())
        id3_samples: list[dict[str, str]] = []
        raw_id3 = b.get("id3")
        if isinstance(raw_id3, list):
            for item in cast(list[object], raw_id3):
                if not isinstance(item, dict):
                    continue
                sample: dict[str, str] = {}
                for k, v in cast(dict[str, object], item).items():
                    if isinstance(v, str):
                        vv = v.strip()
                        if vv:
                            sample[str(k)] = vv
                if sample:
                    id3_samples.append(sample)
        batch_books.append(
            {
                "label": label,
                "default_title": default_title,
                "group_root": group_root,
                "root_audio": root_audio,
                "audio_files": audio_files,
                "id3": id3_samples,
            }
        )

    if not batch_books:
        return None

    payload = {"source_name": source_name, "books": batch_books}
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    cache_key = _cache_key("batch", cfg, source, payload_json)

    cached = _cache_get(cache_key)
    if cached is not None:
        cached_obj = _parse_batch_payload(cached)
        return _batch_suggestions_from_payload(cached_obj)

    eff = _effective_cfg(cfg)
    endpoint = str(eff.get("endpoint") or DEFAULT_AI_CFG["endpoint"])
    model = str(eff.get("model") or DEFAULT_AI_CFG["model"])
    timeout = _float_value(eff.get("timeout_s"), 20.0)
    api_key = _api_key(cfg)
    if not api_key:
        return None

    prompt = (
        "Normalize selected audiobook metadata. Return only JSON with keys "
        "source_author and books. "
        "source_author must be an ASCII-only string or null. books must be a list of objects with "
        "label and title. Each label must match an input label exactly. Do not invent new labels. "
        "Normalize titles to ASCII. If present, id3 contains read-only hints from existing MP3 "
        "tags and may help disambiguate titles. "
        "Input:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    body = {
        "model": model,
        "temperature": _float_value(eff.get("temperature"), 0.0),
        "max_completion_tokens": _int_value(
            eff.get("max_completion_tokens"),
            _int_value(eff.get("max_tokens"), 80),
        ),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON with keys source_author and books. "
                    "books must contain the same labels as the input. "
                    "All suggestions must be ASCII-only. Existing id3 fields are read-only hints "
                    "only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    req = Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        out(f"[ai] ask batch: source='{source}' books={len(batch_books)}")
        time.sleep(0.2)
        raw = _request_text_with_retries(req, timeout)
        _write_artifact(artifact_dir, "batch", cache_key, raw)
        data = _json_load_object(raw)
        content = _extract_content(data)
        if not content:
            _cache_put(cache_key, None)
            return None
        obj = _parse_batch_payload(content)
        if obj is None:
            _cache_put(cache_key, None)
            return None

        result = _batch_suggestions_from_payload(obj)
        if result is None:
            _cache_put(cache_key, None)
            return None
        cache_payload = {
            "source_author": result.source_author,
            "books": [
                {"label": label, "title": title}
                for label, title in sorted(result.book_titles.items())
            ],
        }
        _cache_put(cache_key, json.dumps(cache_payload, ensure_ascii=False, sort_keys=True))
        return result
    except HTTPError as exc:
        out(f"[ai] failed batch: HTTP {exc.code}")
        cached_after = _cache_get(cache_key)
        if cached_after is None:
            return None
        cached_obj = _parse_batch_payload(cached_after)
        return _batch_suggestions_from_payload(cached_obj)
    except Exception:
        out("[ai] failed batch: unavailable")
        return None
