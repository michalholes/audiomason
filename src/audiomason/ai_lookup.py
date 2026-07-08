from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast
from urllib.request import Request, urlopen

from audiomason.util import strip_diacritics

DEFAULT_AI_CFG: dict[str, object] = {
    "enabled": False,
    "provider": "openai_compatible",
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o-mini",
    "api_key_env": "OPENAI_API_KEY",
    "timeout_s": 20,
    "temperature": 0,
    "max_tokens": 80,
}

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
        data: object = _json_load_object(raw)
        if not isinstance(data, dict):
            _cache = {}
            return _cache
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
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    msg = first.get("message")
    if not isinstance(msg, dict):
        return None
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

    suggestion = data.get("suggestion") or data.get("title") or data.get("author")
    if not isinstance(suggestion, str):
        return (
            None,
            float(data.get("confidence") or 0.0)
            if isinstance(data.get("confidence"), (int, float))
            else 0.0,
        )

    confidence = data.get("confidence")
    if isinstance(confidence, (int, float)):
        return (suggestion.strip() or None, float(confidence))
    return (suggestion.strip() or None, 1.0)


def _call_ai(kind: str, prompt: str, cfg: Mapping[str, object] | None) -> str | None:
    if not _enabled(cfg):
        return None
    if _dry_run():
        return _cache_get(_cache_key(kind, cfg, prompt))

    eff = _effective_cfg(cfg)
    endpoint = str(eff.get("endpoint") or DEFAULT_AI_CFG["endpoint"])
    model = str(eff.get("model") or DEFAULT_AI_CFG["model"])
    timeout_raw = eff.get("timeout_s")
    timeout = _float_value(timeout_raw, 20.0)
    api_key = _api_key(cfg)
    if not api_key:
        return _cache_get(_cache_key(kind, cfg, prompt))

    cache_key = _cache_key(kind, cfg, prompt)
    hit = _cache_get(cache_key)
    if hit is not None:
        return hit or None

    body = {
        "model": model,
        "temperature": _float_value(eff.get("temperature"), 0.0),
        "max_tokens": _int_value(eff.get("max_tokens"), 80),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON with keys suggestion and confidence. "
                    "Suggestion must be ASCII-only and concise. "
                    "If unsure, return an empty suggestion."
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
        time.sleep(0.2)
        raw = _request_text(req, timeout)
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
        suggestion = _sanitize_suggestion(prompt, suggestion)
        _cache_put(cache_key, suggestion)
        return suggestion
    except Exception:
        return _cache_get(cache_key)


def suggest_author(name: str, cfg: Mapping[str, object] | None = None) -> str | None:
    q = (name or "").strip()
    if not q:
        return None
    prompt = (
        "Normalize this audiobook author name to an ASCII-only canonical form. "
        'Return JSON: {"suggestion": "...", "confidence": 0.0-1.0}. '
        f"Author: {q}"
    )
    return _call_ai("author", prompt, cfg)


def suggest_title(author: str, title: str, cfg: Mapping[str, object] | None = None) -> str | None:
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
    return _call_ai("title", prompt, cfg)
